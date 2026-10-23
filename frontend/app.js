/* =========================================================
   Bimodal CV Demo – Frontend Logic
   ========================================================= */

const API = '';

// --- DOM refs ---
const sampleGrid   = document.getElementById('sample-grid');
const btnAnalyse   = document.getElementById('btn-analyse');
const btnReset     = document.getElementById('btn-reset');
const spinner      = document.getElementById('spinner');
const cardsArea    = document.getElementById('cards-area');
const warningsEl   = document.getElementById('warnings-panel');
const dlRow        = document.getElementById('dl-row');
const tooltip      = document.getElementById('tooltip');

// --- Controls ---
const sigmaSlider   = document.getElementById('sigma');
const sigmaVal      = document.getElementById('sigma-val');
const promSlider    = document.getElementById('prom');
const promVal       = document.getElementById('prom-val');
const manualChk     = document.getElementById('manual-chk');
const manualSlider  = document.getElementById('manual-thr');
const manualVal     = document.getElementById('manual-val');
const cleanupChk    = document.getElementById('cleanup-chk');
const methodSel     = document.getElementById('sharpen-method');
const methodDesc    = document.getElementById('method-desc');
const radiusSlider  = document.getElementById('radius');
const radiusVal     = document.getElementById('radius-val');
const amountSlider  = document.getElementById('amount');
const amountVal     = document.getElementById('amount-val');
const amountFgSl    = document.getElementById('amount-fg');
const amountFgVal   = document.getElementById('amount-fg-val');
const amountBgSl    = document.getElementById('amount-bg');
const amountBgVal   = document.getElementById('amount-bg-val');
const amountRows    = document.getElementById('amount-rows');
const amountFgRows  = document.getElementById('amount-fg-rows');

// State
let currentSample = null;
let lastResult    = null;
let debounceTimer = null;
let histChart     = null;
let otsuChart     = null;

// ---- Method descriptions ----
const METHOD_DESCS = {
  mask_aware: 'Sharpens foreground objects more strongly than the background, with a smooth feathered edge between them. Best method when you have a clean segmentation — the teaching highlight of this demo.',
  unsharp:    'Classic unsharp masking: blurs the image, subtracts the blur to isolate detail, then adds that detail back scaled by Strength. Applies uniformly across the whole image.',
  laplacian:  'Uses second-derivative (Laplacian) edges to boost contrast at boundaries. Fast but can amplify noise on textured regions. Good for comparing with unsharp masking.',
};

function updateMethodDesc() {
  if (methodDesc) methodDesc.textContent = METHOD_DESCS[methodSel.value] || '';
}

// ---- Tooltip ----
document.querySelectorAll('.hint-icon').forEach(icon => {
  icon.addEventListener('mouseenter', e => {
    const tip = icon.dataset.tip;
    if (!tip) return;
    tooltip.textContent = tip;
    tooltip.classList.remove('hidden');
    const r = icon.getBoundingClientRect();
    tooltip.style.left = Math.min(r.left, window.innerWidth - 260) + 'px';
    tooltip.style.top  = (r.top - tooltip.offsetHeight - 8 + window.scrollY) + 'px';
  });
  icon.addEventListener('mouseleave', () => tooltip.classList.add('hidden'));
  icon.addEventListener('click', e => e.stopPropagation());
});

// ---- Helpers ----
function showSpinner() { spinner.classList.add('show'); }
function hideSpinner() { spinner.classList.remove('show'); }

function sliderSetup(slider, display, decimals = 1) {
  display.textContent = parseFloat(slider.value).toFixed(decimals);
  slider.addEventListener('input', () => {
    display.textContent = parseFloat(slider.value).toFixed(decimals);
    scheduleAutoRun();
  });
}

function scheduleAutoRun() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => { if (currentSample) doAnalyse(); }, 400);
}

function polarity() {
  return document.querySelector('input[name=polarity]:checked')?.value || 'auto';
}

// ---- Init sliders ----
sliderSetup(sigmaSlider, sigmaVal, 1);
sliderSetup(promSlider, promVal, 2);
sliderSetup(manualSlider, manualVal, 0);
sliderSetup(radiusSlider, radiusVal, 1);
sliderSetup(amountSlider, amountVal, 1);
sliderSetup(amountFgSl, amountFgVal, 1);
sliderSetup(amountBgSl, amountBgVal, 1);

