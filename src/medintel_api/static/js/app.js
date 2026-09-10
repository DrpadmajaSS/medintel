/**
 * MedIntel Dashboard Application Controller
 */

// Application State
const state = {
  currentFacility: '',
  activeTab: 'tab-home',
  metadata: null,
  metrics: null,
  dailyBrief: null,
  risksList: [],
  riskPage: 1,
  riskPageSize: 20,
  selectedMedDetail: null,
  currentModalFacility: null
};

// Initialize Application on DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  setupEventListeners();
  await loadMetadata();
  await refreshDashboard();
  setupWhatIfSliders();
  runWhatIfSimulation();
  renderHomeWidgets();
});

function setupEventListeners() {
  // Sidebar Navigation Items
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      if (tabId) {
        switchTab(tabId);
      }
    });
  });

  // Sidebar Copilot Button
  document.getElementById('sidebar-copilot-btn')?.addEventListener('click', () => {
    const copilot = document.getElementById('copilot-panel');
    copilot?.classList.toggle('active-drawer');
    document.getElementById('copilot-input')?.focus();
  });

  // Minimize Copilot
  document.getElementById('btn-minimize-copilot')?.addEventListener('click', () => {
    const copilot = document.getElementById('copilot-panel');
    copilot?.classList.remove('active-drawer');
  });

  // Facility Dropdown Change
  const facilitySelect = document.getElementById('global-facility-select');
  if (facilitySelect) {
    facilitySelect.addEventListener('change', async (e) => {
      state.currentFacility = e.target.value;
      await refreshDashboard();
    });
  }

  // Risk Filters
  const searchInput = document.getElementById('risk-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(() => fetchAndRenderRisks(), 300));
  }

  const filterLevel = document.getElementById('filter-risk-level');
  if (filterLevel) {
    filterLevel.addEventListener('change', () => fetchAndRenderRisks());
  }

  const filterClass = document.getElementById('filter-therapeutic-class');
  if (filterClass) {
    filterClass.addEventListener('change', () => fetchAndRenderRisks());
  }

  const filterCrit = document.getElementById('filter-criticality');
  if (filterCrit) {
    filterCrit.addEventListener('change', () => fetchAndRenderRisks());
  }

  // Pagination
  document.getElementById('btn-prev-page')?.addEventListener('click', () => {
    if (state.riskPage > 1) {
      state.riskPage--;
      renderRisksTable();
    }
  });

  document.getElementById('btn-next-page')?.addEventListener('click', () => {
    const maxPages = Math.ceil(state.risksList.length / state.riskPageSize);
    if (state.riskPage < maxPages) {
      state.riskPage++;
      renderRisksTable();
    }
  });

  // What-If Controls
  document.getElementById('btn-run-whatif')?.addEventListener('click', () => {
    runWhatIfSimulation();
  });

  document.getElementById('whatif-med-select')?.addEventListener('change', () => {
    runWhatIfSimulation();
  });

  document.getElementById('whatif-loc-select')?.addEventListener('change', () => {
    runWhatIfSimulation();
  });

  // Modal Simulate in What-If
  document.getElementById('btn-modal-simulate-whatif')?.addEventListener('click', () => {
    if (state.selectedMedDetail) {
      closeMedModal();
      switchTab('tab-what-if');
      const medSelect = document.getElementById('whatif-med-select');
      const locSelect = document.getElementById('whatif-loc-select');
      if (medSelect) medSelect.value = state.selectedMedDetail.medication_id;
      if (locSelect && state.currentModalFacility) locSelect.value = state.currentModalFacility.location_id;
      runWhatIfSimulation();
    }
  });

  // Network Map Node Hover Interactions
  setupMapNodeInteractions();
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-tab="${tabId}"]`)?.classList.add('active');

  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(tabId)?.classList.add('active');

  if (window.lucide) lucide.createIcons();

  if (tabId === 'tab-home') renderHomeWidgets();
  if (tabId === 'tab-risks') fetchAndRenderRisks();
  if (tabId === 'tab-opportunities') loadOpportunitiesTab();
  if (tabId === 'tab-suppliers') loadSuppliersTab();
}

function renderHomeWidgets() {
  // Sparklines
  renderSparkline('sparkline-act', '#ef4444', [105, 110, 118, 122, 116, 128, 134, 138, 145, 142]);
  renderSparkline('sparkline-watch', '#f97316', [24, 26, 25, 29, 31, 35, 38, 42, 46, 52]);

  // Donut Chart
  renderDonutChart('network-donut-chart', 3, 2, 2);
}

function setupMapNodeInteractions() {
  const popover = document.getElementById('map-popover');
  if (!popover) return;

  const nodeData = {
    'LOC001': { name: 'Central AMC', status: 'Healthy', badge: 'badge-low', desc: 'Surplus hub &bull; 1,756 units available' },
    'LOC002': { name: 'North Suburban', status: 'Emerging', badge: 'badge-high', desc: 'Demand acceleration &bull; +76% burn' },
    'LOC003': { name: 'Metro Memorial', status: 'Monitor', badge: 'badge-high', desc: 'Lead time surge &bull; SUP008 hold' },
    'LOC004': { name: 'St. Jude Pavilion', status: 'Protected', badge: 'badge-low', desc: 'Inbound PO-20242 arriving &lt;24h' },
    'LOC005': { name: 'Westside Community', status: 'Deficit', badge: 'badge-critical', desc: '0.0 DOS &bull; Transfer candidate' },
    'LOC006': { name: 'Trauma Center', status: 'High Risk', badge: 'badge-critical', desc: '0.0 DOS &bull; ICU surge' }
  };

  document.querySelectorAll('.map-node').forEach(node => {
    node.addEventListener('mouseenter', (e) => {
      const facId = node.getAttribute('data-facility');
      const info = nodeData[facId];
      if (info) {
        document.getElementById('popover-fac-name').textContent = info.name;
        const badgeEl = document.getElementById('popover-fac-badge');
        badgeEl.className = `badge ${info.badge}`;
        badgeEl.textContent = info.status;
        document.getElementById('popover-fac-desc').innerHTML = info.desc;
      }
    });
  });
}

async function loadMetadata() {
  try {
    const res = await fetch('/api/metadata');
    const data = await res.json();
    state.metadata = data;

    const facSelect = document.getElementById('global-facility-select');
    if (facSelect) {
      facSelect.innerHTML = '<option value="">All Facilities (Network View)</option>';
      data.facilities.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.id;
        opt.textContent = `${f.name} (${f.id})`;
        facSelect.appendChild(opt);
      });
    }

    const classSelect = document.getElementById('filter-therapeutic-class');
    if (classSelect) {
      classSelect.innerHTML = '<option value="">All Classes</option>';
      data.therapeutic_classes.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        classSelect.appendChild(opt);
      });
    }

    const snapBadge = document.getElementById('snapshot-date-text');
    if (snapBadge) snapBadge.textContent = `Snapshot: ${data.snapshot_date}`;
  } catch (err) {
    console.error('Failed to load metadata:', err);
  }
}

async function refreshDashboard() {
  await Promise.all([
    loadMetrics(),
    fetchAndRenderRisks()
  ]);
}

async function loadMetrics() {
  try {
    const locParam = state.currentFacility ? `?location_id=${state.currentFacility}` : '';
    const res = await fetch(`/api/metrics${locParam}`);
    const data = await res.json();
    state.metrics = data;

    const totalIssues = data.critical_risks + data.emerging_risks + data.potential_redistribution_opportunities;
    const attnEl = document.getElementById('hero-attention-count');
    if (attnEl) attnEl.textContent = `${totalIssues} things`;
  } catch (err) {
    console.error('Failed to load metrics:', err);
  }
}

async function fetchAndRenderRisks() {
  try {
    const search = document.getElementById('risk-search-input')?.value || '';
    const riskLevel = document.getElementById('filter-risk-level')?.value || '';
    const thClass = document.getElementById('filter-therapeutic-class')?.value || '';
    const crit = document.getElementById('filter-criticality')?.value || '';

    const params = new URLSearchParams();
    if (state.currentFacility) params.append('location_id', state.currentFacility);
    if (search) params.append('search', search);
    if (riskLevel) params.append('risk_level', riskLevel);
    if (thClass) params.append('therapeutic_class', thClass);
    if (crit) params.append('criticality', crit);
    params.append('limit', '525');

    const res = await fetch(`/api/risks?${params.toString()}`);
    const data = await res.json();
    state.risksList = data.items;
    state.riskPage = 1;

    const countBadge = document.getElementById('risk-count-badge');
    if (countBadge) countBadge.textContent = `${data.total} SKUs Monitored`;
    renderRisksTable();
  } catch (err) {
    console.error('Failed to load risks:', err);
  }
}

function renderRisksTable() {
  const tbody = document.getElementById('risks-table-body');
  if (!tbody) return;

  const total = state.risksList.length;
  if (total === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">No medication risks matched your filters.</td></tr>';
    return;
  }

  const startIdx = (state.riskPage - 1) * state.riskPageSize;
  const endIdx = Math.min(startIdx + state.riskPageSize, total);
  const pageItems = state.risksList.slice(startIdx, endIdx);

  tbody.innerHTML = pageItems.map(item => {
    const badgeClass = `badge-${item.risk_level.toLowerCase()}`;
    const stockoutText = item.days_to_stockout !== null 
      ? `<strong>${item.days_to_stockout.toFixed(1)}d</strong> <span class="text-muted" style="font-size:0.7rem; white-space:nowrap;">(${item.predicted_stockout_date})</span>` 
      : `<span class="text-success" style="font-weight:600; font-size:0.75rem;">None (&gt;60d)</span>`;

    return `
      <tr onclick="openScenarioDetail('${item.medication_id}', '${item.location_id}')">
        <td>
          <div style="font-weight:700; color:var(--text-dark); line-height:1.25; font-size:0.84rem; word-wrap:break-word; overflow-wrap:break-word;">${item.generic_name}</div>
          <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px; display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
            <span style="word-break:normal;">${item.therapeutic_class}</span>
            <span>&bull;</span>
            <span class="badge badge-neutral" style="padding:1px 5px; font-size:0.65rem;">${item.criticality}</span>
          </div>
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-dark); font-size:0.8rem; line-height:1.25; word-wrap:break-word; overflow-wrap:break-word;">${item.location_name}</div>
        </td>
        <td>
          <span class="badge ${badgeClass}" style="white-space:nowrap; font-size:0.72rem; padding:0.25rem 0.65rem; font-weight:700;">${item.risk_level} &bull; ${item.risk_score.toFixed(1)}</span>
        </td>
        <td>
          <div style="font-weight:700; color:var(--text-dark); font-size:0.82rem;">${item.days_of_supply.toFixed(1)} days</div>
          <div style="font-size:0.7rem; color:var(--text-muted);">${item.quantity_on_hand.toFixed(0)} units</div>
        </td>
        <td>
          <div style="font-size:0.8rem; line-height:1.3;">${stockoutText}</div>
          <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">${item.trend_ratio.toFixed(2)}x (${item.average_daily_usage.toFixed(0)}/d)</div>
        </td>
        <td class="col-action">
          <button class="table-action-btn" onclick="event.stopPropagation(); openScenarioDetail('${item.medication_id}', '${item.location_id}')">
            <span>Diagnose</span>
            <i data-lucide="arrow-right"></i>
          </button>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) {
    lucide.createIcons();
  }

  document.getElementById('pagination-info').textContent = `Showing ${startIdx + 1} to ${endIdx} of ${total} SKUs`;
  document.getElementById('btn-prev-page').disabled = state.riskPage <= 1;
  document.getElementById('btn-next-page').disabled = endIdx >= total;
}

