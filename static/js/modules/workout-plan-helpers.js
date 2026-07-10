// Pure helpers for the workout plan page.
//
// Extracted verbatim from the page-local inline script in
// templates/workout_plan.html (Refactor Plan v3 WP3.2c). These are the three
// genuinely-pure computations behind the plan-generator preview UI: the volume
// slider colour class, the plan-preview summary strings, and the per-environment
// equipment list. DOM-free and side-effect-free so they can be unit-tested under
// the node-environment Vitest runner. The DOM wrappers in workout-plan-page.js
// call these and keep their branching byte-identical to the original inline code.

// Temperature colour class for the volume-scale value display.
export function volumeColorClass(value) {
    const v = parseFloat(value);
    if (v <= 0.8) {
        return 'volume-value-blue';
    } else if (v <= 1.1) {
        return 'volume-value-green';
    } else if (v <= 1.5) {
        return 'volume-value-yellow';
    } else if (v <= 1.7) {
        return 'volume-value-orange';
    } else {
        return 'volume-value-red';
    }
}

// Preview summary (routines / rep range / base set count) for the generator form.
export function planPreviewData(trainingDays, goal, volumeScaleVal) {
    let routines = 'Full Body: Workout A';
    if (trainingDays === '2') {
        routines = '2 Days Split: Workout A, Workout B';
    } else if (trainingDays === '3') {
        routines = '3 Days Split: Workout A, Workout B, Workout C';
    } else if (trainingDays === '4') {
        routines = 'Upper Lower: Upper 1, Lower 1, Upper 2, Lower 2';
    } else if (trainingDays === '5') {
        routines = '5 Days Split: Day 1, Day 2, Day 3, Day 4, Day 5';
    }

    let repRange = '6-10, 10-15';
    if (goal === 'strength') {
        repRange = '3-6, 6-10';
    } else if (goal === 'general') {
        repRange = '5-8, 8-12';
    }

    const baseSets = Math.round(18 * parseFloat(volumeScaleVal));

    return { routines, repRange, baseSets };
}

// Equipment available in each training environment.
export function equipmentForEnvironment(environment) {
    const gymEquipment = ['Barbell', 'Dumbbells', 'Cables', 'Machine', 'Bodyweight', 'Kettlebells',
                         'Smith_Machine', 'Trapbar', 'Band', 'Trx', 'Plate', 'Medicine_Ball'];
    const homeEquipment = ['Dumbbells', 'Bodyweight', 'Band', 'Kettlebells', 'Trx', 'Medicine_Ball'];

    return environment === 'gym' ? gymEquipment : homeEquipment;
}