manualChk.addEventListener('change', () => {
  manualSlider.disabled = !manualChk.checked;
  scheduleAutoRun();
});

methodSel.addEventListener('change', () => {
  const m = methodSel.value;
  amountRows.classList.toggle('hidden', m !== 'unsharp');
  amountFgRows.classList.toggle('hidden', m !== 'mask_aware');
  updateMethodDesc();
  scheduleAutoRun();
});

document.querySelectorAll('input[name=polarity]').forEach(r => r.addEventListener('change', scheduleAutoRun));
cleanupChk.addEventListener('change', scheduleAutoRun);

// ---- Samples ----
async function loadSampleList() {
  try {
    const res = await fetch(`${API}/api/samples`);
    const items = await res.json();
    if (!sampleGrid) return;
    sampleGrid.innerHTML = '';
    items.forEach(s => {
      const btn = document.createElement('button');
      btn.className = 'sample-btn';
      btn.dataset.name = s.name;
      const label = s.label || s.name.replace('.png', '');
      btn.innerHTML = `<span class="sample-label">${label}</span><span class="sample-desc">${s.description}</span>`;
      btn.addEventListener('click', () => {
        document.querySelectorAll('.sample-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentSample = s.name;
        doAnalyse();
      });
      sampleGrid.appendChild(btn);
    });
  } catch(e) { console.error('Failed to load sample list:', e); }
}

// ---- Reset ----
function resetAll() {
  clearTimeout(debounceTimer);
  currentSample = null;
  lastResult = null;

  // Reset sliders to defaults
  sigmaSlider.value = 3;     sigmaVal.textContent = '3.0';
  promSlider.value = 0.10;   promVal.textContent = '0.10';
  manualChk.checked = false;
  manualSlider.value = 128;  manualVal.textContent = '128';
  manualSlider.disabled = true;
  cleanupChk.checked = true;
  document.querySelector('input[name=polarity][value=auto]').checked = true;
  methodSel.value = 'mask_aware';
  radiusSlider.value = 1.5;  radiusVal.textContent = '1.5';
  amountSlider.value = 1.0;  amountVal.textContent = '1.0';
  amountFgSl.value = 1.5;    amountFgVal.textContent = '1.5';
  amountBgSl.value = 0.3;    amountBgVal.textContent = '0.3';

  // Reset method UI
  amountRows.classList.add('hidden');
  amountFgRows.classList.remove('hidden');
  updateMethodDesc();

  // Deselect sample buttons
  document.querySelectorAll('.sample-btn').forEach(b => b.classList.remove('active'));

  // Clear results
  const placeholder = document.getElementById('placeholder');
  if (placeholder) placeholder.classList.remove('hidden');
  cardsArea.innerHTML = '';
  warningsEl.classList.add('hidden');
  dlRow.classList.add('hidden');

  // Destroy charts
  if (histChart) { histChart.destroy(); histChart = null; }
  if (otsuChart) { otsuChart.destroy(); otsuChart = null; }
}

btnReset.addEventListener('click', resetAll);
btnAnalyse.addEventListener('click', doAnalyse);

// ---- Analyse ----
async function doAnalyse() {
  if (!currentSample) return;
  showSpinner();
  btnAnalyse.disabled = true;
  try {
    const fd = new FormData();
    fd.append('sample_name', currentSample);
    fd.append('smoothing_sigma', sigmaSlider.value);
    fd.append('min_prominence_frac', promSlider.value);
    fd.append('polarity', polarity());
    if (manualChk.checked) fd.append('manual_threshold', manualSlider.value);
    fd.append('cleanup', cleanupChk.checked ? 'true' : 'false');
    fd.append('sharpen_method', methodSel.value);
    fd.append('radius', radiusSlider.value);
    fd.append('amount', amountSlider.value);
    fd.append('amount_fg', amountFgSl.value);
    fd.append('amount_bg', amountBgSl.value);

    const res = await fetch(`${API}/api/analyze`, { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`Error ${res.status}: ${err.detail || res.statusText}`);
      return;
    }
    lastResult = await res.json();
    renderResult(lastResult);
  } catch (e) {
    alert('Request failed: ' + e.message);
  } finally {
    hideSpinner();
    btnAnalyse.disabled = false;
  }
}

// ---- Render ----
function b64src(b64) { return `data:image/png;base64,${b64}`; }

function expl(step) {
  return lastResult.explanations.find(e => e.step === step) || {};
}

function makeCard(num, title, bodyHtml) {
  return `
  <div class="step-card">
    <div class="step-header">
      <div class="step-num">${num}</div>
      <h3>${title}</h3>
    </div>
    <div class="step-body">${bodyHtml}</div>
  </div>`;
}

function summaryDetail(step) {
  const e = expl(step);
  return `
    <p class="summary-text">${e.summary || ''}</p>
    <details class="why"><summary>Why?</summary><p>${e.detail || ''}</p></details>`;
}

function renderResult(r) {
  const placeholder = document.getElementById('placeholder');
  if (placeholder) placeholder.classList.add('hidden');

  cardsArea.innerHTML = '';
  dlRow.classList.remove('hidden');

  const cards = [
    cardInput(r),
    cardHistogram(r),
    cardBimodality(r),
    cardThreshold(r),
    cardSegmentation(r),
    cardSharpening(r),
  ];
  cardsArea.innerHTML = cards.join('');

  try { drawHistChart(r); } catch(e) { console.warn('Histogram chart error:', e); }
  try { drawOtsuChart(r); } catch(e) { console.warn('Otsu chart error:', e); }
  initBASlider();
  renderWarnings(r.warnings);
}

// Card 1 – Input
function cardInput(r) {
  const m = r.meta;
  const e = expl('input');
  const colourNote = m.was_colour ? 'Colour \u2192 Grayscale' : 'Grayscale';
  const rescaledNote = m.was_rescaled ? ' (16-bit rescaled)' : '';
  return makeCard(1, 'Input Image', `
    <div class="input-layout">
      <div class="img-card" style="flex:1;min-width:0">
        <img src="${b64src(r.images.original)}" alt="original">
        <span>${m.width} \u00d7 ${m.height} px</span>
      </div>
      <div class="meta-stats">
        <div class="meta-stat"><span class="meta-label">Dimensions</span><span class="meta-value">${m.width} \u00d7 ${m.height}</span></div>
        <div class="meta-stat"><span class="meta-label">Pixels</span><span class="meta-value">${(m.width * m.height).toLocaleString()}</span></div>
        <div class="meta-stat"><span class="meta-label">Channels</span><span class="meta-value">${colourNote}${rescaledNote}</span></div>
        <div class="meta-stat"><span class="meta-label">Processing</span><span class="meta-value">${m.elapsed_ms} ms</span></div>
      </div>
    </div>
    <p class="summary-text">${e.summary || ''}</p>
    <details class="why"><summary>Why?</summary><p>${e.detail || ''}</p></details>
  `);
}

// Card 2 – Histogram
function cardHistogram(r) {
  return makeCard(2, 'Intensity Histogram', `
    <div class="chart-wrap"><canvas id="hist-chart"></canvas></div>
    <div class="chart-wrap" style="height:120px"><canvas id="otsu-chart"></canvas></div>
    ${summaryDetail('histogram')}
  `);
}

function drawHistChart(r) {
  if (histChart) histChart.destroy();
  const ctx = document.getElementById('hist-chart')?.getContext('2d');
  if (!ctx) return;
  const labels = Array.from({length: 256}, (_, i) => i);
  const datasets = [
    {
      label: 'Raw histogram',
      data: r.histogram.raw.map(v => v / Math.max(...r.histogram.raw)),
      borderColor: 'rgba(150,150,150,.5)',
      borderWidth: 1,
      pointRadius: 0,
      fill: false,
    },
    {
      label: 'Smoothed',
      data: r.histogram.smoothed.map(v => v / Math.max(...r.histogram.smoothed)),
      borderColor: '#2563eb',
      borderWidth: 2,
      pointRadius: 0,
      fill: true,
      backgroundColor: 'rgba(37,99,235,.08)',
    },
  ];

  const annotations = {};
  if (r.histogram.peaks.length === 2) {
    const [p0, p1] = r.histogram.peaks;
    const valley = r.histogram.valley;
    annotations['peak0'] = vertLine(p0, '#16a34a', 'Peak 1');
    annotations['peak1'] = vertLine(p1, '#16a34a', 'Peak 2');
    if (valley != null) annotations['valley'] = vertLine(valley, '#f59e0b', 'Valley');
  }
  if (r.threshold.otsu != null) {
    annotations['otsu'] = vertLine(r.threshold.otsu, '#dc2626', 'Otsu', [6, 3]);
  }

  histChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, font: { size: 11 } } },
        annotation: { annotations },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 16, font: { size: 10 } }, title: { display: true, text: 'Grey level (0 = black, 255 = white)', font: { size: 11 } } },
        y: { ticks: { font: { size: 10 } }, title: { display: true, text: 'Relative frequency', font: { size: 11 } } },
      },
    },
  });
}

