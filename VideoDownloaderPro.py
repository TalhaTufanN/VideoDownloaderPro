# yt-dlp'yi (varsa) önbellekteki daha yeni sürümle etkinleştir.
# ÖNEMLİ: Bu satır, yt_dlp'yi import eden herhangi bir modülden (webui.backend ->
# core.downloader) ÖNCE çalışmalıdır; aksi halde gömülü sürüm import edilir.
from utils.ytdlp_updater import activate_cached_ytdlp
activate_cached_ytdlp()

from webui.backend import run

if __name__ == "__main__":
    run()
