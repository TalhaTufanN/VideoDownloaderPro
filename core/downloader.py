import yt_dlp
import os
import time

class YouTubeDownloader:
    def __init__(self, progress_callback=None, completion_callback=None, error_callback=None, info_callback=None):
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        self.info_callback = info_callback

    def _hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes')
            if total_bytes and downloaded_bytes and self.progress_callback:
                progress = int(downloaded_bytes / total_bytes * 100)
                self.progress_callback(progress)
        elif d['status'] == 'finished':
            if self.progress_callback:
                self.progress_callback(100)

    def download(self, video_url, save_path, audio_only=False, mp4_only=False):
        try:
            is_instagram = 'instagram.com' in video_url
            if is_instagram:
                format_string = 'best'
            else:
                if audio_only:
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

            ydl_opts = {
                'format': format_string,
                'postprocessors': postprocessors,
                'outtmpl': f'{save_path}/%(title)s.%(ext)s',
                'progress_hooks': [self._hook],
                'quiet': True,
                'noprogress': True
            }
            
            if mp4_only and not audio_only:
                ydl_opts['merge_output_format'] = 'mp4'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)
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
