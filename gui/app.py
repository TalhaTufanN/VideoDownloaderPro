import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import subprocess
import webbrowser
import json
import requests
from io import BytesIO
from PIL import Image

from core.downloader import YouTubeDownloader
from utils.helpers import (
    resource_path, load_settings, set_setting, get_setting,
    load_history, add_to_history, check_ffmpeg_installed, HISTORY_FILE
)
from utils.updater import check_for_updates, perform_update, get_current_version
from utils.ytdlp_updater import start_background_update, get_active_version
from gui import theme as T


class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        ctk.set_appearance_mode("Dark")          # Nocturne koyu tema
        ctk.set_default_color_theme("blue")

        self.title("Video Downloader Pro")
        self.geometry("1200x780")
        self.minsize(1040, 700)
        self.configure(fg_color=T.BG)

        try:
            self.iconbitmap(resource_path("icon.ico"))
        except Exception as e:
            print(f"İcon yüklenirken hata: {e}")

        # Yazı tipleri
        fam = T.pick_family()
        self.f_h2      = ctk.CTkFont(family=fam, size=26, weight="bold")
        self.f_h3      = ctk.CTkFont(family=fam, size=19, weight="bold")
        self.f_kicker  = ctk.CTkFont(family=fam, size=12, weight="bold")
        self.f_body    = ctk.CTkFont(family=fam, size=13)
        self.f_body_m  = ctk.CTkFont(family=fam, size=13, weight="bold")
        self.f_small   = ctk.CTkFont(family=fam, size=12)
        self.f_tiny    = ctk.CTkFont(family=fam, size=11)
        self.f_stat    = ctk.CTkFont(family=fam, size=26, weight="bold")
        self.f_btn     = ctk.CTkFont(family=fam, size=14, weight="bold")
        self.f_brand   = ctk.CTkFont(family=fam, size=14, weight="bold")

        # İndirici çekirdeği
        self.downloader = YouTubeDownloader(
            progress_callback=self.update_progress,
            completion_callback=self.on_download_success,
            error_callback=self.on_download_error,
            info_callback=self.on_download_info
        )

        # Durum
        self.success_downloads = 0
        self.error_downloads = 0
        self.path_var = tk.StringVar(value=get_setting('last_folder') or "")
        default_mp4 = self.settings.get('default_mp4', True)
        self.format_choice = "mp4" if default_mp4 else "both"
        self.nav_items = {}
        self.format_cards = {}
        self._thumb_img = None
        self.current_save_path = ""
        self.current_download_type = ""

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.screens = {}
        self._build_home()
        self._build_history()
        self._build_settings()
        self._build_help()

        self.show_screen("home")
        self._pulse_dot()

        # Kısayol: Enter -> indir
        self.bind("<Return>", lambda e: self.start_download())

        # Arka plan güncelleme kontrolleri
        threading.Thread(target=self._check_updates_async, daemon=True).start()
        start_background_update(on_updated=self._on_ytdlp_updated)

    # ══════════════════════════════════════════════════════════ helpers ═════

    def _load_logo(self, height=17):
        """app.png'yi yükler; siyah zeminini saydamlaştırıp oka kırpar ve
        kenar çubuğundaki vurgu kutusuna sığacak bir CTkImage döndürür."""
        try:
            img = Image.open(resource_path('app.png')).convert("RGBA")
            img.thumbnail((96, 96))               # hız için önce küçült
            px = img.getdata()
            img.putdata([(r, g, b, 0) if (r < 45 and g < 45 and b < 45) else (r, g, b, a)
                         for (r, g, b, a) in px])
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            w, h = img.size
            size = (max(1, round(w * height / h)), height)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception as e:
            print(f"Logo yüklenemedi: {e}")
            return None

    def _card(self, parent, **kw):
        opts = dict(fg_color=T.PANEL, corner_radius=T.RADIUS_MD,
                    border_width=1, border_color=T.BORDER)
        opts.update(kw)
        return ctk.CTkFrame(parent, **opts)

    def _kicker(self, parent, text):
        return ctk.CTkLabel(parent, text=text.upper(), font=self.f_kicker,
                            text_color=T.N500)

    def _tag(self, parent, text, fg_color, text_color):
        """Rozet: iç boşluğu olan yuvarlatılmış küçük etiket."""
        wrap = ctk.CTkFrame(parent, fg_color=fg_color, corner_radius=6)
        lbl = ctk.CTkLabel(wrap, text=text, font=self.f_tiny, text_color=text_color)
        lbl.pack(padx=9, pady=2)
        wrap._label = lbl
        return wrap

    # ══════════════════════════════════════════════════════════ sidebar ═════

    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=236, corner_radius=0, fg_color=T.SIDEBAR_BG)
        bar.grid(row=0, column=0, sticky="nsew")
        bar.grid_propagate(False)
        bar.grid_rowconfigure(2, weight=1)

        # Marka
        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 30))
        logo = ctk.CTkFrame(brand, width=30, height=30, corner_radius=8,
                            fg_color=T.ACCENT_900, border_width=1, border_color=T.ACCENT_800)
        logo.pack(side="left", padx=(0, 11))
        logo.pack_propagate(False)
        self._logo_img = self._load_logo()
        if self._logo_img is not None:
            ctk.CTkLabel(logo, text="", image=self._logo_img).pack(expand=True)
        else:
            ctk.CTkLabel(logo, text="▼", font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=T.ACCENT_300).pack(expand=True)
        txt = ctk.CTkFrame(brand, fg_color="transparent")
        txt.pack(side="left")
        ctk.CTkLabel(txt, text="Video Downloader", font=self.f_brand,
                     text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(txt, text="P R O", font=self.f_tiny,
                     text_color=T.ACCENT_400).pack(anchor="w")

        # Menü
        menu = ctk.CTkFrame(bar, fg_color="transparent")
        menu.grid(row=1, column=0, sticky="ew", padx=12)
        items = [
            ("home",     "🏠", "Ana Sayfa"),
            ("history",  "🕒", "İndirme Geçmişi"),
            ("settings", "⚙",  "Ayarlar"),
            ("help",     "❓", "Yardım"),
        ]
        for key, icon, label in items:
            self._make_nav_item(menu, key, icon, label)

        # Alt: motor durumu
        footer = ctk.CTkFrame(bar, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 22))
        row = ctk.CTkFrame(footer, fg_color="transparent")
        row.pack(anchor="w")
        self.dot = ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=10),
                                text_color=T.ACCENT_400)
        self.dot.pack(side="left", padx=(0, 7))
        eng = get_active_version() or "—"
        ctk.CTkLabel(row, text=f"Motor aktif · yt-dlp {eng}", font=self.f_tiny,
                     text_color=T.N500).pack(side="left")
        ctk.CTkLabel(footer, text=f"Sürüm {get_current_version()}", font=self.f_tiny,
                     text_color=T.N600).pack(anchor="w", pady=(5, 0))

    def _make_nav_item(self, parent, key, icon, label):
        frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=T.RADIUS_MD,
                             height=40)
        frame.pack(fill="x", pady=1)
        frame.pack_propagate(False)

        bar = ctk.CTkFrame(frame, width=3, height=24, corner_radius=2, fg_color=T.ACCENT_400)
        # accent strip (only visible when active)

        icon_lbl = ctk.CTkLabel(frame, text=icon, font=ctk.CTkFont(size=14),
                                text_color=T.N400, width=20)
        icon_lbl.pack(side="left", padx=(14, 10))
        text_lbl = ctk.CTkLabel(frame, text=label, font=self.f_body, text_color=T.N400)
        text_lbl.pack(side="left")

        self.nav_items[key] = {"frame": frame, "bar": bar,
                               "icon": icon_lbl, "text": text_lbl}

        def on_click(_=None):
            self.show_screen(key)

        def on_enter(_=None):
            if self.current_screen != key:
                frame.configure(fg_color=T.N900)
                text_lbl.configure(text_color=T.N200)
                icon_lbl.configure(text_color=T.N200)

        def on_leave(_=None):
            if self.current_screen != key:
                frame.configure(fg_color="transparent")
                text_lbl.configure(text_color=T.N400)
                icon_lbl.configure(text_color=T.N400)

        for w in (frame, icon_lbl, text_lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def _set_active_nav(self, key):
        for k, it in self.nav_items.items():
            active = (k == key)
            it["frame"].configure(fg_color=T.ACCENT_900 if active else "transparent")
            it["text"].configure(text_color=T.ACCENT_200 if active else T.N400)
            it["icon"].configure(text_color=T.ACCENT_300 if active else T.N400)
            if active:
                it["bar"].place(x=0, y=8)
            else:
                it["bar"].place_forget()

    def _pulse_dot(self):
        cur = self.dot.cget("text_color")
        self.dot.configure(text_color=T.ACCENT_800 if cur == T.ACCENT_400 else T.ACCENT_400)
        self.after(1200, self._pulse_dot)

    # ══════════════════════════════════════════════════════════ routing ═════

    def show_screen(self, name):
        self.current_screen = name
        for n, f in self.screens.items():
            f.grid_forget()
        self.screens[name].grid(row=0, column=0, sticky="nsew")
        self._set_active_nav(name)
        if name == "history":
            self._refresh_history()

    # ══════════════════════════════════════════════════════════════ home ════

    def _build_home(self):
        home = ctk.CTkFrame(self.container, fg_color=T.BG, corner_radius=0)
        home.grid_rowconfigure(0, weight=1)
        home.grid_columnconfigure(0, weight=1)
        home.grid_columnconfigure(1, weight=0)
        self.screens["home"] = home

        content = ctk.CTkScrollableFrame(home, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=(34, 10), pady=(30, 20))
        content.grid_columnconfigure(0, weight=1)

        # Başlık
        head = ctk.CTkFrame(content, fg_color="transparent")
        head.pack(fill="x", pady=(0, 4), anchor="w")
        ctk.CTkLabel(head, text="Bir bağlantı yapıştırın", font=self.f_h2,
                     text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(head, text="YouTube, Instagram, X ve yt-dlp'nin desteklediği yüzlerce platform.",
                     font=self.f_body, text_color=T.N500).pack(anchor="w", pady=(4, 0))

        # URL satırı
        url_row = ctk.CTkFrame(content, fg_color="transparent")
        url_row.pack(fill="x", pady=(22, 0))
        wrap = ctk.CTkFrame(url_row, height=52, corner_radius=26, fg_color=T.PANEL,
                            border_width=1, border_color=T.ACCENT_800)
        wrap.pack(side="left", fill="x", expand=True, padx=(0, 11))
        wrap.pack_propagate(False)
        ctk.CTkLabel(wrap, text="🔗", font=ctk.CTkFont(size=14),
                     text_color=T.N500).pack(side="left", padx=(18, 0))
        self.url_entry = ctk.CTkEntry(wrap, placeholder_text="Yapıştırın veya arayın...",
                                      border_width=0, fg_color="transparent",
                                      font=self.f_body, text_color=T.TEXT,
                                      placeholder_text_color=T.N600)
        self.url_entry.pack(side="left", fill="both", expand=True, padx=12, pady=6)
        ctk.CTkLabel(wrap, text="Ctrl + V", font=self.f_tiny,
                     text_color=T.N600).pack(side="right", padx=18)
        ctk.CTkButton(url_row, text="İNDİR", font=self.f_btn, width=120, height=52,
                      corner_radius=26, fg_color=T.ACCENT_600, hover_color=T.ACCENT_700,
                      text_color="#ffffff", command=self.start_download).pack(side="left")

        # Biçim
        self._kicker(content, "Biçim").pack(anchor="w", pady=(26, 12))
        fmt = ctk.CTkFrame(content, fg_color="transparent")
        fmt.pack(fill="x")
        cards = [
            ("both", "Video + Ses", "En yüksek kalite"),
            ("mp4",  "Sadece MP4",  "H.264 + AAC"),
            ("mp3",  "Sadece Ses",  "MP3 · 320 kbps"),
        ]
        for key, title, sub in cards:
            self._make_format_card(fmt, key, title, sub)
        self._update_format_cards()

        # Kayıt yeri
        self._kicker(content, "Kayıt yeri").pack(anchor="w", pady=(26, 12))
        path_row = ctk.CTkFrame(content, fg_color="transparent")
        path_row.pack(fill="x")
        pbox = ctk.CTkFrame(path_row, height=42, corner_radius=T.RADIUS_MD, fg_color=T.PANEL,
                            border_width=1, border_color=T.BORDER)
        pbox.pack(side="left", fill="x", expand=True, padx=(0, 10))
        pbox.pack_propagate(False)
        ctk.CTkLabel(pbox, text="📁", font=ctk.CTkFont(size=13),
                     text_color=T.N500).pack(side="left", padx=(14, 8))
        ctk.CTkLabel(pbox, textvariable=self.path_var, font=self.f_body,
                     text_color=T.N300, anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(path_row, text="Gözat", font=self.f_body, width=90, height=42,
                      corner_radius=T.RADIUS_MD, fg_color=T.PANEL, hover_color=T.N900,
                      border_width=1, border_color=T.BORDER, text_color=T.N200,
                      command=self.browse_folder).pack(side="left")

        # Aktif indirme
        act_head = ctk.CTkFrame(content, fg_color="transparent")
        act_head.pack(fill="x", pady=(26, 12))
        self._kicker(act_head, "Aktif indirme").pack(side="left")
        self.lbl_status = ctk.CTkLabel(act_head, text="Hazır", font=self.f_tiny,
                                       text_color=T.N600)
        self.lbl_status.pack(side="right")

        card = self._card(content, corner_radius=T.RADIUS_LG)
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        self.thumb = ctk.CTkFrame(inner, width=130, height=74, corner_radius=T.RADIUS_MD,
                                  fg_color=T.PANEL_ALT, border_width=1, border_color=T.BORDER)
        self.thumb.pack(side="left", padx=(0, 16))
        self.thumb.pack_propagate(False)
        self.thumb_lbl = ctk.CTkLabel(self.thumb, text="▶", font=ctk.CTkFont(size=22),
                                      text_color=T.N700)
        self.thumb_lbl.pack(expand=True)

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        title_row = ctk.CTkFrame(info, fg_color="transparent")
        title_row.pack(fill="x")
        self.lbl_title = ctk.CTkLabel(title_row, text="Bekleniyor...", font=self.f_body_m,
                                      text_color=T.TEXT, anchor="w")
        self.lbl_title.pack(side="left", fill="x", expand=True)
        self.lbl_fmt_tag = self._tag(title_row, "", T.ACCENT_800, T.ACCENT_100)
        self.progress = ctk.CTkProgressBar(info, height=6, corner_radius=3,
                                           progress_color=T.ACCENT_500, fg_color=T.N900)
        self.progress.pack(fill="x", pady=(11, 9))
        self.progress.set(0)
        meta = ctk.CTkFrame(info, fg_color="transparent")
        meta.pack(fill="x")
        self.lbl_prog = ctk.CTkLabel(meta, text="Hazır", font=self.f_tiny, text_color=T.N500)
        self.lbl_prog.pack(side="left")
        self.lbl_speed = ctk.CTkLabel(meta, text="", font=self.f_tiny, text_color=T.N500)
        self.lbl_speed.pack(side="right")

        # ── Sağ ray ─────────────────────────────────────────────────────────
        self._build_home_rail(home)

    def _build_home_rail(self, home):
        rail = ctk.CTkScrollableFrame(home, fg_color=T.RAIL_BG, width=300, corner_radius=0)
        rail.grid(row=0, column=1, sticky="nsew")
        rail.grid_columnconfigure(0, weight=1)

        # Oturum
        self._kicker(rail, "Oturum").pack(anchor="w", padx=6, pady=(14, 12))
        stats = ctk.CTkFrame(rail, fg_color="transparent")
        stats.pack(fill="x", padx=6)
        c1 = self._card(stats)
        c1.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.lbl_success = ctk.CTkLabel(c1, text="0", font=self.f_stat, text_color=T.ACCENT_300)
        self.lbl_success.pack(anchor="w", padx=14, pady=(14, 0))
        ctk.CTkLabel(c1, text="Başarılı", font=self.f_tiny, text_color=T.N500).pack(
            anchor="w", padx=14, pady=(4, 14))
        c2 = self._card(stats)
        c2.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.lbl_error = ctk.CTkLabel(c2, text="0", font=self.f_stat, text_color=T.N400)
        self.lbl_error.pack(anchor="w", padx=14, pady=(14, 0))
        ctk.CTkLabel(c2, text="Hatalı", font=self.f_tiny, text_color=T.N500).pack(
            anchor="w", padx=14, pady=(4, 14))

        # Sistem durumu
        self._kicker(rail, "Sistem durumu").pack(anchor="w", padx=6, pady=(28, 12))
        sysf = ctk.CTkFrame(rail, fg_color="transparent")
        sysf.pack(fill="x", padx=6)
        ff_ok, _ = check_ffmpeg_installed()
        rows = [
            ("İndirme motoru", "Aktif", T.ACCENT_300),
            ("FFmpeg", "Kurulu" if ff_ok else "Eksik", T.ACCENT_300 if ff_ok else "#ff6b6b"),
            ("Motor sürümü", get_active_version() or "—", T.N300),
            ("Uygulama", f"v{get_current_version()}", T.N300),
        ]
        for label, value, color in rows:
            r = ctk.CTkFrame(sysf, fg_color="transparent")
            r.pack(fill="x", pady=5)
            ctk.CTkLabel(r, text=label, font=self.f_body, text_color=T.N500).pack(side="left")
            ctk.CTkLabel(r, text=value, font=self.f_body, text_color=color).pack(side="right")

        # Motor güncelleme kartı (varsayılan gizli)
        self.engine_card = ctk.CTkFrame(rail, fg_color=T.ACCENT_900, corner_radius=T.RADIUS_MD,
                                        border_width=1, border_color=T.ACCENT_800)
        ctk.CTkLabel(self.engine_card, text="Motor güncellemesi hazır", font=self.f_small,
                     text_color=T.TEXT, anchor="w").pack(fill="x", padx=15, pady=(15, 5))
        self.engine_card_body = ctk.CTkLabel(
            self.engine_card, text="", font=self.f_tiny, text_color=T.ACCENT_200,
            anchor="w", justify="left", wraplength=230)
        self.engine_card_body.pack(fill="x", padx=15)
        ctk.CTkButton(self.engine_card, text="Yeniden başlat", font=self.f_tiny, height=30,
                      fg_color="transparent", hover_color=T.ACCENT_800, text_color=T.ACCENT_300,
                      command=self._restart_app).pack(anchor="w", padx=11, pady=(11, 13))

        # Kısayollar
        ctk.CTkLabel(rail, text="Kısayollar", font=self.f_tiny, text_color=T.N600).pack(
            anchor="w", padx=6, pady=(28, 2))
        ctk.CTkLabel(rail, text="Ctrl+V yapıştır · Enter indir", font=self.f_tiny,
                     text_color=T.N500).pack(anchor="w", padx=6)

    def _make_format_card(self, parent, key, title, sub):
        card = ctk.CTkFrame(parent, fg_color=T.PANEL, corner_radius=T.RADIUS_MD,
                            border_width=1, border_color=T.BORDER)
        card.pack(side="left", padx=(0, 9))
        t = ctk.CTkLabel(card, text=title, font=self.f_body_m, text_color=T.TEXT)
        t.pack(anchor="w", padx=17, pady=(13, 0))
        s = ctk.CTkLabel(card, text=sub, font=self.f_tiny, text_color=T.N500)
        s.pack(anchor="w", padx=17, pady=(2, 13))
        self.format_cards[key] = card

        def choose(_=None):
            self.format_choice = key
            self._update_format_cards()

        for w in (card, t, s):
            w.bind("<Button-1>", choose)

    def _update_format_cards(self):
        for key, card in self.format_cards.items():
            if key == self.format_choice:
                card.configure(fg_color=T.ACCENT_900, border_color=T.ACCENT_600)
            else:
                card.configure(fg_color=T.PANEL, border_color=T.BORDER)

    # ═══════════════════════════════════════════════════════════ history ════

    def _build_history(self):
        scr = ctk.CTkFrame(self.container, fg_color=T.BG, corner_radius=0)
        self.screens["history"] = scr

        head = ctk.CTkFrame(scr, fg_color="transparent")
        head.pack(fill="x", padx=34, pady=(34, 0))
        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="İndirme Geçmişi", font=self.f_h2, text_color=T.TEXT).pack(anchor="w")
        self.lbl_hist_sub = ctk.CTkLabel(left, text="", font=self.f_body, text_color=T.N500)
        self.lbl_hist_sub.pack(anchor="w", pady=(4, 0))
        ctk.CTkButton(head, text="Geçmişi temizle", font=self.f_small, height=34, width=130,
                      fg_color="transparent", hover_color=T.N900, text_color=T.ACCENT_300,
                      command=self._clear_history).pack(side="right")

        # Sütun başlıkları
        header = ctk.CTkFrame(scr, fg_color="transparent")
        header.pack(fill="x", padx=34, pady=(22, 0))
        for text, w in (("BAŞLIK", 0), ("BİÇİM", 120), ("TARİH", 150), ("", 110)):
            lbl = ctk.CTkLabel(header, text=text, font=self.f_tiny, text_color=T.N600,
                               anchor="w", width=w if w else 0)
            lbl.pack(side="left", fill="x", expand=(w == 0))
        ctk.CTkFrame(scr, height=1, fg_color=T.N900).pack(fill="x", padx=34, pady=(6, 0))

        self.hist_scroll = ctk.CTkScrollableFrame(scr, fg_color="transparent")
        self.hist_scroll.pack(fill="both", expand=True, padx=28, pady=(4, 20))

    def _refresh_history(self):
        for c in self.hist_scroll.winfo_children():
            c.destroy()
        history = load_history()
        self.lbl_hist_sub.configure(
            text=f"Bu bilgisayarda tamamlanan {len(history)} işlem." if history
            else "Henüz tamamlanmış indirme yok.")
        if not history:
            ctk.CTkLabel(self.hist_scroll, text="İndirme geçmişi boş.", font=self.f_body,
                         text_color=T.N500).pack(pady=20)
            return
        for item in history:
            row = ctk.CTkFrame(self.hist_scroll, fg_color="transparent", height=48)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=item.get('title', 'Bilinmeyen'), font=self.f_body,
                         text_color=T.N200, anchor="w").pack(
                side="left", fill="x", expand=True, padx=(6, 8))
            self._tag(row, item.get('type', '—'), T.N800, T.N100).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=item.get('date', ''), font=self.f_small,
                         text_color=T.N500, width=150, anchor="w").pack(side="left")
            path = item.get('path', '')
            ctk.CTkButton(row, text="Klasörü aç", font=self.f_tiny, width=100, height=30,
                          fg_color="transparent", hover_color=T.N900, text_color=T.ACCENT_300,
                          command=lambda p=path: self._open_folder(p)).pack(side="right", padx=6)
            ctk.CTkFrame(self.hist_scroll, height=1, fg_color=T.N900).pack(fill="x")

    def _clear_history(self):
        if not load_history():
            return
        if messagebox.askyesno("Geçmişi temizle",
                               "Tüm indirme geçmişi silinsin mi?\nDosyalarınız silinmez, yalnızca liste temizlenir."):
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception as e:
                messagebox.showerror("Hata", f"Geçmiş temizlenemedi: {e}")
            self._refresh_history()

    def _open_folder(self, path):
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("Uyarı", "Seçili klasör artık mevcut değil.")

    # ══════════════════════════════════════════════════════════ settings ════

    def _build_settings(self):
        scr = ctk.CTkFrame(self.container, fg_color=T.BG, corner_radius=0)
        self.screens["settings"] = scr
        wrap = ctk.CTkScrollableFrame(scr, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=34, pady=(34, 20))

        ctk.CTkLabel(wrap, text="Ayarlar", font=self.f_h2, text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text="Tercihler settings.json dosyasında saklanır.",
                     font=self.f_body, text_color=T.N500).pack(anchor="w", pady=(4, 22))

        body = ctk.CTkFrame(wrap, fg_color="transparent")
        body.pack(fill="x")
        body.configure(width=720)

        # Tema
        r1 = self._settings_row(body, "Görünüm teması",
                                "Uygulama Nocturne koyu teması için ayarlanmıştır.")
        self.seg_theme = ctk.CTkSegmentedButton(
            r1, values=["Koyu", "Açık", "Sistem"], command=self._change_theme,
            font=self.f_small, fg_color=T.SIDEBAR_BG,
            selected_color=T.ACCENT_700, selected_hover_color=T.ACCENT_600,
            unselected_color=T.SIDEBAR_BG, unselected_hover_color=T.N900,
            text_color=T.N300)
        tr = {"Dark": "Koyu", "Light": "Açık", "System": "Sistem"}
        self.seg_theme.set(tr.get(self.settings.get('theme', 'Dark'), "Koyu"))
        self.seg_theme.pack(side="right")

        # MP4 varsayılan
        r2 = self._settings_row(body, "İndirmelerde \"Sadece MP4\" varsayılan olsun",
                                "H.264 + AAC doğrudan çekilir, dönüştürme beklemezsiniz.")
        self.sw_mp4 = ctk.CTkSwitch(r2, text="", width=44, progress_color=T.ACCENT_600,
                                    fg_color=T.N800, button_color=T.N100,
                                    command=self._toggle_mp4)
        if self.settings.get('default_mp4', True):
            self.sw_mp4.select()
        self.sw_mp4.pack(side="right")

        # Otomatik klasör
        r3 = self._settings_row(body, "İndirme bitince klasörü otomatik aç",
                                "Dosya gezgini tamamlanan indirmenin klasöründe açılır.")
        self.sw_auto = ctk.CTkSwitch(r3, text="", width=44, progress_color=T.ACCENT_600,
                                     fg_color=T.N800, button_color=T.N100,
                                     command=self._toggle_auto)
        if self.settings.get('auto_open_folder', False):
            self.sw_auto.select()
        self.sw_auto.pack(side="right")

    def _settings_row(self, parent, title, sub):
        card = ctk.CTkFrame(parent, fg_color=T.PANEL, corner_radius=T.RADIUS_MD)
        card.pack(fill="x", pady=2)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text=title, font=self.f_body_m, text_color=T.TEXT,
                     anchor="w", justify="left").pack(anchor="w")
        ctk.CTkLabel(left, text=sub, font=self.f_small, text_color=T.N500,
                     anchor="w", justify="left").pack(anchor="w", pady=(3, 0))
        return inner

    def _change_theme(self, choice):
        mp = {"Koyu": "Dark", "Açık": "Light", "Sistem": "System"}
        val = mp.get(choice, "Dark")
        ctk.set_appearance_mode(val)
        set_setting('theme', val)

    def _toggle_mp4(self):
        val = bool(self.sw_mp4.get())
        set_setting('default_mp4', val)
        self.format_choice = "mp4" if val else "both"
        self._update_format_cards()

    def _toggle_auto(self):
        set_setting('auto_open_folder', bool(self.sw_auto.get()))

    # ══════════════════════════════════════════════════════════════ help ════

    def _build_help(self):
        scr = ctk.CTkFrame(self.container, fg_color=T.BG, corner_radius=0)
        self.screens["help"] = scr
        wrap = ctk.CTkScrollableFrame(scr, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=34, pady=(34, 20))

        ctk.CTkLabel(wrap, text="Yardım", font=self.f_h2, text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text="Sistem gereksinimleri ve sık sorulanlar.",
                     font=self.f_body, text_color=T.N500).pack(anchor="w", pady=(4, 22))

        ff_ok, _ = check_ffmpeg_installed()
        cards = ctk.CTkFrame(wrap, fg_color="transparent")
        cards.pack(fill="x")
        stat_cards = [
            ("FFmpeg", "Kurulu ve çalışıyor" if ff_ok else "Bulunamadı",
             T.ACCENT_300 if ff_ok else "#ff6b6b"),
            ("İndirme motoru", f"yt-dlp {get_active_version() or '—'}", T.N200),
            ("Uygulama", f"v{get_current_version()} · güncel", T.N200),
        ]
        for label, value, color in stat_cards:
            c = self._card(cards)
            c.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ctk.CTkLabel(c, text=label, font=self.f_small, text_color=T.N500).pack(
                anchor="w", padx=16, pady=(16, 4))
            ctk.CTkLabel(c, text=value, font=self.f_h3, text_color=color).pack(
                anchor="w", padx=16, pady=(0, 16))

        if not ff_ok:
            warn = ctk.CTkFrame(wrap, fg_color=T.PANEL, corner_radius=T.RADIUS_MD)
            warn.pack(fill="x", pady=(14, 0))
            ctk.CTkLabel(warn, text="FFmpeg bulunamadı. MP3 dönüştürme ve MP4 birleştirme hata verebilir.",
                         font=self.f_small, text_color="#ff8888", anchor="w",
                         justify="left").pack(side="left", padx=16, pady=12)
            ctk.CTkButton(warn, text="Nasıl kurarım?", font=self.f_tiny, width=110, height=30,
                          fg_color="transparent", hover_color=T.N900, text_color=T.ACCENT_300,
                          command=lambda: webbrowser.open("https://ffmpeg.org/download.html")
                          ).pack(side="right", padx=12)

        faq = [
            ("Nasıl indiririm?",
             "Ana sayfada URL kutusuna bağlantıyı yapıştırın, biçimi ve kayıt yerini seçin, İNDİR'e basın."),
            ("Hangi platformlar destekleniyor?",
             "YouTube, Instagram, X dahil yt-dlp'nin desteklediği çoğu güncel platform."),
            ("\"Sadece MP4\" ne yapar?",
             "YouTube normalde Opus/WebM verir. Bu seçenekle H.264 + AAC doğrudan çekilir, dönüştürme adımı atlanır."),
            ("İndirdiğim dosyaları nerede bulurum?",
             "İndirme Geçmişi ekranından ilgili satırın klasörünü açabilirsiniz."),
            ("FFmpeg nedir?",
             "MP3 dönüştürme ve video–ses birleştirme için gereken araç. Paketlenmiş sürümde uygulamayla birlikte gelir."),
        ]
        fbox = ctk.CTkFrame(wrap, fg_color="transparent")
        fbox.pack(fill="x", pady=(20, 0))
        for q, a in faq:
            item = ctk.CTkFrame(fbox, fg_color="transparent")
            item.pack(fill="x", pady=(0, 0))
            ctk.CTkLabel(item, text=q, font=self.f_body_m, text_color=T.TEXT,
                         anchor="w").pack(anchor="w", pady=(16, 4))
            ctk.CTkLabel(item, text=a, font=self.f_body, text_color=T.N500, anchor="w",
                         justify="left", wraplength=760).pack(anchor="w", pady=(0, 16))
            ctk.CTkFrame(fbox, height=1, fg_color=T.N900).pack(fill="x")

    # ══════════════════════════════════════════════════════ downloading ═════

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            set_setting('last_folder', folder)

    def start_download(self):
        video_url = self.url_entry.get().strip()
        save_path = self.path_var.get().strip()
        if not video_url or not save_path:
            messagebox.showwarning("Uyarı", "Lütfen URL ve Kayıt Yeri belirtiniz.")
            return

        audio_only = self.format_choice == "mp3"
        mp4_only = self.format_choice == "mp4"
        ftyp = "MP3 Audio" if audio_only else ("MP4 Video" if mp4_only else "Default Video")
        fmt_tag = {"mp3": "MP3 320", "mp4": "MP4", "both": "Video + Ses"}[self.format_choice]

        self.show_screen("home")
        self.lbl_title.configure(text="Sorgulanıyor...")
        self.lbl_fmt_tag._label.configure(text=fmt_tag)
        self.lbl_fmt_tag.pack(side="right", padx=(8, 0))
        self.lbl_status.configure(text="1 işlem sürüyor", text_color=T.ACCENT_300)
        self.lbl_prog.configure(text="İndiriliyor · %0")
        self.lbl_speed.configure(text="")
        self.progress.set(0)

        threading.Thread(target=self._run_downloader_thread,
                         args=(video_url, save_path, audio_only, mp4_only, ftyp),
                         daemon=True).start()

    def _run_downloader_thread(self, video_url, save_path, audio_only, mp4_only, ftyp):
        self.current_download_type = ftyp
        self.current_save_path = save_path
        self.downloader.download(video_url, save_path, audio_only, mp4_only)
        self.after(0, lambda: self.url_entry.delete(0, 'end'))

    def on_download_info(self, video_title, thumbnail_url):
        img_ctk = None
        if thumbnail_url:
            try:
                r = requests.get(thumbnail_url, timeout=5)
                if r.status_code == 200:
                    image_data = Image.open(BytesIO(r.content))
                    img_ctk = ctk.CTkImage(light_image=image_data, dark_image=image_data,
                                           size=(130, 74))
            except Exception as e:
                print(f"Thumbnail yüklenemedi: {e}")
        self.after(0, self._show_video_info, video_title, img_ctk)

    def _show_video_info(self, video_title, img_ctk):
        self.lbl_title.configure(text=video_title)
        if img_ctk:
            self._thumb_img = img_ctk
            self.thumb_lbl.configure(image=img_ctk, text="")
        else:
            self.thumb_lbl.configure(image=None, text="▶")

    def update_progress(self, progress):
        self.after(0, self._update_progress_ui, progress)

    def _update_progress_ui(self, progress):
        self.progress.set(progress / 100)
        self.lbl_prog.configure(text=f"İndiriliyor · %{progress}")

    def on_download_success(self, video_title):
        self.after(0, self._show_success, video_title)

    def _show_success(self, video_title):
        self.progress.set(1)
        self.lbl_prog.configure(text="Tamamlandı", text_color=T.ACCENT_300)
        self.lbl_status.configure(text="Başarıyla tamamlandı", text_color=T.ACCENT_300)
        self.lbl_title.configure(text=video_title)
        self.success_downloads += 1
        self.lbl_success.configure(text=str(self.success_downloads))
        add_to_history(video_title, self.current_save_path, self.current_download_type)
        if get_setting('auto_open_folder'):
            self._open_folder(self.current_save_path)

    def on_download_error(self, error_msg):
        self.after(0, self._show_error, error_msg)

    def _show_error(self, error_msg):
        self.progress.set(0)
        self.lbl_prog.configure(text="İndirme başarısız", text_color="#ff6b6b")
        self.lbl_status.configure(text="Hata oluştu", text_color="#ff6b6b")
        self.lbl_title.configure(text="Hata oluştu.")
        self.error_downloads += 1
        self.lbl_error.configure(text=str(self.error_downloads))
        messagebox.showerror("Hata", error_msg)

    # ═══════════════════════════════════════════════════════════ updates ════

    def _check_updates_async(self):
        update_available, new_version, download_url = check_for_updates()
        if update_available:
            self.after(2000, self._prompt_update, new_version, download_url)

    def _prompt_update(self, new_version, download_url):
        current = get_current_version()
        if messagebox.askyesno(
            "Yeni Güncelleme Mevcut!",
            f"Video Downloader Pro'nun yeni bir sürümü ({new_version}) bulundu.\n"
            f"(Mevcut Sürümünüz: {current})\n\nŞimdi güncellenip yeniden başlatılsın mı?"):
            success, msg = perform_update(download_url)
            if success:
                messagebox.showinfo("Güncelleniyor", msg)
                self.destroy()
            else:
                messagebox.showerror("Güncelleme Hatası", msg)

    def _on_ytdlp_updated(self, new_version):
        self.after(0, self._show_ytdlp_updated, new_version)

    def _show_ytdlp_updated(self, new_version):
        self.engine_card_body.configure(
            text=f"yt-dlp {new_version} indirildi. Uygulamayı yeniden "
                 "başlattığınızda etkinleşir.")
        self.engine_card.pack(fill="x", padx=6, pady=(20, 0))

    def _restart_app(self):
        try:
            subprocess.Popen([sys.executable] + sys.argv)
        except Exception as e:
            print(f"Yeniden başlatılamadı: {e}")
        self.destroy()
