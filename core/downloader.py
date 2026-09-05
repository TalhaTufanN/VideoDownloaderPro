import yt_dlp
import os
import time

from utils.helpers import get_ffmpeg_path

# Kalite -> maksimum yükseklik (px). "best" sınırsız.
QUALITY_HEIGHTS = {"best": None, "1080": 1080, "720": 720, "480": 480}


class YouTubeDownloader:
    def __init__(self, progress_callback=None, info_callback=None, status_callback=None):
        self.progress_callback = progress_callback   # (pct:int)
        self.info_callback = info_callback            # (title:str, thumbnail:str|None)
        self.status_callback = status_callback        # (note:str)  — canlı durum satırı
        self._last_pl_title = None
        self._done_indices = set()

    # ── yardımcılar ──────────────────────────────────────────────────────────
    def _note(self, text):
        if self.status_callback:
            self.status_callback(text)

    def _hook(self, d):
        if d['status'] == 'downloading':
            info = d.get('info_dict') or {}
            idx = info.get('playlist_index')
            if idx is not None and self.info_callback:
                title = info.get('title', '')
                if title != self._last_pl_title:
                    self._last_pl_title = title
                    n = info.get('n_entries', '?')
                    self.info_callback(f"[{idx}/{n}] {title}", info.get('thumbnail'))
                    self._note(f"[{idx}/{n}] indiriliyor…")
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes')
            if total_bytes and downloaded_bytes and self.progress_callback:
                self.progress_callback(int(downloaded_bytes / total_bytes * 100))
        elif d['status'] == 'finished':
            info = d.get('info_dict') or {}
            idx = info.get('playlist_index')
            if idx is not None:
                self._done_indices.add(idx)
            if self.progress_callback:
                self.progress_callback(100)
            self._note("İşleniyor / dönüştürülüyor…")

    def _pp_hook(self, d):
        if d.get('status') == 'started':
            self._note("Dönüştürülüyor… (ffmpeg)")

    def _format_string(self, audio_only, mp4_only, is_instagram, quality):
        if is_instagram:
            return 'best'
        if audio_only:
            return 'bestaudio/best'
        h = QUALITY_HEIGHTS.get(quality)
        if mp4_only:
            if h:
                return (f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/'
                        f'best[height<={h}][ext=mp4]/best[height<={h}]/best')
            return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        if h:
            return f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'
        return 'bestvideo+bestaudio/best'

    def _base_opts(self, save_path, audio_only, mp4_only, is_instagram, quality, is_youtube):
        postprocessors = []
        if audio_only and not is_instagram:
            postprocessors.append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3',
                                   'preferredquality': '320', 'nopostoverwrites': True})
        elif mp4_only and not audio_only:
            postprocessors.append({'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'})

        opts = {
            'format': self._format_string(audio_only, mp4_only, is_instagram, quality),
            'postprocessors': postprocessors,
            'progress_hooks': [self._hook],
            'postprocessor_hooks': [self._pp_hook],
            'quiet': True,
            'noprogress': True,
            'retries': 10,
            'fragment_retries': 10,
            'http_headers': {
                'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/122.0.0.0 Safari/537.36')
            },
        }
        if mp4_only and not audio_only:
            opts['merge_output_format'] = 'mp4'
        if is_youtube:
            opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web_safari', 'web']}}
        ffmpeg_dir = get_ffmpeg_path()
        if ffmpeg_dir:
            opts['ffmpeg_location'] = ffmpeg_dir
        return opts

    # ── HIZLI ÖN-İNCELEME (indirmeden) ─────────────────────────────────────────
    def probe(self, url):
        """URL'yi hızlıca (flat) çözer; (info, meta) döndürür.
        meta = {type, title, count, uploader}."""
        is_youtube = 'youtube.com' in url or 'youtu.be' in url
        opts = {
            'quiet': True, 'noprogress': True, 'extract_flat': 'in_playlist',
            'http_headers': {'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                                            'Chrome/122.0.0.0 Safari/537.36')},
        }
        if is_youtube:
            opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web_safari', 'web']}}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info.get('_type') == 'playlist' or info.get('entries') is not None:
            entries = [e for e in (info.get('entries') or []) if e]
            meta = {'type': 'playlist',
                    'title': info.get('title') or 'Oynatma Listesi',
                    'count': info.get('playlist_count') or len(entries),
                    'uploader': info.get('uploader') or info.get('channel') or ''}
        else:
            meta = {'type': 'single',
                    'title': info.get('title') or '',
                    'count': 1,
                    'uploader': info.get('uploader') or info.get('channel') or ''}
        return info, meta

    # ── İNDİRME ────────────────────────────────────────────────────────────────
    def download(self, url, save_path, audio_only=False, mp4_only=False, quality='best', info=None):
        self._last_pl_title = None
        self._done_indices = set()
        try:
            is_instagram = 'instagram.com' in url
            is_youtube = 'youtube.com' in url or 'youtu.be' in url
            opts = self._base_opts(save_path, audio_only, mp4_only, is_instagram, quality, is_youtube)

            single_tmpl = os.path.join(save_path, '%(title)s.%(ext)s')
            with yt_dlp.YoutubeDL({**opts, 'outtmpl': single_tmpl}) as ydl:
                if info is None:
                    self._note("Bağlantı çözümleniyor…")
                    info = ydl.extract_info(url, download=False)

                is_playlist = info.get('_type') == 'playlist' or info.get('entries') is not None

                # ── Oynatma listesi ──────────────────────────────────────────
                if is_playlist:
                    entries = [e for e in (info.get('entries') or []) if e]
                    pl_title = info.get('title') or 'Oynatma Listesi'
                    total = info.get('playlist_count') or len(entries)
                    if total == 0:
                        return {'ok': False, 'message': 'Oynatma listesi boş ya da erişilemiyor.'}
                    if self.info_callback:
                        thumb = entries[0].get('thumbnail') if entries else None
                        self.info_callback(f"{pl_title} ({total} içerik)", thumb)
                    self._note(f"Oynatma listesi indiriliyor: {total} içerik")

                    pl_tmpl = os.path.join(save_path, '%(playlist_title)s',
                                           '%(playlist_index)02d - %(title)s.%(ext)s')
                    pl_opts = {**opts, 'outtmpl': pl_tmpl, 'ignoreerrors': True}
                    with yt_dlp.YoutubeDL(pl_opts) as pydl:
                        pydl.process_ie_result(info, download=True)
                    done = len(self._done_indices) or total
                    return {'ok': True, 'kind': 'playlist', 'title': pl_title,
                            'total': total, 'done': min(done, total)}

                # ── Tek video ─────────────────────────────────────────────────
                video_title = info.get('title', 'İsimsiz video')
                if self.info_callback:
                    self.info_callback(video_title, info.get('thumbnail'))
                self._note("İndiriliyor…")
                ydl.process_ie_result(info, download=True)

                if audio_only and not is_instagram:
                    path = os.path.splitext(ydl.prepare_filename(info))[0] + '.mp3'
                elif mp4_only and not audio_only:
                    path = os.path.splitext(ydl.prepare_filename(info))[0] + '.mp4'
                else:
                    path = ydl.prepare_filename(info)

                if os.path.exists(path):
                    now = time.time()
                    os.utime(path, (now, now))
                    return {'ok': True, 'kind': 'single', 'title': video_title}
                return {'ok': False, 'message': 'Dosya oluşturulamadı.'}
        except Exception as e:
            msg = str(e)
            if "only available for registered users" in msg:
                msg = "Bu içerik yalnızca kayıtlı kullanıcılar için. Giriş (çerez) gerekebilir."
            elif "Video unavailable" in msg:
                msg = "İçerik kullanılamıyor. URL'nin doğru olduğundan emin olun."
            return {'ok': False, 'message': msg}
