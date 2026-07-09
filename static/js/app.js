/* ═══════════════════════════════════════════════════════════════
   TravelBot v2.0 — Frontend Application Logic
   IBM Watsonx.ai Smart Travel Planner Agent
   Features: AI Chat · Budget Planner · Itinerary Generator ·
             Weather · Currency · Packing List · Saved Trips ·
             Group Trip · Dark Mode · IBM Status Panel · PDF Export
═══════════════════════════════════════════════════════════════ */

'use strict';

// ─── Global State ──────────────────────────────────────────────
const STATE = {
  chatHistory:    [],
  groupMembers:   [],
  profile:        null,
  budgetChart:    null,
  styleChart:     null,
  isDark:         false,
  savedTrips:     [],
  lastItinerary:  null,
  ibmMode:        'checking',   // 'watsonx' | 'smart_demo' | 'offline'
  messageCount:   0,
  lastInferenceMs: null,
  lastTokens:     null,
};

// ─── DOM helpers ─────────────────────────────────────────────
const $  = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

// ─── Toast ────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const toast = $('#appToast');
  const body  = $('#toastBody');
  body.textContent = msg;
  toast.className  = `toast align-items-center text-bg-${
    type === 'error' ? 'danger' : type === 'success' ? 'success' : 'dark'
  }`;
  bootstrap.Toast.getOrCreateInstance(toast, { delay: 3000 }).show();
}

// ─── Loading ──────────────────────────────────────────────────
function showLoading(msg = 'TravelBot is thinking...') {
  $('#loadingText').textContent = msg;
  $('#loadingOverlay').classList.remove('d-none');
}
function hideLoading() { $('#loadingOverlay').classList.add('d-none'); }

// ─── Dark Mode ────────────────────────────────────────────────
function initDarkMode() {
  applyTheme(localStorage.getItem('travelbot-theme') || 'light');
}
function applyTheme(theme) {
  STATE.isDark = theme === 'dark';
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.setAttribute('data-bs-theme', theme);
  $('#darkIcon').className = STATE.isDark ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
  localStorage.setItem('travelbot-theme', theme);
  if (STATE.budgetChart || STATE.styleChart) rebuildCharts();
}
$('#darkModeToggle').addEventListener('click', () => applyTheme(STATE.isDark ? 'light' : 'dark'));

// ─── IBM Panel Update ─────────────────────────────────────────
function updateIBMPanel(mode, model, inferenceMs, tokens) {
  const panelStatus = $('#ibmPanelStatus');
  const panelModel  = $('#ibmPanelModel');

  STATE.ibmMode = mode;

  if (mode === 'watsonx') {
    panelStatus.innerHTML = '<span class="status-dot connected"></span> IBM Granite Connected';
    panelStatus.className = 'ibm-value connected';
    // Navbar
    const navDot   = $('#navStatusDot');
    const navLabel = $('#navStatusLabel');
    if (navDot)   { navDot.className = 'status-dot connected'; }
    if (navLabel) { navLabel.textContent = 'Watsonx Live'; }
    // Sidebar
    const sidebarDot = $('#sidebarDot');
    if (sidebarDot) sidebarDot.className = 'status-dot connected';
    $('#apiStatusText').textContent = 'Watsonx Live';
    $('#modelBadge').textContent    = 'Watsonx AI';
  } else {
    panelStatus.innerHTML = '<span class="status-dot demo"></span> Demo Mode';
    panelStatus.className = 'ibm-value demo-mode';
    const navLabel = $('#navStatusLabel');
    if (navLabel) navLabel.textContent = 'Demo Mode';
    $('#apiStatusText').textContent = 'Demo Mode';
    $('#modelBadge').textContent    = 'Demo Mode';
  }

  if (model && panelModel) panelModel.textContent = model;
  if ($('#navModelName')) $('#navModelName').textContent = model || '—';

  if (inferenceMs != null) {
    $('#ibmPanelInferenceTime').textContent = `${inferenceMs} ms`;
    STATE.lastInferenceMs = inferenceMs;
  }
  if (tokens != null) {
    $('#ibmPanelTokens').textContent = `${tokens} tokens`;
    STATE.lastTokens = tokens;
  }

  STATE.messageCount++;
  const msgEl = $('#ibmPanelMessages');
  if (msgEl) msgEl.textContent = STATE.messageCount;
}

// ─── API Health Check ─────────────────────────────────────────
async function checkApiHealth() {
  try {
    const res  = await fetch('/api/health');
    const data = await res.json();
    const mode = data.watsonx === 'connected' ? 'watsonx' : 'smart_demo';
    updateIBMPanel(mode, data.model || '—', null, null);
  } catch {
    STATE.ibmMode = 'offline';
    $('#apiStatusText').textContent = 'Offline';
    $$('.status-dot').forEach(d => d.className = 'status-dot');
  }
}

