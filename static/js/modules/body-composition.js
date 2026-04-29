// Body Composition tab — live BFP estimator + snapshot capture (Issue #21).
//
// JS MIRROR — must match utils/body_fat.py
// ----------------------------------------
// Every constant table and branching rule below has a paired Python
// counterpart in `utils/body_fat.py`. Editing one side without the
// other will trip the Python<->JS lockstep regression test in
// `tests/test_body_fat.py:test_body_fat_python_js_mirror_in_sync`.
//
// The four pure functions are exported so they can be unit-tested in
// isolation; the live preview and history-table logic live in the
// same file but are scoped to DOM events.

import { api, apiFetch } from './fetch-wrapper.js';
import { showToast } from './toast.js';

// ---------------------------------------------------------------------------
// Mirror constants — keep in lockstep with utils/body_fat.py
// ---------------------------------------------------------------------------

export const BMI_JUVENILE_AGE_CUTOFF = 15;

export const ACE_BANDS_MEN = [
    ['Essential fat', 6.0],
    ['Athletes', 14.0],
    ['Fitness', 18.0],
    ['Average', 25.0],
    ['Obese', Infinity],
];

export const ACE_BANDS_WOMEN = [
    ['Essential fat', 14.0],
    ['Athletes', 21.0],
    ['Fitness', 25.0],
    ['Average', 32.0],
    ['Obese', Infinity],
];

// (age, women_bfp, men_bfp). Must remain sorted by age.
export const JP_TABLE = [
    [20, 17.7, 8.5],
    [25, 18.4, 10.5],
    [30, 19.3, 12.7],
    [35, 21.5, 13.7],
    [40, 22.2, 15.3],
    [45, 22.9, 16.4],
    [50, 25.2, 18.9],
    [55, 26.3, 20.9],
];

// ---------------------------------------------------------------------------
// Pure functions — mirror compute_navy / compute_bmi / ace_category /
// jackson_pollock_ideal in utils/body_fat.py.
// ---------------------------------------------------------------------------

export function computeNavy({ gender, heightCm, neckCm, waistCm, hipCm }) {
    if (gender === 'M') {
        const arg = waistCm - neckCm;
        if (arg <= 0) {
            throw new BodyFatError('LOG_DOMAIN', 'Waist circumference must be larger than neck circumference.', 'waist_cm');
        }
        const denom = 1.0324 - 0.19077 * Math.log10(arg) + 0.15456 * Math.log10(heightCm);
        if (denom <= 0) {
            throw new BodyFatError('LOG_DOMAIN', 'Tape values produce a non-physical body-fat estimate.');
        }
        return 495.0 / denom - 450.0;
    }
    if (hipCm == null) {
        throw new BodyFatError('MISSING_HIP', 'Hip circumference is required for the female Navy formula.', 'hip_cm');
    }
    const arg = waistCm + hipCm - neckCm;
    if (arg <= 0) {
        throw new BodyFatError('LOG_DOMAIN', 'Waist plus hip circumference must be larger than neck circumference.', 'waist_cm');
    }
    const denom = 1.29579 - 0.35004 * Math.log10(arg) + 0.22100 * Math.log10(heightCm);
    if (denom <= 0) {
        throw new BodyFatError('LOG_DOMAIN', 'Tape values produce a non-physical body-fat estimate.');
    }
    return 495.0 / denom - 450.0;
}

export function computeBmi({ gender, age, heightCm, weightKg }) {
    const heightM = heightCm / 100.0;
    const bmi = weightKg / (heightM * heightM);
    if (age <= BMI_JUVENILE_AGE_CUTOFF) {
        if (gender === 'M') return 1.51 * bmi - 0.70 * age - 2.2;
        return 1.51 * bmi - 0.70 * age + 1.4;
    }
    if (gender === 'M') return 1.20 * bmi + 0.23 * age - 16.2;
    return 1.20 * bmi + 0.23 * age - 5.4;
}

export function aceCategory(bfp, gender) {
    const bands = gender === 'M' ? ACE_BANDS_MEN : ACE_BANDS_WOMEN;
    for (const [label, upper] of bands) {
        if (bfp < upper) return label;
    }
    return bands[bands.length - 1][0];
}

