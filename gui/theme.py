"""Nocturne tasarım sistemi token'ları (Claude Design projesinden aktarıldı).

Bu dosya uygulamanın koyu temasının tek doğruluk kaynağıdır. Renkleri burada
değiştirip tüm arayüze yayabilirsiniz. Kaynak: 'Video Downloader Pro.dc.html'
+ nocturne styles.css.
"""

import tkinter.font as tkfont

# ── Zemin & yüzeyler ────────────────────────────────────────────────────────
BG          = "#161826"   # ana zemin
SIDEBAR_BG  = "#14161f"   # sol kenar çubuğu
RAIL_BG     = "#171926"   # sağ bilgi rayı
PANEL       = "#1b1e2b"   # kart / girdi yüzeyi
PANEL_ALT   = "#1a1c28"   # ikincil kart

# ── Nötr rampa ──────────────────────────────────────────────────────────────
TEXT   = "#e9e9ed"
N100   = "#f3f5fe"
N200   = "#e4e7f5"
N300   = "#cfd3e5"
N400   = "#b2b6ca"
N500   = "#9397ab"
N600   = "#75798c"
N700   = "#595d6c"
N800   = "#3f424d"
N900   = "#292b31"

# ── Vurgu rampası (blurple) ─────────────────────────────────────────────────
ACCENT      = "#968ae0"   # accent-500
ACCENT_100  = "#f5f4ff"
ACCENT_200  = "#e7e5fe"
ACCENT_300  = "#d2cefd"
ACCENT_400  = "#b5abfc"
ACCENT_500  = "#968ae0"
ACCENT_600  = "#796cbf"
ACCENT_700  = "#5d5294"
ACCENT_800  = "#423a6a"
ACCENT_900  = "#2b2741"

# Kenarlıklar
BORDER       = N900
BORDER_HOVER = N800

# Köşe yarıçapları
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 14


def pick_family():
    """Inter varsa onu, yoksa Segoe UI / sistem yazı tipini kullan."""
    try:
        families = set(tkfont.families())
    except Exception:
        return "Segoe UI"
    for fam in ("Inter", "Segoe UI Variable Text", "Segoe UI"):
        if fam in families:
            return fam
    return "Segoe UI"
