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

export {
    ACCURACY_MAJOR_MUSCLE_GROUPS,
    COHORT_AGE_YEARS,
    COHORT_BODYWEIGHT_KG,
    COHORT_HEIGHT_CM,
    COLD_START_CANONICAL_COMPOUND,
    COLD_START_RATIOS,
    HIGH_IMPACT_LIFT_PRIORITY,
    bandPillLabel,
    classificationFromForm,
    classifyExperienceTier,
    coldStart1rm,
    computeAccuracyBand,
    epley1rm,
    experienceMultiplier,
    formatYears,
    isLiftFilled,
    liftRowsFromForm,
    nextTierMultiplier,
    tierLabel,
};
