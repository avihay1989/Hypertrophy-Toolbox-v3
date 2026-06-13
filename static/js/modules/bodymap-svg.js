// Shared bodymap-SVG helpers for the Profile-page coverage viewer.
//
// MuscleMap anatomy art (melihcolpan/MuscleMap, MIT), generated into
// static/bodymaps/hypertrophy-advanced/. Regions ship pre-canonicalized with
// `data-canonical-muscles="<key>"`.
const BODYMAP_SVG_PATHS = {
    front: '/static/bodymaps/hypertrophy-advanced/body_anterior.svg',
    back: '/static/bodymaps/hypertrophy-advanced/body_posterior.svg',
};

const svgCache = new Map();

export async function loadBodymapSvg(side) {
    const path = BODYMAP_SVG_PATHS[side];
    if (!path) throw new Error(`Unknown body side: ${side}`);
    if (svgCache.has(path)) return svgCache.get(path);
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Failed to load SVG: ${path}`);
    const text = await response.text();
    svgCache.set(path, text);
    return text;
}

// Backend-muscle → ordered list of reference-lift slugs, mirroring
// `MUSCLE_TO_KEY_LIFT` in `utils/profile_estimator.py`. Used by the JS
// coverage layer to recompute states from live form values without a
// round-trip. KEEP IN SYNC with the Python source of truth.
export const COVERAGE_MUSCLE_CHAIN = {
    'Chest': [
        'barbell_bench_press',
        'dumbbell_bench_press',
        'incline_bench_press',
        'smith_machine_bench_press',
        'machine_chest_press',
        'dumbbell_fly',
    ],
    'Quadriceps': [
        'barbell_back_squat',
        'leg_press',
        'dumbbell_squat',
        'dumbbell_lunge',
        'dumbbell_step_up',
        'bulgarian_split_squat',
        'reverse_lunge',
        'romanian_deadlift',
        'conventional_deadlift',
    ],
    'Hamstrings': [
        'leg_curl',
        'romanian_deadlift',
        'conventional_deadlift',
        'stiff_leg_deadlift',
        'good_morning',
        'seated_good_morning',
        'single_leg_rdl',
        'cable_pull_through',
        'sumo_deadlift',
    ],
    'Gluteus Maximus': [
        'hip_thrust',
        'barbell_glute_bridge',
        'b_stance_hip_thrust',
        'romanian_deadlift',
        'conventional_deadlift',
        'sumo_deadlift',
        'barbell_back_squat',
        'bulgarian_split_squat',
        'dumbbell_squat',
        'dumbbell_lunge',
        'reverse_lunge',
        'dumbbell_step_up',
        'cable_pull_through',
        'cable_kickback',
        'machine_hip_abduction',
    ],
    'Upper Back': ['barbell_row', 'machine_row', 'weighted_pullups'],
    'Lower Back': [
        'romanian_deadlift',
        'conventional_deadlift',
        'sumo_deadlift',
        'back_extension',
        'loaded_back_extension',
        'reverse_hyperextension',
        'good_morning',
        'seated_good_morning',
        'jefferson_curl',
    ],
    'Trapezius': ['barbell_shrugs', 'barbell_row'],
    'Front-Shoulder': [
        'military_press',
        'dumbbell_shoulder_press',
        'arnold_press',
        'machine_shoulder_press',
        'barbell_bench_press',
    ],
    'Rear-Shoulder': ['face_pulls', 'barbell_row'],
    'Biceps': [
        'barbell_bicep_curl',
        'dumbbell_curl',
        'preacher_curl',
        'incline_dumbbell_curl',
    ],
    'Triceps': [
        'triceps_extension',
        'skull_crusher',
        'jm_press',
        'weighted_dips',
        'barbell_bench_press',
    ],
    'Calves': [
        'standing_calf_raise',
        'seated_calf_raise',
        'leg_press_calf_raise',
        'smith_machine_calf_raise',
        'single_leg_standing_calf_raise',
        'donkey_calf_raise',
    ],
    'Abs/Core': ['cable_crunch', 'machine_crunch', 'weighted_crunch'],
    'Obliques': ['cable_woodchop', 'side_bend'],
};

// Friendly labels for surfacing reference-lift names in popovers. Mirrors
// `KEY_LIFT_LABELS` in `utils/profile_estimator.py`.
export const COVERAGE_LIFT_LABELS = {
    barbell_bench_press: 'Barbell Bench Press',
    dumbbell_bench_press: 'Dumbbell Bench Press',
    incline_bench_press: 'Incline Bench Press',
    smith_machine_bench_press: 'Smith Machine Bench Press',
    machine_chest_press: 'Machine Chest Press',
    dumbbell_fly: 'Dumbbell Fly',
    barbell_row: 'Barbell Row',
    machine_row: 'Machine Row',
    weighted_pullups: 'Weighted Pull-ups',
    bodyweight_pullups: 'Bodyweight Pull-ups',
    bodyweight_chinups: 'Bodyweight Chin-ups',
    military_press: 'Military / Shoulder Press',
    dumbbell_shoulder_press: 'Dumbbell Shoulder Press',
    machine_shoulder_press: 'Machine Shoulder Press',
    arnold_press: 'Arnold Press',
    dumbbell_lateral_raise: 'Dumbbell Lateral Raise',
    face_pulls: 'Face Pulls',
    barbell_shrugs: 'Barbell Shrugs',
    barbell_bicep_curl: 'Barbell Bicep Curl',
    dumbbell_curl: 'Dumbbell Curl',
    preacher_curl: 'Preacher Curl (EZ Bar)',
    incline_dumbbell_curl: 'Incline Dumbbell Curl',
    triceps_extension: 'Triceps Extension',
    skull_crusher: 'Skull Crusher (EZ Bar / Barbell)',
    jm_press: 'JM Press',
    weighted_dips: 'Weighted Dips',
    bodyweight_dips: 'Bodyweight Dips',
    barbell_back_squat: 'Barbell Back Squat',
    leg_press: 'Leg Press',
    leg_extension: 'Leg Extension',
    leg_curl: 'Leg Curl',
    dumbbell_squat: 'Dumbbell Squat',
    dumbbell_lunge: 'Dumbbell Lunge',
    dumbbell_step_up: 'Dumbbell Step-Up',
    hip_thrust: 'Hip Thrust',
    romanian_deadlift: 'Romanian Deadlift',
    conventional_deadlift: 'Conventional Deadlift',
    stiff_leg_deadlift: 'Stiff-Leg Deadlift',
    good_morning: 'Good Morning',
    single_leg_rdl: 'Single-Leg RDL',
    standing_calf_raise: 'Standing Calf Raise',
    seated_calf_raise: 'Seated Calf Raise',
    leg_press_calf_raise: 'Leg Press Calf Raise',
    smith_machine_calf_raise: 'Smith Machine Calf Raise',
    single_leg_standing_calf_raise: 'Single-Leg Standing Calf Raise',
    donkey_calf_raise: 'Donkey Calf Raise',
    machine_hip_abduction: 'Machine Hip Abduction',
    barbell_glute_bridge: 'Barbell Glute Bridge',
    cable_pull_through: 'Cable Pull-Through',
    bulgarian_split_squat: 'Bulgarian Split Squat',
    b_stance_hip_thrust: 'B-Stance Hip Thrust',
    reverse_lunge: 'Reverse Lunge',
    sumo_deadlift: 'Sumo Deadlift',
    cable_kickback: 'Cable Kickback',
    cable_crunch: 'Cable Crunch',
    machine_crunch: 'Machine Crunch',
    weighted_crunch: 'Weighted Crunch',
    cable_woodchop: 'Cable Woodchop',
    side_bend: 'Side Bend',
    back_extension: 'Back Extension',
    loaded_back_extension: 'Loaded 45° Back Extension',
    reverse_hyperextension: 'Reverse Hyperextension',
    seated_good_morning: 'Seated Good Morning',
    jefferson_curl: 'Jefferson Curl',
};

// MuscleMap region key → backend coverage muscle(s).
//
// Keys mirror the `data-canonical-muscles` values in
// `static/bodymaps/hypertrophy-advanced/body_{anterior,posterior}.svg`. Values
// are backend muscle names from `COVERAGE_MUSCLE_CHAIN` (above) /
// `BODYMAP_MUSCLE_KEYS` (Python). An empty array means "no coverage chain
// exists for this region" (e.g. forearms, neck, adductors) — the polygon still
// renders but in the `not_assessed` state. The lat-wing region (`lats`) is
// mapped to Upper Back coverage, the only back-width chain that exists.
const CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES = {
    // Anterior (front)
    'chest': ['Chest'],
    'front-deltoid': ['Front-Shoulder'],
    'biceps': ['Biceps'],
    'triceps': ['Triceps'],
    'forearms': [],
    'abs': ['Abs/Core'],
    'obliques': ['Obliques'],
    'quadriceps': ['Quadriceps'],
    'adductors': [],
    'neck': [],
    'calves': ['Calves'],
    // Posterior (back)
    'trapezius': ['Trapezius'],
    'rear-deltoid': ['Rear-Shoulder'],
    'lats': ['Upper Back'],
    'lower-back': ['Lower Back'],
    'gluteal': ['Gluteus Maximus'],
    'hamstring': ['Hamstrings'],
};

// Friendly labels for each backend coverage muscle, used by the annotator.
const COVERAGE_MUSCLE_LABELS = {
    'Chest': 'Chest',
    'Front-Shoulder': 'Front Delts',
    'Biceps': 'Biceps',
    'Triceps': 'Triceps',
    'Abs/Core': 'Abs',
    'Obliques': 'Obliques',
    'Quadriceps': 'Quadriceps',
    'Calves': 'Calves',
    'Trapezius': 'Traps',
    'Rear-Shoulder': 'Rear Delts',
    'Upper Back': 'Upper Back',
    'Lower Back': 'Lower Back',
    'Gluteus Maximus': 'Glutes',
    'Hamstrings': 'Hamstrings',
};

// Annotate every `<path class="muscle-region">` inside a MuscleMap SVG with the
// `data-bodymap-muscle` / `data-bodymap-label` attributes the Profile coverage
// applier expects. Regions carry `data-canonical-muscles="<key>"`; we map those
// through `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES` to the backend coverage
// muscle(s) the region represents. The comma-joined `data-bodymap-muscles`
// (plural) supports multi-muscle regions; the singular `data-bodymap-muscle`
// keeps a representative name so selectors like `[data-bodymap-muscle="Chest"]`
// still match. Idempotent.
export function annotateBodymapPolygons(svgRoot, side) {
    void side; // reserved for future side-specific annotation differences
    svgRoot.querySelectorAll('.muscle-region[data-canonical-muscles]').forEach(region => {
        const simpleKeys = region.dataset.canonicalMuscles
            .split(',')
            .map(k => k.trim())
            .filter(Boolean);
        const muscles = [];
        for (const key of simpleKeys) {
            const mapped = CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES[key];
            if (!mapped) continue;
            for (const muscle of mapped) {
                if (!muscles.includes(muscle)) muscles.push(muscle);
            }
        }
        if (muscles.length === 0) {
            region.dataset.coverageState = 'not_assessed';
            const labels = simpleKeys.map(k => COVERAGE_MUSCLE_LABELS[k] || k).join(' / ');
            region.dataset.bodymapLabel = labels || 'Region';
            return;
        }
        region.dataset.bodymapMuscle = muscles[0];
        if (muscles.length > 1) {
            region.dataset.bodymapMuscles = muscles.join(',');
        }
        region.dataset.bodymapLabel = muscles
            .map(m => COVERAGE_MUSCLE_LABELS[m] || m)
            .join(' / ');
    });
}

