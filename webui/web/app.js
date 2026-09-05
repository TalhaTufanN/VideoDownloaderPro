/* Video Downloader Pro — arayüz mantığı. Python tarafı ile
   window.pywebview.api üzerinden konuşur; Python geri bildirimleri
   window.app.on*() fonksiyonlarını evaluate_js ile çağırarak gönderir. */

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const state = {
  format: "both",
  path: "",
  running: false,
  faq: [
    ["Nasıl indiririm?", "Ana sayfada URL kutusuna bağlantıyı yapıştırın, biçimi ve kayıt yerini seçin, İNDİR'e basın."],
    ["Hangi platformlar destekleniyor?", "YouTube, Instagram, X dahil yt-dlp'nin desteklediği çoğu güncel platform."],
    ["\"Sadece MP4\" ne yapar?", "YouTube yüksek çözünürlükte genelde VP9/AV1 (WebM/MKV) verir. \"Sadece MP4\" H.264 + AAC ile sınırlar: her cihazda oynar ama bazen maksimum çözünürlük biraz düşük olabilir. \"Video + Ses\" ise codec fark etmeden en yüksek kaliteyi indirir."],
    ["İndirdiğim dosyaları nerede bulurum?", "İndirme Geçmişi ekranından ilgili satırın klasörünü açabilirsiniz."],
    ["FFmpeg nedir?", "MP3 dönüştürme ve video–ses birleştirme için gereken araç. Paketlenmiş sürümde uygulamayla birlikte gelir."],
  ],
};

/* ── Navigation ────────────────────────────────────────────────────────── */
function showScreen(name) {
  document.querySelectorAll(".nav-item").forEach(n =>
    n.classList.toggle("active", n.dataset.screen === name));
  document.querySelectorAll(".screen").forEach(s =>
    s.classList.toggle("active", s.id === "screen-" + name));
}
document.querySelectorAll(".nav-item").forEach(n =>
  n.addEventListener("click", async () => {
    showScreen(n.dataset.screen);
    if (n.dataset.screen === "history") renderHistory(await api().get_history());
  }));

/* ── Format selection ──────────────────────────────────────────────────── */
function setFormat(fmt) {
  state.format = fmt;
  document.querySelectorAll(".fmt-card").forEach(c =>
    c.classList.toggle("sel", c.dataset.fmt === fmt));
}
document.querySelectorAll(".fmt-card").forEach(c =>
  c.addEventListener("click", () => setFormat(c.dataset.fmt)));

/* ── Actions ───────────────────────────────────────────────────────────── */
async function browse() {
  const p = await api().choose_folder();
  if (p) { state.path = p; $("path-label").textContent = p; }
}

async function startDownload() {
  const url = $("url").value.trim();
  if (!url) { $("url").focus(); return; }
  if (!state.path) { alert("Lütfen bir kayıt yeri seçin."); return; }
  state.running = true;
  $("active-title").textContent = "Sorgulanıyor...";
  const tag = { both: "Video + Ses", mp4: "MP4", mp3: "MP3 320" }[state.format];
  const tagEl = $("active-tag"); tagEl.textContent = tag; tagEl.hidden = false;
  $("active-status").textContent = "1 işlem sürüyor";
  $("progress-label").textContent = "İndiriliyor · %0";
  $("speed-label").textContent = "";
  $("progress-bar").style.width = "0%";
  showScreen("home");
  await api().start_download(url, state.format, state.path);
}

$("btn-download").addEventListener("click", startDownload);
$("btn-browse").addEventListener("click", browse);
$("url").addEventListener("keydown", e => { if (e.key === "Enter") startDownload(); });
$("btn-restart").addEventListener("click", () => api().restart_app());
$("btn-clear-history").addEventListener("click", async () => {
  if (confirm("Tüm indirme geçmişi silinsin mi?\nDosyalarınız silinmez, yalnızca liste temizlenir.")) {
    const hist = await api().clear_history();
    renderHistory(hist);
  }
});
$("btn-ffmpeg-help").addEventListener("click", () =>
  api().open_url("https://ffmpeg.org/download.html"));

/* Theme segmented + toggles */
document.querySelectorAll("#seg-theme .opt").forEach(o =>
  o.addEventListener("click", () => {
    document.querySelectorAll("#seg-theme .opt").forEach(x => x.classList.remove("sel"));
    o.classList.add("sel");
    api().set_setting("theme", o.dataset.theme);
  }));
function wireToggle(id, key, onChange) {
  $(id).addEventListener("click", () => {
    const on = !$(id).classList.contains("on");
    $(id).classList.toggle("on", on);
    api().set_setting(key, on);
    if (onChange) onChange(on);
  });
}
wireToggle("tg-mp4", "default_mp4", (on) => setFormat(on ? "mp4" : "both"));
wireToggle("tg-auto", "auto_open_folder");

