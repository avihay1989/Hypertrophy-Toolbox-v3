// Workout plan execution-style picker module (Refactor Plan v3 WP3.4d).
//
// Mechanical feature-split extracted from workout-plan.js: the execution-style
// options cache and the AMRAP/EMOM/standard picker overlay. Behavior is
// preserved exactly — this is a move-only change.
//
// showExecutionStylePicker refreshes the plan after saving, which is the
// orchestration fetchWorkoutPlan() that stays in workout-plan.js. Rather than
// import that back — which would create a circular import — workout-plan.js
// injects it once at load via configureExecutionStyle(). The default is a no-op
// so a bare call before configuration cannot throw.
import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';
import { buildExecutionStylePayload } from './workout-plan-helpers.js';

const execDeps = {
    refreshPlan: () => {},  // re-fetch + re-render the plan after a save
};

/**
 * Inject the plan-refresh callback showExecutionStylePicker depends on.
 * Called once by workout-plan.js at module load.
 * @param {Partial<typeof execDeps>} deps
 */
export function configureExecutionStyle(deps) {
    Object.assign(execDeps, deps);
}

let executionStyleOptions = null;

/**
 * Fetches execution style options from the API (cached)
 */
async function getExecutionStyleOptions() {
    if (executionStyleOptions) return executionStyleOptions;
    try {
        const response = await api.get('/api/execution_style_options');
        executionStyleOptions = response.data || response;
        return executionStyleOptions;
    } catch (error) {
        console.error('Failed to load execution style options:', error);
        return null;
    }
}

/**
 * Shows execution style picker for an exercise
 * @param {number} exerciseId - The exercise ID
 * @param {Object} currentExercise - Current exercise data from cache
 */
