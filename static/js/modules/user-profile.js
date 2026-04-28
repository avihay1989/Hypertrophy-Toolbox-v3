import { api } from './fetch-wrapper.js';
import { showToast } from './toast.js';
import {
    annotateBodymapPolygons,
    BODYMAP_COVERAGE_MUSCLES,
    COVERAGE_LIFT_LABELS,
    COVERAGE_MUSCLE_CHAIN,
    loadBodymapSvg,
} from './bodymap-svg.js';

// Issue #17 — JS port of the cold-start + accuracy-band logic that lives
// in `utils/profile_estimator.py`. The estimator stays the source of
// truth (it owns the trace + initial render); this module mirrors only
// the small subset needed to refresh the "How the system sees you" card
// in response to live form input. Any change to the constants below MUST
// be matched in `utils/profile_estimator.py` and vice versa.
const COLD_START_RATIOS = {
    Chest: { M: 1.0, F: 0.65 },
    Quadriceps: { M: 1.5, F: 1.1 },
    Hamstrings: { M: 1.75, F: 1.35 },
    'Gluteus Maximus': { M: 2.0, F: 1.5 },
    'Latissimus Dorsi': { M: 1.1, F: 0.7 },
    'Front-Shoulder': { M: 0.65, F: 0.4 },
    Biceps: { M: 0.4, F: 0.25 },
    Triceps: { M: 0.45, F: 0.3 },
};

const COLD_START_CANONICAL_COMPOUND = [
    { muscle: 'Chest', slug: 'barbell_bench_press', label: 'Barbell Bench Press' },
    { muscle: 'Quadriceps', slug: 'barbell_back_squat', label: 'Barbell Back Squat' },
    { muscle: 'Hamstrings', slug: 'romanian_deadlift', label: 'Romanian Deadlift' },
    { muscle: 'Gluteus Maximus', slug: 'hip_thrust', label: 'Hip Thrust' },
    { muscle: 'Latissimus Dorsi', slug: 'weighted_pullups', label: 'Weighted Pull-ups' },
    { muscle: 'Front-Shoulder', slug: 'military_press', label: 'Military / Shoulder Press' },
    { muscle: 'Biceps', slug: 'barbell_bicep_curl', label: 'Barbell Bicep Curl' },
    { muscle: 'Triceps', slug: 'triceps_extension', label: 'Triceps Extension' },
];

const HIGH_IMPACT_LIFT_PRIORITY = [
    { slug: 'barbell_bench_press', label: 'Barbell Bench Press' },
    { slug: 'barbell_back_squat', label: 'Barbell Back Squat' },
    { slug: 'romanian_deadlift', label: 'Romanian Deadlift' },
    { slug: 'weighted_pullups', label: 'Weighted Pull-ups' },
    { slug: 'military_press', label: 'Military / Shoulder Press' },
    { slug: 'barbell_bicep_curl', label: 'Barbell Bicep Curl' },
    { slug: 'triceps_extension', label: 'Triceps Extension' },
    { slug: 'barbell_row', label: 'Barbell Row' },
    { slug: 'standing_calf_raise', label: 'Standing Calf Raise' },
];

const ACCURACY_MAJOR_MUSCLE_GROUPS = [
    ['Chest', ['barbell_bench_press', 'dumbbell_bench_press', 'incline_bench_press', 'smith_machine_bench_press', 'machine_chest_press', 'dumbbell_fly']],
    ['Back', ['barbell_row', 'machine_row', 'weighted_pullups', 'bodyweight_pullups', 'bodyweight_chinups']],
    ['Legs', ['barbell_back_squat', 'leg_press', 'leg_extension', 'dumbbell_squat', 'dumbbell_lunge', 'dumbbell_step_up', 'hip_thrust', 'romanian_deadlift', 'conventional_deadlift', 'stiff_leg_deadlift', 'good_morning', 'single_leg_rdl', 'leg_curl']],
    ['Shoulders', ['military_press', 'dumbbell_shoulder_press', 'machine_shoulder_press', 'arnold_press', 'dumbbell_lateral_raise']],
    ['Biceps', ['barbell_bicep_curl', 'dumbbell_curl', 'preacher_curl', 'incline_dumbbell_curl']],
    ['Triceps', ['triceps_extension', 'skull_crusher', 'jm_press', 'weighted_dips', 'bodyweight_dips']],
];

function classifyExperienceTier(years) {
    if (years === null || years === undefined || Number.isNaN(years)) return 'novice';
    if (years < 0) return 'novice';
    if (years <= 1.0) return 'novice';
    if (years <= 3.0) return 'intermediate';
    return 'advanced';
}

function experienceMultiplier(tier) {
    return tier === 'novice' ? 0.7 : tier === 'advanced' ? 1.2 : 1.0;
}

// Issue #18 — Must match cohort buckets in `utils/profile_estimator.py`
// (`COHORT_BODYWEIGHT_KG`, `COHORT_HEIGHT_CM`, `COHORT_AGE_YEARS`,
// `ADVANCED_COHORT_REACH`).
const COHORT_BODYWEIGHT_KG = { M: [70.0, 90.0], F: [55.0, 75.0] };
const COHORT_HEIGHT_CM = { M: [170.0, 188.0], F: [158.0, 175.0] };
const COHORT_AGE_YEARS = [25.0, 45.0];
const TIER_ORDER = ['novice', 'intermediate', 'advanced'];
const ADVANCED_COHORT_REACH = 1.2;