export function jacksonPollockIdeal(age, gender) {
    const col = gender === 'M' ? 2 : 1;
    if (age <= JP_TABLE[0][0]) return JP_TABLE[0][col];
    if (age >= JP_TABLE[JP_TABLE.length - 1][0]) return JP_TABLE[JP_TABLE.length - 1][col];
    for (let i = 0; i < JP_TABLE.length - 1; i++) {
        const [loAge] = JP_TABLE[i];
        const [hiAge] = JP_TABLE[i + 1];
        if (loAge <= age && age <= hiAge) {
            const loVal = JP_TABLE[i][col];
            const hiVal = JP_TABLE[i + 1][col];
            const frac = (age - loAge) / (hiAge - loAge);
            return loVal + frac * (hiVal - loVal);
        }
    }
    return JP_TABLE[JP_TABLE.length - 1][col];
}

class BodyFatError extends Error {
    constructor(code, message, field = null) {
        super(message);
        this.code = code;
        this.field = field;
    }
}

// ---------------------------------------------------------------------------
// DOM logic
// ---------------------------------------------------------------------------

const SELECTORS = {
    form: '[data-testid="body-composition-form"]',
    neck: '#bc-neck',
    waist: '#bc-waist',
    hip: '#bc-hip',
    notes: '#bc-notes',
    saveBtn: '[data-testid="body-composition-save"]',
    resultBfp: '[data-testid="body-composition-result-bfp"]',
    resultBadge: '[data-testid="body-composition-result-badge"]',
    resultMass: '[data-testid="body-composition-result-mass"]',
    resultBmi: '[data-testid="body-composition-result-bmi"]',
    aceBand: '[data-testid="body-composition-ace-band"]',
    jpLine: '[data-testid="body-composition-jp-line"]',
    historyBody: '[data-testid="body-composition-history-body"]',
    historyEmpty: '[data-testid="body-composition-history-empty"]',
    trendChart: '[data-testid="body-composition-trend-chart"]',
    fieldErrors: '[data-field-error]',
};

function getDemographics(formEl) {
    return {
        gender: formEl.dataset.gender,
        age: Number(formEl.dataset.age),
        heightCm: Number(formEl.dataset.heightCm),
        weightKg: Number(formEl.dataset.weightKg),
    };
}

function readTapeInputs(formEl) {
    const get = (sel) => {
        const el = formEl.querySelector(sel);
        if (!el) return null;
        const v = el.value.trim();
        if (v === '') return null;
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
    };
    return {
        neckCm: get(SELECTORS.neck),
        waistCm: get(SELECTORS.waist),
        hipCm: get(SELECTORS.hip),
    };
}

function clearFieldErrors(formEl) {
    formEl.querySelectorAll(SELECTORS.fieldErrors).forEach(el => {
        el.textContent = '';
        el.hidden = true;
    });
}

function setFieldError(formEl, field, message) {
    const el = formEl.querySelector(`[data-field-error="${field}"]`);
    if (el) {
        el.textContent = message;
        el.hidden = false;
    }
}

function tapeMode(gender, tape) {
    const required = gender === 'M' ? ['neckCm', 'waistCm'] : ['neckCm', 'waistCm', 'hipCm'];
    const filled = required.filter(k => tape[k] != null);
    if (filled.length === 0) return 'blank';
    if (filled.length === required.length) return 'complete';
    return 'partial';
}

