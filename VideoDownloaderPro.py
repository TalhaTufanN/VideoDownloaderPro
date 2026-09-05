# yt-dlp'yi (varsa) önbellekteki daha yeni sürümle etkinleştir.
# ÖNEMLİ: Bu satır, yt_dlp'yi import eden herhangi bir modülden (webui.backend ->
# core.downloader) ÖNCE çalışmalıdır; aksi halde gömülü sürüm import edilir.
from utils.ytdlp_updater import activate_cached_ytdlp
activate_cached_ytdlp()

if __name__ == "__main__":
    # Kullanıcı hiçbir şey kurmak zorunda kalmasın: WebView2 çalışma zamanı
    # eksikse (nadiren) sessizce kur. Genelde Win10/11'de zaten yüklüdür.
    try:
        from webui.webview2_setup import ensure as ensure_webview2
        ensure_webview2()
    except Exception as e:
        print(f"WebView2 kontrolü atlandı: {e}")

    from webui.backend import run
    run()