function nextTierMultiplier(tier) {
    const idx = TIER_ORDER.indexOf(tier);
    if (idx >= 0 && idx < TIER_ORDER.length - 1) {
        return experienceMultiplier(TIER_ORDER[idx + 1]);
    }
    return experienceMultiplier('advanced') * ADVANCED_COHORT_REACH;
}

function tierLabel(tier) {
    if (!tier) return null;
    return tier.charAt(0).toUpperCase() + tier.slice(1);
}

function formatYears(years) {
    if (years === null || years === undefined) return null;
    if (Number.isInteger(years)) return `${years} yrs`;
    return `${years} yrs`;
}

function classificationFromForm() {
    const gender = document.getElementById('profile-gender')?.value || '';
    const weightInput = document.getElementById('profile-weight')?.value || '';
    const heightInput = document.getElementById('profile-height')?.value || '';
    const ageInput = document.getElementById('profile-age')?.value || '';
    const experienceInput = document.getElementById('profile-experience')?.value || '';
    const weight = weightInput === '' ? null : Number(weightInput);
    const height = heightInput === '' ? null : Number(heightInput);
    const age = ageInput === '' ? null : Number(ageInput);
    const experience = experienceInput === '' ? null : Number(experienceInput);
    const tier = experience === null ? null : classifyExperienceTier(experience);
    return {
        gender: gender === 'M' ? 'Male' : gender === 'F' ? 'Female' : null,
        rawGender: gender || null,
        bodyweight: Number.isFinite(weight) && weight > 0 ? weight : null,
        height: Number.isFinite(height) && height > 0 ? height : null,
        age: Number.isFinite(age) && age >= 0 ? age : null,
        experienceYears: Number.isFinite(experience) && experience >= 0 ? experience : null,
        experienceTier: tier,
    };
}

function liftRowsFromForm() {
    return Array.from(document.querySelectorAll('.reference-lift-row')).map(row => {
        const liftKey = row.dataset.liftKey;
        const weightStr = row.querySelector('[name="weight_kg"]')?.value ?? '';
        const repsStr = row.querySelector('[name="reps"]')?.value ?? '';
        const weight = weightStr === '' ? null : Number(weightStr);
        const reps = repsStr === '' ? null : Number(repsStr);
        return {
            lift_key: liftKey,
            weight_kg: Number.isFinite(weight) ? weight : null,
            reps: Number.isFinite(reps) ? reps : null,
        };
    });
}

function isLiftFilled(row) {
    if (!row || !row.lift_key) return false;
    const reps = Number(row.reps);
    if (!Number.isFinite(reps) || reps <= 0) return false;
    const weight = Number(row.weight_kg);
    if (!Number.isFinite(weight)) return false;
    if (row.lift_key.startsWith('bodyweight_')) return weight >= 0;
    return weight > 0;
}

function epley1rm(weight, reps) {
    if (reps <= 0 || weight <= 0) return 0;
    const cappedReps = Math.min(reps, 12);
    return weight * (1 + cappedReps / 30);
}

function coldStart1rm(muscle, classification) {
    if (!classification.rawGender || !classification.bodyweight) return null;
    const ratio = COLD_START_RATIOS[muscle]?.[classification.rawGender];
    if (ratio === undefined) return null;
    const tier = classifyExperienceTier(classification.experienceYears);
    const multiplier = experienceMultiplier(tier);
    return classification.bodyweight * ratio * multiplier;
}

function computeAccuracyBand(filledKeys, hasDemographics) {
    const filledCount = filledKeys.size;
    const totalSlugs = document.querySelectorAll('.reference-lift-row').length;
    let band;
    if (totalSlugs > 0 && filledCount >= totalSlugs) {
        band = 'fully';
    } else if (filledCount >= 5 && ACCURACY_MAJOR_MUSCLE_GROUPS.every(([, slugs]) => slugs.some(s => filledKeys.has(s)))) {
        band = 'mostly';
    } else if (filledCount >= 1) {
        band = 'partial';
    } else {
        band = 'population_only';
    }
    const copy = (
        band === 'fully'
            ? 'All your suggestions use your measured lifts. Re-enter your reference lifts when you set a new PR to keep them current.'
            : band === 'mostly'
                ? 'Most of your suggestions use your real data. Add the lifts below to refine the remaining estimates.'
                : band === 'partial'
                    ? 'About a third of your suggestions use your real data. Add the lifts below to lift this further.'
                    : hasDemographics
                        ? 'Numbers come from population averages. Add even one reference lift to start personalising.'
                        : 'No reference lifts or demographics saved yet — fill in either to start personalising your suggestions.'
    );
    return { band, filledCount, totalSlugs, copy };
}

function bandPillLabel(band) {
    return band === 'fully' ? 'Fully personalised'
        : band === 'mostly' ? 'Mostly personalised'
        : band === 'partial' ? 'Partially personalised'
        : 'Population estimate only';
}

function nullableValue(value) {
    const trimmed = String(value ?? '').trim();
    return trimmed === '' ? null : trimmed;
}

function profilePayload(form) {
    const formData = new FormData(form);
    return {
        gender: nullableValue(formData.get('gender')),
        age: nullableValue(formData.get('age')),
        height_cm: nullableValue(formData.get('height_cm')),
        weight_kg: nullableValue(formData.get('weight_kg')),
        experience_years: nullableValue(formData.get('experience_years')),
    };
}

