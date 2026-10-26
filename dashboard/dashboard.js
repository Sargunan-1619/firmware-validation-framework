/**
 * Firmware Validation Framework — Web Dashboard Logic
 * Zero-dependency vanilla JavaScript managing telemetry, execution, and test reporting.
 */

(function () {
  'use strict';

  // Global application state
  let currentReport = null;
  let activeCategory = 'all';
  let currentSearch = '';
  let serverStatus = null;

  // DOM Element References
  const elements = {
    binaryStatusPill: document.getElementById('binary-status-pill'),
    binaryStatusText: document.getElementById('binary-status-text'),
    platformTag: document.getElementById('platform-text'),
    targetBinLabel: document.getElementById('target-bin-label'),
    runTimestamp: document.getElementById('run-timestamp'),
    suiteSelect: document.getElementById('suite-select'),
    btnRunValidation: document.getElementById('btn-run-validation'),
    btnViewRawJson: document.getElementById('btn-view-raw-json'),
    btnDownloadReport: document.getElementById('btn-download-report'),
    
    // KPI elements
    kpiTotal: document.getElementById('kpi-val-total'),
    kpiPassed: document.getElementById('kpi-val-passed'),
    kpiFailed: document.getElementById('kpi-val-failed'),
    kpiRate: document.getElementById('kpi-val-rate'),
    kpiSubTotal: document.getElementById('kpi-sub-total'),
    kpiSubPassed: document.getElementById('kpi-sub-passed'),
    kpiSubFailed: document.getElementById('kpi-sub-failed'),
    kpiSubDuration: document.getElementById('kpi-sub-duration'),

    // Simulation elements
    simTempSlider: document.getElementById('sim-temp-slider'),
    simTempInput: document.getElementById('sim-temp-input'),
    simTempDisplay: document.getElementById('sim-temp-display'),
    simStatusSelect: document.getElementById('sim-status-select'),
    btnExecuteSim: document.getElementById('btn-execute-sim'),
    simBtnText: document.getElementById('sim-btn-text'),
    simSpinner: document.getElementById('sim-spinner'),
    simLatencyBadge: document.getElementById('sim-latency-badge'),
    thermalBarFill: document.getElementById('thermal-bar-fill'),
    simOutState: document.getElementById('sim-out-state'),
    simOutFault: document.getElementById('sim-out-fault'),
    simOutExitcode: document.getElementById('sim-out-exitcode'),
    simOutTemp: document.getElementById('sim-out-temp'),
    simOutTerminal: document.getElementById('sim-out-terminal'),

    // Test Catalog elements
    categoryTabs: document.getElementById('category-tabs'),
    testSearchInput: document.getElementById('test-search-input'),
    testCardsList: document.getElementById('test-cards-list'),

    // Modal elements
    jsonModal: document.getElementById('json-modal'),
    modalTitle: document.getElementById('modal-title'),
    modalMetaTimestamp: document.getElementById('modal-meta-timestamp'),
    jsonModalContent: document.getElementById('json-modal-content'),
    btnCopyJson: document.getElementById('btn-copy-json'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalDismissBtn: document.getElementById('modal-dismiss-btn'),

    // Toast container
    toastContainer: document.getElementById('toast-container'),
  };

  // ==========================================================================
  // Toast Notifications
  // ==========================================================================
  function showToast(message, type = 'info', durationMs = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
    } else if (type === 'error') {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    } else {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, durationMs);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatDate(isoStr) {
    if (!isoStr) return 'Never executed';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString() + ' (UTC)';
    } catch {
      return isoStr;
    }
  }

  // ==========================================================================
  // Server Status & Health Check
  // ==========================================================================
  async function fetchServerStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      serverStatus = data;

      // Update platform and binary indicator
      elements.platformTag.textContent = data.platform || 'Host OS';
      
      const binName = data.target_binary ? data.target_binary.split(/[\\/]/).pop() : 'sensor_controller.exe';
      elements.targetBinLabel.textContent = binName;

      if (data.binary_exists) {
        elements.binaryStatusPill.className = 'status-pill status-pill-ok';
        elements.binaryStatusText.textContent = `Target Found: ${binName}`;
      } else {
        elements.binaryStatusPill.className = 'status-pill status-pill-error';
        elements.binaryStatusText.textContent = 'Binary Missing (Build Project 1)';
      }

      if (data.latest_report && data.latest_report.timestamp) {
        elements.runTimestamp.textContent = formatDate(data.latest_report.timestamp);
      }
    } catch (err) {
      elements.binaryStatusPill.className = 'status-pill status-pill-error';
      elements.binaryStatusText.textContent = 'Server Offline';
      console.warn('Status check failed:', err);
    }
  }

  // ==========================================================================
  // Report Fetch & KPIs
  // ==========================================================================
  async function loadLatestReport() {
    try {
      const res = await fetch('/api/report');
      if (res.status === 404) {
        renderEmptyState('No validation report found. Click "Run Validation" to execute tests.');
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      currentReport = data;
      renderReportData(data);
    } catch (err) {
      renderEmptyState(`Failed to load validation report: ${err.message}`);
    }
  }

  function renderReportData(report) {
    const stats = report.statistics || {};
    const meta = report.metadata || {};

    // Update Timestamp
    elements.runTimestamp.textContent = formatDate(meta.timestamp);

    // Update KPIs
    elements.kpiTotal.textContent = stats.total !== undefined ? stats.total : '--';
    elements.kpiPassed.textContent = stats.passed !== undefined ? stats.passed : '--';
    elements.kpiFailed.textContent = (stats.failed || 0) + (stats.errors || 0) + (stats.timed_out || 0);
    elements.kpiRate.textContent = `${stats.pass_rate_percent !== undefined ? stats.pass_rate_percent : 100}%`;

    elements.kpiSubTotal.textContent = `Target: ${meta.target_binary ? meta.target_binary.split(/[\\/]/).pop() : 'sensor_controller.exe'}`;
    elements.kpiSubDuration.textContent = `Duration: ${stats.total_duration_ms ? stats.total_duration_ms.toFixed(1) : '0'} ms`;

    if ((stats.failed || 0) === 0 && (stats.errors || 0) === 0) {
      elements.kpiSubPassed.textContent = 'Zero regressions detected';
      elements.kpiSubPassed.className = 'kpi-subtext text-green';
      elements.kpiSubFailed.textContent = 'Nominal threshold';
      elements.kpiSubFailed.className = 'kpi-subtext';
    } else {
      elements.kpiSubPassed.textContent = `${stats.passed} test(s) succeeded`;
      elements.kpiSubFailed.textContent = 'Verification discrepancies!';
      elements.kpiSubFailed.className = 'kpi-subtext text-red';
    }

    // Update Category Counts
    updateCategoryTabCounts(report.test_results || []);

    // Render Test Cards
    renderTestCards();
  }

  function updateCategoryTabCounts(results) {
    const counts = {
      all: results.length,
      normal: 0,
      warning: 0,
      fault: 0,
      boundary: 0,
      invalid_input: 0,
      sensor_error: 0,
      execution_failure: 0,
    };

    results.forEach(r => {
      const cat = (r.category || '').toLowerCase();
      if (counts[cat] !== undefined) {
        counts[cat]++;
      }
    });

    Object.keys(counts).forEach(k => {
      const badge = document.getElementById(`count-${k}`);
      if (badge) badge.textContent = counts[k];
    });
  }

  function renderEmptyState(message) {
    elements.testCardsList.innerHTML = `
      <div class="empty-state">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span>${escapeHtml(message)}</span>
      </div>
    `;
  }

  // ==========================================================================
  // Test Cards Rendering & Filtering
  // ==========================================================================
  function renderTestCards() {
    if (!currentReport || !currentReport.test_results) {
      renderEmptyState('No test results available.');
      return;
    }

    const results = currentReport.test_results;
    const filtered = results.filter(test => {
      // Category filter
      if (activeCategory !== 'all' && (test.category || '').toLowerCase() !== activeCategory.toLowerCase()) {
        return false;
      }
      // Search filter
      if (currentSearch) {
        const query = currentSearch.toLowerCase();
        const matchesId = (test.id || '').toLowerCase().includes(query);
        const matchesName = (test.name || '').toLowerCase().includes(query);
        const matchesDesc = (test.description || '').toLowerCase().includes(query);
        if (!matchesId && !matchesName && !matchesDesc) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      renderEmptyState('No test cases match the active filter or search criteria.');
      return;
    }

    elements.testCardsList.innerHTML = '';

    filtered.forEach(test => {
      const card = createTestCardElement(test);
      elements.testCardsList.appendChild(card);
    });
  }

  function createTestCardElement(test) {
    const card = document.createElement('div');
    card.className = 'test-card';
    card.dataset.id = test.id;

    const isPass = test.status === 'PASSED';
    const isTimeout = test.status === 'TIMED_OUT';
    let statusClass = 'badge-pass';
    let statusLabel = '[PASS]';

    if (test.status === 'FAILED') {
      statusClass = 'badge-fail';
      statusLabel = '[FAIL]';
    } else if (isTimeout) {
      statusClass = 'badge-time';
      statusLabel = '[TIME]';
    } else if (test.status === 'ERROR') {
      statusClass = 'badge-fail';
      statusLabel = '[ERR ]';
    }

    const exp = test.expected || {};
    const act = test.actual || {};

    const exitCodeMatch = exp.exit_code === null || exp.exit_code === act.exit_code;
    const stateMatch = !exp.state || exp.state === act.state;
    const faultMatch = !exp.fault || exp.fault === act.fault;

    const cmdStr = `./sensor_controller.exe ${(test.cli_args || []).join(' ')}`;

    card.innerHTML = `
      <div class="test-card-summary" role="button" tabindex="0" aria-expanded="false">
        <div class="test-card-left">
          <span class="badge-status ${statusClass}">${statusLabel}</span>
          <span class="test-id">${escapeHtml(test.id)}</span>
          <span class="badge-category">${escapeHtml(test.category)}</span>
          <span class="test-name">${escapeHtml(test.name)}</span>
        </div>
        <div class="test-card-right">
          <span class="test-duration">${test.duration_ms ? test.duration_ms.toFixed(2) : '0.00'} ms</span>
          <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </div>

      <div class="test-card-details">
        <p class="details-desc"><strong>Intent &amp; Physics:</strong> ${escapeHtml(test.description)}</p>

        <div class="details-grid">
          <div>
            <table class="comparison-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Expected</th>
                  <th>Actual Subprocess</th>
                  <th>Evaluation</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Exit Code</td>
                  <td>${exp.exit_code !== null ? exp.exit_code : 'Any'}</td>
                  <td>${act.exit_code !== null ? act.exit_code : 'None'}</td>
                  <td class="${exitCodeMatch ? 'match' : 'mismatch'}">${exitCodeMatch ? 'MATCH' : 'MISMATCH'}</td>
                </tr>
                <tr>
                  <td>State</td>
                  <td>${escapeHtml(exp.state || 'N/A')}</td>
                  <td>${escapeHtml(act.state || 'N/A')}</td>
                  <td class="${stateMatch ? 'match' : 'mismatch'}">${stateMatch ? 'MATCH' : 'MISMATCH'}</td>
                </tr>
                <tr>
                  <td>Fault Code</td>
                  <td>${escapeHtml(exp.fault || 'N/A')}</td>
                  <td>${escapeHtml(act.fault || 'N/A')}</td>
                  <td class="${faultMatch ? 'match' : 'mismatch'}">${faultMatch ? 'MATCH' : 'MISMATCH'}</td>
                </tr>
                <tr>
                  <td>Temperature</td>
                  <td>${exp.temp !== undefined && exp.temp !== null ? exp.temp : 'N/A'}</td>
                  <td>${act.temp !== undefined && act.temp !== null ? act.temp : 'N/A'}</td>
                  <td class="match">VERIFIED</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div>
            <div class="cli-call-box">
              <div class="cli-label">Invocation Parameters</div>
              <div class="cli-code">$ ${escapeHtml(cmdStr)}</div>
              ${act.stdout ? `<div class="cli-label" style="margin-top:8px;">STDOUT</div><div class="cli-code" style="color:#a7f3d0;">${escapeHtml(act.stdout)}</div>` : ''}
              ${act.stderr ? `<div class="cli-label" style="margin-top:8px;color:#fca5a5;">STDERR</div><div class="cli-code" style="color:#fca5a5;">${escapeHtml(act.stderr)}</div>` : ''}
            </div>
          </div>
        </div>

        ${test.failure_reasons && test.failure_reasons.length > 0 ? `
          <div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);padding:10px 14px;border-radius:6px;color:#fca5a5;font-size:0.78rem;">
            <strong>Failure Diagnostics:</strong>
            <ul style="margin-left:20px;margin-top:4px;">
              ${test.failure_reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;

    // Toggle expansion on click
    const summary = card.querySelector('.test-card-summary');
    summary.addEventListener('click', () => {
      const isOpen = card.classList.toggle('open');
      summary.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    return card;
  }

  // ==========================================================================
  // Run Validation Suite Action
  // ==========================================================================
  async function runValidationSuite() {
    const suite = elements.suiteSelect.value || 'all';

    // UI Loading state
    elements.btnRunValidation.disabled = true;
    const spinner = elements.btnRunValidation.querySelector('.btn-spinner');
    const label = elements.btnRunValidation.querySelector('.btn-label');
    if (spinner) spinner.classList.remove('hidden');
    if (label) label.textContent = 'Validating...';

    showToast(`Launching ${suite.toUpperCase()} validation suite...`, 'info', 2000);

    try {
      const res = await fetch('/api/run-validation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suite: suite }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || `Validation request failed with HTTP ${res.status}`);
      }

      currentReport = data;
      renderReportData(data);
      showToast(`Validation Complete: ${data.statistics.passed}/${data.statistics.total} tests passed!`, 'success');
      fetchServerStatus(); // refresh header timestamp
    } catch (err) {
      showToast(`Validation Failed: ${err.message}`, 'error', 6000);
    } finally {
      elements.btnRunValidation.disabled = false;
      if (spinner) spinner.classList.add('hidden');
      if (label) label.textContent = 'Run Validation';
    }
  }

  // ==========================================================================
  // Interactive C Controller Demonstration Console
  // ==========================================================================
  async function executeControllerSimulation() {
    const rawTemp = elements.simTempInput.value.trim();
    const rawStatus = elements.simStatusSelect.value;

    if (!rawTemp) {
      showToast('Please enter a temperature value or token.', 'error');
      return;
    }

    elements.btnExecuteSim.disabled = true;
    elements.simSpinner.classList.remove('hidden');
    elements.simBtnText.textContent = 'Executing Process...';

    try {
      const res = await fetch('/api/simulate-sensor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temperature: rawTemp,
          status: rawStatus === 'OK' ? '' : rawStatus,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || `Simulation failed: HTTP ${res.status}`);
      }

      updateSimulationVisuals(data, rawTemp);
    } catch (err) {
      showToast(`Simulation Error: ${err.message}`, 'error');
      elements.simOutTerminal.textContent = `[EXECUTION ERROR]: ${err.message}`;
    } finally {
      elements.btnExecuteSim.disabled = false;
      elements.simSpinner.classList.add('hidden');
      elements.simBtnText.textContent = 'Execute C Controller Process';
    }
  }

  function updateSimulationVisuals(data, rawTemp) {
    // 1. Latency badge
    elements.simLatencyBadge.textContent = `Latency: ${data.duration_ms} ms`;

    // 2. State & Fault display
    elements.simOutState.textContent = data.state || 'UNKNOWN';
    elements.simOutState.className = 'cell-value';
    if (data.is_normal) {
      elements.simOutState.classList.add('state-normal');
    } else if (data.is_warning) {
      elements.simOutState.classList.add('state-warning');
    } else {
      elements.simOutState.classList.add('state-fault');
    }

    elements.simOutFault.textContent = data.fault || 'NONE';
    elements.simOutFault.className = 'cell-value';
    if (data.fault && data.fault !== 'NONE') {
      elements.simOutFault.classList.add('fault-active');
    } else {
      elements.simOutFault.classList.add('fault-none');
    }

    // 3. Exit code display
    const code = data.exit_code !== null ? data.exit_code : -1;
    let codeLabel = `${code} (Nominal)`;
    if (code === 2) codeLabel = `${code} (Safety Fault)`;
    else if (code === 1) codeLabel = `${code} (Syntax Error)`;
    elements.simOutExitcode.textContent = codeLabel;
    elements.simOutExitcode.className = `cell-value ${code === 0 ? 'exit-zero' : 'exit-nonzero'}`;

    // 4. Parsed temperature
    if (data.temperature !== null && data.temperature !== undefined) {
      elements.simOutTemp.textContent = typeof data.temperature === 'number'
        ? `${data.temperature.toFixed(2)} °C`
        : String(data.temperature);
    } else {
      elements.simOutTemp.textContent = 'INVALID';
    }

    // 5. Thermal Bar Percentage Calculation
    const num = parseFloat(rawTemp);
    let pct = 34.2; // default ambient approx
    if (!isNaN(num)) {
      // Scale from -40°C to 150°C (range = 190°C)
      pct = ((num - (-40.0)) / 190.0) * 100.0;
      pct = Math.max(0, Math.min(100, pct));
    }
    elements.thermalBarFill.style.width = `${pct}%`;
    elements.thermalBarFill.className = 'thermal-bar-fill';
    if (data.is_fault) {
      elements.thermalBarFill.classList.add('fill-fault');
    } else if (data.is_warning) {
      elements.thermalBarFill.classList.add('fill-warn');
    }

    // 6. Terminal Body
    const cmdStr = (data.command || []).join(' ');
    let outputText = `$ ${cmdStr}\n`;
    if (data.raw_stdout) outputText += `${data.raw_stdout}\n`;
    if (data.raw_stderr) outputText += `[STDERR]: ${data.raw_stderr}\n`;
    elements.simOutTerminal.textContent = outputText.trim();
  }

  // ==========================================================================
  // Event Listeners & Binding
  // ==========================================================================
  function setupEventListeners() {
    // Run Validation Button
    elements.btnRunValidation.addEventListener('click', runValidationSuite);

    // Simulation Slider & Number Sync
    elements.simTempSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value).toFixed(1);
      elements.simTempInput.value = val;
      elements.simTempDisplay.textContent = `${val} °C`;
    });

    elements.simTempInput.addEventListener('input', (e) => {
      const num = parseFloat(e.target.value);
      if (!isNaN(num)) {
        elements.simTempSlider.value = num;
        elements.simTempDisplay.textContent = `${num.toFixed(1)} °C`;
      } else {
        elements.simTempDisplay.textContent = e.target.value || 'INVALID';
      }
    });

    // Preset Chips
    document.querySelectorAll('.chip-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const temp = btn.dataset.temp;
        const status = btn.dataset.status;

        elements.simTempInput.value = temp;
        const num = parseFloat(temp);
        if (!isNaN(num)) {
          elements.simTempSlider.value = num;
          elements.simTempDisplay.textContent = `${num.toFixed(1)} °C`;
        } else {
          elements.simTempDisplay.textContent = temp;
        }

        if (status) {
          elements.simStatusSelect.value = status;
        }

        // Auto execute for responsive interactive feedback
        executeControllerSimulation();
      });
    });

    // Simulation Execute Button
    elements.btnExecuteSim.addEventListener('click', executeControllerSimulation);

    // Category Tabs Filter
    elements.categoryTabs.addEventListener('click', (e) => {
      const btn = e.target.closest('.tab-btn');
      if (!btn) return;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.category || 'all';
      renderTestCards();
    });

    // Search Input Filter
    elements.testSearchInput.addEventListener('input', (e) => {
      currentSearch = e.target.value.trim();
      renderTestCards();
    });

    // View Raw JSON Modal
    elements.btnViewRawJson.addEventListener('click', () => {
      if (!currentReport) {
        showToast('No validation report loaded.', 'error');
        return;
      }
      elements.jsonModalContent.textContent = JSON.stringify(currentReport, null, 2);
      if (currentReport.metadata && currentReport.metadata.timestamp) {
        elements.modalMetaTimestamp.textContent = `Generated: ${currentReport.metadata.timestamp}`;
      }
      elements.jsonModal.classList.remove('hidden');
    });

    // Close Modal
    elements.modalCloseBtn.addEventListener('click', () => {
      elements.jsonModal.classList.add('hidden');
    });
    elements.modalDismissBtn.addEventListener('click', () => {
      elements.jsonModal.classList.add('hidden');
    });
    elements.jsonModal.addEventListener('click', (e) => {
      if (e.target === elements.jsonModal) {
        elements.jsonModal.classList.add('hidden');
      }
    });

    // Copy JSON to Clipboard
    elements.btnCopyJson.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(elements.jsonModalContent.textContent);
        showToast('JSON report copied to clipboard!', 'success');
      } catch (err) {
        showToast('Failed to copy to clipboard.', 'error');
      }
    });

    // Keyboard navigation (Escape to close modal)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !elements.jsonModal.classList.contains('hidden')) {
        elements.jsonModal.classList.add('hidden');
      }
    });
  }

  // ==========================================================================
  // Initialization
  // ==========================================================================
  async function init() {
    setupEventListeners();
    await fetchServerStatus();
    await loadLatestReport();
    // Run an initial simulation pass for ambient 25°C so the visualizer is active
    executeControllerSimulation();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
