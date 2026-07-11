// Workout plan media integration (Refactor Plan v3 WP3.4h).
//
// Keeps the plan-specific thumbnail, image-preview, and reference-video glue
// together while the shared media implementations remain reusable by other
// pages (notably Workout Log and User Profile).
import { escapeHtml, resolveExerciseMediaSrc } from './exercise-helpers.js';
import { initializeExerciseImagePreview } from './exercise-image-preview.js';
import { buildPlayButton } from './exercise-video-modal.js';

export function initializeWorkoutPlanMedia() {
    initializeExerciseImagePreview();
}

export function buildExerciseThumbnailHtml(exercise) {
    const exerciseName = exercise.exercise || 'N/A';
    const mediaSrc = resolveExerciseMediaSrc(exercise.media_path);

    return mediaSrc
        ? `<img class="exercise-thumbnail" src="${escapeHtml(mediaSrc)}" alt="${escapeHtml(exerciseName)} reference" data-preview-label="${escapeHtml(exerciseName)}" loading="lazy" width="32" height="32" tabindex="0">`
        : '';
}

export function appendExerciseVideoButton(row, exercise) {
    const cellContent = row.querySelector('.exercise-cell-content');
    if (cellContent) {
        const playBtn = buildPlayButton({
            videoId: exercise.youtube_video_id,
            exerciseName: exercise.exercise || '',
        });
        cellContent.appendChild(playBtn);
    }
}
