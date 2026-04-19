import { showToast } from './modules/toast.js';
import { fetchWorkoutPlan, handleRoutineSelection, updateExerciseDetails, updateExerciseForm, handleAddExercise } from './modules/workout-plan.js';
import { initializeWorkoutLog, deleteWorkoutLog, updateScoredValue, handleDateChange, importFromWorkoutPlan, confirmClearWorkoutLog } from './modules/workout-log.js';
import { initializeFilters, initializeAdvancedFilters, initializeSearchFilter, initializeFilterKeyboardEvents } from './modules/filters.js';
import { addExercise, removeExercise, clearWorkoutPlan } from './modules/exercises.js';
import { initializeUIHandlers, initializeFormHandlers, initializeTooltips, initializeDropdowns, handleTableSort } from './modules/ui-handlers.js';
import { exportToExcel, exportToWorkoutLog, exportSummary } from './modules/exports.js';
import { initializeWorkoutPlanHandlers, updateWorkoutPlanUI } from './modules/workout-plan.js';
import { initializeWorkoutLogFilters } from './modules/workout-log.js';
import { initializeDataTables, initializeCharts } from './modules/ui-handlers.js';
import { 
    fetchWeeklySummary,
    fetchSessionSummary 
} from './modules/summary.js';
import { 
    updateProgressionDate,
    updateProgressionStatus 
} from './modules/workout-log.js';
import { validateScoredValue } from './modules/workout-log.js';
import { 
    checkProgressionStatus,
    initializeProgressionChecks 
} from './modules/workout-log.js';
import { initializeNavHighlighting } from './modules/navbar.js';
import { initializeNavbar } from './modules/navbar.js';
import { initializeNavbarEnhancements } from './modules/navbar-enhancements.js';
import { initializeProgressionPlan } from './modules/progression-plan.js';
import { initializeVolumeSplitter } from './modules/volume-splitter.js';
import { initializeWorkoutDropdowns } from './modules/workout-dropdowns.js';
import { initializeWorkoutControlsAnimation } from './modules/workout-controls-animation.js';
import { initializeRoutineCascade } from './modules/routine-cascade.js';
import { initializeProgramBackup, showAutoBackupBanner } from './modules/program-backup.js';

const APP_DEBUG = false;
const appDebugLog = (...args) => {
    if (APP_DEBUG) {
        console.log(...args);
    }
};

// Make certain functions globally available
window.addExercise = addExercise;
window.removeExercise = removeExercise;
window.clearWorkoutPlan = clearWorkoutPlan;
window.exportToExcel = exportToExcel;
window.exportToWorkoutLog = exportToWorkoutLog;
window.exportSummary = exportSummary;
window.deleteWorkoutLog = deleteWorkoutLog;
window.updateExerciseDetails = updateExerciseDetails;
window.updateExerciseForm = updateExerciseForm;
window.updateProgressionDate = updateProgressionDate;
window.updateProgressionStatus = updateProgressionStatus;
window.validateScoredValue = validateScoredValue;
window.checkProgressionStatus = checkProgressionStatus;
window.handleAddExercise = handleAddExercise;
window.updateScoredValue = updateScoredValue;
window.handleDateChange = handleDateChange;
window.importFromWorkoutPlan = importFromWorkoutPlan;
window.confirmClearWorkoutLog = confirmClearWorkoutLog;
window.showAutoBackupBanner = showAutoBackupBanner;