// ─── Traveller Profile ────────────────────────────────────────
function getProfile() {
  const name         = $('#profName').value.trim();
  const age          = parseInt($('#profAge').value);
  const gender       = $('#profGender').value;
  const nationality  = $('#profNationality').value.trim();
  const travel_style = $('#profTravelStyle').value;
  const goals        = $('#profGoals').value.trim();
  const budget       = $('#profBudget').value.trim();
  const requirements = $('#profRequirements').value.trim();
  if (!name || !age || !gender) return null;
  return { name, age, gender, nationality, travel_style, goals, budget, requirements };
}

function saveProfile() {
  const p = getProfile();
  if (!p) { showToast('Please fill in name, age and gender', 'error'); return; }
  STATE.profile = p;
  localStorage.setItem('travelbot-profile', JSON.stringify(p));
  $('#profileSaved').classList.remove('d-none');
  setTimeout(() => $('#profileSaved').classList.add('d-none'), 2500);
  showToast(`Profile saved for ${p.name}! ✈️`, 'success');
}

function loadSavedProfile() {
  const raw = localStorage.getItem('travelbot-profile');
  if (!raw) return;
  try {
    const p = JSON.parse(raw);
    STATE.profile = p;
    if (p.name)         $('#profName').value         = p.name;
    if (p.age)          $('#profAge').value          = p.age;
    if (p.gender)       $('#profGender').value       = p.gender;
    if (p.nationality)  $('#profNationality').value  = p.nationality;
    if (p.travel_style) $('#profTravelStyle').value  = p.travel_style;
    if (p.goals)        $('#profGoals').value        = p.goals;
    if (p.budget)       $('#profBudget').value       = p.budget;
    if (p.requirements) $('#profRequirements').value = p.requirements;
  } catch { /* ignore */ }
}

$('#saveProfile').addEventListener('click', saveProfile);

let profileOpen = true;
$('#toggleProfile').addEventListener('click', () => {
  profileOpen = !profileOpen;
  $('#profileBody').style.display = profileOpen ? '' : 'none';
  $('#profileChevron').className  = profileOpen ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
});

// ─── Markdown renderer ───────────────────────────────────────
function formatMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g,     '<em>$1</em>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<br><strong style="font-size:1.05em;color:var(--accent)">$1</strong><br>')
    .replace(/^(\d+)\.\s+/gm, '<br><strong>$1.</strong> ')
    .replace(/^[-•]\s+/gm,    '<br>• ')
    .replace(/\n/g, '<br>')
    .replace(/(<br>\s*){3,}/g, '<br><br>');
}

function escapeHtml(text) {
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── Chat ─────────────────────────────────────────────────────
function addMessage(role, content, meta = null) {
  const win   = $('#chatWindow');
  const isBot = role === 'bot';
  const time  = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  let metaHtml = '';
  if (isBot && meta) {
    const ibmTag = meta.mode === 'watsonx'
      ? `<span class="msg-ibm-tag">IBM Watsonx.ai</span>`
      : `<span class="msg-ibm-tag" style="background:var(--accent-green)">TravelBot AI</span>`;
    const timeStr = meta.inferenceMs ? `<span><i class="bi bi-stopwatch"></i> ${meta.inferenceMs}ms</span>` : '';
    const tokStr  = meta.tokens      ? `<span><i class="bi bi-hash"></i> ${meta.tokens} tokens</span>` : '';
    const modStr  = meta.model       ? `<span><i class="bi bi-cpu"></i> ${meta.model}</span>` : '';
    const modeStr = meta.mode === 'watsonx'
      ? `<span style="color:var(--accent-green)"><i class="bi bi-circle-fill" style="font-size:.5rem"></i> Live</span>`
      : `<span><i class="bi bi-circle-fill" style="font-size:.5rem"></i> Smart AI</span>`;
    metaHtml = `<div class="msg-meta">${ibmTag}${modeStr}${timeStr}${tokStr}${modStr}</div>`;
  }

  const msg = document.createElement('div');
  msg.className = `chat-message ${isBot ? 'bot-message' : 'user-message'}`;
  msg.innerHTML = `
    <div class="avatar ${isBot ? 'bot-avatar' : 'user-avatar'}">${isBot ? '✈️' : '👤'}</div>
    <div class="message-bubble">
      <div class="message-content">${isBot ? formatMarkdown(content) : escapeHtml(content)}</div>
      <div class="message-time">
        <span>${isBot ? 'TravelBot' : 'You'} • ${time}</span>
        ${isBot ? '<span class="msg-ibm-tag" style="background:var(--accent-green)">TravelBot AI</span>' : ''}
      </div>
      ${metaHtml}
    </div>`;
  win.appendChild(msg);
  win.scrollTop = win.scrollHeight;
  STATE.chatHistory.push({ role: isBot ? 'assistant' : 'user', content });
}

function addTypingIndicator() {
  const win = $('#chatWindow');
  const el  = document.createElement('div');
  el.id        = 'typingIndicator';
  el.className = 'chat-message bot-message';
  el.innerHTML = `
    <div class="avatar bot-avatar">✈️</div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
      </div>
      <div style="font-size:.68rem;color:var(--text-muted);margin-top:.4rem">
        TravelBot is preparing your response...
      </div>
    </div>`;
  win.appendChild(el);
  win.scrollTop = win.scrollHeight;
}
function removeTypingIndicator() { const el = $('#typingIndicator'); if (el) el.remove(); }

async function sendMessage() {
  const input   = $('#chatInput');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  resizeChatInput(); updateCharCount();
  $('#sendBtn').disabled = true;
  addMessage('user', message);
  addTypingIndicator();

  try {
    const res  = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history: STATE.chatHistory.slice(-10),
        profile: STATE.profile || getProfile(),
      }),
    });
    const data = await res.json();
    removeTypingIndicator();

    if (data.error) {
      addMessage('bot', `⚠️ ${data.error}`);
    } else {
      const meta = {
        mode:        data.mode,
        model:       data.model,
        inferenceMs: data.inference_ms,
        tokens:      data.output_tokens,
      };
      addMessage('bot', data.response, meta);
      updateIBMPanel(data.mode, data.model, data.inference_ms,
                     (data.input_tokens || 0) + (data.output_tokens || 0));
    }
  } catch {
    removeTypingIndicator();
    addMessage('bot', '⚠️ Connection error. Please check your internet and try again.');
  } finally {
    $('#sendBtn').disabled = false;
    input.focus();
  }
}