function vertLine(x, color, label, dash = []) {
  return {
    type: 'line',
    xMin: x, xMax: x,
    borderColor: color,
    borderWidth: 2,
    borderDash: dash,
    label: { content: label, display: true, position: 'start', font: { size: 9 }, color },
  };
}

function drawOtsuChart(r) {
  if (otsuChart) otsuChart.destroy();
  const ctx = document.getElementById('otsu-chart')?.getContext('2d');
  if (!ctx) return;
  const curve = r.histogram.otsu_curve;
  const mx = Math.max(...curve);
  const argmax = curve.indexOf(mx);
  otsuChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({length: 256}, (_, i) => i),
      datasets: [{
        label: 'Otsu between-class variance \u03c3\u00b2B',
        data: curve,
        borderColor: '#7c3aed',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: true,
        backgroundColor: 'rgba(124,58,237,.08)',
      }],
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, font: { size: 11 } } },
        annotation: {
          annotations: {
            otsuMax: vertLine(argmax, '#7c3aed', `Otsu = ${argmax}`),
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 16, font: { size: 10 } }, title: { display: true, text: 'Threshold candidate', font: { size: 11 } } },
        y: { ticks: { font: { size: 10 } } },
      },
    },
  });
}

// Card 3 – Bimodality
function cardBimodality(r) {
  const bm = r.bimodality;
  const verdictText = {
    strongly_bimodal: 'Strongly Bimodal',
    weakly_bimodal:   'Weakly Bimodal',
    unimodal:         'Unimodal',
  }[bm.verdict] || bm.verdict;

  // Bar fills from 0 to 2× threshold. 50% = at threshold (passing).
  const gaugePct = (val, ref) => Math.min(100, (val / (ref * 2)) * 100).toFixed(1);

  return makeCard(3, 'Bimodality Evidence', `
    <div class="bm-gauges">
      ${gauge('Valley Depth Ratio', bm.vdr.toFixed(2), gaugePct(bm.vdr, 0.5), '0.5',
        'How deep is the dip between the two histogram peaks? 0 = no dip, 1 = valley touches zero.')}
      ${gauge('Bimodality Coeff.', bm.bc.toFixed(3), gaugePct(bm.bc, 0.555), '0.555',
        "Sarle\u2019s coefficient based on skewness and kurtosis. Values above 0.555 suggest bimodality.")}
      ${gauge("Ashman\u2019s D", bm.ashman_d.toFixed(2), gaugePct(bm.ashman_d, 2.0), '2.0',
        'Separation of the two Gaussian components. D > 2 means the modes are cleanly separated.')}
    </div>
    <p class="gauge-legend">Bar fills to 50% at threshold, 100% at 2\u00d7 threshold. <span style="color:var(--success);font-weight:600">Green</span> = above threshold (pass).</p>
    <div style="margin-top:6px">Verdict: <span class="verdict-badge ${bm.verdict}">${verdictText}</span></div>
    ${summaryDetail('bimodality')}
  `);
}