function liftPayload(form) {
    return Array.from(form.querySelectorAll('.reference-lift-row')).map(row => ({
        lift_key: row.dataset.liftKey,
        weight_kg: nullableValue(row.querySelector('[name="weight_kg"]')?.value),
        reps: nullableValue(row.querySelector('[name="reps"]')?.value),
    }));
}

function preferencesPayload(form) {
    return Array.from(form.querySelectorAll('.preference-group')).reduce((payload, group) => {
        const checked = group.querySelector('input[type="radio"]:checked');
        if (checked) {
            payload[group.dataset.tier] = checked.value;
        }
        return payload;
    }, {});
}

const AUTOSAVE_DEBOUNCE_MS = 700;

function formatTimeHHMM(date) {
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
}

function setAutosaveStatus(form, state, options = {}) {
    const pill = form.querySelector('[data-autosave-status]');
    if (!pill) return;
    const text = pill.querySelector('[data-autosave-text]');
    const retry = pill.querySelector('[data-autosave-retry]');
    pill.dataset.autosaveStatus = state;
    if (retry) retry.hidden = state !== 'error';
    if (!text) return;
    if (state === 'idle') {
        text.textContent = options.message || 'Changes save automatically';
    } else if (state === 'pending') {
        text.textContent = 'Unsaved changes…';
    } else if (state === 'saving') {
        text.textContent = 'Saving…';
    } else if (state === 'saved') {
        text.textContent = `Saved · ${formatTimeHHMM(options.savedAt || new Date())}`;
    } else if (state === 'error') {
        text.textContent = options.message || 'Save failed';
    }
}

async function performSave(form, buildPayload, endpoint) {
    setAutosaveStatus(form, 'saving');
    try {
        const response = await api.post(endpoint, buildPayload(form), {
            showLoading: false,
            showErrorToast: false,
        });
        setAutosaveStatus(form, 'saved', { savedAt: new Date() });
        return response;
    } catch (error) {
        const message = error?.message || 'Unable to save profile section.';
        setAutosaveStatus(form, 'error', { message: `Save failed — ${message}` });
        showToast('error', message, { requestId: error?.requestId });
        throw error;
    }
}

function bindAutosaveForm(formId, buildPayload, endpoint, options = {}) {
    const form = document.getElementById(formId);
    if (!form) {
        return;
    }

    const debounceMs = options.debounceMs ?? AUTOSAVE_DEBOUNCE_MS;
    let timer = null;
    let inFlight = null;
    let pendingAfterFlight = false;

    const flush = async () => {
        if (inFlight) {
            pendingAfterFlight = true;
            return;
        }
        inFlight = performSave(form, buildPayload, endpoint)
            .catch(() => {})
            .finally(() => {
                inFlight = null;
                if (pendingAfterFlight) {
                    pendingAfterFlight = false;
                    schedule(0);
                }
            });
    };

    const schedule = (delay = debounceMs) => {
        if (timer) clearTimeout(timer);
        setAutosaveStatus(form, 'pending');
        timer = setTimeout(() => {
            timer = null;
            flush();
        }, delay);
    };

    form.addEventListener('submit', event => {
        event.preventDefault();
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
        flush();
    });

    const inputDelay = options.inputImmediate ? 0 : debounceMs;
    form.addEventListener('input', () => schedule(inputDelay));
    form.addEventListener('change', () => schedule(options.changeImmediate ? 0 : inputDelay));

    form.querySelector('[data-autosave-retry]')?.addEventListener('click', () => {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
        flush();
    });
}

function initializeCollapseToggles() {
    const toggleButtons = document.querySelectorAll('.user-profile-page .collapse-toggle');
    toggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            const frame = button.closest('.collapsible-frame');
            if (!frame) return;
            const wasExpanded = button.getAttribute('aria-expanded') === 'true';
            const nowExpanded = !wasExpanded;
            frame.classList.toggle('collapsed', !nowExpanded);
            button.setAttribute('aria-expanded', String(nowExpanded));
            const icon = button.querySelector('.toggle-icon');
            if (icon) {
                icon.classList.toggle('fa-chevron-up', nowExpanded);
                icon.classList.toggle('fa-chevron-down', !nowExpanded);
            }
            const text = button.querySelector('.toggle-text');
            if (text) {
                text.textContent = nowExpanded ? 'Hide' : 'Show';
            }
        });
    });
}

