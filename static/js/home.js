startClock('board-clock');

function renderOverview(services) {
  const strip = document.getElementById('overview-strip');
  strip.innerHTML = Object.entries(services).map(([name, info]) => `
    <div class="overview-tile">
      <div class="ot-service">${name}</div>
      <div class="ot-current">${String(info.current || 0).padStart(2, '0')}</div>
      <div class="ot-waiting">${info.waiting} waiting</div>
    </div>
  `).join('');

  SERVICES.forEach((s) => {
    const pillEl = document.querySelector(`[data-service="${s}"] [data-role="waiting-pill"]`);
    if (!pillEl) return;
    const count = services[s] ? services[s].waiting : 0;
    const { cls, text } = qlPillFor(count);
    pillEl.className = `pill ${cls}`;
    pillEl.textContent = text;
  });
}

async function refreshOverview() {
  const { ok, data } = await qlFetch('/api/overview');
  if (ok && data.success) renderOverview(data.services);
}

refreshOverview();
setInterval(refreshOverview, 4000);

async function refreshImpact() {
  const { ok, data } = await qlFetch('/api/impact');
  if (ok && data.success) {
    document.getElementById('impact-minutes').textContent = qlFormatMinutes(data.minutes_saved);
    document.getElementById('impact-tokens').textContent = data.tokens_served;
  }
}

refreshImpact();
setInterval(refreshImpact, 15000);
