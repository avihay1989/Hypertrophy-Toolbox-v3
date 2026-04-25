export function notifyVolumeAffectingPlanChange(reason) {
    document.dispatchEvent(new CustomEvent('workout-plan:volume-affecting-change', {
        detail: { reason }
    }));
}