function renderTiles(card, classification) {
    const setTile = (key, { value, cohort, empty }) => {
        const tile = card.querySelector(`[data-insights-tile="${key}"]`);
        if (!tile) return;
        if (empty) {
            tile.dataset.empty = 'true';
        } else {
            delete tile.dataset.empty;
        }
        const valueNode = tile.querySelector('[data-tile-value]');
        const cohortNode = tile.querySelector('[data-tile-cohort]');
        if (valueNode) valueNode.textContent = value;
        if (cohortNode) cohortNode.textContent = cohort;
    };

    // Bodyweight (used).
    if (classification.bodyweight) {
        const range = classification.rawGender ? COHORT_BODYWEIGHT_KG[classification.rawGender] : null;
        const tier = classification.experienceTier;
        const cohortText = range
            ? (classification.rawGender && tier
                ? `Cohort: ${range[0]}–${range[1]} kg (${classification.gender.toLowerCase()} ${tier})`
                : `Cohort: ${range[0]}–${range[1]} kg (${classification.gender.toLowerCase()})`)
            : 'Cohort range needs gender';
        setTile('bodyweight', {
            value: `${classification.bodyweight} kg`,
            cohort: cohortText,
            empty: false,
        });
    } else {
        setTile('bodyweight', { value: '—', cohort: 'Add bodyweight to enable', empty: true });
    }

    // Height (unused).
    if (classification.height) {
        const range = classification.rawGender ? COHORT_HEIGHT_CM[classification.rawGender] : null;
        setTile('height', {
            value: `${classification.height} cm`,
            cohort: range
                ? `Cohort: ${range[0]}–${range[1]} cm (${classification.gender.toLowerCase()})`
                : 'Cohort range needs gender',
            empty: false,
        });
    } else {
        setTile('height', {
            value: '—',
            cohort: 'Add height (currently unused — flagged for future use)',
            empty: true,
        });
    }

    // Age (unused).
    if (classification.age !== null) {
        setTile('age', {
            value: `${classification.age} yrs`,
            cohort: `Cohort: ${COHORT_AGE_YEARS[0]}–${COHORT_AGE_YEARS[1]} yrs`,
            empty: false,
        });
    } else {
        setTile('age', {
            value: '—',
            cohort: 'Add age (currently unused)',
            empty: true,
        });
    }

    // Experience (used).
    const tier = classification.experienceTier;
    if (tier) {
        const mult = experienceMultiplier(tier);
        const yearsText = formatYears(classification.experienceYears);
        const tile = card.querySelector('[data-insights-tile="experience"]');
        if (tile) {
            delete tile.dataset.empty;
            const valueNode = tile.querySelector('[data-tile-value]');
            const cohortNode = tile.querySelector('[data-tile-cohort]');
            if (valueNode) {
                valueNode.innerHTML = '';
                valueNode.appendChild(document.createTextNode(tierLabel(tier)));
                if (yearsText) {
                    const small = document.createElement('small');
                    small.textContent = ` · ${yearsText}`;
                    valueNode.appendChild(small);
                }
            }
            if (cohortNode) cohortNode.textContent = `Tier multiplier: ×${mult.toFixed(2)} of trained max`;
        }
    } else {
        setTile('experience', {
            value: '—',
            cohort: 'Pick a level to enable cold-start estimates',
            empty: true,
        });
    }
}

function renderCohortSummary(card, classification) {
    const node = card.querySelector('[data-cohort-summary]');
    if (!node) return;
    const genderText = classification.gender ? classification.gender.toLowerCase() : 'unknown gender';
    const ageText = `age ${COHORT_AGE_YEARS[0]}–${COHORT_AGE_YEARS[1]}`;
    const range = classification.rawGender ? COHORT_BODYWEIGHT_KG[classification.rawGender] : null;
    const bodyweightText = range
        ? `bodyweight ${range[0]}–${range[1]} kg`
        : 'bodyweight unknown';
    const tier = classification.experienceTier;
    const yearsText = formatYears(classification.experienceYears);
    const experienceText = tier && yearsText
        ? `${tier} (${yearsText} trained)`
        : 'experience level unknown';
    const missing = !classification.gender || experienceText === 'experience level unknown';
    const body = `${genderText}, ${ageText}, ${bodyweightText}, ${experienceText}`;
    node.textContent = missing
        ? `Estimator cohort: ${body} — fill these to calibrate.`
        : `Estimator cohort: ${body}. Suggestions are calibrated to lifters in this bucket.`;
}