$('#sendBtn').addEventListener('click', sendMessage);
$('#chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); sendMessage(); }
});
function resizeChatInput() {
  const ta = $('#chatInput');
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}
function updateCharCount() {
  $('#charCount').textContent = `${$('#chatInput').value.length} / 500`;
}
$('#chatInput').addEventListener('input', () => { resizeChatInput(); updateCharCount(); });

$$('.qp-btn').forEach(btn => btn.addEventListener('click', () => {
  $('#chatInput').value = btn.dataset.prompt;
  resizeChatInput(); updateCharCount(); sendMessage();
}));

$('#clearChat').addEventListener('click', () => {
  $('#chatWindow').innerHTML = '';
  STATE.chatHistory = [];
  addMessage('bot', '👋 Chat cleared! Where would you like to travel today? 🌍');
});

// ─── Budget Dashboard Charts ──────────────────────────────────
function getChartColors() {
  return STATE.isDark
    ? { grid: '#2d3a5a', text: '#6b7fa8', bg: '#1c2237' }
    : { grid: '#e2e8f0', text: '#718096', bg: '#ffffff' };
}

function buildBudgetBreakdownChart(accommodation, food, transport, sightseeing, misc) {
  const ctx    = $('#budgetChart').getContext('2d');
  const colors = getChartColors();
  if (STATE.budgetChart) STATE.budgetChart.destroy();
  STATE.budgetChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels:   ['Accommodation', 'Food & Dining', 'Transport', 'Sightseeing', 'Misc'],
      datasets: [{
        data:            [accommodation, food, transport, sightseeing, misc],
        backgroundColor: ['#f59e0b', '#0f62fe', '#ef4444', '#24a148', '#8a3ffc'],
        borderColor:     colors.bg, borderWidth: 3, hoverOffset: 8,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: colors.text, font: { size: 10 }, padding: 8, boxWidth: 11, boxHeight: 11 },
        },
        tooltip: { callbacks: { label: c => ` ${c.label}: ₹${c.parsed.toLocaleString()}` } },
      },
      cutout: '62%',
    },
  });
}

function buildStyleComparisonChart(destination, days, travellers) {
  const ctx    = $('#styleChart').getContext('2d');
  const colors = getChartColors();

  // Destination-aware costs fetched from last budget call, fallback to generic
  const bases = STATE._destDailyCosts || { budget: 2000, balanced: 5000, luxury: 15000, adventure: 3500, family: 6500 };
  const styles = ['Budget', 'Balanced', 'Luxury', 'Adventure', 'Family'];
  const keys   = ['budget', 'balanced', 'luxury', 'adventure', 'family'];
  const vals   = keys.map(k => (bases[k] || 3000) * days * travellers);
  const bgColors = ['#3b82f6cc','#24a14899','#f59e0bcc','#ef444499','#8a3ffc99'];
  const borderColors = ['#3b82f6','#24a148','#f59e0b','#ef4444','#8a3ffc'];

  if (STATE.styleChart) STATE.styleChart.destroy();
  STATE.styleChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: styles,
      datasets: [{
        label: 'Total Cost (₹)',
        data: vals,
        backgroundColor: bgColors,
        borderColor: borderColors,
        borderWidth: 2, borderRadius: 6,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { grid: { color: colors.grid }, ticks: { color: colors.text, font: { size: 10 } } },
        y: {
          grid: { color: colors.grid },
          ticks: { color: colors.text, font: { size: 10 }, callback: v => `₹${(v/1000).toFixed(0)}k` },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => ` ₹${c.parsed.y.toLocaleString()}` } },
      },
    },
  });
}

