import os
import sys
import subprocess
import requests
import tempfile
from packaging.version import parse as parse_version

GITHUB_REPO = "TalhaTufanN/VideoDownloaderPro"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def get_current_version():
    try:
        from utils.helpers import resource_path
        with open(resource_path('version.txt'), 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Sürüm bilgisi okunamadı: {e}")
        return "1.0.0"

def get_latest_release_info():
    """Returns (latest_version_tag_string, download_url)"""
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            tag_name = data.get("tag_name", "").lstrip('v') # Remove 'v' if present like v1.0.1
            
            # Find the exe asset
            download_url = None
            for asset in data.get("assets", []):
                if asset.get("name", "").endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break
            
            return tag_name, download_url
    except Exception as e:
        print(f"Güncel sürüm API'den kontrol edilemedi: {e}")
    return None, None

def check_for_updates():
    """Returns (update_available: bool, latest_version: str, download_url: str)"""
    current = get_current_version()
    latest_tag, download_url = get_latest_release_info()
    
    if latest_tag and current and download_url:
        try:
            if parse_version(latest_tag) > parse_version(current):
                return True, latest_tag, download_url
        except Exception as e:
            print(f"Sürüm karşılaştırma hatası: {e}")
    return False, current, None

def perform_update(download_url):
    """Downloads the latest executable and spawns a batch script to replace the current one."""
    try:
        current_exe = sys.executable
        if not current_exe.endswith('.exe'):
            # Only run update logic if running as a compiled exe
            return False, "Sadece derlenmiş uygulama üzerinden güncelleme yapılabilir."

        # Download the new EXE to a temporary file
        temp_dir = tempfile.gettempdir()
        downloaded_exe_path = os.path.join(temp_dir, "VideoDownloaderPro_update.exe")

        print("Güncelleme indiriliyor...")
        response = requests.get(download_url, stream=True, timeout=60)
        if response.status_code != 200:
            return False, "Güncelleme dosyası indirilemedi."

        with open(downloaded_exe_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        # Create a batch script to swap the files
        bat_script_path = os.path.join(temp_dir, "update_videodownloader.bat")
        
        # Batch script content:
        # 1. Wait a bit for the current exe to fully close
        # 2. Delete the current exe
        # 3. Move the downloaded exe to the current exe's location
        # 4. Start the new exe
        # 5. Delete this batch file
        batch_script = f"""@echo off
echo Guncelleniyor, lutfen bekleyin...
timeout /t 3 /nobreak > NUL
del /q /f "{current_exe}"
move /y "{downloaded_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        with open(bat_script_path, 'w', encoding='utf-8') as f:
            f.write(batch_script)

        # Launch the batch script detached
        subprocess.Popen([bat_script_path], creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
        
        # Signal to close the app immediately
        return True, "Güncelleme başlatıldı. Uygulama yeniden başlatılacak."

    except Exception as e:
        return False, f"Güncelleme sırasında hata: {e}"
