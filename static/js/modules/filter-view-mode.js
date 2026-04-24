/**
 * Filter View Mode Module
 * 
 * Manages global Simple/Advanced toggle for muscle group displays across:
 * - Filter dropdowns (Primary, Secondary, Tertiary Muscle Group, Isolated Muscles)
 * - Table columns (Primary Muscle, Secondary Muscle, Tertiary Muscle, Isolated Muscles)
 * - Weekly Summary and Session Summary pages
 * 
 * Simple Mode: User-friendly groupings (biceps, triceps, chest, etc.)
 * Advanced Mode: Anatomical precision (long-head-bicep, anterior-deltoid, etc.)
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'hypertrophy_filter_view_mode';
    const DEBUG = false;
    
    const log = (...args) => DEBUG && console.log('[FilterViewMode]', ...args);

    // =========================================================================
    // MUSCLE MAPPING DEFINITIONS
    // =========================================================================

    /**
     * Simple muscle names (user-friendly) with display labels
     * Front body muscles come first, then rear body
     */
    const SIMPLE_MUSCLES = {
        // Front Body
        'front-shoulders': { label: 'Front Shoulders', side: 'front' },
        'chest': { label: 'Chest', side: 'front' },
        'biceps': { label: 'Biceps', side: 'front' },
        'forearms': { label: 'Forearms', side: 'front' },
        'abs': { label: 'Abs', side: 'front' },
        'obliques': { label: 'Obliques', side: 'front' },
        'quads': { label: 'Quads', side: 'front' },
        
        // Rear Body
        'traps': { label: 'Traps', side: 'rear' },
        'traps-middle': { label: 'Middle Traps', side: 'rear' },
        'rear-shoulders': { label: 'Rear Shoulders', side: 'rear' },
        'middle-shoulders': { label: 'Middle Shoulders', side: 'rear' },
        'triceps': { label: 'Triceps', side: 'rear' },
        'lats': { label: 'Lats', side: 'rear' },
        'lower-back': { label: 'Lower Back', side: 'rear' },
        'glutes': { label: 'Glutes', side: 'rear' },
        'hamstrings': { label: 'Hamstrings', side: 'rear' },
        'calves': { label: 'Calves', side: 'rear' },
        'upper-back': { label: 'Upper Back', side: 'rear' }
    };

    /**
     * Advanced muscle names (anatomical precision) with display labels
     */
    const ADVANCED_MUSCLES = {
        // Front Body - Shoulders
        'anterior-deltoid': { label: 'Anterior Deltoid', side: 'front' },
        
        // Front Body - Chest
        'upper-pectoralis': { label: 'Upper Pectoralis', side: 'front' },
        'lower-pectoralis': { label: 'Lower Pectoralis', side: 'front' },
        
        // Front Body - Arms
        'long-head-bicep': { label: 'Long Head Bicep', side: 'front' },
        'short-head-bicep': { label: 'Short Head Bicep', side: 'front' },
        'wrist-extensors': { label: 'Wrist Extensors', side: 'front' },
        'wrist-flexors': { label: 'Wrist Flexors', side: 'front' },
        
        // Front Body - Core
        'upper-abdominals': { label: 'Upper Abdominals', side: 'front' },
        'lower-abdominals': { label: 'Lower Abdominals', side: 'front' },
        'obliques': { label: 'Obliques', side: 'front' },
        
        // Front Body - Legs
        'inner-thigh': { label: 'Inner Thigh', side: 'front' },
        'rectus-femoris': { label: 'Rectus Femoris', side: 'front' },
        'outer-quadricep': { label: 'Outer Quadricep', side: 'front' },
        'quadriceps': { label: 'Quadriceps', side: 'front' },
        
        // Rear Body - Traps
        'upper-trapezius': { label: 'Upper Trapezius', side: 'rear' },
        'lower-trapezius': { label: 'Lower Trapezius', side: 'rear' },
        
        // Rear Body - Shoulders
        'lateral-deltoid': { label: 'Lateral Deltoid', side: 'rear' },
        'posterior-deltoid': { label: 'Posterior Deltoid', side: 'rear' },
        
        // Rear Body - Arms
        'lateral-head-triceps': { label: 'Lateral Head Triceps', side: 'rear' },
        'long-head-triceps': { label: 'Long Head Triceps', side: 'rear' },
        'medial-head-triceps': { label: 'Medial Head Triceps', side: 'rear' },
        
        // Rear Body - Back
        'lats': { label: 'Latissimus Dorsi', side: 'rear' },
        
        // Rear Body - Glutes
        'gluteus-maximus': { label: 'Gluteus Maximus', side: 'rear' },
        'gluteus-medius': { label: 'Gluteus Medius', side: 'rear' },
        
        // Rear Body - Legs
        'lateral-hamstrings': { label: 'Lateral Hamstrings', side: 'rear' },
        'medial-hamstrings': { label: 'Medial Hamstrings', side: 'rear' },
        'soleus': { label: 'Soleus', side: 'rear' },
        'gastrocnemius': { label: 'Gastrocnemius', side: 'rear' },
        'tibialis': { label: 'Tibialis', side: 'rear' },
        
        // Misc
        'serratus-anterior': { label: 'Serratus Anterior', side: 'front' }
    };

    /**
     * Maps database primary_muscle_group values to simple muscle keys
     * This is how the database stores muscles → how we display them in simple mode
     */
    const DB_TO_SIMPLE = {
        // Shoulders
        'Front-Shoulder': 'front-shoulders',
        'Middle-Shoulder': 'middle-shoulders',
        'Rear-Shoulder': 'rear-shoulders',
        
        // Chest
        'Chest': 'chest',
        'Upper Chest': 'chest',
        
        // Arms
        'Biceps': 'biceps',
        'Triceps': 'triceps',
        'Forearms': 'forearms',
        
        // Core
        'Abs/Core': 'abs',
        'Core': 'abs',
        'Rectus Abdominis': 'abs',
        'External Obliques': 'obliques',
        
        // Back
        'Trapezius': 'traps',
        'Upper Traps': 'traps',
        'Middle-Traps': 'traps-middle',
        'Latissimus Dorsi': 'lats',
        'Upper Back': 'upper-back',
        'Lower Back': 'lower-back',
        'Erectors': 'lower-back',
        
        // Lower Body
        'Gluteus Maximus': 'glutes',
        'Hip-Adductors': 'glutes',
        'Quadriceps': 'quads',
        'Hamstrings': 'hamstrings',
        'Calves': 'calves',
        
        // Misc
        'Neck': 'front-shoulders',  // Group with shoulders for simplicity
        'Shoulders': 'front-shoulders'  // Generic shoulders
    };

    /**
     * Maps database primary_muscle_group values to scientific display names
     * Used in advanced/scientific mode for weekly/session summaries
     * Matches naming style from ADVANCED_MUSCLES
     */
    const DB_TO_ADVANCED = {
        // Shoulders
        'Front-Shoulder': 'Anterior Deltoid',
        'Middle-Shoulder': 'Lateral Deltoid',
        'Rear-Shoulder': 'Posterior Deltoid',
        'Shoulders': 'Anterior Deltoid',
        
        // Chest
        'Chest': 'Upper / Lower Pectoralis',
        'Upper Chest': 'Upper Pectoralis',
        
        // Arms
        'Biceps': 'Long / Short Head Bicep',
        'Triceps': 'Lateral / Long / Medial Head Triceps',
        'Forearms': 'Wrist Flexors / Extensors',
        
        // Core
        'Abs/Core': 'Upper / Lower Abdominals',
        'Core': 'Upper / Lower Abdominals',
        'Rectus Abdominis': 'Upper / Lower Abdominals',
        'External Obliques': 'Obliques',
        
        // Back
        'Trapezius': 'Upper / Lower Trapezius',
        'Upper Traps': 'Upper Trapezius',
        'Middle-Traps': 'Lower Trapezius',
        'Latissimus Dorsi': 'Latissimus Dorsi',
        'Upper Back': 'Upper Back',
        'Lower Back': 'Lower Back',
        'Erectors': 'Lower Back',
        
        // Lower Body
        'Gluteus Maximus': 'Gluteus Maximus',
        'Glutes': 'Gluteus Maximus / Medius',
        'Hip-Adductors': 'Inner Thigh',
        'Quadriceps': 'Rectus Femoris / Outer Quadricep',
        'Hamstrings': 'Lateral / Medial Hamstrings',
        'Calves': 'Gastrocnemius / Soleus',
        
        // Misc
        'Neck': 'Neck'
    };

    /**
     * Reverse mapping: Simple key → All DB values that map to it
     * Used for filtering: when user selects "biceps" in simple mode,
     * we need to search for exercises with any of these DB values
     */
    const SIMPLE_TO_DB = {};
    Object.entries(DB_TO_SIMPLE).forEach(([dbValue, simpleKey]) => {
        if (!SIMPLE_TO_DB[simpleKey]) {
            SIMPLE_TO_DB[simpleKey] = [];
        }
        SIMPLE_TO_DB[simpleKey].push(dbValue);
    });

    /**
     * Maps simple muscles to their advanced sub-muscles
     * When switching from simple to advanced, these become the detailed options
     */
    const SIMPLE_TO_ADVANCED = {
        'front-shoulders': ['anterior-deltoid'],
        'middle-shoulders': ['lateral-deltoid'],
        'rear-shoulders': ['posterior-deltoid'],
        'chest': ['upper-pectoralis', 'lower-pectoralis'],
        'biceps': ['long-head-bicep', 'short-head-bicep'],
        'triceps': ['lateral-head-triceps', 'long-head-triceps', 'medial-head-triceps'],
        'forearms': ['wrist-extensors', 'wrist-flexors'],
        'abs': ['upper-abdominals', 'lower-abdominals'],
        'obliques': ['obliques'],
        'traps': ['upper-trapezius'],
        'traps-middle': [],  // No advanced breakdown
        'lower-back': [],
        'lats': ['lats'],
        'upper-back': [],
        'glutes': ['gluteus-maximus', 'gluteus-medius'],
        'quads': ['rectus-femoris', 'outer-quadricep', 'quadriceps', 'inner-thigh'],
        'hamstrings': ['lateral-hamstrings', 'medial-hamstrings'],
        'calves': ['soleus', 'gastrocnemius', 'tibialis']
    };

    /**
     * Reverse mapping: Advanced key → Simple parent
     */
    const ADVANCED_TO_SIMPLE = {};
    Object.entries(SIMPLE_TO_ADVANCED).forEach(([simpleKey, advancedKeys]) => {
        advancedKeys.forEach(advKey => {
            ADVANCED_TO_SIMPLE[advKey] = simpleKey;
        });
    });

    /**
     * Maps advanced muscle keys to their DB isolated_muscles values
     * The database stores these in the exercise_isolated_muscles table
     */
    const ADVANCED_TO_DB_ISOLATED = {
        'anterior-deltoid': 'anterior-deltoid',
        'lateral-deltoid': 'lateral-deltoid',
        'posterior-deltoid': 'posterior-deltoid',
        'upper-pectoralis': 'upper-pectoralis',
        'lower-pectoralis': 'lower-pectoralis',
        'long-head-bicep': 'long-head-bicep',
        'short-head-bicep': 'short-head-bicep',
        'lateral-head-triceps': 'lateral-head-triceps',
        'long-head-triceps': 'long-head-triceps',
        'medial-head-triceps': 'medial-head-triceps',
        'wrist-extensors': 'wrist-extensors',
        'wrist-flexors': 'wrist-flexors',
        'upper-abdominals': 'upper-abdominals',
        'lower-abdominals': 'lower-abdominals',
        'obliques': 'obliques',
        'upper-trapezius': 'upper-trapezius',
        'lower-trapezius': 'lower-trapezius',
        'lats': 'lats',
        'gluteus-maximus': 'gluteus-maximus',
        'gluteus-medius': 'gluteus-medius',
        'inner-thigh': 'inner-thigh',
        'rectus-femoris': 'rectus-femoris',
        'outer-quadricep': 'outer-quadricep',
        'quadriceps': 'quadriceps',
        'lateral-hamstrings': 'lateral-hamstrings',
        'medial-hamstrings': 'medial-hamstrings',
        'soleus': 'soleus',
        'gastrocnemius': 'gastrocnemius',
        'tibialis': 'tibialis',
        'serratus-anterior': 'serratus-anterior'
    };

    // =========================================================================
    // STATE MANAGEMENT
    // =========================================================================

    /**
     * Get current view mode from localStorage
     * @returns {'simple' | 'advanced'}
     */
    function getViewMode() {
        try {
            return localStorage.getItem(STORAGE_KEY) || 'simple';
        } catch (e) {
            return 'simple';
        }
    }

    /**
     * Set view mode and persist to localStorage
     * @param {'simple' | 'advanced'} mode
     */
    function setViewMode(mode) {
        try {
            localStorage.setItem(STORAGE_KEY, mode);
            log('View mode set to:', mode);
            // Dispatch custom event so other modules can react
            document.dispatchEvent(new CustomEvent('filterViewModeChanged', { 
                detail: { mode } 
            }));
        } catch (e) {
            console.warn('Failed to save view mode:', e);
        }
    }

    /**
     * Toggle between simple and advanced modes
     * @returns {'simple' | 'advanced'} The new mode
     */
    function toggleViewMode() {
        const current = getViewMode();
        const newMode = current === 'simple' ? 'advanced' : 'simple';
        setViewMode(newMode);
        return newMode;
    }

    // =========================================================================
    // DISPLAY VALUE TRANSFORMATIONS
    // =========================================================================

    /**
     * Transform a database muscle value to its display value based on current view mode
     * @param {string} dbValue - The raw database value
     * @param {'simple' | 'advanced'} mode - Current view mode
     * @returns {string} - Display value
     */
    function transformMuscleDisplay(dbValue, mode = null) {
        if (!dbValue) return '';
        mode = mode || getViewMode();
        
        if (mode === 'simple') {
            // Convert DB value to simple display
            const simpleKey = DB_TO_SIMPLE[dbValue];
            if (simpleKey && SIMPLE_MUSCLES[simpleKey]) {
                return SIMPLE_MUSCLES[simpleKey].label;
            }
            // If no mapping, return original (might already be simple or unmapped)
            return dbValue;
        } else {
            // In advanced mode, try to get more detailed label
            // First check if it's already an advanced key
            if (ADVANCED_MUSCLES[dbValue.toLowerCase()]) {
                return ADVANCED_MUSCLES[dbValue.toLowerCase()].label;
            }
            // Check DB_TO_ADVANCED mapping for scientific names
            if (DB_TO_ADVANCED[dbValue]) {
                return DB_TO_ADVANCED[dbValue];
            }
            // Return original if no advanced mapping
            return dbValue;
        }
    }

    /**
     * Transform an isolated muscle value to its display label
     * @param {string} isolatedValue - The database isolated muscle value
     * @param {'simple' | 'advanced'} mode - Current view mode
     * @returns {string} - Display value
     */
    function transformIsolatedMuscleDisplay(isolatedValue, mode = null) {
        if (!isolatedValue) return '';
        mode = mode || getViewMode();
        
        const normalizedKey = isolatedValue.toLowerCase();
        
        if (mode === 'simple') {
            // Map to parent simple muscle
            const simpleKey = ADVANCED_TO_SIMPLE[normalizedKey];
            if (simpleKey && SIMPLE_MUSCLES[simpleKey]) {
                return SIMPLE_MUSCLES[simpleKey].label;
            }
        }
        
        // In advanced mode or no simple mapping, use advanced label
        if (ADVANCED_MUSCLES[normalizedKey]) {
            return ADVANCED_MUSCLES[normalizedKey].label;
        }
        
        // Fallback: titlecase the value
        return isolatedValue.split('-').map(w => 
            w.charAt(0).toUpperCase() + w.slice(1)
        ).join(' ');
    }

    // =========================================================================
    // FILTER DROPDOWN OPTIONS
    // =========================================================================

    /**
     * Get muscle options for filter dropdowns based on current view mode
     * @param {'primary' | 'secondary' | 'tertiary' | 'isolated'} muscleType
     * @param {'simple' | 'advanced'} mode
     * @returns {Array<{value: string, label: string}>}
     */
    function getMuscleFilterOptions(muscleType, mode = null) {
        mode = mode || getViewMode();
        
        if (mode === 'simple') {
            // Simple mode: show simple groupings for all filter types
            return Object.entries(SIMPLE_MUSCLES)
                .map(([key, data]) => ({ value: key, label: data.label }))
                .sort((a, b) => a.label.localeCompare(b.label));
        } else {
            // Advanced/Scientific mode: show detailed anatomical names for all filter types
            return Object.entries(ADVANCED_MUSCLES)
                .map(([key, data]) => ({ value: key, label: data.label }))
                .sort((a, b) => a.label.localeCompare(b.label));
        }
    }

    /**
     * Resolve a filter selection so it can survive a mode switch.
     * When a simple group does not map 1:1 to advanced options, keep the
     * original simple key as a temporary "group" option in advanced mode.
     * @param {string} filterValue
     * @param {'primary' | 'secondary' | 'tertiary' | 'isolated'} muscleType
     * @param {'simple' | 'advanced'} mode
     * @returns {{value: string, label: string, isSynthetic: boolean} | null}
     */
    function resolveFilterSelection(filterValue, muscleType, mode = null) {
        if (!filterValue) return null;

        mode = mode || getViewMode();

        const options = getMuscleFilterOptions(muscleType, mode);
        const exactMatch = options.find(option => option.value === filterValue);
        if (exactMatch) {
            return {
                value: exactMatch.value,
                label: exactMatch.label,
                isSynthetic: false
            };
        }

        if (mode === 'simple') {
            const simpleKey = ADVANCED_TO_SIMPLE[filterValue];
            if (!simpleKey || !SIMPLE_MUSCLES[simpleKey]) {
                return null;
            }

            return {
                value: simpleKey,
                label: SIMPLE_MUSCLES[simpleKey].label,
                isSynthetic: false
            };
        }

        if (SIMPLE_MUSCLES[filterValue]) {
            return {
                value: filterValue,
                label: `${SIMPLE_MUSCLES[filterValue].label} (Group)`,
                isSynthetic: true
            };
        }

        return null;
    }

    /**
     * Convert a simple filter selection to database query values
     * Used when user selects from simple mode dropdown but we need to query DB
     * @param {string} simpleValue - The simple muscle key
     * @returns {Array<string>} - Array of DB values to search for
     */
    function simpleToDbValues(simpleValue) {
        return SIMPLE_TO_DB[simpleValue] || [simpleValue];
    }

    /**
     * Get the filter query configuration for a muscle filter selection
     * @param {string} filterValue - The selected filter value
     * @param {'primary' | 'secondary' | 'tertiary' | 'isolated'} muscleType
     * @param {'simple' | 'advanced'} mode
     * @returns {{column: string, values: Array<string>, isIsolated: boolean}}
     */
    function getFilterQueryConfig(filterValue, muscleType, mode = null) {
        mode = mode || getViewMode();
        
        const columnMap = {
            'primary': 'primary_muscle_group',
            'secondary': 'secondary_muscle_group',
            'tertiary': 'tertiary_muscle_group',
            'isolated': 'advanced_isolated_muscles'
        };
        
        const column = columnMap[muscleType];
        const isIsolated = muscleType === 'isolated';
        
        if (mode === 'simple') {
            if (isIsolated) {
                // For isolated in simple mode, get all advanced children
                const advancedKeys = SIMPLE_TO_ADVANCED[filterValue] || [];
                const dbValues = advancedKeys.map(k => ADVANCED_TO_DB_ISOLATED[k] || k);
                return { column, values: dbValues.length ? dbValues : [filterValue], isIsolated };
            } else {
                // For P/S/T in simple mode, map to DB values
                const dbValues = SIMPLE_TO_DB[filterValue] || [filterValue];
                return { column, values: dbValues, isIsolated };
            }
        } else {
            // Advanced/Scientific mode
            if (isIsolated) {
                // For isolated muscles, use the advanced key directly (it matches DB)
                return { column, values: [ADVANCED_TO_DB_ISOLATED[filterValue] || filterValue], isIsolated };
            } else {
                // For P/S/T in advanced mode, map advanced key → simple parent → DB values
                const simpleParent = ADVANCED_TO_SIMPLE[filterValue];
                if (simpleParent) {
                    const dbValues = SIMPLE_TO_DB[simpleParent] || [simpleParent];
                    return { column, values: dbValues, isIsolated };
                }
                // Fallback: use value directly
                return { column, values: [filterValue], isIsolated };
            }
        }
    }

    // =========================================================================
    // UI TOGGLE COMPONENT (NAVBAR)
    // =========================================================================

    /**
     * Initialize the navbar muscle mode toggle button
     * This is called automatically on DOMContentLoaded
     */
    function initNavbarToggle() {
        const toggleBtn = document.getElementById('muscleModeToggle');
        if (!toggleBtn) {
            log('Navbar toggle button not found');
            return;
        }
        
        // Prevent duplicate listeners
        if (toggleBtn.dataset.initialized === 'true') {
            log('Navbar toggle already initialized, skipping');
            return;
        }
        toggleBtn.dataset.initialized = 'true';
        
        const mode = getViewMode();
        updateNavbarToggleUI(toggleBtn, mode);
        
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const currentMode = getViewMode();
            const newMode = currentMode === 'simple' ? 'advanced' : 'simple';
            log('Toggle clicked: current=' + currentMode + ', new=' + newMode);
            setViewMode(newMode);
            updateNavbarToggleUI(toggleBtn, newMode);
        });
        
        log('Navbar toggle initialized with mode:', mode);
    }

    /**
     * Update the navbar toggle button appearance
     * @param {HTMLElement} btn - The toggle button element
     * @param {'simple' | 'advanced'} mode - Current mode
     */
    function updateNavbarToggleUI(btn, mode) {
        if (!btn) return;
        
        const icon = btn.querySelector('.muscle-mode-icon');
        const label = btn.querySelector('.muscle-mode-label');
        
        if (mode === 'simple') {
            btn.classList.remove('scientific-mode');
            if (icon) {
                icon.classList.remove('fa-microscope');
                icon.classList.add('fa-user');
            }
            if (label) label.textContent = 'Simple';
            btn.title = 'Currently showing simple muscle names. Click for scientific names.';
        } else {
            btn.classList.add('scientific-mode');
            if (icon) {
                icon.classList.remove('fa-user');
                icon.classList.add('fa-microscope');
            }
            if (label) label.textContent = 'Scientific';
            btn.title = 'Currently showing scientific muscle names. Click for simple names.';
        }
    }

    /**
     * Create and insert the view mode toggle button (legacy - for non-navbar contexts)
     * @param {HTMLElement} container - Container to insert the toggle into
     * @returns {HTMLElement} - The created toggle button
     */
    function createToggleButton(container) {
        if (!container) return null;
        
        // Check if toggle already exists
        const existing = container.querySelector('[data-filter-view-toggle]');
        if (existing) return existing;
        
        const mode = getViewMode();
        
        const toggleWrapper = document.createElement('div');
        toggleWrapper.className = 'filter-view-toggle-wrapper';
        toggleWrapper.innerHTML = `
            <div class="btn-group btn-group-sm filter-view-toggle" role="group" aria-label="Muscle naming mode">
                <button type="button" 
                        class="btn ${mode === 'simple' ? 'btn-primary' : 'btn-outline-secondary'}" 
                        data-filter-view-toggle 
                        data-mode="simple"
                        title="Show simplified muscle names (Biceps, Triceps, etc.)">
                    <i class="fas fa-user" aria-hidden="true"></i>
                    <span class="toggle-label">Simple</span>
                </button>
                <button type="button" 
                        class="btn ${mode === 'advanced' ? 'btn-primary' : 'btn-outline-secondary'}" 
                        data-filter-view-toggle 
                        data-mode="advanced"
                        title="Show anatomical muscle names (Long Head Bicep, Anterior Deltoid, etc.)">
                    <i class="fas fa-microscope" aria-hidden="true"></i>
                    <span class="toggle-label">Advanced</span>
                </button>
            </div>
        `;
        
        // Add click handlers
        toggleWrapper.querySelectorAll('[data-filter-view-toggle]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const targetMode = btn.dataset.mode;
                if (targetMode !== getViewMode()) {
                    setViewMode(targetMode);
                    updateToggleUI(toggleWrapper, targetMode);
                }
            });
        });
        
        container.appendChild(toggleWrapper);
        return toggleWrapper;
    }

    /**
     * Update toggle button appearance
     * @param {HTMLElement} wrapper - Toggle wrapper element
     * @param {'simple' | 'advanced'} mode - Current mode
     */
    function updateToggleUI(wrapper, mode) {
        if (!wrapper) return;
        
        wrapper.querySelectorAll('[data-filter-view-toggle]').forEach(btn => {
            const btnMode = btn.dataset.mode;
            if (btnMode === mode) {
                btn.classList.remove('btn-outline-secondary');
                btn.classList.add('btn-primary');
            } else {
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-outline-secondary');
            }
        });
    }

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    // Initialize navbar toggle when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNavbarToggle);
    } else {
        // DOM already loaded
        initNavbarToggle();
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    window.FilterViewMode = {
        // State
        getViewMode,
        setViewMode,
        toggleViewMode,
        
        // Transformations
        transformMuscleDisplay,
        transformIsolatedMuscleDisplay,
        
        // Filter options
        getMuscleFilterOptions,
        resolveFilterSelection,
        simpleToDbValues,
        getFilterQueryConfig,
        
        // UI
        createToggleButton,
        updateToggleUI,
        initNavbarToggle,
        
        // Data exports (for external use)
        SIMPLE_MUSCLES,
        ADVANCED_MUSCLES,
        DB_TO_SIMPLE,
        SIMPLE_TO_DB,
        SIMPLE_TO_ADVANCED,
        ADVANCED_TO_SIMPLE,
        ADVANCED_TO_DB_ISOLATED
    };

    log('FilterViewMode module loaded');
})();
