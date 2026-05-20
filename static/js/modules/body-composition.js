/**
 * Body Composition (Issue #21) page module.
 *
 * MUST MATCH PYTHON. The four pure functions (computeNavy, computeBmi,
 * aceCategory, jacksonPollockIdeal) below mirror utils/body_fat.py byte-
 * for-byte so the live preview on /body_composition agrees with the
 * server-side persisted values. Any change here MUST be reflected in
 * utils/body_fat.py (and vice versa).
 */

import { api, isHandledApiError } from './fetch-wrapper.js';
import { showToast } from './toast.js';

const CIRCUMFERENCE_MIN_CM = 20.0;
const CIRCUMFERENCE_MAX_CM = 250.0;
const HEIGHT_MIN_CM = 100.0;
const HEIGHT_MAX_CM = 250.0;
const BODYWEIGHT_MIN_KG = 20.0;
const BODYWEIGHT_MAX_KG = 350.0;
const ADULT_AGE_THRESHOLD = 18;

const JACKSON_POLLOCK_TABLE = [
    [20, 17.7, 8.5],
    [25, 18.4, 10.5],
    [30, 19.3, 12.7],
    [35, 21.5, 13.7],
    [40, 22.2, 15.3],
    [45, 22.9, 16.4],
    [50, 25.2, 18.9],
    [55, 26.3, 20.9],
];

const ACE_BANDS_MALE = [
    ['Essential fat', 2.0, 6.0],
    ['Athletes', 6.0, 14.0],
    ['Fitness', 14.0, 18.0],
    ['Average', 18.0, 25.0],
    ['Obese', 25.0, null],
];
const ACE_BANDS_FEMALE = [
    ['Essential fat', 10.0, 14.0],
    ['Athletes', 14.0, 21.0],
    ['Fitness', 21.0, 25.0],
    ['Average', 25.0, 32.0],
    ['Obese', 32.0, null],
];

function log10(x) {
    return Math.log(x) / Math.LN10;
}

function checkRange(value, lo, hi, field) {
    if (value === null || value === undefined || Number.isNaN(value)) {
        throw new Error(`${field} must be a number in [${lo}, ${hi}]`);
    }
    if (value < lo || value > hi) {
        throw new Error(`${field} must be in [${lo}, ${hi}]`);
    }
}

export function computeNavy({ gender, heightCm, neckCm, waistCm, hipCm = null }) {
    const sex = String(gender || '').trim().toUpperCase();
    if (sex !== 'M' && sex !== 'F') {
        throw new Error("gender must be 'M' or 'F'");
    }
    checkRange(heightCm, HEIGHT_MIN_CM, HEIGHT_MAX_CM, 'height');
    checkRange(neckCm, CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM, 'neck');
    checkRange(waistCm, CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM, 'waist');

    if (sex === 'M') {
        if (hipCm !== null && hipCm !== undefined) {
            throw new Error("hip must not be provided when gender is 'M'");
        }
        const delta = waistCm - neckCm;
        if (delta <= 0) {
            throw new Error('waist circumference must be larger than neck circumference');
        }
        return 495.0 / (1.0324 - 0.19077 * log10(delta) + 0.15456 * log10(heightCm)) - 450.0;
    }
    if (hipCm === null || hipCm === undefined) {
        throw new Error("hip is required when gender is 'F'");
    }
    checkRange(hipCm, CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM, 'hip');
    const delta = waistCm + hipCm - neckCm;
    if (delta <= 0) {
        throw new Error('waist + hip must be larger than neck circumference');
    }
    return 495.0 / (1.29579 - 0.35004 * log10(delta) + 0.22100 * log10(heightCm)) - 450.0;
}