function renderCohortBars(card, classification, liftRows) {
    const section = card.querySelector('[data-insights-bars]');
    const list = card.querySelector('[data-bar-list]');
    if (!section || !list) return;

    if (!classification.rawGender || !classification.bodyweight) {
        list.innerHTML = '';
        section.hidden = true;
        return;
    }

    const tier = classifyExperienceTier(classification.experienceYears);
    const currentMult = experienceMultiplier(tier);
    const nextMult = nextTierMultiplier(tier);

    const filledByKey = new Map(liftRows.map(r => [r.lift_key, r]));
    const newRows = [];
    for (const anchor of COLD_START_CANONICAL_COMPOUND) {
        if (anchor.slug.startsWith('bodyweight_')) continue;
        const row = filledByKey.get(anchor.slug);
        if (!isLiftFilled(row)) continue;
        const weight = Number(row.weight_kg);
        const reps = Number(row.reps);
        if (!(weight > 0) || !(reps > 0)) continue;
        const coldStart = coldStart1rm(anchor.muscle, classification);
        if (coldStart === null || coldStart <= 0) continue;
        const userOneRm = epley1rm(weight, reps);
        const cohortUpper = coldStart * (nextMult / currentMult);
        const maxKg = Math.max(coldStart, userOneRm, cohortUpper) * 1.05;
        const range = (maxKg - 0) || 1;
        const csPct = (coldStart / range) * 100;
        const userPct = (userOneRm / range) * 100;
        const cuPct = (cohortUpper / range) * 100;
        newRows.push({ anchor, coldStart, userOneRm, cohortUpper, csPct, userPct, cuPct });
    }

    if (newRows.length === 0) {
        list.innerHTML = '';
        section.hidden = true;
        return;
    }

    section.hidden = false;
    list.innerHTML = '';
    for (const row of newRows) {
        const li = document.createElement('li');
        li.className = 'profile-insights-bar-row';
        li.dataset.barSlug = row.anchor.slug;

        const head = document.createElement('div');
        head.className = 'profile-insights-bar-head';
        const strong = document.createElement('strong');
        strong.textContent = row.anchor.label;
        const userSpan = document.createElement('span');
        userSpan.className = 'profile-insights-bar-user';
        userSpan.textContent = `≈ ${row.userOneRm.toFixed(1)} kg 1RM`;
        head.appendChild(strong);
        head.appendChild(userSpan);

        const track = document.createElement('div');
        track.className = 'profile-insights-bar-track';
        track.setAttribute('role', 'img');
        track.setAttribute(
            'aria-label',
            `${row.anchor.label}: cold-start ${row.coldStart.toFixed(1)} kg, you ${row.userOneRm.toFixed(1)} kg, cohort upper ${row.cohortUpper.toFixed(1)} kg`,
        );
        const fill = document.createElement('span');
        fill.className = 'profile-insights-bar-fill';
        fill.style.setProperty('--cs-pct', `${row.csPct.toFixed(2)}%`);
        fill.style.setProperty('--cu-pct', `${row.cuPct.toFixed(2)}%`);
        track.appendChild(fill);
        for (const [cls, pct] of [
            ['is-cold-start', row.csPct],
            ['is-user', row.userPct],
            ['is-cohort-upper', row.cuPct],
        ]) {
            const marker = document.createElement('span');
            marker.className = `profile-insights-bar-marker ${cls}`;
            marker.style.setProperty('--mark-pct', `${pct.toFixed(2)}%`);
            track.appendChild(marker);
        }

        const foot = document.createElement('div');
        foot.className = 'profile-insights-bar-foot';
        const csSpan = document.createElement('span');
        csSpan.textContent = `cold-start ≈ ${row.coldStart.toFixed(1)} kg`;
        const cuSpan = document.createElement('span');
        cuSpan.textContent = `cohort upper ≈ ${row.cohortUpper.toFixed(1)} kg`;
        foot.appendChild(csSpan);
        foot.appendChild(cuSpan);

        li.appendChild(head);
        li.appendChild(track);
        li.appendChild(foot);
        list.appendChild(li);
    }
}

function renderProfileInsights() {
    const card = document.querySelector('[data-profile-insights="true"]');
    if (!card) return;

    const classification = classificationFromForm();
    const liftRows = liftRowsFromForm();
    const filledKeys = new Set(liftRows.filter(isLiftFilled).map(r => r.lift_key));
    const hasDemographics = Boolean(classification.gender || classification.bodyweight || classification.experienceYears !== null);

    // Issue #18 — stats tiles + cohort summary + bars.
    renderTiles(card, classification);
    renderCohortSummary(card, classification);
    renderCohortBars(card, classification, liftRows);

    // Cold-start anchors.
    const anchorsSection = card.querySelector('[data-insights-anchors]');
    const anchorList = card.querySelector('[data-anchor-list]');
    const anchorsReady = Boolean(classification.rawGender && classification.bodyweight);
    if (anchorsSection) {
        anchorsSection.hidden = !anchorsReady;
    }
    if (anchorList) {
        anchorList.innerHTML = '';
        for (const anchor of COLD_START_CANONICAL_COMPOUND) {
            const seed = coldStart1rm(anchor.muscle, classification);
            const li = document.createElement('li');
            li.dataset.anchorSlug = anchor.slug;
            const label = document.createElement('strong');
            label.textContent = anchor.label;
            const value = document.createElement('span');
            value.dataset.anchorValue = '';
            value.textContent = seed && seed > 0 ? `≈ ${seed.toFixed(1)} kg 1RM` : '—';
            li.appendChild(label);
            li.appendChild(document.createTextNode(' '));
            li.appendChild(value);
            anchorList.appendChild(li);
        }
    }

    // Replaced-by-your-data list.
    const replacedSection = card.querySelector('[data-insights-replaced]');
    const replacedList = card.querySelector('[data-replaced-list]');
    if (replacedList) {
        replacedList.innerHTML = '';
        const filledByKey = new Map(liftRows.map(r => [r.lift_key, r]));
        for (const anchor of COLD_START_CANONICAL_COMPOUND) {
            if (anchor.slug.startsWith('bodyweight_')) continue;
            const row = filledByKey.get(anchor.slug);
            if (!isLiftFilled(row)) continue;
            const weight = Number(row.weight_kg);
            const reps = Number(row.reps);
            if (!(weight > 0) || !(reps > 0)) continue;
            const oneRm = epley1rm(weight, reps);
            const li = document.createElement('li');
            li.dataset.replacedSlug = anchor.slug;
            const strong = document.createElement('strong');
            strong.textContent = anchor.label;
            const span = document.createElement('span');
            span.textContent = ` (saved ${weight} kg × ${reps} → 1RM ≈ ${oneRm.toFixed(1)} kg)`;
            li.appendChild(strong);
            li.appendChild(span);
            replacedList.appendChild(li);
        }
        if (replacedSection) {
            replacedSection.hidden = replacedList.children.length === 0;
        }
    }

    // Next-high-impact missing list.
    const missingSection = card.querySelector('[data-insights-missing]');
    const missingList = card.querySelector('[data-missing-list]');
    if (missingList) {
        missingList.innerHTML = '';
        const collected = [];
        for (const entry of HIGH_IMPACT_LIFT_PRIORITY) {
            if (filledKeys.has(entry.slug)) continue;
            collected.push(entry);
            if (collected.length >= 3) break;
        }
        for (const entry of collected) {
            const li = document.createElement('li');
            li.dataset.missingSlug = entry.slug;
            li.textContent = entry.label;
            missingList.appendChild(li);
        }
        if (missingSection) {
            missingSection.hidden = collected.length === 0;
        }
    }

    // Accuracy band pill, copy, count, fill bar + Issue #18 donut.
    const summary = computeAccuracyBand(filledKeys, hasDemographics);
    card.dataset.band = summary.band;
    const bandRoot = card.querySelector('[data-insights-band]');
    if (bandRoot) {
        bandRoot.dataset.bandKey = summary.band;
    }
    const pill = card.querySelector('[data-band-pill]');
    if (pill) pill.textContent = bandPillLabel(summary.band);
    const count = card.querySelector('[data-band-count]');
    if (count) count.textContent = `${summary.filledCount} / ${summary.totalSlugs} reference lifts`;
    const copy = card.querySelector('[data-band-copy]');
    if (copy) copy.textContent = summary.copy;
    const fill = card.querySelector('[data-band-fill]');
    if (fill) {
        fill.style.setProperty('--band-progress', String(summary.filledCount));
        fill.style.setProperty('--band-total', String(summary.totalSlugs || 1));
    }
    const donutCount = card.querySelector('[data-donut-count]');
    if (donutCount) {
        donutCount.innerHTML = '';
        donutCount.appendChild(document.createTextNode(String(summary.filledCount)));
        const ofSpan = document.createElement('span');
        ofSpan.className = 'profile-insights-donut-of';
        ofSpan.textContent = `/${summary.totalSlugs}`;
        donutCount.appendChild(ofSpan);
    }
    const donutFill = card.querySelector('[data-donut-fill]');
    if (donutFill) {
        const totalSlugs = summary.totalSlugs || 1;
        const pct = (summary.filledCount / totalSlugs) * 100;
        donutFill.style.strokeDasharray = `${pct.toFixed(2)} ${(100 - pct).toFixed(2)}`;
    }
}

