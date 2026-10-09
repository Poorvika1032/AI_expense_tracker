(() => {
  const form = document.querySelector('#planner-form');
  if (!form) return;

  const field = (name) => form.elements.namedItem(name);
  const source = field('source');
  const destination = field('destination');
  const travelers = field('travelers');
  const days = field('days');
  const budget = field('budget');
  const transport = field('transportation');
  const start = field('start_date');
  const end = field('end_date');
  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
  const output = {
    source: document.querySelector('#preview-source'),
    destination: document.querySelector('#preview-destination'),
    days: document.querySelector('#preview-days'),
    travelers: document.querySelector('#preview-travelers'),
    cost: document.querySelector('#preview-cost'),
    hint: document.querySelector('#preview-hint'),
    status: document.querySelector('#budget-status'),
    detail: document.querySelector('#budget-detail'),
    fill: document.querySelector('#budget-fill'),
    track: document.querySelector('.budget-track'),
    options: document.querySelector('#transport-options'),
    recommendation: document.querySelector('#live-recommendation'),
  };
  let timer;
  let requestNumber = 0;
  let prices = {};
  let modelReady = false;
  const money = (amount) => new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(amount);

  function updateTripLength() {
    if (!start.value || !end.value || end.value < start.value) return;
    const duration = Math.floor((new Date(`${end.value}T00:00:00`) - new Date(`${start.value}T00:00:00`)) / 86400000) + 1;
    if (duration >= 1 && duration <= 365) days.value = duration;
  }

  function showBudget(amount) {
    const limit = Number(budget.value);
    if (!Number.isFinite(limit) || limit <= 0 || !Number.isFinite(amount)) {
      output.status.textContent = 'Add a budget';
      output.detail.textContent = 'Budget meter uses the model estimate.';
      output.fill.style.width = '0%';
      output.fill.className = '';
      output.track.setAttribute('aria-valuenow', '0');
      return;
    }
    const ratio = amount / limit;
    const percent = Math.round(ratio * 100);
    output.fill.style.width = `${Math.min(100, percent)}%`;
    output.fill.className = ratio > 1 ? 'is-over' : ratio >= .85 ? '' : 'is-good';
    output.track.setAttribute('aria-valuenow', String(Math.min(100, percent)));
    if (ratio > 1) {
      output.status.textContent = 'Over budget';
      output.detail.textContent = `${money(amount - limit)} over your budget (${percent}% used).`;
    } else if (ratio >= .85) {
      output.status.textContent = 'Near your limit';
      output.detail.textContent = `${money(limit - amount)} remaining. You are approaching your budget.`;
    } else {
      output.status.textContent = 'Within budget';
      output.detail.textContent = `${money(limit - amount)} remaining (${percent}% of budget used).`;
    }
  }

  function renderOptions(data) {
    prices = data.predictions;
    const chosen = data.recommended_transport;
    const entries = ['Bus', 'Train', 'Car'];
    output.options.innerHTML = '';
    entries.forEach((mode) => {
      const item = prices[mode];
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'transport-card';
      button.setAttribute('aria-pressed', String(mode === transport.value));
      button.setAttribute('aria-label', `${mode}: ${money(item.total_cost)}${mode === chosen ? ', lowest affordable estimate' : ''}`);
      const label = document.createElement('span');
      label.className = 'transport-name';
      label.textContent = mode.toUpperCase() + (mode === chosen ? ' · BEST VALUE' : '');
      const cost = document.createElement('span');
      cost.className = 'transport-cost';
      cost.textContent = money(item.total_cost);
      button.append(label, cost);
      button.addEventListener('click', () => {
        transport.value = mode;
        output.options.querySelectorAll('.transport-card').forEach((card) => card.setAttribute('aria-pressed', String(card === button)));
        showBudget(item.total_cost);
        if (mode === chosen) output.recommendation.textContent = `Best value: ${mode} is the lowest modeled option that fits this budget.`;
        else if (item.total_cost <= Number(budget.value)) output.recommendation.textContent = `${mode} is selected. The model estimates it at ${money(item.total_cost)}.`;
        else output.recommendation.textContent = `${mode} is selected, but its estimate is over this budget. ${chosen} is the best affordable option.`;
      });
      output.options.append(button);
    });
    const selected = prices[transport.value] || prices[chosen];
    output.cost.textContent = money(selected.total_cost);
    showBudget(selected.total_cost);
    if (selected.total_cost <= Number(budget.value)) {
      output.recommendation.textContent = `${chosen} has the lowest modeled cost within this budget. Choose a transport card to compare.`;
    } else {
      output.recommendation.textContent = `All modeled options exceed this budget. ${chosen} is the lowest estimated cost.`;
    }
    output.hint.textContent = 'Live estimate from your Random Forest model.';
  }

  async function preview() {
    const myRequest = ++requestNumber;
    const details = {
      source: source.value.trim(), destination: destination.value.trim(),
      travelers: Number(travelers.value), days: Number(days.value), budget: Number(budget.value),
    };
    output.source.textContent = details.source || 'Origin';
    output.destination.textContent = details.destination || 'Destination';
    output.days.textContent = days.value || '—';
    output.travelers.textContent = travelers.value || '—';
    const complete = details.source && details.destination && details.source.toLowerCase() !== details.destination.toLowerCase()
      && Number.isInteger(details.travelers) && details.travelers >= 1 && details.travelers <= 100
      && Number.isInteger(details.days) && details.days >= 1 && details.days <= 365
      && Number.isFinite(details.budget) && details.budget > 0;
    if (!complete) {
      modelReady = false;
      output.cost.textContent = '—';
      output.hint.textContent = 'Add a different origin and destination, travelers, and budget for a live estimate.';
      output.recommendation.textContent = 'The best-value option appears after a valid route is entered.';
      output.options.innerHTML = '<div class="transport-card" aria-disabled="true"><span class="transport-name">BUS</span><span class="transport-cost">—</span></div><div class="transport-card" aria-disabled="true"><span class="transport-name">TRAIN</span><span class="transport-cost">—</span></div><div class="transport-card" aria-disabled="true"><span class="transport-name">CAR</span><span class="transport-cost">—</span></div>';
      showBudget(NaN);
      return;
    }
    modelReady = false;
    output.hint.textContent = 'Checking your route with the travel cost model…';
    try {
      const response = await fetch('/api/predict', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
        body: JSON.stringify(details),
      });
      const result = await response.json();
      if (myRequest !== requestNumber) return;
      if (!response.ok || !result.success) throw new Error(result.error || 'Prediction unavailable.');
      modelReady = true;
      renderOptions(result.data);
    } catch (error) {
      output.cost.textContent = '—';
      output.hint.textContent = error.message || 'Live estimate unavailable. Submit the form to try again.';
      output.recommendation.textContent = 'The saved trip estimate is calculated by the server when you submit.';
      showBudget(NaN);
    }
  }

  function schedulePreview() {
    updateTripLength();
    modelReady = false;
    clearTimeout(timer);
    timer = setTimeout(preview, 420);
  }

  [source, destination, travelers, days, budget, transport, start, end].forEach((input) => {
    input.addEventListener('input', schedulePreview);
    input.addEventListener('change', schedulePreview);
  });
  const submitButton = document.querySelector('#predict-button');
  form.addEventListener('submit', (event) => {
    if (!modelReady) {
      event.preventDefault();
      clearTimeout(timer);
      preview().then(() => { if (modelReady && form.reportValidity()) form.requestSubmit(submitButton); });
      return;
    }
    submitButton.disabled = true;
    submitButton.textContent = 'Calculating and saving your trip…';
  });

  document.querySelectorAll('[data-count]').forEach((node) => {
    const target = Number(node.dataset.count);
    if (!Number.isFinite(target) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const duration = 550;
    const started = performance.now();
    const currency = node.dataset.format === 'currency';
    function tick(now) {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - (1 - progress) ** 3;
      const value = target * eased;
      node.textContent = currency ? money(value) : Math.round(value).toLocaleString('en-IN');
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });

  if (start && end) {
    start.addEventListener('change', () => { end.min = start.value; if (end.value && end.value < start.value) end.value = ''; });
    end.addEventListener('change', () => { start.max = end.value; if (start.value && start.value > end.value) start.value = ''; });
  }
})();