function gauge(label, val, pct, threshold, tip) {
  const pctNum = parseFloat(pct);
  const isGood = pctNum >= 50;
  const barColor = isGood ? 'var(--success)' : 'var(--amber)';
  const valColor = isGood ? 'var(--success)' : 'var(--warning)';
  const tipAttr = tip ? `title="${tip}"` : '';
  return `<div class="bm-gauge" ${tipAttr}>
    <div class="label">${label} <small class="threshold-ref">threshold: ${threshold}</small></div>
    <div class="value" style="color:${valColor}">${val}</div>
    <div class="bar-track">
      <div class="bar-fill" style="width:${pct}%;background:${barColor}"></div>
      <div class="bar-threshold-mark"></div>
    </div>
  </div>`;
}

// Card 4 – Threshold
function cardThreshold(r) {
  const thr = r.threshold;
  const isValley = thr.method === 'valley';
  const isOtsu   = thr.method === 'otsu' || thr.method === 'manual';

  const valleyBox = thr.valley != null
    ? `<div class="thr-box ${isValley ? 'chosen' : ''}">
         <div class="thr-label">Valley method</div>
         <div class="thr-val">${thr.valley}</div>
         <div class="thr-method">histogram dip${isValley ? ' \u2713' : ''}</div>
       </div>`
    : `<div class="thr-box">
         <div class="thr-label">Valley method</div>
         <div class="thr-val" style="color:var(--muted);font-size:18px">N/A</div>
         <div class="thr-method">no valley found</div>
       </div>`;

  return makeCard(4, 'Threshold Selection', `
    <div class="thr-compare">
      ${valleyBox}
      <div class="thr-box ${isOtsu ? 'chosen' : ''}">
        <div class="thr-label">Otsu method</div>
        <div class="thr-val">${thr.otsu}</div>
        <div class="thr-method">max class variance${isOtsu ? ' \u2713' : ''}</div>
      </div>
      <div class="thr-box thr-applied">
        <div class="thr-label">Applied</div>
        <div class="thr-val">${thr.chosen}</div>
        <div class="thr-method">${thr.method}</div>
      </div>
    </div>
    <p class="summary-text" style="font-size:13px;color:var(--muted);margin-top:4px">${thr.reason}</p>
    ${summaryDetail('threshold')}
  `);
}