function bindInsightsAutoUpdate() {
    const refresh = () => {
        renderProfileInsights();
        renderBodymapCoverage();
    };
    document.getElementById('profile-demographics-form')?.addEventListener('input', refresh);
    document.getElementById('profile-demographics-form')?.addEventListener('change', refresh);
    document.getElementById('profile-lifts-form')?.addEventListener('input', refresh);
    document.getElementById('profile-lifts-form')?.addEventListener('change', refresh);
}

// =============================================================================
// Issue #19 — Bodymap coverage view
// =============================================================================

const BODYMAP_STATE = {
    side: 'front',
    svgMounted: { front: false, back: false },
};

const STATE_LABELS = {
    measured: 'Measured',
    cross_muscle: 'Cross-muscle fallback',
    cold_start_only: 'Population estimate',
    not_assessed: 'Not assessed',
};

function computeMuscleCoverage(filledByKey) {
    // Mirror of `muscle_coverage_state` in `utils/profile_estimator.py`.
    // Enforced in lockstep — see the comment on COVERAGE_MUSCLE_CHAIN in
    // bodymap-svg.js.
    const out = {};
    for (const [muscle, chain] of Object.entries(COVERAGE_MUSCLE_CHAIN)) {
        const chainEntries = [];
        const filledEntries = [];
        let firstFilledIdx = null;
        chain.forEach((slug, idx) => {
            const lift = filledByKey.get(slug);
            const filled = isLiftFilled(lift);
            const entry = {
                lift_key: slug,
                label: COVERAGE_LIFT_LABELS[slug] || slug,
                filled,
            };
            if (filled && lift) {
                const weight = Number(lift.weight_kg);
                const reps = Number(lift.reps);
                entry.weight_kg = weight;
                entry.reps = reps;
                if (!slug.startsWith('bodyweight_') && weight > 0 && reps > 0) {
                    entry.estimated_1rm = Math.round(epley1rm(weight, reps) * 10) / 10;
                }
                if (firstFilledIdx === null) firstFilledIdx = idx;
                filledEntries.push(entry);
            }
            chainEntries.push(entry);
        });

        let state;
        if (chain.length === 0) {
            state = 'not_assessed';
        } else if (firstFilledIdx === 0) {
            state = 'measured';
        } else if (firstFilledIdx !== null) {
            state = 'cross_muscle';
        } else {
            state = 'cold_start_only';
        }

        let improvementSlug = null;
        if (state === 'cross_muscle' || state === 'cold_start_only') {
            const next = chainEntries.find(e => !e.filled);
            improvementSlug = next ? next.lift_key : null;
        }

        out[muscle] = {
            muscle,
            state,
            chain: chainEntries,
            filled: filledEntries,
            primary_lift_key: chain[0] || null,
            primary_lift_label: chain[0] ? (COVERAGE_LIFT_LABELS[chain[0]] || chain[0]) : null,
            improvement_lift_key: improvementSlug,
            improvement_lift_label: improvementSlug ? (COVERAGE_LIFT_LABELS[improvementSlug] || improvementSlug) : null,
        };
    }
    return out;
}