// Modal Diagnostic Viewer
async function openScenarioDetail(medId, locId) {
  try {
    const res = await fetch(`/api/risks/${medId}`);
    const drugDetail = await res.json();
    state.selectedMedDetail = drugDetail;

    document.getElementById('modal-drug-name').textContent = drugDetail.generic_name;
    document.getElementById('modal-drug-sub').textContent = `${drugDetail.strength} • ${drugDetail.dosage_form} • $${drugDetail.unit_cost.toFixed(2)}/unit • ID: ${drugDetail.medication_id}`;
    document.getElementById('modal-class-badge').textContent = drugDetail.therapeutic_class;
    document.getElementById('modal-crit-badge').textContent = `${drugDetail.criticality} Criticality`;

    const facSelect = document.getElementById('modal-facility-select');
    facSelect.innerHTML = '';
    drugDetail.facilities.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f.location_id;
      opt.textContent = `${f.location_name} (Risk: ${f.risk_level}, Score: ${f.risk_score.toFixed(1)})`;
      facSelect.appendChild(opt);
    });

    if (locId) {
      facSelect.value = locId;
    }

    renderSelectedFacilityDiagnostic();

    const targetLoc = locId || drugDetail.facilities[0].location_id;
    const utilRes = await fetch(`/api/utilization/${medId}?location_id=${targetLoc}`);
    const utilData = await utilRes.json();
    renderUtilizationChart('modal-util-chart', utilData.time_series, 0, '');

    document.getElementById('med-detail-modal').classList.add('active');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Failed to load drug diagnostic detail:', err);
  }
}

