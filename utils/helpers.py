import os
import sys
import json
import subprocess
from datetime import datetime

APP_DIR = os.path.join(os.path.expanduser('~'), '.VideoDownloaderPro')
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(APP_DIR, 'settings.json')
HISTORY_FILE = os.path.join(APP_DIR, 'history.json')

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_settings():
    default_settings = {
        'last_folder': '',
        'theme': 'Dark',
        'default_mp4': True,
        'auto_open_folder': False
    }
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                default_settings.update(settings)
    except Exception as e:
        print(f"Ayarlar yüklenirken hata oluştu: {e}")
    return default_settings

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ayarlar kaydedilirken hata oluştu: {e}")

def get_setting(key):
    return load_settings().get(key)

def set_setting(key, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Geçmiş yüklenirken hata: {e}")
    return []

def add_to_history(title, path, file_type):
    history = load_history()
    entry = {
        'title': title,
        'path': path,
        'type': file_type,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    history.insert(0, entry)  # Add to top
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Geçmiş kaydedilirken hata: {e}")

def check_ffmpeg_installed():
    """Sistemde FFmpeg'in kurulu ve PATH'e ekli olup olmadığını kontrol eder."""
    try:
        # Run ffmpeg -version and suppress output
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode == 0:
            return True, "FFmpeg kurulu ve algılandı."
        else:
            return False, "FFmpeg çalıştırılamadı."
    except FileNotFoundError:
        return False, "FFmpeg bulunamadı. PATH ortam değişkenine eklenmemiş olabilir."
    except Exception as e:
        return False, f"FFmpeg kontrol edilirken hata oluştu: {str(e)}"