function renderResult(formEl, demographics, tape) {
    clearFieldErrors(formEl);
    const root = formEl.closest('[data-testid="body-composition-calculator"]');
    if (!root) return;

    const bfpEl = root.querySelector(SELECTORS.resultBfp);
    const badgeEl = root.querySelector(SELECTORS.resultBadge);
    const massEl = root.querySelector(SELECTORS.resultMass);
    const bmiEl = root.querySelector(SELECTORS.resultBmi);
    const aceEl = root.querySelector(SELECTORS.aceBand);
    const jpEl = root.querySelector(SELECTORS.jpLine);

    const mode = tapeMode(demographics.gender, tape);

    let bfpBmi;
    try {
        bfpBmi = computeBmi(demographics);
    } catch (err) {
        bfpEl.textContent = '—';
        return;
    }

    let primaryBfp = bfpBmi;
    let badge = 'BMI-based — less accurate than Navy method';

    if (mode === 'complete') {
        try {
            primaryBfp = computeNavy({
                gender: demographics.gender,
                heightCm: demographics.heightCm,
                neckCm: tape.neckCm,
                waistCm: tape.waistCm,
                hipCm: tape.hipCm,
            });
            badge = 'Navy method';
        } catch (err) {
            if (err instanceof BodyFatError) {
                if (err.field) setFieldError(formEl, err.field, err.message);
                bfpEl.textContent = '—';
                badgeEl.textContent = err.message;
                return;
            }
            throw err;
        }
    } else if (mode === 'partial') {
        bfpEl.textContent = '—';
        badgeEl.textContent = 'Provide all tape measurements or none — partial input is not supported.';
        return;
    }

    const fatMassKg = (primaryBfp / 100.0) * demographics.weightKg;
    const leanMassKg = demographics.weightKg - fatMassKg;

    bfpEl.textContent = `${primaryBfp.toFixed(1)} %`;
    badgeEl.textContent = badge;
    massEl.textContent = `Fat mass: ${fatMassKg.toFixed(1)} kg · Lean mass: ${leanMassKg.toFixed(1)} kg`;
    bmiEl.textContent = mode === 'complete'
        ? `BMI estimate: ${bfpBmi.toFixed(1)} %`
        : '';

    renderAceBand(aceEl, primaryBfp, demographics.gender);
    renderJpLine(jpEl, primaryBfp, demographics);
}

function renderAceBand(svgEl, bfp, gender) {
    if (!svgEl) return;
    const bands = gender === 'M' ? ACE_BANDS_MEN : ACE_BANDS_WOMEN;
    // Map domain to [0, 50] BFP range; segments share equal visual width
    // (the table is qualitative, not linear in BFP).
    const max = 50;
    const segWidth = 100 / bands.length;
    const segs = bands.map(([label], i) => {
        const x = i * segWidth;
        return `<rect x="${x}%" y="0" width="${segWidth}%" height="100%" data-band="${label}"></rect>`;
    }).join('');
    const tickX = Math.min(Math.max(bfp / max, 0), 1) * 100;
    svgEl.innerHTML = `${segs}<line x1="${tickX}%" x2="${tickX}%" y1="0" y2="100%" data-tick="bfp"></line>`;
    svgEl.dataset.label = aceCategory(bfp, gender);

    // Legend renders in HTML so labels don't get stretched by the SVG's
    // `preserveAspectRatio="none"` viewport.
    const legend = svgEl.parentElement
        ? svgEl.parentElement.querySelector('[data-testid="body-composition-ace-legend"]')
        : null;
    if (legend) {
        const current = aceCategory(bfp, gender);
        legend.innerHTML = bands.map(([label]) => {
            const isActive = label === current ? ' aria-current="true"' : '';
            return `<li data-band="${label}"${isActive}>${label}</li>`;
        }).join('');
    }
}

function renderJpLine(el, bfp, demographics) {
    if (!el) return;
    const ideal = jacksonPollockIdeal(demographics.age, demographics.gender);
    const genderLabel = demographics.gender === 'M' ? 'M' : 'F';
    el.textContent = `Jackson & Pollock ideal for your age (${demographics.age}, ${genderLabel}): ${ideal.toFixed(1)} %. Your current estimate: ${bfp.toFixed(1)} %.`;
}

// ---------------------------------------------------------------------------
// Snapshot save / list / delete
// ---------------------------------------------------------------------------

async function handleSave(formEl) {
    clearFieldErrors(formEl);
    const tape = readTapeInputs(formEl);
    const notesEl = formEl.querySelector(SELECTORS.notes);
    const payload = {
        neck_cm: tape.neckCm,
        waist_cm: tape.waistCm,
        hip_cm: tape.hipCm,
        notes: notesEl ? notesEl.value : null,
    };
    try {
        const result = await api.post('/api/body_composition/snapshot', payload, {
            showErrorToast: false,
        });
        showToast('success', 'Snapshot saved');
        await refreshHistory();
    } catch (err) {
        const apiError = err && err.error;
        if (apiError && apiError.field) {
            setFieldError(formEl, apiError.field, apiError.message || 'Invalid input.');
        }
        if (apiError && Array.isArray(apiError.missing_fields)) {
            apiError.missing_fields.forEach(f => setFieldError(formEl, f, 'Required.'));
        }
        showToast('error', apiError ? apiError.message : 'Failed to save snapshot');
    }
}

