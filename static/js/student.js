const STORAGE_KEY = 'queueless_ticket_id';

const joinStep = document.getElementById('join-step');
const ticketStep = document.getElementById('ticket-step');
const nameInput = document.getElementById('name-input');
const joinBtn = document.getElementById('join-btn');
const joinError = document.getElementById('join-error');
const cancelBtn = document.getElementById('cancel-btn');
const newTicketBtn = document.getElementById('new-ticket-btn');

let selectedService = null;
let currentTicketId = null;
let pollTimer = null;
let notifiedClose = false;
let notifiedTurn = false;

function setError(msg) {
  if (!msg) { joinError.classList.remove('show'); return; }
  joinError.textContent = msg;
  joinError.classList.add('show');
}

function selectService(service) {
  selectedService = service;
  document.querySelectorAll('#service-picker .service-card').forEach((card) => {
    card.classList.toggle('is-selected', card.dataset.service === service);
  });
  updateJoinButton();
}

function updateJoinButton() {
  joinBtn.disabled = !(selectedService && nameInput.value.trim().length > 0);
}

document.querySelectorAll('#service-picker .service-card').forEach((card) => {
  card.addEventListener('click', () => selectService(card.dataset.service));
});
nameInput.addEventListener('input', updateJoinButton);

if (PRESELECT && SERVICES.includes(PRESELECT)) selectService(PRESELECT);

async function handleJoin() {
  setError(null);
  joinBtn.disabled = true;
  const { ok, data } = await qlFetch('/api/join', {
    method: 'POST',
    body: JSON.stringify({ name: nameInput.value.trim(), service: selectedService }),
  });

  if (!ok || !data.success) {
    setError(data.message || 'Could not join the queue. Try again.');
    if (data.existing_id) {
      currentTicketId = data.existing_id;
      localStorage.setItem(STORAGE_KEY, String(data.existing_id));
      showTicketView();
      startPolling();
    }
    updateJoinButton();
    return;
  }

  currentTicketId = data.id;
  localStorage.setItem(STORAGE_KEY, String(data.id));
  showTicketView();
  applyStatus({ status: 'waiting', ...data });
  startPolling();
}

joinBtn.addEventListener('click', handleJoin);

function showTicketView() {
  joinStep.style.display = 'none';
  ticketStep.style.display = 'block';
}

function showJoinView() {
  ticketStep.style.display = 'none';
  joinStep.style.display = 'block';
  newTicketBtn.style.display = 'none';
  cancelBtn.style.display = 'inline-flex';
  nameInput.value = '';
  selectedService = null;
  document.querySelectorAll('#service-picker .service-card').forEach((c) => c.classList.remove('is-selected'));
  updateJoinButton();
  setError(null);
}

function requestNotifyPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function notify(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body });
  }
  qlToast(body);
}

function applyStatus(data) {
  document.getElementById('t-service').textContent = data.service;
  document.getElementById('t-name').textContent = data.name;

  const tokenEl = document.getElementById('t-token');
  const newTokenText = String(data.token).padStart(2, '0');
  if (tokenEl.textContent !== newTokenText) {
    tokenEl.textContent = newTokenText;
  }

  document.getElementById('t-current').textContent = String(data.current || 0).padStart(2, '0');

  const dot = document.getElementById('t-status-dot');
  const statusText = document.getElementById('t-status-text');

  if (data.status === 'waiting') {
    dot.className = 'status-dot waiting';
    statusText.textContent = 'Waiting';
    document.getElementById('t-ahead').textContent = data.ahead;
    document.getElementById('t-eta').textContent = data.estimated_minutes;
    const progressBase = Math.max(data.ahead + 1, 1);
    const pct = Math.max(6, 100 - (data.ahead / progressBase) * 100);
    document.getElementById('t-progress').style.width = `${pct}%`;

    if (data.ahead <= 2 && !notifiedClose) {
      notifiedClose = true;
      requestNotifyPermission();
      const who = data.ahead === 0 ? 'You\u2019re next' : `Only ${data.ahead} ${data.ahead === 1 ? 'person' : 'people'} ahead of you`;
      notify('You\u2019re almost up', `${who} at ${data.service}. Start heading over.`);
    }
  } else if (data.status === 'serving') {
    dot.className = 'status-dot';
    statusText.textContent = "It's your turn!";
    document.getElementById('t-ahead').textContent = 0;
    document.getElementById('t-eta').textContent = 0;
    document.getElementById('t-progress').style.width = '100%';
    if (!notifiedTurn) {
      notifiedTurn = true;
      notify("\ud83c\udf89 It's your turn!", `Head to ${data.service} now — token #${data.token}.`);
    }
    cancelBtn.style.display = 'none';
  } else {
    dot.className = 'status-dot done';
    statusText.textContent = data.status === 'served' ? 'Completed' : 'Cancelled';
    document.getElementById('t-progress').style.width = '100%';
    cancelBtn.style.display = 'none';
    newTicketBtn.style.display = 'inline-flex';
    stopPolling();
    localStorage.removeItem(STORAGE_KEY);
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(pollStatus, 3500);
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

async function pollStatus() {
  if (!currentTicketId) return;
  const { ok, data } = await qlFetch(`/api/status/${currentTicketId}`);
  if (!ok || !data.success) return;
  applyStatus(data);
}

cancelBtn.addEventListener('click', async () => {
  if (!currentTicketId) return;
  const { ok, data } = await qlFetch(`/api/leave/${currentTicketId}`, { method: 'POST' });
  if (ok && data.success) {
    qlToast('Ticket cancelled.');
    stopPolling();
    localStorage.removeItem(STORAGE_KEY);
    currentTicketId = null;
    showJoinView();
  } else {
    qlToast(data.message || 'Could not cancel right now.');
  }
});

newTicketBtn.addEventListener('click', () => {
  currentTicketId = null;
  showJoinView();
});

async function updateServicePickerPills() {
  const { ok, data } = await qlFetch('/api/overview');
  if (!ok || !data.success) return;
  SERVICES.forEach((s) => {
    const pillEl = document.querySelector(`[data-service-pill="${s}"]`);
    if (!pillEl) return;
    const count = data.services[s] ? data.services[s].waiting : 0;
    const { cls, text } = qlPillFor(count);
    pillEl.className = `pill ${cls}`;
    pillEl.textContent = text;
  });
}
updateServicePickerPills();
setInterval(() => { if (ticketStep.style.display === 'none') updateServicePickerPills(); }, 5000);

// Resume an in-flight ticket after a page reload.
(function resume() {
  const savedId = localStorage.getItem(STORAGE_KEY);
  if (!savedId) return;
  currentTicketId = savedId;
  showTicketView();
  pollStatus().then(startPolling);
})();
