import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import webbrowser
import requests
from io import BytesIO
from PIL import Image
from core.downloader import YouTubeDownloader
from utils.helpers import resource_path, load_settings, set_setting, get_setting, load_history, add_to_history, check_ffmpeg_installed
from utils.updater import check_for_updates, perform_update, get_current_version

class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load Settings
        self.settings = load_settings()
        theme = self.settings.get('theme', 'Dark')
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.title("Video Downloader Pro")
        self.geometry("1100x700")
        self.minsize(950, 600)
        
        try:
            icon_path = resource_path("icon.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"İcon yüklenirken hata: {e}")

        # Core instance
        self.downloader = YouTubeDownloader(
            progress_callback=self.update_progress,
            completion_callback=self.on_download_success,
            error_callback=self.on_download_error,
            info_callback=self.on_download_info
        )

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        
        # Frames Container
        self.frames_container = ctk.CTkFrame(self, fg_color="transparent")
        self.frames_container.grid(row=0, column=1, sticky="nsew")
        self.frames_container.grid_rowconfigure(0, weight=1)
        self.frames_container.grid_columnconfigure(0, weight=1)

        # Initialize Frames
        self.home_frame = None
        self.downloads_frame = None
        self.settings_frame = None
        self.help_frame = None

        self._build_home_frame()
        self._build_downloads_frame()
        self._build_settings_frame()
        self._build_help_frame()
        
        # Load default UI states based on settings
        self._load_saved_path()
        if self.settings.get('default_mp4', True):
            self.var_mp4.set(True)

        self.show_frame("home")
        
        # Check for updates in background
        threading.Thread(target=self._check_updates_async, daemon=True).start()

    def _check_updates_async(self):
        update_available, new_version, download_url = check_for_updates()
        if update_available:
            self.after(2000, self._prompt_update, new_version, download_url)

    def _prompt_update(self, new_version, download_url):
        current = get_current_version()
        answer = messagebox.askyesno(
            "Yeni Güncelleme Mevcut!",
            f"Video Downloader Pro'nun yeni bir sürümü ({new_version}) bulundu.\n(Mevcut Sürümünüz: {current})\n\nŞimdi otomatik olarak güncellenip yeniden başlatılmasını ister misiniz?"
        )
        if answer:
            success, msg = perform_update(download_url)
            if success:
                messagebox.showinfo("Güncelleniyor", msg)
                self.destroy()
            else:
                messagebox.showerror("Güncelleme Hatası", msg)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("#f0f0f0", "#15171e"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Title
        self.title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.title_frame.grid(row=0, column=0, padx=20, pady=(30, 40), sticky="w")
        
        self.lbl_icon = ctk.CTkLabel(self.title_frame, text="⬇", font=ctk.CTkFont(size=20), text_color=("#0099cc", "#00e5ff"))
        self.lbl_icon.pack(side="left", padx=(0, 10))
        self.logo_label = ctk.CTkLabel(self.title_frame, text="Video Downloader Pro", font=ctk.CTkFont(size=14, weight="bold"))
        self.logo_label.pack(side="left")

        # Menu Buttons
        self.sidebar_btns = {}
        
        def create_btn(row, key, text, command):
            btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color=("#555555", "#a0a0ae"), hover_color=("#e5e5e5", "#1c1e26"), anchor="w", height=45, corner_radius=8, command=command)
            btn.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
            self.sidebar_btns[key] = btn
            return btn

        create_btn(1, "home", "🏠   Home", lambda: self.show_frame("home"))
        create_btn(2, "downloads", "⬇   Downloads History", lambda: self.show_frame("downloads"))
        create_btn(3, "settings", "⚙   Settings", lambda: self.show_frame("settings"))
        create_btn(4, "help", "❓   Help", lambda: self.show_frame("help"))

    def show_frame(self, frame_name):
        # Update button colors
        for key, btn in self.sidebar_btns.items():
            if key == frame_name:
                btn.configure(fg_color=("#d9d9d9", "#212a31"), text_color=("#0099cc", "#00e5ff"))
            else:
                btn.configure(fg_color="transparent", text_color=("#555555", "#a0a0ae"))
                
        # Hide all frames
        self.home_frame.grid_forget()
        self.downloads_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.help_frame.grid_forget()
        
        # Show target
        if frame_name == "home":
            self.home_frame.grid(row=0, column=0, sticky="nsew")
        elif frame_name == "downloads":
            self._refresh_downloads()
            self.downloads_frame.grid(row=0, column=0, sticky="nsew")
        elif frame_name == "settings":
            self.settings_frame.grid(row=0, column=0, sticky="nsew")
        elif frame_name == "help":
            self.help_frame.grid(row=0, column=0, sticky="nsew")

    def _build_home_frame(self):
        self.home_frame = ctk.CTkFrame(self.frames_container, fg_color=("#ffffff", "#111319"), corner_radius=0)
        self.home_frame.grid_rowconfigure(0, weight=1)
        self.home_frame.grid_columnconfigure(0, weight=3) # left side
        self.home_frame.grid_columnconfigure(1, weight=1) # right sidebar

        self.main_content = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.main_content.grid(row=0, column=0, sticky="nsew")
        self.main_content.grid_rowconfigure(5, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

        self._build_right_sidebar(self.home_frame)

        # Top URL Input Area
        self.top_bar = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="ew")
        self.top_bar.columnconfigure(0, weight=1)

        self.url_wrapper = ctk.CTkFrame(self.top_bar, fg_color=("#f9f9f9", "#1a1c23"), border_color=("#0099cc", "#00e5ff"), border_width=1, corner_radius=25, height=55)
        self.url_wrapper.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        self.url_wrapper.grid_columnconfigure(0, weight=1)
        self.url_wrapper.grid_propagate(False)

        self.entry_url = ctk.CTkEntry(self.url_wrapper, placeholder_text="Yapıştırın veya Arayın...", height=40, border_width=0, fg_color="transparent", placeholder_text_color=("#888888", "#6c6c75"))
        self.entry_url.grid(row=0, column=0, sticky="ew", padx=20, pady=7)

        self.btn_download = ctk.CTkButton(self.top_bar, text="İNDİR", font=ctk.CTkFont(weight="bold", size=14), fg_color=("#0099cc", "#00e5ff"), text_color=("white", "black"), hover_color=("#007799", "#00b8cc"), height=55, corner_radius=25, width=130, command=self.start_download)
        self.btn_download.grid(row=0, column=1)

        # Quick Links / Options Area
        self.quick_links_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.quick_links_frame.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        self.quick_links_frame.grid_columnconfigure(1, weight=1)
        
        self.lbl_quick = ctk.CTkLabel(self.quick_links_frame, text="Hızlı Ayarlar", font=ctk.CTkFont(weight="bold", size=15))
        self.lbl_quick.grid(row=0, column=0, sticky="w", pady=(0,15))

        self.format_frame = ctk.CTkFrame(self.quick_links_frame, fg_color="transparent")
        self.format_frame.grid(row=1, column=0, sticky="w")
        
        self.var_audio = ctk.BooleanVar(value=False)
        self.check_audio = ctk.CTkCheckBox(self.format_frame, text="Sadece Ses (MP3)", variable=self.var_audio, checkbox_height=20, checkbox_width=20, corner_radius=5)
        self.check_audio.pack(side="left", padx=(0, 25))

        self.var_mp4 = ctk.BooleanVar(value=False)
        self.check_mp4 = ctk.CTkCheckBox(self.format_frame, text="Sadece MP4", variable=self.var_mp4, checkbox_height=20, checkbox_width=20, corner_radius=5)
        self.check_mp4.pack(side="left")

        # Save Path setting
        self.path_frame = ctk.CTkFrame(self.quick_links_frame, fg_color="transparent")
        self.path_frame.grid(row=2, column=0, sticky="w", pady=(20, 0))
        
        self.lbl_path = ctk.CTkLabel(self.path_frame, text="Kayıt Yeri:", text_color=("#555555", "#a0a0ae"))
        self.lbl_path.pack(side="left", padx=(0, 15))
        
        self.entry_path = ctk.CTkEntry(self.path_frame, width=350, height=35, fg_color=("#f9f9f9", "#1a1c23"), border_color=("#cccccc", "#2b2d35"))
        self.entry_path.pack(side="left", padx=(0, 15))
        
        self.btn_browse = ctk.CTkButton(self.path_frame, text="Gözat", width=80, height=35, fg_color=("#e0e0e0", "#2b2d35"), hover_color=("#d0d0d0", "#3c3e47"), text_color=("black", "white"), command=self.browse_folder)
        self.btn_browse.pack(side="left")

        # Active Downloads Section
        self.lbl_active = ctk.CTkLabel(self.main_content, text="Aktif İndirme", font=ctk.CTkFont(weight="bold", size=16))
        self.lbl_active.grid(row=2, column=0, sticky="w", padx=40, pady=(30, 10))

        self.active_dl_frame = ctk.CTkFrame(self.main_content, fg_color=("#f5f5f5", "#1c1e26"), corner_radius=12, border_color=("#cccccc", "#2b2d35"), border_width=1)
        self.active_dl_frame.grid(row=3, column=0, sticky="ew", padx=40, pady=(0, 10), ipady=10)
        self.active_dl_frame.columnconfigure(1, weight=1)
        
        self.thumb_placeholder = ctk.CTkFrame(self.active_dl_frame, width=100, height=60, fg_color=("#e0e0e0", "#2b2d35"), corner_radius=8)
        self.thumb_placeholder.grid(row=0, column=0, rowspan=3, padx=15, pady=10)
        self.thumb_placeholder.pack_propagate(False)
        self.thumb_placeholder.grid_propagate(False)
        
        self.lbl_thumbnail = ctk.CTkLabel(self.thumb_placeholder, text="")
        self.lbl_thumbnail.pack(expand=True, fill="both")
        
        self.lbl_video_title = ctk.CTkLabel(self.active_dl_frame, text="Bekleniyor...", font=ctk.CTkFont(weight="bold", size=13))
        self.lbl_video_title.grid(row=0, column=1, sticky="w", padx=5, pady=(10,0))
        
        self.progress_bar = ctk.CTkProgressBar(self.active_dl_frame, mode="determinate", progress_color="#00e5ff", fg_color=("#e0e0e0", "#2b2d35"), height=6)
        self.progress_bar.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.progress_bar.set(0)
        
        self.label_status = ctk.CTkLabel(self.active_dl_frame, text="Hazır", text_color=("#555555", "#a0a0ae"), font=ctk.CTkFont(size=11))
        self.label_status.grid(row=2, column=1, sticky="w", padx=5, pady=(0,10))

    def _build_right_sidebar(self, parent):
        self.right_sidebar = ctk.CTkFrame(parent, width=280, corner_radius=0, fg_color=("#fcfcfc", "#181a20"), border_width=1, border_color=("#cccccc", "#2b2d35"))
        self.right_sidebar.grid(row=0, column=1, sticky="nsew")

        lbl_history = ctk.CTkLabel(self.right_sidebar, text="📌 Oturum Bilgisi", font=ctk.CTkFont(weight="bold", size=14))
        lbl_history.pack(pady=(40, 10), padx=25, anchor="w")

        stat1_frame = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
        stat1_frame.pack(fill="x", padx=25, pady=10)
        ctk.CTkLabel(stat1_frame, text="✅ Başarılı İşlemler", text_color=("#555555", "#a0a0ae")).pack(side="left")
        self.lbl_success_count = ctk.CTkLabel(stat1_frame, text="0", text_color=("#0099cc", "#00e5ff"), font=ctk.CTkFont(weight="bold", size=14))
        self.lbl_success_count.pack(side="right")
        
        stat2_frame = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
        stat2_frame.pack(fill="x", padx=25, pady=15)
        ctk.CTkLabel(stat2_frame, text="❌ Hatalı İşlemler", text_color=("#555555", "#a0a0ae")).pack(side="left")
        self.lbl_error_count = ctk.CTkLabel(stat2_frame, text="0", text_color=("#cc0000", "#ff4444"), font=ctk.CTkFont(weight="bold", size=14))
        self.lbl_error_count.pack(side="right")

        lbl_active = ctk.CTkLabel(self.right_sidebar, text="💻 Sistem Durumu", font=ctk.CTkFont(weight="bold", size=14))
        lbl_active.pack(pady=(30, 10), padx=25, anchor="w")

        status_frame = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
        status_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(status_frame, text="İndirme Motoru:", text_color=("#555555", "#a0a0ae")).pack(side="left")
        ctk.CTkLabel(status_frame, text="Aktif", text_color=("#0099cc", "#00e5ff"), font=ctk.CTkFont(weight="bold")).pack(side="right")
        
        status2_frame = ctk.CTkFrame(self.right_sidebar, fg_color="transparent")
        status2_frame.pack(fill="x", padx=25, pady=5)
        ctk.CTkLabel(status2_frame, text="Sürüm:", text_color=("#555555", "#a0a0ae")).pack(side="left")
        ctk.CTkLabel(status2_frame, text=f"v{get_current_version()}").pack(side="right")

        self.success_downloads = 0
        self.error_downloads = 0

    def _build_downloads_frame(self):
        self.downloads_frame = ctk.CTkFrame(self.frames_container, fg_color=("#ffffff", "#111319"), corner_radius=0)
        
        lbl_title = ctk.CTkLabel(self.downloads_frame, text="İndirme Geçmişi", font=ctk.CTkFont(weight="bold", size=20))
        lbl_title.pack(pady=(40, 20), padx=40, anchor="w")

        self.history_scroll = ctk.CTkScrollableFrame(self.downloads_frame, fg_color="transparent")
        self.history_scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))

    def _refresh_downloads(self):
        for child in self.history_scroll.winfo_children():
            child.destroy()
            
        history = load_history()
        
        if not history:
            ctk.CTkLabel(self.history_scroll, text="İndirme geçmişi boş.", text_color=("#555555", "#a0a0ae")).pack(pady=20)
            return
            
        for item in history:
            comp_frame = ctk.CTkFrame(self.history_scroll, fg_color=("#f5f5f5", "#1c1e26"), corner_radius=12, border_color=("#cccccc", "#2b2d35"), border_width=1)
            comp_frame.pack(fill="x", pady=(0, 10), ipady=5)
            
            ctk.CTkLabel(comp_frame, text="✅", font=ctk.CTkFont(size=20)).pack(side="left", padx=20)
            
            info_frame = ctk.CTkFrame(comp_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, pady=10)
            
            ctk.CTkLabel(info_frame, text=item.get('title', 'Bilinmeyen'), font=ctk.CTkFont(weight="bold", size=13), anchor="w").pack(fill="x")
            meta_text = f"Tarih: {item.get('date', '')}  |  Format: {item.get('type', '')}"
            ctk.CTkLabel(info_frame, text=meta_text, font=ctk.CTkFont(size=11), text_color=("#6c6c75", "#6c6c75"), anchor="w").pack(fill="x")
            
            path = item.get('path', '')
            btn_open = ctk.CTkButton(comp_frame, text="Klasörü Aç", width=100, fg_color=("#e0e0e0", "#2b2d35"), hover_color=("#d0d0d0", "#3c3e47"), corner_radius=8, command=lambda p=path: self._open_folder(p))
            btn_open.pack(side="right", padx=20)

    def _open_folder(self, path):
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Uyarı", "Seçili klasör artık mevcut değil.")

    def _build_settings_frame(self):
        self.settings_frame = ctk.CTkFrame(self.frames_container, fg_color=("#ffffff", "#111319"), corner_radius=0)
        
        lbl_title = ctk.CTkLabel(self.settings_frame, text="Ayarlar", font=ctk.CTkFont(weight="bold", size=20))
        lbl_title.pack(pady=(40, 20), padx=40, anchor="w")

        panel = ctk.CTkFrame(self.settings_frame, fg_color=("#f9f9f9", "#1a1c23"), corner_radius=12)
        panel.pack(fill="x", padx=40, pady=10, ipady=10)
        
        # Tema
        theme_frame = ctk.CTkFrame(panel, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(theme_frame, text="Görünüm Teması", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.opt_theme = ctk.CTkOptionMenu(theme_frame, values=["Dark", "Light", "System"], command=self._change_theme, fg_color=("#e0e0e0", "#2b2d35"), button_color=("#e0e0e0", "#2b2d35"))
        self.opt_theme.set(self.settings.get('theme', 'Dark'))
        self.opt_theme.pack(side="right")

        # Varsayılan MP4
        def_mp4_frame = ctk.CTkFrame(panel, fg_color="transparent")
        def_mp4_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(def_mp4_frame, text="İndirmelerde 'Sadece MP4' Varsayılan Olsun", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.sw_mp4 = ctk.CTkSwitch(def_mp4_frame, text="", progress_color="#00e5ff", command=self._toggle_def_mp4)
        if self.settings.get('default_mp4', True):
            self.sw_mp4.select()
        self.sw_mp4.pack(side="right")

        # Otomatik Klasör Açma
        auto_open_frame = ctk.CTkFrame(panel, fg_color="transparent")
        auto_open_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(auto_open_frame, text="İndirme Bitince Klasörü Otomatik Aç", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.sw_auto = ctk.CTkSwitch(auto_open_frame, text="", progress_color="#00e5ff", command=self._toggle_auto_open)
        if self.settings.get('auto_open_folder', False):
            self.sw_auto.select()
        self.sw_auto.pack(side="right")

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        set_setting('theme', choice)

    def _toggle_def_mp4(self):
        val = bool(self.sw_mp4.get())
        set_setting('default_mp4', val)
        self.var_mp4.set(val)

    def _toggle_auto_open(self):
        set_setting('auto_open_folder', bool(self.sw_auto.get()))

    def _build_help_frame(self):
        self.help_frame = ctk.CTkFrame(self.frames_container, fg_color=("#ffffff", "#111319"), corner_radius=0)
        
        lbl_title = ctk.CTkLabel(self.help_frame, text="Yardım & Sistem Gereksinimleri", font=ctk.CTkFont(weight="bold", size=20))
        lbl_title.pack(pady=(40, 20), padx=40, anchor="w")

        # System Requirements Checker
        req_frame = ctk.CTkFrame(self.help_frame, fg_color=("#f9f9f9", "#1a1c23"), corner_radius=12, border_color=("#cccccc", "#2b2d35"), border_width=1)
        req_frame.pack(fill="x", padx=40, pady=(0, 20), ipady=15)
        
        ctk.CTkLabel(req_frame, text="Sistem Bağımlılıkları Kontrolü", font=ctk.CTkFont(weight="bold", size=15)).pack(anchor="w", padx=20, pady=(10, 5))
        
        # FFmpeg check
        ffmpeg_frame = ctk.CTkFrame(req_frame, fg_color="transparent")
        ffmpeg_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(ffmpeg_frame, text="FFmpeg (Gerekli):", font=ctk.CTkFont(size=14)).pack(side="left")
        
        is_installed, msg = check_ffmpeg_installed()
        status_text = "Kurulu ve Çalışıyor ✅" if is_installed else "Eksik! ❌"
        color = "#00e5ff" if is_installed else "#ff4444"
        
        ctk.CTkLabel(ffmpeg_frame, text=status_text, font=ctk.CTkFont(weight="bold", size=14), text_color=color).pack(side="left", padx=10)
        
        if not is_installed:
            ctk.CTkButton(ffmpeg_frame, text="Nasıl Kurarım?", width=100, height=30, fg_color=("#e0e0e0", "#2b2d35"), hover_color=("#d0d0d0", "#3c3e47"), 
                          command=lambda: webbrowser.open("https://ffmpeg.org/download.html")).pack(side="right", padx=10)
            
            ctk.CTkLabel(req_frame, text="FFmpeg kurulu değil. Ses (MP3) dönüştürme ve MP4 birleştirme işlemleri HATA VEREBİLİR.\nLütfen FFmpeg indirip sistem ortam değişkenlerine (PATH) ekleyin.", 
                         text_color=("#cc0000", "#ff4444"), justify="left").pack(anchor="w", padx=20, pady=5)

        # Help Info Text
        info_box = ctk.CTkTextbox(self.help_frame, fg_color=("#f9f9f9", "#1a1c23"), corner_radius=12, font=ctk.CTkFont(size=14))
        info_box.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        help_text = """Burası Video Downloader Pro Hakkında Yardım Sayfasıdır!

* Nasıl İndiririm?: Ana Sayfaya giderek url kutucuğuna video linkini yapıştırın. Konum seçin ve 'İNDİR'e tıklayın.
* Hangi formatları destekler?: YouTube, Instagram, Twitter dahil çoğu güncel platformu yt-dlp destekler.
* Varsayılan MP4 özelliği nedir?: YouTube normalde Opus/WebM indirir. Sadece MP4 seçeneği ile H264+AAC direkt YouTube'dan çekilir.
* İndirdiğim dosyaları nerede bulurum?: İndirme Geçmişi (Downloads) ekranından geçmiş klasörleri açabilirsiniz.
* FFmpeg nedir?: MP4 dönüştürebilmek ve kalite artırabilmek için yukarıdaki menüden indirip işletim sisteminize kurmanız gereken araçtır.
"""
        info_box.insert("1.0", help_text)
        info_box.configure(state="disabled")

    def _load_saved_path(self):
        path = get_setting('last_folder')
        if path and os.path.exists(path):
            self.entry_path.insert(0, path)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.entry_path.delete(0, 'end')
            self.entry_path.insert(0, folder_selected)
            set_setting('last_folder', folder_selected)

    def start_download(self):
        video_url = self.entry_url.get().strip()
        save_path = self.entry_path.get().strip()
        audio_only = self.var_audio.get()
        mp4_only = self.var_mp4.get()

        if video_url and save_path:
            self.lbl_video_title.configure(text="Sorgulanıyor...")
            self.label_status.configure(text="İndirme başlatıldı: 0%", text_color=("#0099cc", "#00e5ff"))
            self.progress_bar.set(0)
            self.btn_download.configure(state="disabled")
            
            # Kaydetme pathi type parametresi 
            ftyp = "MP3 Audio" if audio_only else ("MP4 Video" if mp4_only else "Default Video")
            
            threading.Thread(
                target=self._run_downloader_thread, 
                args=(video_url, save_path, audio_only, mp4_only, ftyp),
                daemon=True
            ).start()
        else:
            messagebox.showwarning("Uyarı", "Lütfen URL ve Kayıt Yeri belirtiniz.\nBoş alanları doldurun.")

    def _run_downloader_thread(self, video_url, save_path, audio_only, mp4_only, ftyp):
        self.current_download_type = ftyp
        self.current_save_path = save_path
        self.downloader.download(video_url, save_path, audio_only, mp4_only)
        self.after(0, self._reset_ui_state)

    def _reset_ui_state(self):
        self.btn_download.configure(state="normal")
        self.entry_url.delete(0, 'end')

    def on_download_info(self, video_title, thumbnail_url):
        img_ctk = None
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url, timeout=5)
                if response.status_code == 200:
                    image_data = Image.open(BytesIO(response.content))
                    img_ctk = ctk.CTkImage(light_image=image_data, dark_image=image_data, size=(100, 60))
            except Exception as e:
                print(f"Thumbnail yüklenemedi: {e}")
                
        self.after(0, self._show_video_info, video_title, img_ctk)

    def _show_video_info(self, video_title, img_ctk):
        self.lbl_video_title.configure(text=video_title)
        if img_ctk:
            self.lbl_thumbnail.configure(image=img_ctk)
        else:
            self.lbl_thumbnail.configure(image="")

    def update_progress(self, progress):
        self.after(0, self._update_progress_ui, progress)

    def _update_progress_ui(self, progress):
        self.progress_bar.set(progress / 100)
        self.label_status.configure(text=f"İndirme durumu: %{progress}")

    def on_download_success(self, video_title):
        self.after(0, self._show_success, video_title)

    def _show_success(self, video_title):
        self.progress_bar.set(1)
        self.label_status.configure(text="Başarıyla Tamamlandı!", text_color=("#0099cc", "#00e5ff"))
        self.lbl_video_title.configure(text=video_title)
        
        self.success_downloads += 1
        self.lbl_success_count.configure(text=str(self.success_downloads))
        
        # Save to history
        add_to_history(video_title, self.current_save_path, self.current_download_type)
        
        # Check auto open
        if get_setting('auto_open_folder'):
            self._open_folder(self.current_save_path)
            
        messagebox.showinfo("Başarılı", f"Başarıyla indirildi:\n{video_title}")

    def on_download_error(self, error_msg):
        self.after(0, self._show_error, error_msg)

    def _show_error(self, error_msg):
        self.progress_bar.set(0)
        self.label_status.configure(text="İndirme Başarısız", text_color=("#cc0000", "#ff4444"))
        self.lbl_video_title.configure(text="Hata oluştu.")
        
        self.error_downloads += 1
        self.lbl_error_count.configure(text=str(self.error_downloads))
        
        messagebox.showerror("Hata", error_msg)