// Generate Starter Plan function
window.generateStarterPlan = async function() {
    const submitBtn = document.getElementById('generatePlanSubmit');
    const originalText = submitBtn.innerHTML;
    
    try {
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
        
        // Gather form values
        const trainingDays = parseInt(document.getElementById('gen-training-days').value);
        const environment = document.getElementById('gen-environment').value;
        const experienceLevel = document.getElementById('gen-experience').value;
        const goal = document.getElementById('gen-goal').value;
        const volumeScale = parseFloat(document.getElementById('gen-volume-scale').value);
        const overwrite = document.getElementById('gen-overwrite').checked;
        
        // Movement restrictions
        const movementRestrictions = {};
        if (document.getElementById('gen-no-overhead').checked) {
            movementRestrictions.no_overhead_press = true;
        }
        if (document.getElementById('gen-no-deadlift').checked) {
            movementRestrictions.no_deadlift = true;
        }
        
        // Equipment whitelist - collect all checked equipment
        const equipmentWhitelist = [];
        document.querySelectorAll('.equipment-check:checked').forEach(checkbox => {
            equipmentWhitelist.push(checkbox.value);
        });
        
        // Validate at least one equipment is selected
        if (equipmentWhitelist.length === 0) {
            showToast('Please select at least one equipment type.', 'warning');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
            return;
        }
        
        // Priority muscles - collect selected muscles from muscle selector (max 2)
        let priorityMuscles = [];
        if (window.muscleSelector) {
            priorityMuscles = window.muscleSelector.getSelectedMusclesForBackend();
            // Limit to 2 priority muscles
            if (priorityMuscles.length > 2) {
                showToast('Maximum 2 priority muscles allowed. Using first 2 selected.', 'warning');
                priorityMuscles = priorityMuscles.slice(0, 2);
            }
        }
        
        // Make API request
        const response = await fetch('/generate_starter_plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                training_days: trainingDays,
                environment: environment,
                experience_level: experienceLevel,
                goal: goal,
                volume_scale: volumeScale,
                overwrite: overwrite,
                movement_restrictions: Object.keys(movementRestrictions).length > 0 ? movementRestrictions : null,
                equipment_whitelist: equipmentWhitelist,
                priority_muscles: priorityMuscles.length > 0 ? priorityMuscles : null,
                persist: true
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.data) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('generatePlanModal'));
            modal.hide();
            
            // Show success message
            const routines = Object.keys(result.data.routines).join(', ');
            const totalExercises = result.data.total_exercises;
            showToast(`Plan generated successfully! Created routines: ${routines} with ${totalExercises} exercises.`, 'success');
            
            // Refresh the workout plan table
            if (typeof fetchWorkoutPlan === 'function') {
                fetchWorkoutPlan();
            } else {
                // Fallback: reload the page
                window.location.reload();
            }
        } else {
            const errorMsg = result.message || 'Failed to generate plan';
            showToast(errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error generating plan:', error);
        showToast('Error generating plan. Please try again.', 'error');
    } finally {
        // Restore button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
};

// Initialize navbar
initializeNavbar();
initializeNavbarEnhancements();

// Initialize workout plan dropdowns
initializeWorkoutDropdowns();

// Page initializer functions
function initializeHomePage() {
    appDebugLog('Initializing Home page');
    return {
        cleanup: () => {
            appDebugLog('Cleaning up Home page');
        }
    };
}

function initializeWeeklySummary() {
    appDebugLog('Initializing Weekly Summary page');
    initializeCharts();
    fetchWeeklySummary();
    return {
        cleanup: () => {
            appDebugLog('Cleaning up Weekly Summary page');
        }
    };
}

function initializeSessionSummary() {
    appDebugLog('Initializing Session Summary page');
    initializeCharts();
    fetchSessionSummary();
    return {
        cleanup: () => {
            appDebugLog('Cleaning up Session Summary page');
        }
    };
}

function initializeWorkoutPlan() {
    appDebugLog('Initializing Workout Plan page');
    initializeFilters();
    initializeFilterKeyboardEvents();
    initializeAdvancedFilters();
    initializeSearchFilter();
    initializeRoutineCascade(); // Initialize cascading routine selector
    handleRoutineSelection();
    initializeWorkoutPlanHandlers();
    initializeWorkoutControlsAnimation();
    // fetchWorkoutPlan is already called inside initializeWorkoutPlanHandlers
    return {
        cleanup: () => {
            appDebugLog('Cleaning up Workout Plan page');
        }
    };
}

function initializeProgressionPage() {
    appDebugLog('Initializing Progression Plan page');
    initializeProgressionPlan();
}

const pageInitializers = {
    '/': initializeHomePage,
    '/workout_plan': initializeWorkoutPlan,
    '/workout_log': initializeWorkoutLog,
    '/weekly_summary': initializeWeeklySummary,
    '/session_summary': initializeSessionSummary,
    '/progression': initializeProgressionPage,
    '/volume_splitter': initializeVolumeSplitter
};

document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;

    // Common initializations
    const commonInit = () => {
        initializeUIHandlers();
        initializeFormHandlers();
        initializeTooltips();
        initializeDropdowns();
        handleTableSort();
        initializeProgramBackup();
    };

    // Initialize common elements
    commonInit();

    // Initialize page-specific functionality
    const initializer = pageInitializers[currentPath];
    if (initializer) {
        initializer();
    } else {
        appDebugLog(`No specific initialization for path: ${currentPath}`);
    }
});

function initializeModules() {
    const path = window.location.pathname;
    appDebugLog(`Initializing modules for path: ${path}`);

    switch (path) {
        // ... other cases ...
        case '/progression':
            appDebugLog('Initializing Progression Plan page');
            initializeProgressionPage();
            break;
    }
}

// Ensure erase data button only exists on welcome page
document.addEventListener('DOMContentLoaded', function() {
    // Remove any errant erase data buttons outside welcome page
    if (!document.querySelector('.welcome-container')) {
        const errantButtons = document.querySelectorAll('#eraseDataBtn, .erase-data-btn');
        errantButtons.forEach(button => button.remove());
    }
});