function renderSelectedFacilityDiagnostic() {
  if (!state.selectedMedDetail) return;

  const locId = document.getElementById('modal-facility-select').value;
  const fDetail = state.selectedMedDetail.facilities.find(f => f.location_id === locId) || state.selectedMedDetail.facilities[0];
  state.currentModalFacility = fDetail;

  const riskBadge = document.getElementById('modal-risk-badge');
  riskBadge.className = `badge badge-${fDetail.risk_level.toLowerCase()}`;
  riskBadge.textContent = fDetail.risk_level;

  document.getElementById('mstat-qoh').textContent = `${fDetail.quantity_on_hand.toFixed(0)} units`;
  document.getElementById('mstat-dos').textContent = `${fDetail.days_of_supply.toFixed(1)} days`;
  document.getElementById('mstat-adu').textContent = `${fDetail.average_daily_usage.toFixed(1)} /day`;
  document.getElementById('mstat-trend').textContent = `${fDetail.trend_ratio.toFixed(2)}x Velocity`;
  document.getElementById('mstat-stockout').textContent = fDetail.days_to_stockout !== null ? `${fDetail.days_to_stockout.toFixed(1)}d (${fDetail.predicted_stockout_date})` : 'None (&gt;60d)';
  document.getElementById('mstat-score').textContent = `${fDetail.risk_score.toFixed(1)}/100`;

  document.getElementById('mfactor-primary').textContent = fDetail.primary_risk_factors;
  document.getElementById('mfactor-contrib').textContent = fDetail.contributing_factors;
  document.getElementById('mfactor-mitig').textContent = fDetail.mitigating_factors;
  document.getElementById('mfactor-rec').textContent = fDetail.recommended_review;

  // Open POs
  const poTbody = document.getElementById('modal-po-tbody');
  if (fDetail.open_pos && fDetail.open_pos.length > 0) {
    poTbody.innerHTML = fDetail.open_pos.map(po => `
      <tr>
        <td><strong>${po.po_id}</strong></td>
        <td>${po.order_date}</td>
        <td>${po.expected_delivery_date}</td>
        <td><strong>${po.quantity_ordered}</strong> units</td>
        <td><span class="badge ${po.status === 'In Transit' ? 'badge-primary' : 'badge-high'}">${po.status}</span></td>
      </tr>
    `).join('');
  } else {
    poTbody.innerHTML = '<tr><td colspan="5" class="text-center py-2 text-muted">No active open purchase orders for this location.</td></tr>';
  }

  // Sister Surplus
  const surplusTbody = document.getElementById('modal-surplus-tbody');
  if (fDetail.regional_surplus && fDetail.regional_surplus.length > 0) {
    surplusTbody.innerHTML = fDetail.regional_surplus.map(s => `
      <tr>
        <td><strong>${s.location_name}</strong></td>
        <td>${s.quantity_on_hand.toFixed(0)} units</td>
        <td><span class="badge badge-low">${s.days_of_supply.toFixed(1)} DOS</span></td>
        <td><span class="text-success" style="font-weight:700;">Available for Transfer</span></td>
      </tr>
    `).join('');
  } else {
    surplusTbody.innerHTML = '<tr><td colspan="4" class="text-center py-2 text-muted">No sister facilities maintain surplus stock (&ge;25 DOS) for this drug.</td></tr>';
  }
}