// Card 5 – Segmentation
function cardSegmentation(r) {
  const seg = r.segmentation;
  return makeCard(5, 'Segmentation', `
    <div class="img-grid cols-3">
      <div class="img-card"><img src="${b64src(r.images.mask)}" alt="Mask"><span>Binary mask</span></div>
      <div class="img-card"><img src="${b64src(r.images.overlay)}" alt="Overlay"><span>Overlay (foreground tinted)</span></div>
      <div class="img-card"><img src="${b64src(r.images.contours)}" alt="Contours"><span>Detected contours</span></div>
    </div>
    <div class="img-grid cols-2" style="max-width:400px">
      <div class="img-card"><img src="${b64src(r.images.foreground)}" alt="FG"><span>Foreground only</span></div>
      <div class="img-card"><img src="${b64src(r.images.background)}" alt="BG"><span>Background only</span></div>
    </div>
    <div class="seg-stats">
      <div class="seg-stat"><span class="seg-label">Threshold used</span><span class="seg-value">${seg.threshold_used}</span></div>
      <div class="seg-stat"><span class="seg-label">Foreground</span><span class="seg-value">${(seg.fg_fraction * 100).toFixed(1)}%</span></div>
      <div class="seg-stat"><span class="seg-label">Regions</span><span class="seg-value">${seg.n_components}</span></div>
      <div class="seg-stat"><span class="seg-label">Mean FG intensity</span><span class="seg-value">${seg.mean_fg.toFixed(0)}</span></div>
      <div class="seg-stat"><span class="seg-label">Mean BG intensity</span><span class="seg-value">${seg.mean_bg.toFixed(0)}</span></div>
    </div>
    ${summaryDetail('segmentation')}
  `);
}

