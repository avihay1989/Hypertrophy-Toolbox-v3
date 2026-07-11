// Shared mutable state for the workout plan page (Refactor Plan v3 WP3.3).
//
// These four values were previously module-level `let`/`const` bindings inside
// workout-plan.js, mutated across many functions (routine-tab filtering, the
// exercise cache, superset selection, and the per-render superset colour map).
// They are consolidated here as a single named state object so the later
// feature split (WP3.4a `state.js`) has one explicit seam to inject, instead of
// module-private variables that every extracted feature module would have to
// reach back into.
//
// Design note — state module vs. dependency object: the workout plan page is a
// single instance (one page, one table), so there is never more than one state
// bag; a shared singleton object is enough and keeps every existing function
// signature intact (app.js calls `fetchWorkoutPlan()`, `handleAddExercise(e)`,
// etc. with fixed arities, so threading a deps parameter through would force
// wrapper churn at those boundaries). Property access on this object preserves
// the original semantics exactly: reassignment (`state.currentRoutineTabFilter =
// 'all'`) matches the old `let` reassignment, and in-place mutation
// (`state.selectedExerciseIds.add(id)`) matches the old `Set`/`Map` mutation.
export const workoutPlanState = {
    // Which routine tab is active ('all' or a routine name).
    currentRoutineTabFilter: 'all',
    // Every exercise returned by the last /get_workout_plan fetch (unfiltered).
    allExercisesCache: [],
    // Exercise ids currently checked for superset link/unlink.
    selectedExerciseIds: new Set(),
    // Maps a superset_group to its colour index (1-4), rebuilt per table render.
    supersetColorMap: new Map(),
};