function rebuildCharts() {
  if (STATE.budgetChart && STATE._lastBreakdown) {
    const b = STATE._lastBreakdown;
    buildBudgetBreakdownChart(b.accommodation, b.food, b.transport, b.sightseeing, b.misc);
  }
  if (STATE.styleChart && STATE._lastChartParams) {
    const p = STATE._lastChartParams;
    buildStyleComparisonChart(p.dest, p.days, p.travellers);
  }
}

async function calculateDashboard() {
  const destination    = $('#budgetDestination').value.trim() || 'India';
  const days           = Math.max(1, parseInt($('#budgetDays').value) || 5);
  const travel_style   = $('#budgetStyle').value;
  const num_travellers = Math.max(1, parseInt($('#budgetTravellers').value) || 1);

  showLoading(`Calculating budget for ${destination}...`);
  try {
    const res  = await fetch('/api/budget', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ destination, days, travel_style, num_travellers }),
    });
    const data = await res.json();

    if (data.error) { showToast(data.error, 'error'); return; }

    // Metric cards
    $('#dashTotalBudget').textContent = `₹${data.total_group.toLocaleString()}`;
    $('#dashPerPerson').textContent   = `₹${data.total_per_person.toLocaleString()}`;
    $('#dashDailyBudget').textContent = `₹${data.daily_per_person.toLocaleString()}`;
    const season = data.best_season || '—';
    $('#dashBestSeason').textContent  = season.length > 15 ? season.slice(0, 15) + '…' : season;

    // Breakdown pills (5 categories)
    const b = data.breakdown;
    $('#budgetAccommodation').textContent = `₹${(b.accommodation||0).toLocaleString()}`;
    $('#budgetFood').textContent          = `₹${(b.food||0).toLocaleString()}`;
    $('#budgetTransport').textContent     = `₹${(b.transport||0).toLocaleString()}`;
    $('#budgetSightseeing').textContent   = `₹${(b.sightseeing||0).toLocaleString()}`;
    $('#budgetMisc').textContent          = `₹${(b.misc||0).toLocaleString()}`;
    $('#budgetBreakdown').style.display   = '';

    // Season info box
    if (data.season_reason) {
      $('#seasonInfoDest').textContent = destination;
      $('#seasonInfoText').textContent = `Best time: ${data.best_season}. ${data.season_reason}`;
      $('#seasonInfoBox').style.display = '';
    }

    // Save state for chart rebuild and style comparison
    STATE._lastBreakdown   = b;
    STATE._lastChartParams = { dest: destination, days, travellers: num_travellers };
    // Store destination-specific daily costs for style comparison chart
    if (data.destination_info) {
      STATE._destDailyCosts = null; // we'll derive from API data
    }

    // Build charts
    buildBudgetBreakdownChart(b.accommodation, b.food, b.transport, b.sightseeing||0, b.misc||0);
    buildStyleComparisonChart(destination, days, num_travellers);

    showToast(`Budget estimated for ${destination}! 💰`, 'success');
  } catch (err) {
    showToast('Budget calculation failed. Try again.', 'error');
  } finally {
    hideLoading();
  }
}

$('#calcDashBtn').addEventListener('click', calculateDashboard);

// ─── Itinerary Generator ──────────────────────────────────────
const PACKING_LISTS = {
  beach:     ['Sunscreen SPF 50+', 'Swimwear', 'Flip flops', 'Sunglasses', 'Insect repellent', 'Light cotton clothes', 'Beach towel', 'Waterproof bag'],
  mountain:  ['Warm jacket', 'Thermal layers', 'Trekking shoes', 'Woollen socks', 'Gloves & cap', 'Raincoat/poncho', 'Power bank', 'First-aid kit'],
  heritage:  ['Comfortable walking shoes', 'Modest clothing', 'Guidebook / offline maps', 'Sun hat', 'Water bottle', 'Camera', 'Hand sanitiser'],
  city:      ['Smart casuals', 'Comfortable shoes', 'Portable charger', 'Metro card/UPI app', 'Raincoat (monsoon)', 'Daypack'],
  default:   ['Valid ID/Passport', 'Travel insurance docs', 'Power bank', 'First-aid kit', 'Local currency', 'Sunscreen', 'Comfortable shoes', 'Water bottle'],
};

