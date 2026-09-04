# yt-dlp'yi (varsa) önbellekteki daha yeni sürümle etkinleştir.
# ÖNEMLİ: Bu satır, yt_dlp'yi import eden herhangi bir modülden (gui.app ->
# core.downloader) ÖNCE çalışmalıdır; aksi halde gömülü sürüm import edilir
# ve artık değiştirilemez.
from utils.ytdlp_updater import activate_cached_ytdlp
activate_cached_ytdlp()

from gui.app import DownloaderApp

if __name__ == "__main__":
    # Yeni bir yt-dlp sürümü var mı kontrolü, arayüz bildirimi gösterebilmesi
    # için uygulamanın kendi içinde arka planda başlatılır (bkz. DownloaderApp).
    app = DownloaderApp()
    app.mainloop()
