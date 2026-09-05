import yt_dlp
import os
import time

from utils.helpers import get_ffmpeg_path


class YouTubeDownloader:
    def __init__(self, progress_callback=None, completion_callback=None, error_callback=None, info_callback=None):
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        self.info_callback = info_callback
        self._last_pl_title = None

    def _hook(self, d):
        if d['status'] == 'downloading':
            # Oynatma listesinde yeni bir videoya geçildiyse kartı güncelle
            info = d.get('info_dict') or {}
            idx = info.get('playlist_index')
            if idx is not None and self.info_callback:
                title = info.get('title', '')
                if title != self._last_pl_title:
                    self._last_pl_title = title
                    n = info.get('n_entries', '?')
                    self.info_callback(f"[{idx}/{n}] {title}", info.get('thumbnail'))

            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes')
            if total_bytes and downloaded_bytes and self.progress_callback:
                progress = int(downloaded_bytes / total_bytes * 100)
                self.progress_callback(progress)
        elif d['status'] == 'finished':
            if self.progress_callback:
                self.progress_callback(100)

    def _build_opts(self, save_path, audio_only, mp4_only, is_instagram):
        if is_instagram:
            format_string = 'best'
        elif audio_only:
            format_string = 'bestaudio/best'
        elif mp4_only:
            format_string = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            format_string = 'bestvideo+bestaudio/best'

        postprocessors = []
        if audio_only and not is_instagram:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
                'nopostoverwrites': True
            })
        elif mp4_only and not audio_only:
            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            })

        opts = {
            'format': format_string,
            'postprocessors': postprocessors,
            'progress_hooks': [self._hook],
            'quiet': True,
            'noprogress': True,
            # 403 Forbidden hatalarına karşı dayanıklılık (bkz. player_client)
            'retries': 10,
            'fragment_retries': 10,
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/122.0.0.0 Safari/537.36'
                )
            },
        }
        if mp4_only and not audio_only:
            opts['merge_output_format'] = 'mp4'

        ffmpeg_dir = get_ffmpeg_path()
        if ffmpeg_dir:
            opts['ffmpeg_location'] = ffmpeg_dir
        return opts

    def download(self, video_url, save_path, audio_only=False, mp4_only=False):
        try:
            self._last_pl_title = None
            is_instagram = 'instagram.com' in video_url
            is_youtube = 'youtube.com' in video_url or 'youtu.be' in video_url

            opts = self._build_opts(save_path, audio_only, mp4_only, is_instagram)
            if is_youtube:
                opts['extractor_args'] = {
                    'youtube': {'player_client': ['android', 'web_safari', 'web']}
                }

            # Tek video çıktı şablonu; playlist için aşağıda değiştirilir
            single_tmpl = os.path.join(save_path, '%(title)s.%(ext)s')

            with yt_dlp.YoutubeDL({**opts, 'outtmpl': single_tmpl}) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)

                # ── Oynatma listesi (playlist) ────────────────────────────────
                if info_dict.get('_type') == 'playlist' or info_dict.get('entries') is not None:
                    entries = [e for e in (info_dict.get('entries') or []) if e]
                    pl_title = info_dict.get('title') or 'Oynatma Listesi'
                    total = len(entries)
                    if total == 0:
                        if self.error_callback:
                            self.error_callback("Oynatma listesi boş ya da erişilemiyor.")
                        return

                    thumb = entries[0].get('thumbnail')
                    if self.info_callback:
                        self.info_callback(f"{pl_title} ({total} video)", thumb)

                    # Her videoyu, playlist adıyla bir alt klasöre sıra numaralı indir
                    pl_tmpl = os.path.join(
                        save_path, '%(playlist_title)s',
                        '%(playlist_index)02d - %(title)s.%(ext)s'
                    )
                    pl_opts = {**opts, 'outtmpl': pl_tmpl, 'ignoreerrors': True}
                    with yt_dlp.YoutubeDL(pl_opts) as pydl:
                        pydl.process_ie_result(info_dict, download=True)

                    dest = os.path.join(save_path, self._safe(pl_title))
                    if self.completion_callback:
                        self.completion_callback(f"{pl_title} — {total} video")
                    return

                # ── Tek video ─────────────────────────────────────────────────
                video_title = info_dict.get('title', 'İsimsiz video')
                thumbnail_url = info_dict.get('thumbnail')
                if self.info_callback:
                    self.info_callback(video_title, thumbnail_url)

                ydl.process_ie_result(info_dict, download=True)

                if audio_only and not is_instagram:
                    downloaded_file_path = os.path.splitext(ydl.prepare_filename(info_dict))[0] + '.mp3'
                elif mp4_only and not audio_only:
                    downloaded_file_path = os.path.splitext(ydl.prepare_filename(info_dict))[0] + '.mp4'
                else:
                    downloaded_file_path = ydl.prepare_filename(info_dict)

                if os.path.exists(downloaded_file_path):
                    current_time = time.time()
                    os.utime(downloaded_file_path, (current_time, current_time))
                    if self.completion_callback:
                        self.completion_callback(video_title)
                else:
                    if self.error_callback:
                        self.error_callback("Dosya oluşturulamadı.")
        except Exception as e:
            error_message = str(e)
            user_msg = error_message
            if "This video is only available for registered users" in error_message:
                user_msg = "Bu video sadece kayıtlı kullanıcılar için kullanılabilir. Lütfen giriş yapın."
            elif "Video unavailable" in error_message:
                user_msg = "Video kullanılamıyor. URL'nin doğru olduğundan emin olun."

            if self.error_callback:
                self.error_callback(user_msg)

    @staticmethod
    def _safe(name):
        for ch in '<>:"/\\|?*':
            name = name.replace(ch, '_')
        return name.strip()
