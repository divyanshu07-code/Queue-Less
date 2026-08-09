let activeService = SERVICES[0];
let refreshTimer = null;

const tabs = document.querySelectorAll('.service-tab');
tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    activeService = tab.dataset.service;
    tabs.forEach((t) => t.classList.toggle('active', t === tab));
    document.getElementById('active-service-name').textContent = activeService;
    refresh();
  });
});
document.getElementById('active-service-name').textContent = activeService;

function fmtTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (_e) { return ''; }
}

function renderWaitList(waiting) {
  const el = document.getElementById('wait-list');
  if (!waiting.length) {
    el.innerHTML = `<div class="empty-state">Nobody in line right now.</div>`;
    return;
  }
  el.innerHTML = waiting.map((p, idx) => `
    <div class="wait-row" data-id="${p.id}">
      <span class="wr-token">#${String(p.token).padStart(2, '0')}</span>
      <span class="wr-name">${escapeHtml(p.name)}${idx === 0 ? ' <span class="pill" style="margin-left:6px;">up next</span>' : ''}</span>
      <span class="wr-time">${fmtTime(p.joined_at)}</span>
      <span class="wr-actions">
        <button class="btn btn-ghost btn-sm" data-action="serve" data-id="${p.id}">Serve</button>
        <button class="btn btn-ghost btn-sm" data-action="skip" data-id="${p.id}">Skip</button>
      </span>
    </div>
  `).join('');

  el.querySelectorAll('[data-action="serve"]').forEach((btn) => {
    btn.addEventListener('click', () => actOnTicket(btn.dataset.id, 'serve'));
  });
  el.querySelectorAll('[data-action="skip"]').forEach((btn) => {
    btn.addEventListener('click', () => actOnTicket(btn.dataset.id, 'skip'));
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function actOnTicket(id, action) {
  const { ok, data } = await qlFetch(`/api/${action}/${id}`, { method: 'POST' });
  if (ok && data.success) {
    qlToast(action === 'serve' ? 'Marked as served.' : 'Sent back into the line.');
    refresh();
  } else {
    qlToast(data.message || 'Something went wrong.');
  }
}

function renderIntelligence(d) {
  const badge = document.getElementById('traffic-badge');
  badge.textContent = d.traffic_level.charAt(0).toUpperCase() + d.traffic_level.slice(1);
  badge.className = `traffic-badge ${d.traffic_level}`;
  document.getElementById('intel-rec').textContent = d.recommendation;
  document.getElementById('intel-clearing').textContent = d.clearing_minutes;
  document.getElementById('intel-avg').textContent = d.avg_minutes;
}

async function refresh() {
  const [{ data: qData }, { data: sData }, { data: iData }] = await Promise.all([
    qlFetch(`/api/queue/${encodeURIComponent(activeService)}`),
    qlFetch(`/api/stats/${encodeURIComponent(activeService)}`),
    qlFetch(`/api/intelligence/${encodeURIComponent(activeService)}`),
  ]);

  if (iData && iData.success) renderIntelligence(iData);

  if (qData && qData.success) {
    const digits = document.getElementById('serving-digits');
    const newVal = qData.current ? String(qData.current).padStart(2, '0') : '--';
    if (digits.textContent !== newVal) {
      digits.textContent = newVal;
      digits.classList.remove('pulse');
      void digits.offsetWidth;
      digits.classList.add('pulse');
    }
    document.getElementById('serving-name').textContent = qData.current_name
      ? `Serving ${qData.current_name}`
      : 'No one at the counter';
    renderWaitList(qData.waiting);

    const badge = document.querySelector(`[data-service-count="${activeService}"]`);
    if (badge) badge.textContent = qData.count;
  }

  if (sData && sData.success) {
    document.getElementById('stat-waiting').textContent = sData.waiting;
    document.getElementById('stat-serving').textContent = sData.serving;
    document.getElementById('stat-served').textContent = sData.served;
    document.getElementById('stat-cancelled').textContent = sData.cancelled;
  }

  // Keep sidebar counts fresh for every tab, not just the active one.
  SERVICES.forEach(async (s) => {
    if (s === activeService) return;
    const { data } = await qlFetch(`/api/queue/${encodeURIComponent(s)}`);
    const badge = document.querySelector(`[data-service-count="${s}"]`);
    if (badge && data && data.success) badge.textContent = data.count;
  });
}

document.getElementById('call-next-btn').addEventListener('click', async () => {
  const { ok, data } = await qlFetch('/api/next', {
    method: 'POST',
    body: JSON.stringify({ service: activeService }),
  });
  if (ok && data.success) {
    qlToast(`Now serving #${data.token} — ${data.name}`);
  } else {
    qlToast((data && data.message) || 'No one is waiting.');
  }
  refresh();
});

document.getElementById('reset-btn').addEventListener('click', async () => {
  if (!confirm(`Clear all tickets for ${activeService}? This can't be undone.`)) return;
  const { ok, data } = await qlFetch(`/api/reset/${encodeURIComponent(activeService)}`, { method: 'POST' });
  if (ok && data.success) qlToast('Counter reset.');
  refresh();
});

document.getElementById('refresh-btn').addEventListener('click', refresh);

document.getElementById('logout-btn').addEventListener('click', async () => {
  await qlFetch('/api/admin/logout', { method: 'POST' });
  window.location.href = '/admin/login';
});

refresh();
refreshTimer = setInterval(refresh, 4000);
