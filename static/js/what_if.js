(() => {
  const form = document.querySelector('#what-if-form');
  if (!form) return;
  const read = (key) => form.elements.namedItem(key);
  const source = read('source');
  const destination = read('destination');
  const days = read('days');
  const travelers = read('travelers');
  const budget = read('budget');
  const transportation = read('transportation');
  const csrf = form.querySelector('[name="csrf_token"]').value;
  const views = {
    baseCost: document.querySelector('#base-cost'), scenarioCost: document.querySelector('#scenario-cost'),
    delta: document.querySelector('#scenario-delta'), baseDescription: document.querySelector('#base-description'),
    scenarioDescription: document.querySelector('#scenario-description'), budget: document.querySelector('#scenario-budget'),
    hint: document.querySelector('#scenario-hint'),
  };
  let baseline = null;
  let timer;
  let sequence = 0;
  const formatMoney = (amount) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);

  async function estimate(plan) {
    const response = await fetch('/api/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ source: plan.source, destination: plan.destination, travelers: plan.travelers,
        days: plan.days, budget: plan.budget }),
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'Prediction service is unavailable.');
    return result.data.predictions[plan.transportation].total_cost;
  }

  async function update() {
    const currentSequence = ++sequence;
    document.querySelector('#days-value').value = days.value;
    document.querySelector('#travelers-value').value = travelers.value;
    const route = source.value.trim() && destination.value.trim() && source.value.trim().toLowerCase() !== destination.value.trim().toLowerCase();
    const budgetValue = Number(budget.value);
    if (!route || !Number.isFinite(budgetValue) || budgetValue <= 0) {
      views.hint.textContent = 'Enter two different places and a positive budget for real model estimates.';
      views.baseCost.textContent = views.scenarioCost.textContent = views.delta.textContent = '—';
      return;
    }
    if (!baseline) baseline = { source: source.value.trim(), destination: destination.value.trim(), days: Number(days.value),
      travelers: Number(travelers.value), budget: budgetValue, transportation: transportation.value };
    const scenario = { source: source.value.trim(), destination: destination.value.trim(), days: Number(days.value),
      travelers: Number(travelers.value), budget: budgetValue, transportation: transportation.value };
    views.hint.textContent = 'Recalculating both plans with the Random Forest model…';
    try {
      const [baseCost, scenarioCost] = await Promise.all([estimate(baseline), estimate(scenario)]);
      if (currentSequence !== sequence) return;
      views.baseCost.textContent = formatMoney(baseCost);
      views.scenarioCost.textContent = formatMoney(scenarioCost);
      views.delta.textContent = `${scenarioCost > baseCost ? '+' : scenarioCost < baseCost ? '−' : ''}${formatMoney(Math.abs(scenarioCost - baseCost))}`;
      views.delta.className = scenarioCost > baseCost ? 'delta-up' : scenarioCost < baseCost ? 'delta-down' : '';
      views.baseDescription.textContent = `${baseline.days} days · ${baseline.travelers} traveler${baseline.travelers === 1 ? '' : 's'} · ${baseline.transportation}`;
      views.scenarioDescription.textContent = `${scenario.days} days · ${scenario.travelers} traveler${scenario.travelers === 1 ? '' : 's'} · ${scenario.transportation}`;
      const remaining = budgetValue - scenarioCost;
      views.budget.textContent = remaining >= 0 ? `${formatMoney(remaining)} remaining · within budget` : `${formatMoney(Math.abs(remaining))} over budget`;
      views.hint.textContent = 'Both costs are calculated by the saved travel expense model.';
    } catch (error) {
      if (currentSequence !== sequence) return;
      views.hint.textContent = error.message;
      views.baseCost.textContent = views.scenarioCost.textContent = views.delta.textContent = '—';
    }
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(update, 360);
  }
  days.addEventListener('input', () => { document.querySelector('#days-value').value = days.value; schedule(); });
  travelers.addEventListener('input', () => { document.querySelector('#travelers-value').value = travelers.value; schedule(); });
  [source, destination, budget, transportation].forEach((field) => field.addEventListener('input', schedule));
  transportation.addEventListener('change', schedule);
  form.addEventListener('submit', () => {
    const button = document.querySelector('#scenario-submit');
    button.disabled = true;
    button.textContent = 'Calculating scenarios…';
  });
  update();
})();