async function refreshHistory() {
    try {
        const result = await api.get('/api/body_composition/snapshots');
        const rows = (result && result.data) || [];
        renderHistory(rows);
        renderTrendChart(rows);
    } catch (err) {
        // Silent fail — the history table just stays at its last good state.
    }
}

function renderHistory(rows) {
    const tbody = document.querySelector(SELECTORS.historyBody);
    const empty = document.querySelector(SELECTORS.historyEmpty);
    if (!tbody) return;
    if (!rows.length) {
        tbody.innerHTML = '';
        if (empty) empty.hidden = false;
        return;
    }
    if (empty) empty.hidden = true;
    tbody.innerHTML = rows.map(row => {
        const navy = row.bfp_navy != null ? row.bfp_navy.toFixed(1) : '—';
        const bmi = row.bfp_bmi != null ? row.bfp_bmi.toFixed(1) : '—';
        const lean = row.lean_mass_kg != null ? row.lean_mass_kg.toFixed(1) : '—';
        const fat = row.fat_mass_kg != null ? row.fat_mass_kg.toFixed(1) : '—';
        return `
            <tr data-snapshot-id="${row.id}">
                <td>${row.captured_at}</td>
                <td>${navy}</td>
                <td>${bmi}</td>
                <td>${lean}</td>
                <td>${fat}</td>
                <td><button type="button" class="btn btn-sm btn-outline-danger" data-action="delete-snapshot" data-snapshot-id="${row.id}">Delete</button></td>
            </tr>
        `;
    }).join('');
}

function renderTrendChart(rows) {
    const svg = document.querySelector(SELECTORS.trendChart);
    if (!svg) return;
    const empty = document.querySelector('[data-testid="body-composition-trend-empty"]');
    if (!rows.length) {
        svg.innerHTML = '';
        svg.hidden = true;
        if (empty) empty.hidden = false;
        return;
    }
    svg.hidden = false;
    if (empty) empty.hidden = true;
    // Reverse so oldest is leftmost.
    const series = [...rows].reverse().map(r => r.bfp_navy != null ? r.bfp_navy : r.bfp_bmi);
    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = max - min || 1;
    const points = series.map((v, i) => {
        const x = (i / Math.max(series.length - 1, 1)) * 100;
        const y = 100 - ((v - min) / range) * 80 - 10;
        return `${x},${y}`;
    }).join(' ');
    svg.innerHTML = `<polyline points="${points}" fill="none" stroke="currentColor" stroke-width="1.5" data-trend="line" />`;
}

async function handleDelete(snapshotId) {
    try {
        await api.delete(`/api/body_composition/snapshots/${snapshotId}`, { showErrorToast: false });
        showToast('success', 'Snapshot deleted');
        await refreshHistory();
    } catch (err) {
        const apiError = err && err.error;
        showToast('error', apiError ? apiError.message : 'Failed to delete snapshot');
    }
}

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

function bindForm(formEl) {
    const demographics = getDemographics(formEl);
    if (!demographics.gender) return;

    const onInput = () => {
        const tape = readTapeInputs(formEl);
        renderResult(formEl, demographics, tape);
    };
    formEl.addEventListener('input', onInput);

    const saveBtn = formEl.querySelector(SELECTORS.saveBtn);
    if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            handleSave(formEl);
        });
    }

    // Initial render so the BMI fallback shows on page load.
    onInput();
}

function bindHistoryDelete() {
    const tbody = document.querySelector(SELECTORS.historyBody);
    if (!tbody) return;
    tbody.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action="delete-snapshot"]');
        if (!btn) return;
        const id = btn.dataset.snapshotId;
        if (id) handleDelete(id);
    });
}

function init() {
    const formEl = document.querySelector(SELECTORS.form);
    if (formEl) bindForm(formEl);
    bindHistoryDelete();
    // Render trend chart from server-rendered rows on first load.
    refreshHistory();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