export async function showExecutionStylePicker(exerciseId, currentExercise) {
    const options = await getExecutionStyleOptions();
    if (!options) {
        showToast('Failed to load execution style options', true);
        return;
    }
    
    // Remove any existing picker through its own cleanup path so its
    // document-level outside-click listener is detached too
    const existingPicker = document.querySelector('.execution-style-picker');
    if (existingPicker) {
        if (typeof existingPicker._closePicker === 'function') {
            existingPicker._closePicker();
        } else {
            existingPicker.remove();
        }
    }
    
    const currentStyle = currentExercise?.execution_style || 'standard';
    const timeCap = currentExercise?.time_cap_seconds || 60;
    const emomInterval = currentExercise?.emom_interval_seconds || 60;
    const emomRounds = currentExercise?.emom_rounds || 5;
    
    // Create picker element
    const picker = document.createElement('div');
    picker.className = 'execution-style-picker frame-calm-glass';
    picker.innerHTML = `
        <div class="execution-picker-content">
            <div class="execution-picker-header">
                <h6><i class="fas fa-stopwatch me-2"></i>Execution Style</h6>
                <button class="btn-close btn-close-picker" aria-label="Close"></button>
            </div>
            <div class="execution-picker-body">
                <div class="execution-style-options">
                    <label class="execution-option ${currentStyle === 'standard' ? 'active' : ''}">
                        <input type="radio" name="exec-style-${exerciseId}" value="standard" ${currentStyle === 'standard' ? 'checked' : ''}>
                        <span class="option-icon"><i class="fas fa-dumbbell"></i></span>
                        <span class="option-text">
                            <strong>Standard</strong>
                            <small>Traditional sets with rest</small>
                        </span>
                    </label>
                    <label class="execution-option ${currentStyle === 'amrap' ? 'active' : ''}">
                        <input type="radio" name="exec-style-${exerciseId}" value="amrap" ${currentStyle === 'amrap' ? 'checked' : ''}>
                        <span class="option-icon"><i class="fas fa-stopwatch"></i></span>
                        <span class="option-text">
                            <strong>AMRAP</strong>
                            <small>As Many Reps As Possible</small>
                        </span>
                    </label>
                    <label class="execution-option ${currentStyle === 'emom' ? 'active' : ''}">
                        <input type="radio" name="exec-style-${exerciseId}" value="emom" ${currentStyle === 'emom' ? 'checked' : ''}>
                        <span class="option-icon"><i class="fas fa-clock"></i></span>
                        <span class="option-text">
                            <strong>EMOM</strong>
                            <small>Every Minute On the Minute</small>
                        </span>
                    </label>
                </div>
                
                <div class="execution-params amrap-params" style="display: ${currentStyle === 'amrap' ? 'block' : 'none'}">
                    <label class="param-label">
                        <span>Time Cap (seconds)</span>
                        <input type="number" class="form-control form-control-sm input-calm-inset" id="time-cap-${exerciseId}"
                               value="${timeCap}" min="10" max="600" step="5">
                    </label>
                </div>
                
                <div class="execution-params emom-params" style="display: ${currentStyle === 'emom' ? 'block' : 'none'}">
                    <label class="param-label">
                        <span>Interval (seconds)</span>
                        <input type="number" class="form-control form-control-sm input-calm-inset" id="emom-interval-${exerciseId}"
                               value="${emomInterval}" min="15" max="180" step="5">
                    </label>
                    <label class="param-label">
                        <span>Rounds</span>
                        <input type="number" class="form-control form-control-sm input-calm-inset" id="emom-rounds-${exerciseId}"
                               value="${emomRounds}" min="1" max="20">
                    </label>
                </div>
            </div>
            <div class="execution-picker-footer">
                <button class="btn btn-sm btn-outline-secondary btn-calm-ghost btn-cancel-exec">Cancel</button>
                <button class="btn btn-sm btn-primary btn-calm-primary btn-save-exec" data-exercise-id="${exerciseId}">
                    <i class="fas fa-check me-1"></i>Apply
                </button>
            </div>
        </div>
    `;
    
    // Position picker near the clicked cell
    const cell = document.querySelector(`.execution-style-cell[data-exercise-id="${exerciseId}"]`);
    document.body.appendChild(picker);
    
    if (cell) {
        const rect = cell.getBoundingClientRect();
        const pickerHeight = picker.offsetHeight || 350; // Estimated height if not yet rendered
        const viewportHeight = window.innerHeight;
        const spaceBelow = viewportHeight - rect.bottom;
        const spaceAbove = rect.top;
        
        picker.style.position = 'fixed';
        picker.style.left = `${Math.max(10, rect.left - 100)}px`;
        picker.style.zIndex = '1050';
        
        // Position above if not enough space below, otherwise position below
        if (spaceBelow < pickerHeight && spaceAbove > spaceBelow) {
            picker.style.bottom = `${viewportHeight - rect.top + 5}px`;
            picker.style.top = 'auto';
            picker.classList.add('picker-dropup');
        } else {
            picker.style.top = `${rect.bottom + 5}px`;
            picker.style.bottom = 'auto';
        }
    }
    
    // Single close path — every way of dismissing the picker (Close, Cancel,
    // Save, outside click, replacement by a newly opened picker) must go
    // through closePicker() so the document-level outside-click listener
    // never outlives the picker element.
    let outsideClickTimer = null;
    const closeOnOutside = (e) => {
        if (!picker.contains(e.target) && !e.target.closest('.execution-style-cell')) {
            closePicker();
        }
    };
    const closePicker = () => {
        clearTimeout(outsideClickTimer);
        document.removeEventListener('click', closeOnOutside);
        picker.remove();
    };
    picker._closePicker = closePicker;

    // Event listeners
    const radios = picker.querySelectorAll('input[type="radio"]');
    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            picker.querySelectorAll('.execution-option').forEach(opt => opt.classList.remove('active'));
            radio.closest('.execution-option').classList.add('active');
            
            const style = radio.value;
            picker.querySelector('.amrap-params').style.display = style === 'amrap' ? 'block' : 'none';
            picker.querySelector('.emom-params').style.display = style === 'emom' ? 'block' : 'none';
        });
    });
    
    picker.querySelector('.btn-close-picker').addEventListener('click', () => closePicker());
    picker.querySelector('.btn-cancel-exec').addEventListener('click', () => closePicker());
    
    picker.querySelector('.btn-save-exec').addEventListener('click', async () => {
        const selectedStyle = picker.querySelector(`input[name="exec-style-${exerciseId}"]:checked`).value;
        const timeCap = parseInt(picker.querySelector(`#time-cap-${exerciseId}`).value);
        const emomInterval = parseInt(picker.querySelector(`#emom-interval-${exerciseId}`).value);
        const emomRounds = parseInt(picker.querySelector(`#emom-rounds-${exerciseId}`).value);
        const payload = buildExecutionStylePayload(exerciseId, selectedStyle, { timeCap, emomInterval, emomRounds });
        
        try {
            const result = await api.post('/api/execution_style', payload);
            showToast(`Execution style set to ${selectedStyle.toUpperCase()}`);
            closePicker();
            // Refresh the workout plan to show updated badge
            await execDeps.refreshPlan();
        } catch (error) {
            showToast(error.message || 'Failed to update execution style', true);
        }
    });
    
    // Close on outside click (delayed so the click that opened the picker
    // does not immediately close it). closePicker() cancels this timer if the
    // picker is dismissed before the listener is ever attached.
    outsideClickTimer = setTimeout(() => {
        document.addEventListener('click', closeOnOutside);
    }, 100);
}
