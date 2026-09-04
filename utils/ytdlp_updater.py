"""yt-dlp'yi uygulamadan bağımsız, kendi kendine güncel tutan modül.

Uygulama derlenmiş bir .exe olduğu için içindeki yt-dlp gömülüdür ve
`pip` ile güncellenemez (kullanıcıda Python/pip yoktur). Bunun yerine:

  1. Açılışta (AĞ YOK, anında): daha önce indirilmiş daha yeni bir yt-dlp
     paketi varsa `sys.path`'in başına eklenerek gömülü sürüm yerine o
     kullanılır. Bu YÜZDEN `import yt_dlp`'den ÖNCE çağrılmalıdır.
  2. Arka planda (uygulamayı dondurmadan): PyPI'den en son yt-dlp sürümü
     kontrol edilir; daha yeniyse wheel (~3 MB saf Python) indirilip
     ayrıştırılır. Yeni sürüm BİR SONRAKİ açılışta devreye girer, çünkü
     çalışan bir Python modülü anlık olarak değiştirilemez.

Tüm ağ işlemleri hatalara karşı dayanıklıdır: internet yoksa ya da bir
sorun olursa sessizce gömülü yt-dlp'ye düşülür, uygulama asla çökmez.
"""

import os
import sys
import io
import shutil
import zipfile
import threading
import importlib.abc
import importlib.machinery

from packaging.version import parse as parse_version

from utils.helpers import APP_DIR

# İndirilen yt-dlp sürümlerinin saklandığı klasör (her sürüm kendi alt klasöründe)
CACHE_DIR = os.path.join(APP_DIR, 'ytdlp')
PYPI_URL = 'https://pypi.org/pypi/yt-dlp/json'


def _valid_version_dirs():
    """Cache içindeki geçerli (içinde yt_dlp paketi olan) sürüm klasörlerini
    (version_string, path) olarak döndürür, en yeniden eskiye sıralı."""
    results = []
    try:
        for name in os.listdir(CACHE_DIR):
            pkg_dir = os.path.join(CACHE_DIR, name)
            if os.path.isdir(os.path.join(pkg_dir, 'yt_dlp')):
                try:
                    results.append((parse_version(name), name, pkg_dir))
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    except Exception:
        pass
    results.sort(key=lambda t: t[0], reverse=True)
    return results


class _CacheYtdlpFinder(importlib.abc.MetaPathFinder):
    """`yt_dlp` ve alt modüllerini önbellekteki klasörden yükleyen meta-path
    bulucusu. `sys.meta_path`'in EN BAŞINA eklenir; böylece PyInstaller'ın
    gömülü modülleri bulan kendi bulucusundan (FrozenImporter) ÖNCE devreye
    girer. Sadece `sys.path` başına eklemek derlenmiş .exe'de yetmez, çünkü
    FrozenImporter sys.path'ten önce çalışır."""

    def __init__(self, pkg_dir):
        self._pkg_dir = pkg_dir

    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'yt_dlp':
            return importlib.machinery.PathFinder.find_spec(fullname, [self._pkg_dir])
        if fullname.startswith('yt_dlp.'):
            # Alt modüller ebeveynin __path__'inden (önbellek) çözülür
            return importlib.machinery.PathFinder.find_spec(fullname, path)
        return None


def activate_cached_ytdlp():
    """Önbellekte indirilmiş daha yeni bir yt-dlp varsa, gömülü sürüm yerine
    onu kullanmak için `sys.meta_path`'in başına bir bulucu ekler.

    `import yt_dlp` yapan HERHANGİ bir koddan ÖNCE çağrılmalıdır.
    Ağ kullanmaz, hata durumunda sessizce None döner.

    Dönüş: aktif edilen sürüm string'i ya da None (gömülü kullanılacaksa).
    """
    try:
        dirs = _valid_version_dirs()
        if not dirs:
            return None
        _, version_str, pkg_dir = dirs[0]
        # Aynı bulucu iki kez eklenmesin
        if not any(isinstance(f, _CacheYtdlpFinder) for f in sys.meta_path):
            sys.meta_path.insert(0, _CacheYtdlpFinder(pkg_dir))
        return version_str
    except Exception:
        return None


def _cleanup_old_versions(keep_path):
    """En yeni (aktif) sürüm dışındaki eski indirmeleri ve yarım kalan .tmp
    klasörlerini temizler."""
    try:
        for name in os.listdir(CACHE_DIR):
            path = os.path.join(CACHE_DIR, name)
            if path == keep_path:
                continue
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def _current_active_version():
    """Şu an kullanılan yt-dlp sürümünü döndürür (önbellek varsa o, yoksa
    gömülü). yt_dlp bu noktada zaten import edilmiş olur."""
    dirs = _valid_version_dirs()
    if dirs:
        return dirs[0][1]
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return None


def _do_update_check(on_updated=None):
    import requests  # zaten uygulama bağımlılığı

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

        # 1) PyPI'den en son sürümü ve wheel URL'sini al
        resp = requests.get(PYPI_URL, timeout=15)
        if resp.status_code != 200:
            return
        data = resp.json()
        latest = data['info']['version']

        current = _current_active_version()
        if current and parse_version(latest) <= parse_version(current):
            _cleanup_old_versions(_valid_version_dirs()[0][2] if _valid_version_dirs() else None)
            return  # zaten güncel

        # Zaten bu sürüm indirilmişse tekrar indirme
        target_dir = os.path.join(CACHE_DIR, latest)
        if os.path.isdir(os.path.join(target_dir, 'yt_dlp')):
            return

        # 2) Saf-python wheel dosyasını bul
        wheel_url = None
        for f in data['releases'].get(latest, []):
            if f['filename'].endswith('-py3-none-any.whl'):
                wheel_url = f['url']
                break
        if not wheel_url:
            return

        # 3) İndir (belleğe) ve geçici klasöre ayrıştır
        wheel_resp = requests.get(wheel_url, timeout=120)
        if wheel_resp.status_code != 200:
            return

        tmp_dir = os.path.join(CACHE_DIR, latest + '.tmp')
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(tmp_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(wheel_resp.content)) as z:
            z.extractall(tmp_dir)

        # yt_dlp paketi gerçekten geldi mi?
        if not os.path.isdir(os.path.join(tmp_dir, 'yt_dlp')):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return

        # 4) Atomik olarak yerine koy (aktif klasörle çakışmaz, ayrı isimde)
        shutil.rmtree(target_dir, ignore_errors=True)
        os.rename(tmp_dir, target_dir)

        # 5) Eskileri temizle (aktif olan bir sonraki açılışta bu olacak)
        _cleanup_old_versions(target_dir)

        print(f"yt-dlp {latest} indirildi, bir sonraki açılışta etkinleşecek.")
        if on_updated:
            try:
                on_updated(latest)
            except Exception:
                pass
    except Exception as e:
        # Ağ yok / API değişti / disk hatası vb. — sessizce gömülüye düş
        print(f"yt-dlp güncelleme kontrolü başarısız (gömülü sürüm kullanılıyor): {e}")


def get_active_version():
    """Şu an çalışan (import edilmiş) yt-dlp sürümünü döndürür ya da None."""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return None


def start_background_update(on_updated=None):
    """yt-dlp güncelleme kontrolünü arka planda (uygulamayı bloklamadan)
    başlatır. `on_updated(new_version)` isteğe bağlı olarak yeni bir sürüm
    indirildiğinde çağrılır."""
    t = threading.Thread(target=_do_update_check, args=(on_updated,), daemon=True)
    t.start()
    return t