function getPackingType(destination) {
  const d = destination.toLowerCase();
  if (/goa|beach|andaman|kovalam|pondicherry/.test(d))            return 'beach';
  if (/ladakh|manali|shimla|himachal|trek|mountain|auli/.test(d)) return 'mountain';
  if (/jaipur|rajasthan|varanasi|hampi|agra|delhi/.test(d))       return 'heritage';
  if (/mumbai|bangalore|hyderabad|chennai|kolkata/.test(d))       return 'city';
  return 'default';
}

function renderPackingList(destination) {
  const type  = getPackingType(destination);
  const items = [...PACKING_LISTS[type], ...PACKING_LISTS.default.filter(i => !PACKING_LISTS[type].includes(i))];
  const grid  = $('#packingGrid');
  $('#packingDest').textContent = destination;

  grid.innerHTML = items.map(item => `
    <label class="packing-item" onclick="this.classList.toggle('checked')">
      <input type="checkbox">
      <span>${item}</span>
    </label>
  `).join('');

  $('#packingSection').classList.remove('d-none');
}

function renderDestCard(info, destination) {
  const card = $('#itineraryDestCard');
  if (!info || info.key === 'generic') { card.classList.add('d-none'); return; }

  const attractions = (info.top_attractions || []).slice(0, 4).map(a => `<span class="dest-tag">${a}</span>`).join('');
  const foods       = (info.local_food || []).slice(0, 3).map(f => `<span class="dest-tag" style="background:var(--accent-green)">${f}</span>`).join('');

  card.innerHTML = `
    <div class="d-flex align-items-center gap-2 mb-2">
      <span class="dest-title">📍 ${destination.charAt(0).toUpperCase() + destination.slice(1)} — ${info.region || 'India'}</span>
    </div>
    <div class="mb-2"><strong style="font-size:.75rem;color:var(--text-muted);text-transform:uppercase">Top Attractions</strong><br>${attractions}</div>
    <div><strong style="font-size:.75rem;color:var(--text-muted);text-transform:uppercase">Local Food</strong><br>${foods}</div>
  `;
  card.classList.remove('d-none');
}

async function generateItinerary() {
  const destination  = $('#itineraryDestination').value.trim();
  const days         = $('#itineraryDays').value;
  const travel_style = $('#itineraryStyle').value;
  const interests    = $('#itineraryInterests').value.trim();
  const profile      = STATE.profile || getProfile();

  if (!destination) { showToast('Please enter a destination!', 'error'); $('#itineraryDestination').focus(); return; }

  const output = $('#itineraryOutput');
  output.innerHTML = '';
  showLoading(`Generating ${days}-day ${destination} itinerary with IBM Granite AI...`);

  // Show PDF/Print buttons
  $('#downloadItineraryBtn').classList.remove('d-none');
  $('#printItineraryBtn').classList.remove('d-none');

  try {
    const res = await fetch('/api/itinerary', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days: parseInt(days), destination, travel_style, interests, profile }),
    });
    const data = await res.json();

    if (data.error) {
      output.innerHTML = `<div class="alert alert-danger">⚠️ ${escapeHtml(data.error)}</div>`;
      showToast('Itinerary generation failed', 'error');
    } else if (!data.itinerary?.trim()) {
      output.innerHTML = `<div class="alert alert-warning">Empty response. Please try again.</div>`;
      showToast('Empty response — try again', 'error');
    } else {
      // Render destination info card
      if (data.destination_info) renderDestCard(data.destination_info, destination);

      // Render itinerary
      const ibmBadge = data.mode === 'watsonx'
        ? `<div style="margin-bottom:.75rem"><span class="msg-ibm-tag">IBM Watsonx.ai Granite</span> <span style="font-size:.7rem;color:var(--text-muted)">${data.model || ''}</span>${data.inference_ms ? ` · ${data.inference_ms}ms` : ''}</div>`
        : `<div style="margin-bottom:.75rem"><span class="msg-ibm-tag" style="background:var(--accent-green)">TravelBot AI</span></div>`;

      output.innerHTML = `<div class="trip-plan-content">${ibmBadge}${formatMarkdown(data.itinerary)}</div>`;

      // Store for save/PDF
      STATE.lastItinerary = { destination, days, style: travel_style, content: data.itinerary, date: new Date().toLocaleDateString() };

      // Render packing list
      renderPackingList(destination);

      // Update IBM panel
      if (data.model) updateIBMPanel(data.mode, data.model, data.inference_ms, null);

      showToast(`${days}-day ${destination} itinerary ready! 🗺️`, 'success');
    }
  } catch (err) {
    output.innerHTML = `<div class="alert alert-danger">⚠️ Could not reach the server. Is Flask running on port 5000?<br><small>${escapeHtml(String(err))}</small></div>`;
    showToast('Connection failed', 'error');
  } finally {
    hideLoading();
  }
}