// Card 6 – Sharpening
function cardSharpening(r) {
  const shp = r.sharpening;
  const methodLabels = { unsharp: 'Unsharp mask', laplacian: 'Laplacian', mask_aware: 'Mask-aware unsharp' };
  const methodNote = shp.mask_aware
    ? '<span style="font-size:11px;color:var(--accent);font-weight:600">Foreground sharpened more strongly than background</span>'
    : '';

  return makeCard(6, 'Sharpening', `
    <p style="font-size:12px;color:var(--muted);margin-bottom:6px">Drag the divider to compare before &amp; after. The detail layer shows what was added.</p>
    <div class="ba-wrapper" id="ba-wrapper">
      <img src="${b64src(r.images.sharpened)}" alt="After (sharpened)" id="ba-before">
      <div class="ba-after" id="ba-after">
        <img src="${b64src(r.images.original)}" alt="Before (original)" id="ba-after-img">
      </div>
      <div class="ba-divider" id="ba-divider"></div>
      <div class="ba-label-left">Before</div>
      <div class="ba-label-right">After</div>
    </div>
    <div class="sharp-bottom">
      <div class="img-card" style="flex:1;max-width:220px">
        <img src="${b64src(r.images.detail)}" alt="Detail layer">
        <span>Detail layer (what was added)</span>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:8px;justify-content:center">
        ${methodNote}
        <table class="metrics-table">
          <tr><th></th><th>Before</th><th>After</th><th>Change</th></tr>
          <tr>
            <td title="Higher = sharper image">Lap. var.</td>
            <td>${shp.lap_var_before.toFixed(0)}</td>
            <td>${shp.lap_var_after.toFixed(0)}</td>
            <td class="pct">${shp.lap_var_pct > 0 ? '+' : ''}${shp.lap_var_pct.toFixed(0)}%</td>
          </tr>
          <tr>
            <td title="Sobel gradient energy">Tenengrad</td>
            <td>${shp.tenengrad_before.toFixed(0)}</td>
            <td>${shp.tenengrad_after.toFixed(0)}</td>
            <td class="pct">${shp.tenengrad_pct > 0 ? '+' : ''}${shp.tenengrad_pct.toFixed(0)}%</td>
          </tr>
        </table>
      </div>
    </div>
    ${summaryDetail('sharpening')}
  `);
}

// ---- Before/After slider ----
function initBASlider() {
  const wrapper = document.getElementById('ba-wrapper');
  const after   = document.getElementById('ba-after');
  const divider = document.getElementById('ba-divider');
  if (!wrapper) return;

  let dragging = false;

  function setPos(x) {
    const rect = wrapper.getBoundingClientRect();
    const pct = Math.min(100, Math.max(0, (x - rect.left) / rect.width * 100));
    after.style.width = pct + '%';
    divider.style.left = pct + '%';
    const afterImg = document.getElementById('ba-after-img');
    if (afterImg) afterImg.style.width = rect.width + 'px';
  }

  wrapper.addEventListener('mousedown', e => { dragging = true; setPos(e.clientX); });
  window.addEventListener('mousemove', e => { if (dragging) setPos(e.clientX); });
  window.addEventListener('mouseup', () => { dragging = false; });
  wrapper.addEventListener('touchstart', e => { dragging = true; setPos(e.touches[0].clientX); }, { passive: true });
  window.addEventListener('touchmove', e => { if (dragging) setPos(e.touches[0].clientX); }, { passive: true });
  window.addEventListener('touchend', () => { dragging = false; });
}

// ---- Warnings ----
function renderWarnings(warnings) {
  if (!warnings || warnings.length === 0) {
    warningsEl.classList.add('hidden');
    return;
  }
  warningsEl.classList.remove('hidden');
  warningsEl.innerHTML = `<h4>Warnings</h4><ul>${warnings.map(w => `<li>${w}</li>`).join('')}</ul>`;
}

// ---- Downloads ----
document.getElementById('btn-dl-json')?.addEventListener('click', () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
  download(blob, 'bimodal-cv-results.json');
});

document.getElementById('btn-dl-zip')?.addEventListener('click', async () => {
  if (!lastResult) return;
  if (typeof JSZip === 'undefined') { alert('JSZip not loaded'); return; }
  const zip = new JSZip();
  for (const [k, b64] of Object.entries(lastResult.images)) {
    zip.file(`${k}.png`, b64, { base64: true });
  }
  zip.file('metrics.json', JSON.stringify({
    meta: lastResult.meta,
    bimodality: lastResult.bimodality,
    threshold: lastResult.threshold,
    segmentation: lastResult.segmentation,
    sharpening: lastResult.sharpening,
  }, null, 2));
  const blob = await zip.generateAsync({ type: 'blob' });
  download(blob, 'bimodal-cv-images.zip');
});

function download(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Before/after label overlay ----
document.head.insertAdjacentHTML('beforeend', `<style>
  .ba-wrapper { position:relative; }
  .ba-label-left, .ba-label-right {
    position:absolute; bottom:8px; font-size:11px; font-weight:700;
    color:#fff; text-shadow:0 1px 3px rgba(0,0,0,.6);
    pointer-events:none; z-index:2;
  }
  .ba-label-left  { left:10px; }
  .ba-label-right { right:10px; }
</style>`);

// ---- Bootstrap ----
loadSampleList();
methodSel.dispatchEvent(new Event('change'));
