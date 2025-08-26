(function () {
  const ONE_SEC = 1000;
  let initialLeftMs = null;

  function pad2(n) { return String(n).padStart(2, "0"); }
  function fmtCountdown(ms) {
    const t = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(t / 60);
    const s = t % 60;
    return `${pad2(m)}:${pad2(s)}`;
  }
  function relTime(ms) {
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.round(s / 60);
    if (m < 60) return `${m}m`;
    const h = Math.round(m / 60);
    return `${h}h`;
  }
  function setChip(el, state) {
    el.classList.remove("chip-open", "chip-closing", "chip-closed");
    if (state === "open") { el.classList.add("chip-open"); el.textContent = "✅ Gate Open"; }
    else if (state === "closing") { el.classList.add("chip-closing"); el.textContent = "⚠️ Gate Closing Soon"; }
    else { el.classList.add("chip-closed"); el.textContent = "🚧 Gate Closed"; }
  }

  window.initHeroCountdown = function ({ preCloseSec = 120, enableSticky = true } = {}) {
    const hero = document.getElementById("hero");
    if (!hero) return;
    const etaStr = hero.dataset.eta;
    if (!etaStr) return;

    const eta = new Date(etaStr).getTime();
    const statusEl = document.getElementById("gate-status");
    const cdEl = document.getElementById("countdown");
    const ariaEl = document.getElementById("countdown-aria");
    const sticky = document.getElementById("stickyNow");
    const stickyCd = document.getElementById("stickyCountdown");
    const stickyProg = document.getElementById("stickyProgress");

    function tick() {
      const now = Date.now();
      const diff = eta - now;

      if (initialLeftMs === null) initialLeftMs = Math.max(diff, 60 * 1000);

      if (diff <= 0) {
        cdEl && (cdEl.textContent = "00:00");
        stickyCd && (stickyCd.textContent = "00:00");
        setChip(statusEl, "closed");
        ariaEl && (ariaEl.textContent = "Gate closed.");
        if (sticky) sticky.hidden = false, stickyProg.style.width = "100%";
        return;
      }

      const closingMs = preCloseSec * 1000;
      cdEl && (cdEl.textContent = fmtCountdown(diff));
      ariaEl && (ariaEl.textContent = `Arrives in ${fmtCountdown(diff)}.`);
      if (diff <= closingMs) setChip(statusEl, "closing"); else setChip(statusEl, "open");

      if (enableSticky && sticky && stickyCd && stickyProg) {
        sticky.hidden = false;
        stickyCd.textContent = fmtCountdown(diff);
        const pct = Math.min(1, Math.max(0, 1 - diff / initialLeftMs));
        stickyProg.style.width = (pct * 100).toFixed(1) + "%";
      }
    }

    tick();
    setInterval(tick, ONE_SEC);
  };

  window.initRelativeTimes = function () {
    function update() {
      const now = Date.now();
      document.querySelectorAll("[data-eta] .rel, tr[data-eta] .rel, article[data-eta] .rel").forEach((row) => {
        const el = row.closest("[data-eta]"); if (!el) return;
        const etaStr = el.getAttribute("data-eta"); if (!etaStr) return;
        const diff = new Date(etaStr).getTime() - now;
        row.textContent = diff <= 0 ? "now" : `in ${relTime(diff)}`;
      });
    }
    update();
    setInterval(update, 15 * ONE_SEC);
  };

  // Text size controls
  const root = document.documentElement;
  function applyScale(px) { root.style.setProperty("font-size", `${px}px`); }
  function getScale() { return Math.min(24, Math.max(16, Number(localStorage.getItem("rg_font_scale") || 18))); }
  function setScale(n) { const v = Math.min(24, Math.max(16, n)); localStorage.setItem("rg_font_scale", v); applyScale(v); }

  window.addEventListener("DOMContentLoaded", () => {
    applyScale(getScale());
    const dec = document.getElementById("dec-font");
    const inc = document.getElementById("inc-font");
    dec && dec.addEventListener("click", () => setScale(getScale() - 1));
    inc && inc.addEventListener("click", () => setScale(getScale() + 1));
  });
})();