function closeMedModal() {
  document.getElementById('med-detail-modal').classList.remove('active');
}

// What-If Sliders & Simulation
function setupWhatIfSliders() {
  const dSlider = document.getElementById('slider-demand-change');
  const dVal = document.getElementById('val-demand-change');
  dSlider?.addEventListener('input', (e) => {
    const v = parseInt(e.target.value);
    dVal.textContent = `${v >= 0 ? '+' : ''}${v}%`;
  });

  const sSlider = document.getElementById('slider-supplier-delay');
  const sVal = document.getElementById('val-supplier-delay');
  sSlider?.addEventListener('input', (e) => {
    const v = parseInt(e.target.value);
    sVal.textContent = `+${v} days`;
  });

  const iSlider = document.getElementById('slider-inventory-change');
  const iVal = document.getElementById('val-inventory-change');
  iSlider?.addEventListener('input', (e) => {
    const v = parseInt(e.target.value);
    iVal.textContent = `${v >= 0 ? '+' : ''}${v}%`;
  });

  const tSlider = document.getElementById('slider-transfer-units');
  const tVal = document.getElementById('val-transfer-units');
  tSlider?.addEventListener('input', (e) => {
    const v = parseInt(e.target.value);
    tVal.textContent = `+${v} units`;
  });
}