/* ── Rendering ─────────────────────────────────────────────────────────── */
function renderHistory(list) {
  const body = $("hist-body");
  $("hist-sub").textContent = list.length
    ? `Bu bilgisayarda tamamlanan ${list.length} işlem.`
    : "Henüz tamamlanmış indirme yok.";
  body.innerHTML = "";
  if (!list.length) {
    body.innerHTML = `<tr><td colspan="4" class="empty">İndirme geçmişi boş.</td></tr>`;
    return;
  }
  for (const h of list) {
    const tr = document.createElement("tr");
    const title = document.createElement("td");
    title.className = "title-cell"; title.textContent = h.title || "Bilinmeyen";
    const fmt = document.createElement("td");
    fmt.innerHTML = `<span class="tag tag-neutral"></span>`;
    fmt.querySelector("span").textContent = h.type || "—";
    const date = document.createElement("td");
    date.className = "muted"; date.textContent = h.date || "";
    const act = document.createElement("td");
    act.style.textAlign = "right";
    const btn = document.createElement("button");
    btn.className = "btn btn-ghost"; btn.style.height = "30px"; btn.textContent = "Klasörü aç";
    btn.addEventListener("click", () => api().open_folder(h.path || ""));
    act.appendChild(btn);
    tr.append(title, fmt, date, act);
    body.appendChild(tr);
  }
}

function renderFaq() {
  const box = $("faq");
  box.innerHTML = "";
  for (const [q, a] of state.faq) {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `<div class="q"></div><div class="a"></div>`;
    item.querySelector(".q").textContent = q;
    item.querySelector(".a").textContent = a;
    box.appendChild(item);
  }
}

/* ── Backend durum yoklaması (pull) ────────────────────────────────────── */
const prev = {};
function applyState(s) {
  // İlerleme / durum
  if (s.status !== prev.status || s.pct !== prev.pct) {
    if (s.status === "running") {
      $("progress-bar").style.width = s.pct + "%";
      $("progress-label").textContent = "İndiriliyor · %" + s.pct;
      $("active-status").textContent = "1 işlem sürüyor";
    } else if (s.status === "success") {
      $("progress-bar").style.width = "100%";
      $("progress-label").textContent = "Tamamlandı";
      $("active-status").textContent = "Başarıyla tamamlandı";
      if (prev.status === "running") $("url").value = "";
    } else if (s.status === "error") {
      $("progress-bar").style.width = "0%";
      $("progress-label").textContent = "İndirme başarısız";
      $("active-status").textContent = "Hata oluştu";
      $("active-title").textContent = "Hata oluştu.";
    }
  }
  // Başlık / küçük resim
  if (s.title && s.title !== prev.title && s.status !== "error") {
    $("active-title").textContent = s.title;
  }
  if (s.thumb && s.thumb !== prev.thumb) {
    $("thumb").innerHTML = `<img src="${s.thumb}" alt="">`;
  }
  // Sayaçlar
  if (s.success !== prev.success) $("stat-success").textContent = s.success;
  if (s.error !== prev.error) $("stat-error").textContent = s.error;
  // Motor güncelleme kartı (kalıcı)
  if (s.engine_update && s.engine_update !== prev.engine_update) {
    $("engine-card-body").textContent =
      `yt-dlp ${s.engine_update} indirildi. Uygulamayı yeniden başlattığınızda etkinleşir.`;
    $("engine-card").hidden = false;
    $("sys-engine").textContent = s.engine_update;
  }
  // Tek seferlik olaylar
  if (s.error_msg) alert(s.error_msg);
  if (s.app_update) {
    if (confirm(`Video Downloader Pro'nun yeni bir sürümü (${s.app_update}) bulundu.\n\nŞimdi güncellenip yeniden başlatılsın mı?`)) {
      api().do_app_update();
    }
  }
  Object.assign(prev, {
    status: s.status, pct: s.pct, title: s.title, thumb: s.thumb,
    success: s.success, error: s.error, engine_update: s.engine_update,
  });
}

function startPolling() {
  setInterval(async () => {
    try { applyState(await api().poll()); } catch (e) { /* pencere kapanıyor olabilir */ }
  }, 300);
}

/* ── Init ──────────────────────────────────────────────────────────────── */
async function init() {
  renderFaq();
  const d = await api().get_initial();
  $("foot-engine").textContent = d.engine_version;
  $("foot-version").textContent = d.version;
  $("sys-engine").textContent = d.engine_version;
  $("sys-app").textContent = "v" + d.version;
  $("sys-ffmpeg").textContent = d.ffmpeg_ok ? "Kurulu" : "Eksik";
  $("sys-ffmpeg").className = "v " + (d.ffmpeg_ok ? "ok" : "bad");
  $("stat-success").textContent = d.success;
  $("stat-error").textContent = d.error;

  state.path = d.last_folder || "";
  $("path-label").textContent = state.path || "Klasör seçilmedi";
  setFormat(d.settings.default_mp4 ? "mp4" : "both");
  if (d.settings.default_mp4) $("tg-mp4").classList.add("on");
  if (d.settings.auto_open_folder) $("tg-auto").classList.add("on");
  document.querySelectorAll("#seg-theme .opt").forEach(o =>
    o.classList.toggle("sel", o.dataset.theme === (d.settings.theme || "Dark")));

  // Help cards
  $("help-ffmpeg").textContent = d.ffmpeg_ok ? "Kurulu ve çalışıyor" : "Bulunamadı";
  $("help-ffmpeg").className = "v " + (d.ffmpeg_ok ? "ok" : "bad");
  $("help-engine").textContent = "yt-dlp " + d.engine_version;
  $("help-app").textContent = "v" + d.version + " · güncel";
  $("help-warn").hidden = d.ffmpeg_ok;

  renderHistory(d.history || []);
  startPolling();
}

window.addEventListener("pywebviewready", init);