async function mountBodymapForSide(stage, side) {
    if (BODYMAP_STATE.svgMounted[side]) return;
    try {
        const svgText = await loadBodymapSvg(side);
        const wrap = document.createElement('div');
        wrap.className = 'profile-bodymap-svg-pane';
        wrap.dataset.bodymapPane = side;
        wrap.hidden = side !== BODYMAP_STATE.side;
        wrap.innerHTML = svgText;
        const svgEl = wrap.querySelector('svg');
        if (svgEl) {
            annotateBodymapPolygons(svgEl, side);
        }
        const loading = stage.querySelector('[data-bodymap-loading]');
        if (loading) loading.remove();
        stage.appendChild(wrap);
        BODYMAP_STATE.svgMounted[side] = true;
    } catch (error) {
        const stageMsg = stage.querySelector('[data-bodymap-loading]');
        if (stageMsg) {
            stageMsg.textContent = 'Could not load body diagram. Refresh to retry.';
        }
    }
}

function applyCoverageStateToPolygons(stage, coverage) {
    const panes = stage.querySelectorAll('[data-bodymap-pane]');
    panes.forEach(pane => {
        const regions = pane.querySelectorAll('.muscle-region');
        regions.forEach(region => {
            const muscle = region.dataset.bodymapMuscle;
            for (const cls of ['state-measured', 'state-cross_muscle', 'state-cold_start_only', 'state-not_assessed']) {
                region.classList.remove(cls);
            }
            if (!muscle || !coverage[muscle]) {
                region.classList.add('state-not_assessed');
                region.dataset.coverageState = 'not_assessed';
                region.setAttribute('role', 'img');
                region.setAttribute('aria-label', `${region.dataset.bodymapLabel || 'Region'} — Not assessed`);
                return;
            }
            const entry = coverage[muscle];
            region.classList.add(`state-${entry.state}`);
            region.dataset.coverageState = entry.state;
            region.setAttribute('role', 'img');
            region.setAttribute('aria-label', `${region.dataset.bodymapLabel || muscle} — ${STATE_LABELS[entry.state]}`);
            region.dataset.bodymapImprovement = entry.improvement_lift_key || '';
        });
    });
}

function popoverBodyForState(entry) {
    const fragments = [];
    if (entry.state === 'measured' && entry.filled.length > 0) {
        const list = entry.filled.map(lift => {
            if (lift.weight_kg !== undefined && lift.reps !== undefined) {
                if (lift.lift_key.startsWith('bodyweight_')) {
                    return `<li><strong>${lift.label}</strong> &mdash; ${lift.reps} reps (bodyweight)</li>`;
                }
                const oneRm = lift.estimated_1rm !== undefined ? ` &middot; 1RM &asymp; ${lift.estimated_1rm} kg` : '';
                return `<li><strong>${lift.label}</strong> &mdash; ${lift.weight_kg} kg &times; ${lift.reps}${oneRm}</li>`;
            }
            return `<li><strong>${lift.label}</strong></li>`;
        }).join('');
        fragments.push(`<ul class="profile-bodymap-popover-list">${list}</ul>`);
    } else if (entry.state === 'cross_muscle' && entry.filled.length > 0) {
        const fallback = entry.filled[0];
        fragments.push(`<p>Borrowing from <strong>${fallback.label}</strong> with the cross-muscle factor (0.6).</p>`);
    } else if (entry.state === 'cold_start_only') {
        fragments.push(`<p>No reference lift saved. Suggestions for this muscle use the population estimate from your demographics.</p>`);
    } else if (entry.state === 'not_assessed') {
        fragments.push(`<p>The estimator does not seed suggestions for this muscle.</p>`);
    }

    if (entry.improvement_lift_key) {
        fragments.push(
            `<p class="profile-bodymap-popover-action"><a href="#lift-${entry.improvement_lift_key}-weight" data-bodymap-jump="${entry.improvement_lift_key}">How to improve</a> &mdash; enter ${entry.improvement_lift_label}.</p>`
        );
    }
    return fragments.join('');
}

function showPopover(card, region, coverage) {
    const popover = card.querySelector('[data-bodymap-popover]');
    if (!popover) return;
    const muscle = region.dataset.bodymapMuscle;
    const label = region.dataset.bodymapLabel || muscle || 'Region';
    if (!muscle || !coverage[muscle]) {
        popover.querySelector('[data-popover-title]').textContent = label;
        popover.querySelector('[data-popover-state]').textContent = 'Not assessed';
        popover.querySelector('[data-popover-state]').dataset.state = 'not_assessed';
        popover.querySelector('[data-popover-body]').innerHTML = '<p>The estimator does not seed suggestions for this muscle.</p>';
        popover.hidden = false;
        return;
    }
    const entry = coverage[muscle];
    popover.querySelector('[data-popover-title]').textContent = label;
    const stateNode = popover.querySelector('[data-popover-state]');
    stateNode.textContent = STATE_LABELS[entry.state];
    stateNode.dataset.state = entry.state;
    popover.querySelector('[data-popover-body]').innerHTML = popoverBodyForState(entry);
    popover.hidden = false;
}

function hidePopover(card) {
    const popover = card.querySelector('[data-bodymap-popover]');
    if (popover) popover.hidden = true;
}

