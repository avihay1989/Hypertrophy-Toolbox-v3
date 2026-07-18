import { initializeExerciseImagePreview } from './exercise-image-preview.js';
import { initializeProfileForms } from './user-profile-forms.js';
import { bindInsightsAutoUpdate } from './user-profile-insights.js';
import {
    initializeBodymap,
    renderBodymapCoverage,
} from './user-profile-bodymap.js';
import {
    bindCalibrationSettings,
    bindFatigueContextSettings,
} from './user-profile-settings.js';
import { bindCalibrationReview } from './user-profile-calibration-review.js';

initializeExerciseImagePreview();

function initializeUserProfile() {
    initializeProfileForms();
    bindInsightsAutoUpdate(renderBodymapCoverage);
    bindCalibrationSettings();
    bindCalibrationReview();
    bindFatigueContextSettings();
    initializeBodymap();
}

document.addEventListener('DOMContentLoaded', initializeUserProfile);