$('#generateItineraryBtn').addEventListener('click', generateItinerary);

// ─── Print & PDF ──────────────────────────────────────────────
$('#printItineraryBtn').addEventListener('click', () => {
  window.print();
});

$('#downloadItineraryBtn').addEventListener('click', () => {
  if (!STATE.lastItinerary) return;
  const { destination, days, style, content, date } = STATE.lastItinerary;
  const text = `TravelBot — ${days}-Day ${destination} Itinerary (${style.toUpperCase()})\n` +
    `Generated: ${date} | Powered by IBM Watsonx.ai\n` +
    '═'.repeat(60) + '\n\n' +
    content.replace(/\*\*/g, '').replace(/\*/g, '');
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = `travelbot-${destination.replace(/\s+/g,'-')}-${days}days.txt`;
  a.click(); URL.revokeObjectURL(url);
  showToast('Itinerary downloaded! 📥', 'success');
});

// ─── Save Trip ────────────────────────────────────────────────
function saveCurrentTrip() {
  if (!STATE.lastItinerary) { showToast('Generate an itinerary first!', 'error'); return; }
  const trip = { ...STATE.lastItinerary, id: Date.now() };
  STATE.savedTrips.unshift(trip);
  localStorage.setItem('travelbot-saved', JSON.stringify(STATE.savedTrips.slice(0, 10)));
  renderSavedTrips();
  showToast(`${trip.destination} trip saved! 📌`, 'success');
}

function loadSavedTrips() {
  try { STATE.savedTrips = JSON.parse(localStorage.getItem('travelbot-saved') || '[]'); } catch { STATE.savedTrips = []; }
  renderSavedTrips();
}