function applyWhatIfPreset(type) {
  const dSlider = document.getElementById('slider-demand-change');
  const sSlider = document.getElementById('slider-supplier-delay');
  const iSlider = document.getElementById('slider-inventory-change');
  const tSlider = document.getElementById('slider-transfer-units');

  if (type === 'surge') {
    document.getElementById('whatif-med-select').value = 'MED022';
    document.getElementById('whatif-loc-select').value = 'LOC002';
    dSlider.value = 50;
    sSlider.value = 0;
    iSlider.value = 0;
    tSlider.value = 0;
  } else if (type === 'transfer') {
    document.getElementById('whatif-med-select').value = 'MED001';
    document.getElementById('whatif-loc-select').value = 'LOC006';
    dSlider.value = 0;
    sSlider.value = 0;
    iSlider.value = 0;
    tSlider.value = 150;
  } else if (type === 'delay') {
    document.getElementById('whatif-med-select').value = 'MED057';
    document.getElementById('whatif-loc-select').value = 'LOC003';
    dSlider.value = 0;
    sSlider.value = 12;
    iSlider.value = 0;
    tSlider.value = 0;
  } else if (type === 'reset') {
    dSlider.value = 0;
    sSlider.value = 0;
    iSlider.value = 0;
    tSlider.value = 0;
  }

  document.getElementById('val-demand-change').textContent = `${dSlider.value >= 0 ? '+' : ''}${dSlider.value}%`;
  document.getElementById('val-supplier-delay').textContent = `+${sSlider.value} days`;
  document.getElementById('val-inventory-change').textContent = `${iSlider.value >= 0 ? '+' : ''}${iSlider.value}%`;
  document.getElementById('val-transfer-units').textContent = `+${tSlider.value} units`;

  runWhatIfSimulation();
}