export function computeBmi({ gender, ageYears, heightCm, bodyweightKg }) {
    const sex = String(gender || '').trim().toUpperCase();
    if (sex !== 'M' && sex !== 'F') {
        throw new Error("gender must be 'M' or 'F'");
    }
    if (!Number.isInteger(ageYears) || ageYears < 0 || ageYears > 120) {
        throw new Error('age_years must be in [0, 120]');
    }
    checkRange(heightCm, HEIGHT_MIN_CM, HEIGHT_MAX_CM, 'height');
    checkRange(bodyweightKg, BODYWEIGHT_MIN_KG, BODYWEIGHT_MAX_KG, 'bodyweight');

    const heightM = heightCm / 100.0;
    const bmi = bodyweightKg / (heightM * heightM);
    let bfp;
    if (ageYears >= ADULT_AGE_THRESHOLD) {
        bfp = sex === 'M' ? 1.20 * bmi + 0.23 * ageYears - 16.2 : 1.20 * bmi + 0.23 * ageYears - 5.4;
    } else {
        bfp = sex === 'M' ? 1.51 * bmi - 0.70 * ageYears - 2.2 : 1.51 * bmi - 0.70 * ageYears + 1.4;
    }
    return { bmi, bfp };
}

export function aceCategory(bfp, gender) {
    const sex = String(gender || '').trim().toUpperCase();
    if (sex !== 'M' && sex !== 'F') {
        throw new Error("gender must be 'M' or 'F'");
    }
    if (typeof bfp !== 'number' || Number.isNaN(bfp)) {
        throw new Error('bfp must be a number');
    }
    const bands = sex === 'M' ? ACE_BANDS_MALE : ACE_BANDS_FEMALE;
    for (const [label, lo, hi] of bands) {
        if (hi === null) {
            if (bfp >= lo) return label;
        } else if (bfp < hi) {
            return label;
        }
    }
    return bands[bands.length - 1][0];
}

export function jacksonPollockIdeal(ageYears, gender) {
    const sex = String(gender || '').trim().toUpperCase();
    if (sex !== 'M' && sex !== 'F') {
        throw new Error("gender must be 'M' or 'F'");
    }
    if (!Number.isInteger(ageYears) || ageYears < 0 || ageYears > 120) {
        throw new Error('age_years must be in [0, 120]');
    }
    const col = sex === 'M' ? 2 : 1;
    const firstAge = JACKSON_POLLOCK_TABLE[0][0];
    const lastAge = JACKSON_POLLOCK_TABLE[JACKSON_POLLOCK_TABLE.length - 1][0];
    if (ageYears <= firstAge) return JACKSON_POLLOCK_TABLE[0][col];
    if (ageYears >= lastAge) return JACKSON_POLLOCK_TABLE[JACKSON_POLLOCK_TABLE.length - 1][col];
    for (let i = 0; i < JACKSON_POLLOCK_TABLE.length - 1; i += 1) {
        const [loAge, loW, loM] = JACKSON_POLLOCK_TABLE[i];
        const [hiAge, hiW, hiM] = JACKSON_POLLOCK_TABLE[i + 1];
        if (loAge <= ageYears && ageYears <= hiAge) {
            const loVal = sex === 'M' ? loM : loW;
            const hiVal = sex === 'M' ? hiM : hiW;
            const ratio = (ageYears - loAge) / (hiAge - loAge);
            return loVal + (hiVal - loVal) * ratio;
        }
    }
    return JACKSON_POLLOCK_TABLE[JACKSON_POLLOCK_TABLE.length - 1][col];
}

// ---------- DOM wiring (page-only side-effects below) ----------