function attachPolygonInteractivity(card, stage, getCoverage) {
    const panes = stage.querySelectorAll('[data-bodymap-pane]');
    panes.forEach(pane => {
        const regions = pane.querySelectorAll('.muscle-region');
        regions.forEach(region => {
            if (region.dataset.bodymapBound === '1') return;
            region.dataset.bodymapBound = '1';
            const muscle = region.dataset.bodymapMuscle;
            if (!muscle) return;

            region.addEventListener('mouseenter', () => showPopover(card, region, getCoverage()));
            region.addEventListener('mouseleave', () => hidePopover(card));
            region.addEventListener('focus', () => showPopover(card, region, getCoverage()));
            region.addEventListener('blur', () => hidePopover(card));

            // Click → scroll to the matching reference-lift row.
            region.addEventListener('click', event => {
                event.preventDefault();
                const cov = getCoverage();
                const entry = cov[muscle];
                if (!entry) return;
                const target = entry.improvement_lift_key || entry.primary_lift_key;
                if (!target) return;
                const input = document.getElementById(`lift-${target}-weight`);
                if (input) {
                    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    try {
                        input.focus({ preventScroll: true });
                    } catch (_) {
                        input.focus();
                    }
                }
            });

            region.setAttribute('tabindex', '0');
        });
    });
}

function bodymapCoverageSnapshot() {
    const liftRows = liftRowsFromForm();
    const filledByKey = new Map(liftRows.map(r => [r.lift_key, r]));
    return computeMuscleCoverage(filledByKey);
}

function applyBodymapState(card, stage, coverage) {
    applyCoverageStateToPolygons(stage, coverage);
    // Mirror the state into the screen-reader summary list so AT users
    // see the same updates after live form changes.
    const srItems = card.querySelectorAll('[data-bodymap-sr-list] [data-sr-muscle]');
    srItems.forEach(node => {
        const muscle = node.dataset.srMuscle;
        const entry = coverage[muscle];
        if (!entry) return;
        node.dataset.srState = entry.state;
        const dd = node.querySelector('dd');
        if (!dd) return;
        if (entry.state === 'measured') {
            const count = entry.filled.length;
            dd.textContent = `Measured (${count} reference lift${count === 1 ? '' : 's'} saved)`;
        } else if (entry.state === 'cross_muscle') {
            const fallback = entry.filled[0];
            dd.textContent = `Inferred from ${fallback ? fallback.label : 'a related lift'} (cross-muscle fallback)`;
        } else if (entry.state === 'cold_start_only') {
            dd.textContent = 'Population estimate (no reference lift saved)';
        } else {
            dd.textContent = 'Not assessed';
        }
    });
}

let bodymapInitialized = false;

function renderBodymapCoverage() {
    const card = document.querySelector('[data-section="muscle coverage"]');
    if (!card) return;
    const stage = card.querySelector('[data-bodymap-svg]');
    if (!stage) return;
    const coverage = bodymapCoverageSnapshot();
    applyBodymapState(card, stage, coverage);
}

async function initializeBodymap() {
    if (bodymapInitialized) return;
    const card = document.querySelector('[data-section="muscle coverage"]');
    if (!card) return;
    const stage = card.querySelector('[data-bodymap-svg]');
    if (!stage) return;

    bodymapInitialized = true;

    let coverage = bodymapCoverageSnapshot();
    const getCoverage = () => coverage;

    await mountBodymapForSide(stage, 'front');
    await mountBodymapForSide(stage, 'back');
    applyCoverageStateToPolygons(stage, coverage);
    attachPolygonInteractivity(card, stage, getCoverage);

    // Side toggle.
    card.querySelectorAll('[data-bodymap-side]').forEach(button => {
        button.addEventListener('click', () => {
            const side = button.dataset.bodymapSide;
            BODYMAP_STATE.side = side;
            card.querySelectorAll('[data-bodymap-side]').forEach(other => {
                const isActive = other === button;
                other.classList.toggle('is-active', isActive);
                other.setAttribute('aria-pressed', String(isActive));
            });
            stage.querySelectorAll('[data-bodymap-pane]').forEach(pane => {
                pane.hidden = pane.dataset.bodymapPane !== side;
            });
            hidePopover(card);
        });
    });

    // Refresh polygon state whenever live coverage recomputes.
    const refresh = () => {
        coverage = bodymapCoverageSnapshot();
        applyBodymapState(card, stage, coverage);
    };
    document.getElementById('profile-lifts-form')?.addEventListener('input', refresh);
    document.getElementById('profile-lifts-form')?.addEventListener('change', refresh);

    // Hide popover when clicking outside.
    document.addEventListener('click', event => {
        if (!card.contains(event.target)) hidePopover(card);
    });
}

export function initializeUserProfile() {
    bindAutosaveForm('profile-demographics-form', profilePayload, '/api/user_profile');
    bindAutosaveForm('profile-lifts-form', liftPayload, '/api/user_profile/lifts');
    bindAutosaveForm(
        'profile-preferences-form',
        preferencesPayload,
        '/api/user_profile/preferences',
        { changeImmediate: true },
    );
    initializeCollapseToggles();
    bindInsightsAutoUpdate();
    initializeBodymap();
}

document.addEventListener('DOMContentLoaded', initializeUserProfile);
