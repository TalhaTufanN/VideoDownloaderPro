"""PyWebView arka ucu — JS ile Python (yt-dlp çekirdeği) arasındaki köprü.

Arayüz webui/web/ altındaki Nocturne HTML/CSS/JS ile çizilir; render'ı
Windows'un yerleşik WebView2 (Edge) motoru yapar.

İlerleme bildirimi ÇEKME (pull) yöntemiyle taşınır: indirme iş parçacığı
yalnızca Python tarafındaki durumu günceller, arayüz bu durumu bir zamanlayıcı
ile `poll()` üzerinden okur.

ÖNEMLİ: Bu sınıfın JS'e açılmasını İSTEMEDİĞİMİZ tüm nitelikleri alt çizgi (_)
ile başlar. pywebview, js_api nesnesinin genel (public) niteliklerini özyinelemeli
olarak tarar; `_window` gibi bir WebView2/.NET nesnesi public olsaydı tarama
sonsuz özyinelemeye girip API kaydını (window.pywebview.api) tamamen bozardı.
"""

import os
import sys
import json
import threading
import subprocess
import webbrowser

import webview

from core.downloader import YouTubeDownloader
from utils.helpers import (
    resource_path, load_settings, set_setting, get_setting,
    load_history, add_to_history, check_ffmpeg_installed, HISTORY_FILE
)
from utils.updater import check_for_updates, perform_update, get_current_version
from utils.ytdlp_updater import start_background_update, get_active_version


class Api:
    def __init__(self):
        self._window = None
        self._update_url = None
        self._bg_started = False
        self._cur_type = ""
        self._cur_path = ""
        self._lock = threading.Lock()
        # Arayüzün poll() ile okuduğu paylaşılan durum
        self._state = {
            "status": "idle",       # idle | running | success | error
            "title": "",
            "thumb": None,
            "pct": 0,
            "success": 0,
            "error": 0,
            "engine_update": None,  # yeni yt-dlp sürümü (kalıcı — kart)
            "app_update": None,     # yeni uygulama sürümü (kalıcı — kart)
            "error_msg": None,      # hata mesajı (tek sefer)
        }
        self._downloader = YouTubeDownloader(
            progress_callback=self._on_progress,
            completion_callback=self._on_success,
            error_callback=self._on_error,
            info_callback=self._on_info,
        )

    def _set(self, **kw):
        with self._lock:
            self._state.update(kw)

    # ── JS → Python (public API) ─────────────────────────────────────────────
    def get_initial(self):
        settings = load_settings()
        data = {
            "version": get_current_version(),
            "engine_version": get_active_version() or "—",
            "ffmpeg_ok": check_ffmpeg_installed()[0],
            "last_folder": settings.get("last_folder", ""),
            "settings": {
                "default_mp4": settings.get("default_mp4", True),
                "auto_open_folder": settings.get("auto_open_folder", False),
                "theme": settings.get("theme", "Dark"),
            },
            "history": load_history(),
            "success": self._state["success"],
            "error": self._state["error"],
        }
        if not self._bg_started:
            self._bg_started = True
            start_background_update(on_updated=lambda v: self._set(engine_update=v))
            threading.Thread(target=self._check_app_update, daemon=True).start()
        return data

    def poll(self):
        """Arayüzün zamanlayıcısı bunu çağırır. Tek seferlik hata mesajını
        döndürdükten sonra temizler; kart durumları kalıcıdır."""
        with self._lock:
            snap = dict(self._state)
            self._state["error_msg"] = None
        return snap

    def get_history(self):
        return load_history()

    def choose_folder(self):
        try:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            print(f"Klasör seçilemedi: {e}")
            return ""
        if result:
            path = result[0] if isinstance(result, (list, tuple)) else result
            set_setting("last_folder", path)
            return path
        return ""

    def start_download(self, url, fmt, path):
        url = (url or "").strip()
        path = (path or "").strip()
        if not url or not path:
            return {"ok": False}
        set_setting("last_folder", path)
        audio_only = fmt == "mp3"
        mp4_only = fmt == "mp4"
        self._cur_type = "MP3 Audio" if audio_only else ("MP4 Video" if mp4_only else "Default Video")
        self._cur_path = path
        self._set(status="running", pct=0, title="Sorgulanıyor...", thumb=None)
        threading.Thread(
            target=self._downloader.download,
            args=(url, path, audio_only, mp4_only),
            daemon=True,
        ).start()
        return {"ok": True}

    def set_setting(self, key, value):
        set_setting(key, value)
        return True

    def clear_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as e:
            print(f"Geçmiş temizlenemedi: {e}")
        return []

    def open_folder(self, path):
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Klasör açılamadı: {e}")
        return True

    def open_url(self, url):
        webbrowser.open(url)
        return True

    def restart_app(self):
        try:
            args = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable] + sys.argv
            subprocess.Popen(args)
        except Exception as e:
            print(f"Yeniden başlatılamadı: {e}")
        self._destroy()

    def do_app_update(self):
        if not self._update_url:
            return
        success, _msg = perform_update(self._update_url)
        if success:
            self._destroy()

    # ── İndirme geri çağrıları (indirme iş parçacığından) ────────────────────
    def _on_info(self, title, thumb):
        self._set(status="running", title=title or "", thumb=thumb)

    def _on_progress(self, pct):
        self._set(status="running", pct=int(pct))

    def _on_success(self, title):
        add_to_history(title, self._cur_path, self._cur_type)
        with self._lock:
            self._state["success"] += 1
            self._state.update(status="success", pct=100, title=title)
        if get_setting("auto_open_folder"):
            self.open_folder(self._cur_path)

    def _on_error(self, msg):
        with self._lock:
            self._state["error"] += 1
            self._state.update(status="error", error_msg=msg)

    def _check_app_update(self):
        available, version, url = check_for_updates()
        if available and url:
            self._update_url = url
            self._set(app_update=version)

    def _destroy(self):
        try:
            self._window.destroy()
        except Exception:
            pass


def run():
    api = Api()

    # Görev çubuğu simgesinin uygulamaya (python.exe'ye değil) ait olması için
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "TalhaTufan.VideoDownloaderPro")
    except Exception:
        pass

    icon_path = resource_path("icon.ico")
    html_path = resource_path(os.path.join("webui", "web", "index.html"))
    window = webview.create_window(
        "Video Downloader Pro",
        html_path,
        js_api=api,
        width=1200,
        height=780,
        min_size=(1040, 700),
        background_color="#161826",
    )
    api._window = window

    try:
        # 'icon' pencerenin/görev çubuğunun simgesini uygular
        webview.start(icon=icon_path)
    except TypeError:
        # Eski pywebview sürümleri 'icon' parametresini desteklemez
        webview.start()