function renderSavedTrips() {
  const container = $('#savedTripsContainer');
  if (!STATE.savedTrips.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📌</div>
        <p>No saved trips yet. Generate an itinerary and click the bookmark button to save it here.</p>
      </div>`;
    return;
  }
  container.innerHTML = STATE.savedTrips.map(t => `
    <div class="saved-trip-card" onclick="loadSavedTrip(${t.id})">
      <div class="saved-trip-title">📍 ${t.destination} — ${t.days} Days (${t.style || 'balanced'})</div>
      <div class="saved-trip-meta">Saved on ${t.date} · Click to restore itinerary</div>
    </div>`).join('');
}

window.loadSavedTrip = function(id) {
  const trip = STATE.savedTrips.find(t => t.id === id);
  if (!trip) return;
  STATE.lastItinerary = trip;
  $('#itineraryOutput').innerHTML = `<div class="trip-plan-content">${formatMarkdown(trip.content)}</div>`;
  $('#itineraryDestination').value = trip.destination;
  renderPackingList(trip.destination);
  $('#downloadItineraryBtn').classList.remove('d-none');
  $('#printItineraryBtn').classList.remove('d-none');
  document.getElementById('itinerarySection').scrollIntoView({ behavior: 'smooth' });
  showToast(`${trip.destination} trip restored! 🗺️`, 'success');
};

$('#saveTripBtn').addEventListener('click', saveCurrentTrip);
$('#clearSavedBtn').addEventListener('click', () => {
  STATE.savedTrips = [];
  localStorage.removeItem('travelbot-saved');
  renderSavedTrips();
  showToast('Saved trips cleared', 'info');
});

// ─── Weather Guide ────────────────────────────────────────────
const WEATHER_DATA = {
  goa:        { icon:'☀️', temp:'25–32°C', desc:'Sunny & breezy', humidity:'65%', best:'Nov–Feb', rain:'Low (off-season)', season:'Winter (Oct–Feb) is ideal' },
  kerala:     { icon:'🌤️', temp:'22–34°C', desc:'Tropical, humid', humidity:'80%', best:'Sep–Mar', rain:'Moderate–High', season:'Post-monsoon (Sep–Mar) is lush & beautiful' },
  rajasthan:  { icon:'🌞', temp:'10–40°C', desc:'Hot & dry', humidity:'30%', best:'Oct–Mar', rain:'Very Low', season:'Winter (Oct–Mar): cool days, chilly nights' },
  ladakh:     { icon:'⛰️', temp:'5–20°C',  desc:'Cold & dry', humidity:'20%', best:'Jun–Sep', rain:'Very Low', season:'Summer (Jun–Sep): roads open, clear skies' },
  manali:     { icon:'🌨️', temp:'-5–20°C', desc:'Cold, snowy winters', humidity:'55%', best:'Mar–Jun, Oct', rain:'Moderate', season:'Monsoon: lush; Winter: snow activities' },
  andaman:    { icon:'🏝️', temp:'23–30°C', desc:'Warm & tropical', humidity:'75%', best:'Oct–May', rain:'Low (off-season)', season:'Nov–Feb: calm seas, perfect for diving' },
  hyderabad:  { icon:'⛅', temp:'15–38°C', desc:'Moderate, hot summers', humidity:'45%', best:'Oct–Feb', rain:'Low–Moderate', season:'Post-monsoon (Oct–Feb) is comfortable' },
  delhi:      { icon:'🌫️', temp:'5–45°C',  desc:'Extreme seasonal', humidity:'50%', best:'Oct–Mar', rain:'Low', season:'Winter (Nov–Feb): best weather for sightseeing' },
  mumbai:     { icon:'🌊', temp:'20–35°C', desc:'Humid tropical', humidity:'85%', best:'Nov–Feb', rain:'Very High (Jun–Sep)', season:'Winter (Nov–Feb): cooler & pleasant' },
  varanasi:   { icon:'🌅', temp:'5–42°C',  desc:'Extreme, riverine', humidity:'55%', best:'Oct–Mar', rain:'Moderate', season:'Sunrise boat rides best in winter months' },
};

function getWeatherInfo(destination) {
  const d = destination.toLowerCase().trim();
  for (const [key, val] of Object.entries(WEATHER_DATA)) {
    if (d.includes(key) || key.includes(d)) return { ...val, name: destination };
  }
  return null;
}

function showWeather() {
  const dest = $('#weatherDestination').value.trim();
  if (!dest) { showToast('Enter a destination', 'error'); return; }

  const info = getWeatherInfo(dest);
  const out  = $('#weatherOutput');

  if (info) {
    out.innerHTML = `
      <div class="weather-result">
        <div class="weather-main">
          <div class="weather-icon">${info.icon}</div>
          <div>
            <div class="weather-temp">${info.temp}</div>
            <div class="weather-desc">${info.desc}</div>
          </div>
        </div>
        <div class="weather-grid">
          <div class="weather-item">
            <div class="weather-item-label">Best Month</div>
            <div class="weather-item-value">${info.best}</div>
          </div>
          <div class="weather-item">
            <div class="weather-item-label">Humidity</div>
            <div class="weather-item-value">${info.humidity}</div>
          </div>
          <div class="weather-item">
            <div class="weather-item-label">Rainfall</div>
            <div class="weather-item-value">${info.rain}</div>
          </div>
          <div class="weather-item">
            <div class="weather-item-label">Season Tip</div>
            <div class="weather-item-value" style="font-size:.75rem">${info.season}</div>
          </div>
        </div>
      </div>`;
  } else {
    out.innerHTML = `
      <div class="weather-result">
        <div class="weather-main">
          <div class="weather-icon">🌍</div>
          <div>
            <div class="weather-temp">Oct – March</div>
            <div class="weather-desc">Best months for most Indian destinations</div>
          </div>
        </div>
        <div style="font-size:.82rem;color:var(--text-secondary);margin-top:.5rem">
          Generally, <strong>post-monsoon to early spring</strong> offers the best travel conditions 
          across India with comfortable temperatures and minimal rainfall.
        </div>
      </div>`;
  }
}

$('#getWeatherBtn').addEventListener('click', showWeather);
$('#weatherDestination').addEventListener('keydown', e => { if (e.key === 'Enter') showWeather(); });

// ─── Currency Converter ───────────────────────────────────────
const EXCHANGE_RATES = {
  USD: 0.012,  EUR: 0.011, GBP: 0.0095, JPY: 1.81,
  AED: 0.044,  SGD: 0.016, THB: 0.43,   MYR: 0.056,
};
const CURRENCY_FLAGS = {
  USD: '🇺🇸', EUR: '🇪🇺', GBP: '🇬🇧', JPY: '🇯🇵',
  AED: '🇦🇪', SGD: '🇸🇬', THB: '🇹🇭', MYR: '🇲🇾',
};

function convertCurrency() {
  const amount = parseFloat($('#currencyAmount').value);
  const target = $('#currencyTarget').value;
  const out    = $('#currencyOutput');

  if (!amount || amount <= 0) { showToast('Enter a valid amount', 'error'); return; }

  const rate    = EXCHANGE_RATES[target] || 0.012;
  const result  = (amount * rate).toFixed(2);
  const flag    = CURRENCY_FLAGS[target] || '';

  out.innerHTML = `
    <div>
      <div class="currency-amount">${flag} ${Number(result).toLocaleString()} ${target}</div>
      <div class="currency-sub">₹${amount.toLocaleString()} INR</div>
      <div class="currency-rate">Rate: 1 INR ≈ ${rate} ${target} (approx. 2025)</div>
    </div>`;
}

$('#convertCurrencyBtn').addEventListener('click', convertCurrency);
$('#currencyAmount').addEventListener('keydown', e => { if (e.key === 'Enter') convertCurrency(); });

// ─── Group Trip ───────────────────────────────────────────────
function renderGroupMembers() {
  const grid    = $('#familyMembers');
  const empty   = $('#familyEmpty');
  const actions = $('#familyActions');

  if (!STATE.groupMembers.length) {
    grid.innerHTML = ''; empty.style.display = ''; actions.style.display = 'none';
    return;
  }
  empty.style.display = 'none'; actions.style.display = '';

  const avatars = { male: '👨', female: '👩', other: '🧑' };
  grid.innerHTML = STATE.groupMembers.map((m, i) => `
    <div class="family-card">
      <button class="family-remove" onclick="removeMember(${i})"><i class="bi bi-x-circle"></i></button>
      <div class="family-avatar">${parseInt(m.age) < 15 ? '👦' : (avatars[m.gender] || '🧑')}</div>
      <div class="family-name">${escapeHtml(m.name)}</div>
      <div class="family-meta">Age ${m.age} · ${m.gender}</div>
      <div class="family-meta">${escapeHtml(m.goals || 'General sightseeing')}</div>
      <span class="member-style-badge">${m.travel_style || 'Balanced'}</span>
    </div>`).join('');
}

window.removeMember = function(idx) {
  STATE.groupMembers.splice(idx, 1);
  saveGroup(); renderGroupMembers();
};

function saveGroup() { localStorage.setItem('travelbot-group', JSON.stringify(STATE.groupMembers)); }
function loadGroup() {
  try { STATE.groupMembers = JSON.parse(localStorage.getItem('travelbot-group') || '[]'); } catch { STATE.groupMembers = []; }
  renderGroupMembers();
}

function openAddMemberModal() {
  ['memName','memAge','memGoals','memConditions'].forEach(id => { $(`#${id}`).value = ''; });
  $('#memGender').value = 'male'; $('#memTravelStyle').value = 'balanced';
  bootstrap.Modal.getOrCreateInstance($('#addMemberModal')).show();
}

$('#addMemberBtn').addEventListener('click', openAddMemberModal);
$('#addFirstMember').addEventListener('click', openAddMemberModal);

$('#saveMemberBtn').addEventListener('click', () => {
  const name = $('#memName').value.trim();
  const age  = $('#memAge').value.trim();
  if (!name || !age) { showToast('Name and age are required', 'error'); return; }

  STATE.groupMembers.push({
    name, age: parseInt(age), gender: $('#memGender').value,
    travel_style: $('#memTravelStyle').value,
    goals:        $('#memGoals').value.trim()      || 'General sightseeing',
    conditions:   $('#memConditions').value.trim() || 'None',
  });
  saveGroup(); renderGroupMembers();
  bootstrap.Modal.getOrCreateInstance($('#addMemberModal')).hide();
  showToast(`${name} added to group! ✈️`, 'success');
});

async function getGroupPlan() {
  if (!STATE.groupMembers.length) { showToast('Add group members first!', 'error'); return; }

  showLoading(`Planning trip for ${STATE.groupMembers.length} travellers...`);
  const output = $('#familyPlanOutput');
  output.innerHTML = '';

  try {
    const res  = await fetch('/api/group-trip', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ members: STATE.groupMembers }),
    });
    const data = await res.json();
    if (data.error) {
      output.innerHTML = `<div class="text-danger">⚠️ ${escapeHtml(data.error)}</div>`;
    } else {
      const badge = `<div style="margin-bottom:.75rem"><span class="msg-ibm-tag">IBM Watsonx.ai</span></div>`;
      output.innerHTML = `<div class="trip-plan-content">${badge}${formatMarkdown(data.recommendations)}</div>`;
      if (data.model) updateIBMPanel(data.mode, data.model, null, null);
    }
    showToast('Group travel plan ready! 🌍', 'success');
  } catch {
    output.innerHTML = '<div class="text-danger">Failed to get group plan. Please try again.</div>';
  } finally {
    hideLoading();
  }
}

$('#getFamilyPlanBtn').addEventListener('click', getGroupPlan);

// ─── Smooth Scroll + Active Sidebar ──────────────────────────
$$('.sidebar-link, .nav-item-mobile').forEach(link => {
  link.addEventListener('click', e => {
    const id = link.dataset.section || link.getAttribute('href')?.slice(1);
    if (!id) return;
    const el = document.getElementById(id);
    if (el) { e.preventDefault(); el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  });
});

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const id = entry.target.id;
      $$('.sidebar-link').forEach(l => l.classList.toggle('active', l.dataset.section === id));
    }
  });
}, { threshold: 0.25 });

['chatSection','dashSection','itinerarySection','tipsSection','groupSection','savedSection'].forEach(id => {
  const el = document.getElementById(id);
  if (el) observer.observe(el);
});

$$('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
  });
});

// ─── Initialisation ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  checkApiHealth();
  loadSavedProfile();
  loadGroup();
  loadSavedTrips();

  // Auto-convert currency on load
  convertCurrency();
});
