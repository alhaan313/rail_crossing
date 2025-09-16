(function () {
  const ONE_SEC = 1000;
  let initialLeftMs = null;

  function pad2(n) { return String(n).padStart(2, "0"); }
  function fmtCountdown(ms) {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    
    if (totalSeconds < 60) {
      return totalSeconds === 1 ? '1 sec' : `${totalSeconds} secs`;
    }
    
    const totalMinutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    if (totalMinutes < 60) {
      if (seconds === 0) {
        return totalMinutes === 1 ? '1 min' : `${totalMinutes} mins`;
      }
      const minText = totalMinutes === 1 ? '1 min' : `${totalMinutes} mins`;
      const secText = seconds === 1 ? '1 sec' : `${seconds} secs`;
      return `${minText}, ${secText}`;
    }
    
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    
    if (minutes === 0) {
      return hours === 1 ? '1 hr' : `${hours} hrs`;
    }
    
    const hourText = hours === 1 ? '1 hr' : `${hours} hrs`;
    const minText = minutes === 1 ? '1 min' : `${minutes} mins`;
    return `${hourText}, ${minText}`;
  }
  function relTime(ms) {
    const totalSeconds = Math.round(ms / 1000);
    
    if (totalSeconds < 0) return 'now';
    if (totalSeconds < 60) {
      return totalSeconds === 1 ? '1 second' : `${totalSeconds} seconds`;
    }
    
    const totalMinutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    if (totalMinutes < 60) {
      if (seconds === 0) {
        return totalMinutes === 1 ? '1 minute' : `${totalMinutes} minutes`;
      }
      const minText = totalMinutes === 1 ? '1 minute' : `${totalMinutes} minutes`;
      const secText = seconds === 1 ? '1 second' : `${seconds} seconds`;
      return `${minText} and ${secText}`;
    }
    
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    
    if (minutes === 0) {
      return hours === 1 ? '1 hour' : `${hours} hours`;
    }
    
    const hourText = hours === 1 ? '1 hour' : `${hours} hours`;
    const minText = minutes === 1 ? '1 minute' : `${minutes} minutes`;
    return `${hourText} and ${minText}`;
  }
  function setChip(el, state) {
    el.classList.remove("chip-open", "chip-closing", "chip-closed");
    if (state === "open") { el.classList.add("chip-open"); el.textContent = "Gate Open"; }
    else if (state === "closing") { el.classList.add("chip-closing"); el.textContent = "⚠️ Gate Closing Soon"; }
    else { el.classList.add("chip-closed"); el.textContent = "🚫 Gate Closed"; }
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

  // Auto-refresh functionality
  let autoRefreshInterval = null;
  let currentRefreshRate = 30; // seconds
  let isAutoRefreshEnabled = false;

  function getRefreshSettings() {
    return {
      enabled: localStorage.getItem('rg_auto_refresh') === 'true',
      interval: parseInt(localStorage.getItem('rg_refresh_interval') || '30')
    };
  }

  function setRefreshSettings(enabled, interval) {
    localStorage.setItem('rg_auto_refresh', enabled.toString());
    localStorage.setItem('rg_refresh_interval', interval.toString());
    isAutoRefreshEnabled = enabled;
    currentRefreshRate = interval;
  }

  function updateTrainData(data) {
    if (!data.success) {
      console.error('Failed to fetch train data:', data.error);
      return;
    }

    // Update hero section
    const hero = document.getElementById('hero');
    const heroTitle = document.querySelector('.hero-title');
    const heroTrain = document.querySelector('.hero-train');
    const heroTime = document.querySelector('.hero-time');
    
    if (data.next_train && hero) {
      hero.dataset.eta = data.next_train.eta_at_crossing;
      const trainNoEl = document.querySelector('.hero-train .train-no');
      const trainNameEl = document.querySelector('.hero-train .train-name');
      const heroTimeEl = document.querySelector('.hero-time strong');
      
      if (trainNoEl) trainNoEl.textContent = `#${data.next_train.train_no}`;
      if (trainNameEl) trainNameEl.textContent = data.next_train.name;
      if (heroTimeEl) heroTimeEl.textContent = data.next_train.eta_at_crossing_formatted;
      
      // Reinitialize countdown
      if (window.initHeroCountdown) {
        window.initHeroCountdown({ preCloseSec: 120, enableSticky: true });
      }
    }

    // Update cards
    const cardsContainer = document.querySelector('.cards');
    if (cardsContainer && data.trains) {
      const currentPage = parseInt(new URLSearchParams(window.location.search).get('page') || '1');
      const pageSize = 10; // Same as PAGE_SIZE in Python
      const startIdx = (currentPage - 1) * pageSize;
      const endIdx = startIdx + pageSize;
      const pageTrains = data.trains.slice(startIdx, endIdx);
      
      cardsContainer.innerHTML = '';
      pageTrains.forEach(train => {
        const card = document.createElement('article');
        card.className = 'card';
        card.setAttribute('data-eta', train.eta_at_crossing);
        card.innerHTML = `
          <div class="card-head">
            <div class="train">
              <div class="train-no">#${train.train_no}</div>
              <div class="train-name">${train.name}</div>
            </div>
            <div class="tag">${train.source}</div>
          </div>
          <div class="card-row"><span class="muted">ETA</span><strong>${train.eta_at_crossing_formatted}</strong></div>
          <div class="card-row"><span class="muted">In</span><strong class="rel" data-rel>--</strong></div>
        `;
        cardsContainer.appendChild(card);
      });
      
      if (pageTrains.length === 0) {
        cardsContainer.innerHTML = '<article class="card">No upcoming trains on this page.</article>';
      }
    }

    // Update table
    const tbody = document.querySelector('table tbody');
    if (tbody && data.trains) {
      const currentPage = parseInt(new URLSearchParams(window.location.search).get('page') || '1');
      const pageSize = 10;
      const startIdx = (currentPage - 1) * pageSize;
      const endIdx = startIdx + pageSize;
      const pageTrains = data.trains.slice(startIdx, endIdx);
      
      tbody.innerHTML = '';
      pageTrains.forEach(train => {
        const row = document.createElement('tr');
        row.setAttribute('data-eta', train.eta_at_crossing);
        row.innerHTML = `
          <td>#${train.train_no}</td>
          <td>${train.name}</td>
          <td>${train.eta_at_crossing_formatted}</td>
          <td class="rel" data-rel>--</td>
          <td>${train.source}</td>
        `;
        tbody.appendChild(row);
      });
    }

    // Reinitialize relative times
    if (window.initRelativeTimes) {
      window.initRelativeTimes();
    }
    
    // Update last refresh indicator
    updateLastRefreshTime(data.cache_info);
  }

  function updateLastRefreshTime(cacheInfo) {
    const indicator = document.getElementById('last-refresh');
    if (indicator) {
      const now = new Date();
      let text = `Last updated: ${now.toLocaleTimeString()}`;
      
      if (cacheInfo) {
        if (cacheInfo.cached) {
          text += ` (cached ${cacheInfo.age_seconds}s ago)`;
        } else {
          text += ` (fresh data)`;
        }
      }
      
      indicator.textContent = text;
    }
  }

  function fetchTrainData() {
    const manualBtn = document.getElementById('manual-refresh-btn');
    const sectionHeader = document.querySelector('.section-header');
    const heroStatus = document.querySelector('.hero-status');
    const countdown = document.getElementById('countdown');
    const relativeTimeElements = document.querySelectorAll('.rel');
    const trainCards = document.querySelectorAll('.card');
    
    // Show loading state
    if (manualBtn) {
      manualBtn.classList.add('loading');
      manualBtn.disabled = true;
    }
    if (sectionHeader) {
      sectionHeader.classList.add('updating');
    }
    if (heroStatus) {
      heroStatus.classList.add('updating');
    }
    if (countdown) {
      countdown.classList.add('loading');
    }
    // Add stylish loading effect to all "arrives in" times
    relativeTimeElements.forEach(el => el.classList.add('loading'));
    // Add subtle loading state to train cards
    trainCards.forEach(card => card.classList.add('updating'));
    
    fetch('/api/trains')
      .then(response => response.json())
      .then(data => {
        updateTrainData(data);
        // Add a small delay to show the loading animation
        setTimeout(() => {
          if (manualBtn) {
            manualBtn.classList.remove('loading');
            manualBtn.disabled = false;
          }
          if (sectionHeader) {
            sectionHeader.classList.remove('updating');
          }
          if (heroStatus) {
            heroStatus.classList.remove('updating');
          }
          if (countdown) {
            countdown.classList.remove('loading');
          }
          // Remove loading effects from all elements
          document.querySelectorAll('.rel').forEach(el => el.classList.remove('loading'));
          document.querySelectorAll('.card').forEach(card => card.classList.remove('updating'));
        }, 1200); // Longer delay to appreciate the stylish animations
      })
      .catch(error => {
        console.error('Error fetching train data:', error);
        updateLastRefreshTime(null);
        // Remove loading state on error
        if (manualBtn) {
          manualBtn.classList.remove('loading');
          manualBtn.disabled = false;
        }
        if (sectionHeader) {
          sectionHeader.classList.remove('updating');
        }
        if (heroStatus) {
          heroStatus.classList.remove('updating');
        }
        if (countdown) {
          countdown.classList.remove('loading');
        }
        // Remove loading effects from all elements
        document.querySelectorAll('.rel').forEach(el => el.classList.remove('loading'));
        document.querySelectorAll('.card').forEach(card => card.classList.remove('updating'));
      });
  }

  function startAutoRefresh() {
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
    }
    
    if (isAutoRefreshEnabled) {
      autoRefreshInterval = setInterval(fetchTrainData, currentRefreshRate * 1000);
      updateRefreshUI();
    }
  }

  function stopAutoRefresh() {
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = null;
    }
    updateRefreshUI();
  }

  function updateRefreshUI() {
    const toggleBtn = document.getElementById('auto-refresh-toggle');
    const intervalSelect = document.getElementById('refresh-interval');
    
    if (toggleBtn) {
      toggleBtn.textContent = isAutoRefreshEnabled ? 'Disable Auto-refresh' : 'Enable Auto-refresh';
      toggleBtn.className = isAutoRefreshEnabled ? 'refresh-btn active' : 'refresh-btn';
    }
    
    if (intervalSelect) {
      intervalSelect.value = currentRefreshRate;
      intervalSelect.disabled = !isAutoRefreshEnabled;
    }
  }

  window.toggleAutoRefresh = function() {
    const newState = !isAutoRefreshEnabled;
    setRefreshSettings(newState, currentRefreshRate);
    
    if (newState) {
      startAutoRefresh();
    } else {
      stopAutoRefresh();
    }
  };

  window.changeRefreshInterval = function(interval) {
    const newInterval = parseInt(interval);
    if (newInterval >= 10 && newInterval <= 300) { // 10 seconds to 5 minutes
      setRefreshSettings(isAutoRefreshEnabled, newInterval);
      if (isAutoRefreshEnabled) {
        startAutoRefresh(); // Restart with new interval
      }
    }
  };

  window.manualRefresh = function() {
    fetchTrainData();
  };

  window.addEventListener("DOMContentLoaded", () => {
    applyScale(getScale());
    const dec = document.getElementById("dec-font");
    const inc = document.getElementById("inc-font");
    dec && dec.addEventListener("click", () => setScale(getScale() - 1));
    inc && inc.addEventListener("click", () => setScale(getScale() + 1));
    
    // Initialize auto-refresh settings
    const settings = getRefreshSettings();
    isAutoRefreshEnabled = settings.enabled;
    currentRefreshRate = settings.interval;
    
    // Start auto-refresh if enabled
    if (isAutoRefreshEnabled) {
      startAutoRefresh();
    }
    
    // Update UI
    updateRefreshUI();
    updateLastRefreshTime(null);
  });
})();