function parseNumber(value) {
    if (value === '' || value === null || value === undefined) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

function formatPct(value) {
    if (value === null || value === undefined || !Number.isFinite(value)) return '—';
    return `${value.toFixed(1)} %`;
}

function formatKg(value) {
    if (value === null || value === undefined || !Number.isFinite(value)) return '—';
    return `${value.toFixed(1)} kg`;
}

function readProfile(root) {
    const gender = root.dataset.profileGender || null;
    const age = parseNumber(root.dataset.profileAge);
    const heightCm = parseNumber(root.dataset.profileHeightCm);
    const weightKg = parseNumber(root.dataset.profileWeightKg);
    const ageInt = age !== null ? Math.round(age) : null;
    return {
        gender: gender || null,
        ageYears: ageInt,
        heightCm,
        bodyweightKg: weightKg,
        complete: Boolean(gender && ageInt && heightCm && weightKg),
    };
}

function buildBandSegments(target, gender) {
    if (!target) return;
    target.innerHTML = '';
    const bands = gender === 'F' ? ACE_BANDS_FEMALE : ACE_BANDS_MALE;
    const visibleMin = bands[0][1];
    const visibleMax = 40; // open-ended "Obese"; clamp visible scale at 40 %
    const span = visibleMax - visibleMin;
    bands.forEach(([label, lo, hi]) => {
        const segHi = hi === null ? visibleMax : Math.min(hi, visibleMax);
        const widthPct = Math.max(0, (segHi - Math.max(lo, visibleMin)) / span * 100);
        const seg = document.createElement('span');
        seg.className = 'bc-band-segment';
        seg.dataset.bandLabel = label;
        seg.style.width = `${widthPct.toFixed(2)}%`;
        seg.title = `${label} (${lo}${hi === null ? '+' : `–${hi}`} %)`;
        target.appendChild(seg);
    });
    target.dataset.visibleMin = String(visibleMin);
    target.dataset.visibleMax = String(visibleMax);
}

function positionBandTick(track, tick, bfp) {
    if (!track || !tick) return;
    if (bfp === null || bfp === undefined || !Number.isFinite(bfp)) {
        tick.hidden = true;
        return;
    }
    const segments = track.querySelector('[data-bc-band-segments]');
    const visibleMin = Number(segments?.dataset.visibleMin || 2);
    const visibleMax = Number(segments?.dataset.visibleMax || 40);
    const clamped = Math.max(visibleMin, Math.min(visibleMax, bfp));
    const pct = ((clamped - visibleMin) / (visibleMax - visibleMin)) * 100;
    tick.style.left = `${pct.toFixed(2)}%`;
    tick.hidden = false;
}

function renderTrend(svgRoot, line, emptyEl, snapshots) {
    const ordered = [...snapshots].sort((a, b) => (a.captured_at < b.captured_at ? -1 : 1));
    if (!ordered.length) {
        if (emptyEl) emptyEl.hidden = false;
        if (svgRoot) svgRoot.hidden = true;
        if (line) line.setAttribute('points', '');
        return;
    }
    if (emptyEl) emptyEl.hidden = true;
    if (svgRoot) svgRoot.hidden = false;

    const series = ordered.map((s) => (s.bfp_navy ?? s.bfp_bmi));
    const minBfp = Math.min(...series);
    const maxBfp = Math.max(...series);
    const span = maxBfp - minBfp || 1;
    const width = 320;
    const height = 120;
    const padX = 6;
    const padY = 10;

    const points = ordered
        .map((snap, idx) => {
            const value = snap.bfp_navy ?? snap.bfp_bmi;
            const x = ordered.length === 1
                ? width / 2
                : padX + (idx / (ordered.length - 1)) * (width - padX * 2);
            const y = padY + ((maxBfp - value) / span) * (height - padY * 2);
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(' ');
    if (line) line.setAttribute('points', points);
}

function renderResults(root, profile, tape) {
    const bfpEl = root.querySelector('[data-bc-bfp]');
    const fatEl = root.querySelector('[data-bc-fat-mass]');
    const leanEl = root.querySelector('[data-bc-lean-mass]');
    const bmiEl = root.querySelector('[data-bc-bmi]');
    const methodEl = root.querySelector('[data-bc-method-label]');
    const bandLabel = root.querySelector('[data-bc-band-label]');
    const bandTrack = root.querySelector('[data-bc-band-track]');
    const bandTick = root.querySelector('[data-bc-band-tick]');
    const jpIdeal = root.querySelector('[data-bc-jp-ideal]');
    const jpCurrent = root.querySelector('[data-bc-jp-current]');
    const errEl = root.querySelector('#bc-form-error');

    if (errEl) {
        errEl.hidden = true;
        errEl.textContent = '';
    }

    if (!profile.complete) {
        if (bfpEl) bfpEl.textContent = '—';
        if (fatEl) fatEl.textContent = '—';
        if (leanEl) leanEl.textContent = '—';
        if (bmiEl) bmiEl.textContent = '—';
        if (methodEl) methodEl.textContent = 'Profile required';
        if (bandLabel) bandLabel.textContent = '—';
        if (bandTick) bandTick.hidden = true;
        if (jpIdeal) jpIdeal.textContent = '—';
        if (jpCurrent) jpCurrent.textContent = '—';
        return;
    }

    let bmiResult;
    try {
        bmiResult = computeBmi({
            gender: profile.gender,
            ageYears: profile.ageYears,
            heightCm: profile.heightCm,
            bodyweightKg: profile.bodyweightKg,
        });
    } catch (err) {
        if (errEl) {
            errEl.textContent = err.message;
            errEl.hidden = false;
        }
        return;
    }

    const { neckCm, waistCm, hipCm } = tape;
    const requiredTape = profile.gender === 'M' ? [neckCm, waistCm] : [neckCm, waistCm, hipCm];
    const anyTape = [neckCm, waistCm, hipCm].some((v) => v !== null);
    const allTape = requiredTape.every((v) => v !== null);

    let bfpNavy = null;
    if (allTape) {
        try {
            bfpNavy = computeNavy({
                gender: profile.gender,
                heightCm: profile.heightCm,
                neckCm,
                waistCm,
                hipCm: profile.gender === 'F' ? hipCm : null,
            });
        } catch (err) {
            if (errEl) {
                errEl.textContent = err.message;
                errEl.hidden = false;
            }
        }
    } else if (anyTape && errEl) {
        const needed = profile.gender === 'M' ? 'neck and waist' : 'neck, waist, and hip';
        errEl.textContent = `Provide ${needed} for the Navy method, or clear all tape fields to use BMI.`;
        errEl.hidden = false;
    }

    const effectiveBfp = bfpNavy !== null ? bfpNavy : bmiResult.bfp;
    const fatMass = (effectiveBfp / 100.0) * profile.bodyweightKg;
    const leanMass = profile.bodyweightKg - fatMass;

    if (bfpEl) bfpEl.textContent = formatPct(effectiveBfp);
    if (fatEl) fatEl.textContent = formatKg(fatMass);
    if (leanEl) leanEl.textContent = formatKg(leanMass);
    if (bmiEl) bmiEl.textContent = bmiResult.bmi.toFixed(1);
    if (methodEl) methodEl.textContent = bfpNavy !== null ? 'U.S. Navy method' : 'BMI method (fallback)';

    if (bandLabel) bandLabel.textContent = aceCategory(effectiveBfp, profile.gender);
    positionBandTick(bandTrack, bandTick, effectiveBfp);

    const ideal = jacksonPollockIdeal(profile.ageYears, profile.gender);
    if (jpIdeal) jpIdeal.textContent = formatPct(ideal);
    if (jpCurrent) jpCurrent.textContent = formatPct(effectiveBfp);
}

function collectTape(form) {
    return {
        neckCm: parseNumber(form.elements.neck_cm.value),
        waistCm: parseNumber(form.elements.waist_cm.value),
        hipCm: parseNumber(form.elements.hip_cm.value),
    };
}

function bindForm(root) {
    const form = root.querySelector('#bc-form');
    if (!form) return;
    const profile = readProfile(root);
    const hipField = root.querySelector('[data-bc-hip-field]');
    if (hipField) {
        const showHip = profile.gender !== 'M';
        hipField.hidden = !showHip;
        const hipInput = root.querySelector('#bc-hip');
        if (hipInput) hipInput.disabled = !showHip;
    }

    const bandSegments = root.querySelector('[data-bc-band-segments]');
    buildBandSegments(bandSegments, profile.gender);

    const trendSvg = root.querySelector('[data-bc-trend-svg]');
    const trendLine = root.querySelector('[data-bc-trend-line]');
    const trendEmpty = root.querySelector('[data-bc-trend-empty]');
    const historyBody = root.querySelector('[data-bc-history-body]');
    const emptyState = root.querySelector('[data-bc-empty]');

    function refreshResults() {
        renderResults(root, profile, collectTape(form));
    }

    form.addEventListener('input', refreshResults);
    refreshResults();

    async function loadHistory() {
        try {
            const res = await api.get('/api/body_composition/snapshots', { showErrorToast: false });
            const snapshots = res?.data || [];
            renderTrend(trendSvg, trendLine, trendEmpty, snapshots);
            if (emptyState) emptyState.hidden = snapshots.length > 0;
        } catch (err) {
            if (!isHandledApiError(err)) {
                showToast('error', 'Failed to load snapshot history.');
            }
        }
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!profile.complete) {
            showToast('error', 'Complete your User Profile (gender, age, height, bodyweight) first.');
            return;
        }
        const tape = collectTape(form);
        const payload = {
            neck_cm: tape.neckCm,
            waist_cm: tape.waistCm,
            hip_cm: profile.gender === 'F' ? tape.hipCm : null,
            notes: form.elements.notes.value || null,
        };
        try {
            const res = await api.post('/api/body_composition/snapshot', payload, { showErrorToast: false });
            showToast('success', 'Snapshot saved.');
            const created = res?.data;
            if (created && historyBody) {
                prependHistoryRow(historyBody, created);
                if (emptyState) emptyState.hidden = true;
            }
            await loadHistory();
        } catch (err) {
            const msg = (err && err.message) ? err.message : 'Failed to save snapshot.';
            showToast('error', msg);
        }
    });

    if (historyBody) {
        historyBody.addEventListener('click', async (event) => {
            const btn = event.target.closest('[data-bc-delete]');
            if (!btn) return;
            const id = btn.getAttribute('data-bc-delete');
            if (!id) return;
            try {
                await api.delete(`/api/body_composition/snapshots/${id}`, { showErrorToast: false });
                const row = btn.closest('tr');
                if (row) row.remove();
                if (!historyBody.querySelector('tr') && emptyState) emptyState.hidden = false;
                await loadHistory();
            } catch (err) {
                const msg = (err && err.message) ? err.message : 'Failed to delete snapshot.';
                showToast('error', msg);
            }
        });
    }

    loadHistory();
}

function prependHistoryRow(body, snap) {
    const tr = document.createElement('tr');
    tr.dataset.bcSnapshotId = String(snap.id);
    tr.innerHTML = `
        <td data-label="Date">${escapeHtml(snap.captured_at)}</td>
        <td class="is-num" data-label="BFP (Navy)">${snap.bfp_navy !== null ? `${snap.bfp_navy.toFixed(1)} %` : '—'}</td>
        <td class="is-num" data-label="BFP (BMI)">${snap.bfp_bmi.toFixed(1)} %</td>
        <td class="is-num" data-label="Lean Mass">${snap.lean_mass_kg !== null ? `${snap.lean_mass_kg.toFixed(1)} kg` : '—'}</td>
        <td class="is-num" data-label="Fat Mass">${snap.fat_mass_kg !== null ? `${snap.fat_mass_kg.toFixed(1)} kg` : '—'}</td>
        <td data-label="Actions">
            <button type="button" class="btn btn-sm btn-outline-danger btn-calm-ghost"
                    data-bc-delete="${snap.id}"
                    aria-label="Delete snapshot from ${escapeHtml(snap.captured_at)}">
                <i class="fas fa-trash" aria-hidden="true"></i>
            </button>
        </td>
    `;
    body.insertBefore(tr, body.firstChild);
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function init() {
    const root = document.querySelector('[data-bc-app]');
    if (!root) return;
    bindForm(root);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