async function runWhatIfSimulation() {
  const medId = document.getElementById('whatif-med-select')?.value || 'MED022';
  const locId = document.getElementById('whatif-loc-select')?.value || 'LOC002';
  const dChange = parseFloat(document.getElementById('slider-demand-change')?.value || 0);
  const sDelay = parseFloat(document.getElementById('slider-supplier-delay')?.value || 0);
  const iChange = parseFloat(document.getElementById('slider-inventory-change')?.value || 0);
  const tUnits = parseFloat(document.getElementById('slider-transfer-units')?.value || 0);

  try {
    const res = await fetch('/api/what-if', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        medication_id: medId,
        location_id: locId,
        demand_change_percent: dChange,
        supplier_delay_days: sDelay,
        inventory_change_percent: iChange,
        inventory_transfer_units: tUnits
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Simulation error');

    const base = data.baseline;
    document.getElementById('base-med-title').textContent = `${base.generic_name} (${base.medication_id})`;
    document.getElementById('base-loc-sub').textContent = base.location_name;
    document.getElementById('base-qoh').textContent = `${base.quantity_on_hand.toFixed(0)} units`;
    document.getElementById('base-dos').textContent = `${base.days_of_supply.toFixed(1)} days`;
    document.getElementById('base-burn').textContent = `${base.average_daily_usage.toFixed(1)} /day`;
    document.getElementById('base-stockout').textContent = base.days_to_stockout !== null ? `${base.days_to_stockout.toFixed(1)}d (${base.predicted_stockout_date})` : 'None (&gt;60d)';
    
    const baseBadge = document.getElementById('base-risk-badge');
    baseBadge.className = `badge badge-${base.risk_level.toLowerCase()}`;
    baseBadge.textContent = `${base.risk_level} (${base.risk_score.toFixed(1)})`;

    const sim = data.scenario;
    document.getElementById('sim-med-title').textContent = `${base.generic_name} (Simulated)`;
    document.getElementById('sim-loc-sub').textContent = `Perturbed State @ ${base.location_name}`;
    document.getElementById('sim-qoh').textContent = `${sim.projected_quantity_on_hand.toFixed(0)} units`;
    document.getElementById('sim-dos').textContent = `${sim.projected_days_of_supply.toFixed(1)} days`;
    document.getElementById('sim-burn').textContent = `${sim.projected_daily_usage.toFixed(1)} /day`;
    document.getElementById('sim-stockout').textContent = sim.projected_days_to_stockout !== null ? `${sim.projected_days_to_stockout.toFixed(1)}d (${sim.projected_stockout_date})` : 'None (&gt;60d)';

    const simBadge = document.getElementById('sim-risk-badge');
    simBadge.className = `badge badge-${sim.projected_risk_level.toLowerCase()}`;
    simBadge.textContent = `${sim.projected_risk_level} (${sim.projected_risk_score.toFixed(1)})`;

    const imp = data.impact;
    document.getElementById('impact-transition-text').textContent = imp.risk_level_transition;
    document.getElementById('impact-dos-delta').textContent = `Δ ${imp.delta_days_of_supply >= 0 ? '+' : ''}${imp.delta_days_of_supply.toFixed(1)} Days Supply`;
    document.getElementById('impact-explanation-text').textContent = imp.explanation;
    document.getElementById('impact-clinical-text').textContent = imp.clinical_implication;

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Failed to run what-if simulation:', err);
  }
}

// Opportunities Tab Loader
async function loadOpportunitiesTab() {
  try {
    const locParam = state.currentFacility ? `?location_id=${state.currentFacility}` : '';
    const res = await fetch(`/api/opportunities${locParam}`);
    const data = await res.json();

    document.getElementById('opps-total-value').textContent = `Total Value at Stake: $${data.total_value_at_stake_usd.toLocaleString()}`;

    const rTbody = document.getElementById('tbody-rebalancing');
    if (data.redistribution_opportunities.length > 0) {
      rTbody.innerHTML = data.redistribution_opportunities.map(o => `
        <tr>
          <td><strong>${o.generic_name}</strong> <span class="text-muted">(${o.medication_id})</span></td>
          <td>${o.deficit_location_name}</td>
          <td><span class="badge badge-critical">${o.deficit_days_of_supply.toFixed(1)} DOS</span></td>
          <td><strong>${o.surplus_location_name}</strong></td>
          <td><span class="badge badge-low">${o.surplus_days_of_supply.toFixed(1)} DOS</span></td>
          <td><strong>${o.recommended_transfer_units}</strong> units</td>
          <td><strong class="text-success">$${o.estimated_cost_avoidance_usd.toLocaleString()}</strong></td>
          <td><span style="font-size:0.76rem;">${o.action_directive}</span></td>
        </tr>
      `).join('');
    } else {
      rTbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted">No cross-location imbalances detected.</td></tr>';
    }

    const eTbody = document.getElementById('tbody-expiry-opps');
    if (data.expiry_salvage_opportunities.length > 0) {
      eTbody.innerHTML = data.expiry_salvage_opportunities.map(e => `
        <tr>
          <td><strong>${e.lot_id}</strong></td>
          <td><strong>${e.generic_name}</strong></td>
          <td>${e.location_name}</td>
          <td>${e.expiry_date}</td>
          <td><span class="badge badge-high">${e.days_to_expiry} days</span></td>
          <td><strong>${e.projected_unconsumed_units}</strong> / ${e.lot_quantity} units</td>
          <td><strong class="text-critical">$${e.projected_financial_waste_usd.toLocaleString()}</strong></td>
          <td><span style="font-size:0.76rem;">${e.action_directive}</span></td>
        </tr>
      `).join('');
    } else {
      eTbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted">No near-expiry lots with unconsumed risk.</td></tr>';
    }
  } catch (err) {
    console.error('Failed to load opportunities:', err);
  }
}

// Suppliers Tab Loader
async function loadSuppliersTab() {
  try {
    const res = await fetch('/api/suppliers');
    const data = await res.json();

    const tbody = document.getElementById('suppliers-table-body');
    tbody.innerHTML = data.items.map(s => {
      const surgeBadge = s.lead_time_surge_days > 0 
        ? `<span class="badge badge-critical">+${s.lead_time_surge_days}d Surge</span>`
        : `<span class="badge badge-low">Normal</span>`;

      return `
        <tr>
          <td><strong>${s.supplier_id}</strong></td>
          <td><strong>${s.supplier_name}</strong></td>
          <td>${s.medications_supplied_count} drugs</td>
          <td>${s.standard_lead_time_days} days</td>
          <td><strong>${s.current_lead_time_days} days</strong></td>
          <td>${surgeBadge}</td>
          <td><strong>${(s.reliability_score * 100).toFixed(1)}%</strong></td>
          <td>${s.active_disruptions_count > 0 ? `<span class="badge badge-high">${s.active_disruptions_count} Active</span>` : '0'}</td>
          <td>${s.total_delayed_orders_count > 0 ? `<span class="badge badge-critical">${s.total_delayed_orders_count} POs</span>` : '0'}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load suppliers:', err);
  }
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
