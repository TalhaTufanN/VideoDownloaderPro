"""WebView2 Runtime'ın kurulu olduğundan emin olur; değilse sessizce kurar.

Arayüz Windows'un WebView2 (Edge) motorunu kullanır. Win10/11'de bu motor
neredeyse her zaman önceden yüklü gelir. Yine de kullanıcının hiçbir şey
kurmak zorunda kalmaması için:

  1. Kayıt defterinden runtime kurulu mu diye bakılır.
  2. Kurulu değilse:
     - Uygulamayla birlikte gelen (bundle) 'MicrosoftEdgeWebview2Setup.exe'
       varsa o çalıştırılır (çevrimdışı kurulum),
     - yoksa Microsoft'un resmi Evergreen bootstrapper'ı indirilip sessizce
       kurulur.

Herhangi bir hata olursa sessizce geçilir; uygulama yine de açılmayı dener.
"""

import os
import subprocess
import tempfile

from utils.helpers import resource_path

# WebView2 Runtime'ın EdgeUpdate istemci GUID'i
_CLIENT = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
# Microsoft resmi Evergreen bootstrapper (kalıcı kısa bağlantı)
_EVERGREEN_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def is_installed():
    """WebView2 Runtime kayıt defterinde kayıtlı mı?"""
    if os.name != "nt":
        return True
    try:
        import winreg
    except Exception:
        return True
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\%s" % _CLIENT),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\%s" % _CLIENT),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\EdgeUpdate\Clients\%s" % _CLIENT),
    ]
    for hive, path in keys:
        try:
            with winreg.OpenKey(hive, path) as k:
                pv, _ = winreg.QueryValueEx(k, "pv")
                if pv and pv not in ("", "0.0.0.0"):
                    return True
        except OSError:
            continue
    return False


def ensure(timeout=600):
    """Runtime kuruluysa True döner; değilse kurmayı dener ve sonucu döner."""
    if is_installed():
        return True

    setup = resource_path("MicrosoftEdgeWebview2Setup.exe")
    tmp = None
    try:
        if not os.path.exists(setup):
            import urllib.request
            tmp = os.path.join(tempfile.gettempdir(), "MicrosoftEdgeWebview2Setup.exe")
            print("WebView2 çalışma zamanı indiriliyor...")
            urllib.request.urlretrieve(_EVERGREEN_URL, tmp)
            setup = tmp
        print("WebView2 çalışma zamanı kuruluyor...")
        subprocess.run(
            [setup, "/silent", "/install"],
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        print(f"WebView2 kurulumu başarısız: {e}")
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
    return is_installed()
