/**
 * Muscle Group Selector Module v3.0
 * SVG-based anatomically accurate body diagram for muscle group selection
 * 
 * Simple mode uses workout-cool SVGs (MIT License).
 * Advanced mode uses first-party Hypertrophy Toolbox SVGs.
 * 
 * Features:
 * - SVG muscle regions with canonical keys baked into data attributes
 * - Simple/Advanced view modes with proper parent-child mapping
 * - Front/Back tab navigation  
 * - Bilateral synchronization (both sides highlight/select together)
 * - Robust mapping layer: upstream slugs → canonical keys → backend names
 * - Debug mode for development
 */

// ============================================================================
// VENDOR SVG MAPPING LAYER
// ============================================================================

/**
 * Maps upstream react-body-highlighter slugs to our canonical muscle keys.
 * 
 * Upstream slugs (from vendor SVGs):
 *   Front: head, neck, front-deltoids, chest, biceps, triceps, abs, obliques, 
 *          forearm, abductors, quadriceps, knees, calves
 *   Back:  head, trapezius, back-deltoids, upper-back, triceps, lower-back,
 *          forearm, gluteal, abductor, hamstring, knees, calves, left-soleus, right-soleus
 * 
 * View mode determines which canonical keys are active:
 *   Simple: Higher-level muscle groups for quick selection
 *   Advanced: Detailed muscle subdivisions for precise targeting
 */

// Upstream slug → Canonical key mapping (for SVG data-muscle attributes).
// MIRROR of `static/js/modules/bodymap-svg.js`. This file is loaded as a
// classic <script> on /workout_plan, so it can't import the ES-module
// version directly. Any change here must also be made in `bodymap-svg.js`.
// `tests/test_profile_estimator.py::test_bodymap_canonical_in_sync` enforces this.
const VENDOR_SLUG_TO_CANONICAL = {
    // ===== FRONT (Anterior) =====
    'head': null,  // Not selectable for workout targeting
    'neck': 'neck',
    'front-deltoids': 'front-shoulders',  // Simple: front-shoulders
    'chest': 'chest',
    'biceps': 'biceps',
    'triceps': 'triceps',
    'abs': 'abdominals',
    'obliques': 'obliques',
    'forearm': 'forearms',
    'abductors': 'adductors',  // Note: upstream calls these "abductors" but they're inner thigh
    'quadriceps': 'quads',
    'knees': null,  // Not selectable
    'calves': 'calves',
    
    // ===== BACK (Posterior) =====
    'trapezius': 'traps',
    'back-deltoids': 'rear-shoulders',  // Simple: rear-shoulders
    'upper-back': 'upper-back',
    'lower-back': 'lowerback',
    'gluteal': 'glutes',
    'abductor': 'hip-abductors',  // Hip abductors (different from front thigh adductors)
    'hamstring': 'hamstrings',
    'left-soleus': 'calves',  // Map soleus to calves
    'right-soleus': 'calves'
};

/**
 * Simple → Advanced mapping.
 * When simple group is selected, ALL children become selected.
 * When switching Advanced → Simple, parent shows selected if ANY child is selected.
 */
const SIMPLE_TO_ADVANCED_MAP = {
    // Front body - Simple groups
    'front-shoulders': ['anterior-deltoid', 'lateral-deltoid'],
    'chest': ['upper-chest', 'mid-chest', 'lower-chest'],
    'biceps': ['long-head-bicep', 'short-head-bicep'],
    'forearms': ['wrist-flexors', 'wrist-extensors', 'brachioradialis'],
    'abdominals': ['upper-abs', 'lower-abs'],
    'obliques': ['obliques'],  // No subdivision
    'quads': ['rectus-femoris', 'vastus-lateralis', 'vastus-medialis', 'vastus-intermedius'],
    'adductors': ['adductors'],  // Inner thigh
    'neck': ['neck'],
    
    // Back body - Simple groups
    'rear-shoulders': ['posterior-deltoid', 'lateral-deltoid'],
    'traps': ['upper-traps', 'mid-traps', 'lower-traps'],
    'upper-back': ['rhomboids', 'teres-major', 'teres-minor'],
    'lats': ['lats'],
    'lowerback': ['erector-spinae'],
    'triceps': ['lateral-head-triceps', 'long-head-triceps', 'medial-head-triceps'],
    'glutes': ['gluteus-maximus', 'gluteus-medius', 'gluteus-minimus'],
    'hip-abductors': ['tensor-fasciae-latae'],
    'hamstrings': ['biceps-femoris', 'semitendinosus', 'semimembranosus'],
    
    // Shared
    'calves': ['gastrocnemius', 'soleus', 'tibialis-anterior']
};

/**
 * Advanced → Simple reverse mapping (auto-generated)
 */
const ADVANCED_TO_SIMPLE_MAP = {};
Object.entries(SIMPLE_TO_ADVANCED_MAP).forEach(([parent, children]) => {
    children.forEach(child => {
        if (!ADVANCED_TO_SIMPLE_MAP[child]) {
            ADVANCED_TO_SIMPLE_MAP[child] = [];
        }
        ADVANCED_TO_SIMPLE_MAP[child].push(parent);
    });
});

/**
 * Human-readable labels for all muscle keys
 */
const MUSCLE_LABELS = {
    // ===== SIMPLE VIEW LABELS =====
    'front-shoulders': 'Front Delts',
    'chest': 'Chest',
    'biceps': 'Biceps',
    'forearms': 'Forearms',
    'abdominals': 'Abs',
    'obliques': 'Obliques',
    'quads': 'Quadriceps',
    'adductors': 'Adductors',
    'neck': 'Neck',
    'calves': 'Calves',
    'rear-shoulders': 'Rear Delts',
    'traps': 'Traps',
    'upper-back': 'Upper Back',
    'lats': 'Lats',
    'lowerback': 'Lower Back',
    'triceps': 'Triceps',
    'glutes': 'Glutes',
    'hip-abductors': 'Hip Abductors',
    'hamstrings': 'Hamstrings',
    
    // ===== ADVANCED VIEW LABELS =====
    // Shoulders
    'anterior-deltoid': 'Anterior Deltoid',
    'lateral-deltoid': 'Lateral Deltoid',
    'posterior-deltoid': 'Posterior Deltoid',
    // Chest
    'upper-chest': 'Upper Chest',
    'mid-chest': 'Mid Chest',
    'lower-chest': 'Lower Chest',
    // Arms
    'long-head-bicep': 'Long Head Bicep',
    'short-head-bicep': 'Short Head Bicep',
    'lateral-head-triceps': 'Lateral Triceps',
    'long-head-triceps': 'Long Head Triceps',
    'medial-head-triceps': 'Medial Triceps',
    'wrist-flexors': 'Wrist Flexors',
    'wrist-extensors': 'Wrist Extensors',
    'brachioradialis': 'Brachioradialis',
    // Core
    'upper-abs': 'Upper Abs',
    'lower-abs': 'Lower Abs',
    // Back
    'upper-traps': 'Upper Traps',
    'mid-traps': 'Mid Traps',
    'lower-traps': 'Lower Traps',
    'rhomboids': 'Rhomboids',
    'teres-major': 'Teres Major',
    'teres-minor': 'Teres Minor',
    'erector-spinae': 'Erector Spinae',
    // Glutes
    'gluteus-maximus': 'Gluteus Maximus',
    'gluteus-medius': 'Gluteus Medius',
    'gluteus-minimus': 'Gluteus Minimus',
    'tensor-fasciae-latae': 'TFL',
    // Legs
    'rectus-femoris': 'Rectus Femoris',
    'vastus-lateralis': 'Vastus Lateralis',
    'vastus-medialis': 'Vastus Medialis',
    'vastus-intermedius': 'Vastus Intermedius',
    'biceps-femoris': 'Biceps Femoris',
    'semitendinosus': 'Semitendinosus',
    'semimembranosus': 'Semimembranosus',
    'gastrocnemius': 'Gastrocnemius',
    'soleus': 'Soleus',
    'tibialis-anterior': 'Tibialis Anterior'
};

/**
 * Backend muscle group name mapping (for API payload)
 * Maps canonical keys to the exact strings expected by the backend
 */
const MUSCLE_TO_BACKEND = {
    // Simple keys → Backend
    'front-shoulders': 'Shoulders',
    'rear-shoulders': 'Shoulders', 
    'chest': 'Chest',
    'biceps': 'Biceps',
    'forearms': 'Forearms',
    'abdominals': 'Abs',
    'obliques': 'Obliques',
    'quads': 'Quads',
    'adductors': 'Adductors',
    'neck': 'Neck',
    'calves': 'Calves',
    'traps': 'Traps',
    'upper-back': 'Upper Back',
    'lats': 'Lats',
    'lowerback': 'Lower Back',
    'triceps': 'Triceps',
    'glutes': 'Glutes',
    'hip-abductors': 'Glutes',  // Group with glutes
    'hamstrings': 'Hamstrings',
    
    // Advanced keys → Backend (more specific)
    'anterior-deltoid': 'Front Delts',
    'lateral-deltoid': 'Lateral Delts',
    'posterior-deltoid': 'Rear Delts',
    'upper-chest': 'Upper Chest',
    'mid-chest': 'Mid Chest',
    'lower-chest': 'Lower Chest',
    'long-head-bicep': 'Biceps',
    'short-head-bicep': 'Biceps',
    'lateral-head-triceps': 'Triceps',
    'long-head-triceps': 'Triceps',
    'medial-head-triceps': 'Triceps',
    'wrist-flexors': 'Forearms',
    'wrist-extensors': 'Forearms',
    'brachioradialis': 'Forearms',
    'upper-abs': 'Abs',
    'lower-abs': 'Abs',
    'upper-traps': 'Traps',
    'mid-traps': 'Traps',
    'lower-traps': 'Traps',
    'rhomboids': 'Upper Back',
    'teres-major': 'Upper Back',
    'teres-minor': 'Upper Back',
    'erector-spinae': 'Lower Back',
    'gluteus-maximus': 'Glutes',
    'gluteus-medius': 'Glutes',
    'gluteus-minimus': 'Glutes',
    'tensor-fasciae-latae': 'Glutes',
    'rectus-femoris': 'Quads',
    'vastus-lateralis': 'Quads',
    'vastus-medialis': 'Quads',
    'vastus-intermedius': 'Quads',
    'biceps-femoris': 'Hamstrings',
    'semitendinosus': 'Hamstrings',
    'semimembranosus': 'Hamstrings',
    'gastrocnemius': 'Calves',
    'soleus': 'Calves',
    'tibialis-anterior': 'Tibialis'
};

/**
 * SVG file paths keyed by viewMode × bodySide.
 *
 * Simple mode swaps in workout-cool's anatomy art (vendored under
 * static/vendor/workout-cool/, ships pre-canonicalized data-canonical-muscles
 * - see static/vendor/workout-cool/NOTICE.md). Advanced mode uses
 * first-party schematic SVGs whose regions are already keyed to the
 * scientific sub-muscles in SIMPLE_TO_ADVANCED_MAP.
 */
const SVG_PATHS = {
    simple: {
        front: '/static/vendor/workout-cool/body_anterior.svg',
        back: '/static/vendor/workout-cool/body_posterior.svg'
    },
    advanced: {
        front: '/static/bodymaps/hypertrophy-advanced/body_anterior.svg',
        back: '/static/bodymaps/hypertrophy-advanced/body_posterior.svg'
    }
};

function getSvgPathForMode(mode, side) {
    return SVG_PATHS[mode][side];
}

/**
 * Which canonical keys appear on each body side
 */
const MUSCLES_BY_SIDE = {
    front: [
        'neck', 'front-shoulders', 'chest', 'biceps', 'triceps', 
        'forearms', 'abdominals', 'obliques', 'adductors', 'quads', 'calves'
    ],
    back: [
        'traps', 'rear-shoulders', 'upper-back', 'lats', 'triceps',
        'lowerback', 'forearms', 'glutes', 'hip-abductors', 'hamstrings', 'calves'
    ]
};

// ============================================================================
// MUSCLE SELECTOR CLASS
// ============================================================================

class MuscleSelector {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.viewMode = options.viewMode || 'simple';
        this.bodySide = options.bodySide || 'front';
        this.debugMode = options.debug || false;
        
        // Store selections at ADVANCED level (sub-muscles)
        // This allows precise tracking regardless of view mode
        this.selectedMuscles = new Set();
        
        // SVG cache
        this.svgCache = {};
        
        if (this.container) {
            this.init();
        }
    }

    async init() {
        this.renderShell();
        await this.loadAndRenderSVG();
        this.attachGlobalEventListeners();
    }

    /**
     * Render the container shell (controls, tabs, containers)
     */
    renderShell() {
        this.container.innerHTML = `
            <div class="muscle-selector-wrapper">
                <!-- Controls Row -->
                <div class="muscle-selector-controls">
                    <div class="view-toggle-group">
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn ${this.viewMode === 'simple' ? 'btn-primary' : 'btn-outline-secondary'}" data-view="simple">
                                Simple
                            </button>
                            <button type="button" class="btn ${this.viewMode === 'advanced' ? 'btn-primary' : 'btn-outline-secondary'}" data-view="advanced">
                                Advanced
                            </button>
                        </div>
                    </div>
                    <div class="action-buttons">
                        ${this.debugMode ? '<button type="button" class="btn btn-sm btn-outline-info me-1" id="muscle-toggle-debug">Debug</button>' : ''}
                        <button type="button" class="btn btn-sm btn-outline-success" id="muscle-select-all">Select All</button>
                        <button type="button" class="btn btn-sm btn-outline-secondary" id="muscle-clear-all">Clear</button>
                    </div>
                </div>

                <!-- Body Side Tabs -->
                <ul class="nav nav-tabs muscle-body-tabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link ${this.bodySide === 'front' ? 'active' : ''}" 
                                data-side="front" type="button" role="tab">
                            <i class="fas fa-user me-1"></i>Front
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link ${this.bodySide === 'back' ? 'active' : ''}" 
                                data-side="back" type="button" role="tab">
                            <i class="fas fa-user me-1"></i>Back
                        </button>
                    </li>
                </ul>

                <!-- Main Content Area -->
                <div class="muscle-selector-content">
                    <div class="body-diagram-wrapper">
                        <div id="svg-container" class="svg-container">
                            <div class="skeleton" style="height: 400px; width: 100%;"></div>
                        </div>
                        <div class="muscle-tooltip" id="muscle-tooltip">
                            <div class="tooltip-label"></div>
                            <div class="tooltip-key"></div>
                        </div>
                    </div>
                    <div class="muscle-legend" id="muscle-legend">
                        <!-- Legend items rendered dynamically -->
                    </div>
                </div>

                <!-- Selection Summary -->
                <div class="selection-summary">
                    <span class="summary-label">Priority:</span>
                    <span class="summary-value" id="selection-summary-text">
                        None – balanced volume across all muscles
                    </span>
                </div>
            </div>
        `;
    }

    /**
     * Load SVG from vendor directory and render it inline
     */
    async loadAndRenderSVG() {
        const svgPath = getSvgPathForMode(this.viewMode, this.bodySide);
        const svgContainer = this.container.querySelector('#svg-container');
        
        try {
            // Check cache first
            if (this.svgCache[svgPath]) {
                svgContainer.innerHTML = this.svgCache[svgPath];
            } else {
                const response = await fetch(svgPath);
                if (!response.ok) throw new Error(`Failed to load SVG: ${svgPath}`);
                const svgText = await response.text();
                this.svgCache[svgPath] = svgText;
                svgContainer.innerHTML = svgText;
            }
            
            // Map vendor slugs to canonical keys
            this.mapVendorSlugsToCanonical();
            
            // Attach event listeners to muscle regions
            this.attachMuscleEventListeners();
            
            // Update visual state based on current selections
            this.updateAllRegionStates();
            
            // Render legend
            this.renderLegend();
            
            // Update summary
            this.updateSummary();
            
        } catch (error) {
            console.error('Error loading SVG:', error);
            svgContainer.innerHTML = `
                <div class="alert alert-danger m-3">
                    Failed to load muscle diagram. Please refresh the page.
                </div>
            `;
        }
    }

    /**
     * Map vendor SVG slugs to canonical muscle keys.
     * Updates data attributes on SVG elements.
     *
     * Three SVG flavors are supported:
     *   - Pre-canonicalized (workout-cool simple variant and first-party
     *     advanced variant): each region
     *     already carries `data-canonical-muscles="<key1>[,<key2>,...]"`.
     *     No translation needed — left as-is.
     *   - Vendor-slug (react-body-highlighter advanced variant): each region
     *     carries `data-muscle="<vendor-slug>"`. Translate via
     *     VENDOR_SLUG_TO_CANONICAL into a singular `data-canonical-muscle`.
     */
    mapVendorSlugsToCanonical() {
        const regions = this.container.querySelectorAll('.muscle-region');

        regions.forEach(region => {
            // Pre-canonicalized SVGs (workout-cool) ship the plural attribute
            // and need no further mapping.
            if (region.dataset.canonicalMuscles) return;

            const vendorSlug = region.dataset.muscle;
            if (!vendorSlug) return;

            const canonicalKey = VENDOR_SLUG_TO_CANONICAL[vendorSlug];

            if (canonicalKey === null) {
                // Non-selectable region (e.g., head, knees)
                region.classList.add('non-selectable');
                region.style.cursor = 'default';
            } else if (canonicalKey) {
                // Update to canonical key
                region.dataset.canonicalMuscle = canonicalKey;
            } else {
                // Unknown slug - keep original but log warning
                console.warn(`Unknown vendor slug: ${vendorSlug}`);
                region.dataset.canonicalMuscle = vendorSlug;
            }
        });
    }

    /**
     * Get all canonical (simple) keys associated with a region.
     *
     * Multi-key SVG regions (workout-cool's BACK area) ship
     * `data-canonical-muscles="lats,upper-back,lowerback"` which expands to
     * 5 advanced children once flattened through SIMPLE_TO_ADVANCED_MAP.
     * Single-key regions return a one-element array.
     */
    getCanonicalKeys(region) {
        const plural = region.dataset.canonicalMuscles;
        if (plural) {
            return plural.split(',').map(k => k.trim()).filter(Boolean);
        }
        const singular = region.dataset.canonicalMuscle;
        if (singular) return [singular];
        const slug = region.dataset.muscle;
        if (slug) {
            const mapped = VENDOR_SLUG_TO_CANONICAL[slug];
            return mapped ? [mapped] : [slug];
        }
        return [];
    }

    /**
     * Backwards-compatible single-key accessor — returns the first canonical
     * key for a region (or null). New multi-key call sites should use
     * getCanonicalKeys() / flattenToAdvancedChildren() instead.
     */
    getCanonicalKey(region) {
        const keys = this.getCanonicalKeys(region);
        return keys[0] || null;
    }

    /**
     * Flatten an array of simple/advanced muscle keys into the unique set of
     * advanced child keys that `selectedMuscles` actually stores.
     *
     * CRITICAL: `selectedMuscles` always holds advanced keys. Any region
     * click that touches `selectedMuscles.has` / `.add` / `.delete` MUST go
     * through this helper first — otherwise multi-key regions (e.g. BACK)
     * never line up with the underlying selection state.
     * See PLANNING.md §3.4.1.
     */
    flattenToAdvancedChildren(simpleKeys) {
        const out = new Set();
        simpleKeys.forEach(key => {
            const children = SIMPLE_TO_ADVANCED_MAP[key];
            if (children && children.length > 0) {
                children.forEach(c => out.add(c));
            } else {
                out.add(key);
            }
        });
        return Array.from(out);
    }

    /**
     * Compute the visual state of a region from `selectedMuscles`.
     * Returns 'selected', 'partial', or 'unselected'. Tested directly by
     * tests/test_muscle_selector_mapping (rhomboids-only and
     * erector-spinae-only on BACK must yield 'partial').
     */
    regionVisualState(region) {
        const advancedKeys = this.flattenToAdvancedChildren(this.getCanonicalKeys(region));
        if (advancedKeys.length === 0) return 'unselected';
        const hits = advancedKeys.filter(k => this.selectedMuscles.has(k)).length;
        if (hits === 0) return 'unselected';
        if (hits === advancedKeys.length) return 'selected';
        return 'partial';
    }

    /**
     * Attach event listeners to muscle region paths.
     *
     * Multi-key regions (workout-cool BACK) carry several simple keys in
     * `data-canonical-muscles`; clicking and hovering must operate on the
     * full set, not the first key, so we plumb arrays through everywhere.
     */
    attachMuscleEventListeners() {
        const regions = this.container.querySelectorAll('.muscle-region:not(.non-selectable)');

        regions.forEach(region => {
            const canonicalKeys = this.getCanonicalKeys(region);
            if (canonicalKeys.length === 0) return;

            region.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleRegion(region);
            });

            region.addEventListener('mouseenter', (e) => {
                canonicalKeys.forEach(key => this.handleMuscleHover(key, true));
                this.showTooltip(e, canonicalKeys[0]);
            });

            region.addEventListener('mousemove', (e) => {
                this.moveTooltip(e);
            });

            region.addEventListener('mouseleave', () => {
                canonicalKeys.forEach(key => this.handleMuscleHover(key, false));
                this.hideTooltip();
            });
        });
    }

    /**
     * Toggle every advanced child covered by a region's
     * `data-canonical-muscles`. If all are already selected, clear them all;
     * otherwise add the missing ones (promote `partial` → `selected`).
     * Mirrors the parent-key cascade in `toggleMuscle()` but works for
     * regions whose data-canonical-muscles lists multiple simple keys.
     */
    toggleRegion(region) {
        const advancedKeys = this.flattenToAdvancedChildren(this.getCanonicalKeys(region));
        if (advancedKeys.length === 0) return;

        const allSelected = advancedKeys.every(k => this.selectedMuscles.has(k));
        if (allSelected) {
            advancedKeys.forEach(k => this.selectedMuscles.delete(k));
        } else {
            advancedKeys.forEach(k => this.selectedMuscles.add(k));
        }

        this.updateAllRegionStates();
        this.renderLegend();
        this.updateSummary();
    }

    /**
     * Attach global event listeners (tabs, buttons)
     */
    attachGlobalEventListeners() {
        // View mode toggle
        this.container.querySelectorAll('[data-view]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const newMode = e.currentTarget.dataset.view;
                if (newMode !== this.viewMode) {
                    this.switchViewMode(newMode);
                }
            });
        });

        // Body side tabs
        this.container.querySelectorAll('[data-side]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const newSide = e.currentTarget.dataset.side;
                if (newSide !== this.bodySide) {
                    this.switchBodySide(newSide);
                }
            });
        });

        // Select All
        const selectAllBtn = this.container.querySelector('#muscle-select-all');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => this.selectAll());
        }

        // Clear All
        const clearAllBtn = this.container.querySelector('#muscle-clear-all');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAll());
        }

        // Debug toggle
        const debugBtn = this.container.querySelector('#muscle-toggle-debug');
        if (debugBtn) {
            debugBtn.addEventListener('click', () => {
                this.debugMode = !this.debugMode;
                debugBtn.classList.toggle('btn-info', this.debugMode);
                debugBtn.classList.toggle('btn-outline-info', !this.debugMode);
                this.updateAllRegionStates();
                this.renderLegend();
            });
        }
    }

    /**
     * Return true when a region should respond to hover for `muscleKey`.
     * This supports both direct advanced child keys and parent/simple keys
     * used by legend group headers.
     */
    regionMatchesMuscleKey(region, muscleKey) {
        const regionKeys = this.getCanonicalKeys(region);
        if (regionKeys.includes(muscleKey)) return true;

        const targetAdvanced = this.flattenToAdvancedChildren([muscleKey]);
        const regionAdvanced = this.flattenToAdvancedChildren(regionKeys);
        return regionAdvanced.some(key => targetAdvanced.includes(key));
    }

    /**
     * Handle hover state - highlight all paths covered by a canonical key.
     */
    handleMuscleHover(canonicalKey, isHovering) {
        const regions = this.container.querySelectorAll('.muscle-region');
        regions.forEach(region => {
            if (this.regionMatchesMuscleKey(region, canonicalKey)) {
                region.classList.toggle('hover', isHovering);
            }
        });
        
        // Also highlight corresponding legend item
        const legendItem = this.container.querySelector(`.legend-item[data-muscle="${canonicalKey}"]`);
        if (legendItem) {
            legendItem.classList.toggle('hover', isHovering);
        }
    }

    /**
     * Toggle a muscle selection
     * In Simple mode: toggles all children of a parent group
     * In Advanced mode: toggles individual sub-muscles, OR all children if clicking a parent group header
     */
    toggleMuscle(muscleKey) {
        // Check if this is a parent key (has children in SIMPLE_TO_ADVANCED_MAP)
        const isParentKey = SIMPLE_TO_ADVANCED_MAP.hasOwnProperty(muscleKey) && SIMPLE_TO_ADVANCED_MAP[muscleKey].length > 0;
        
        if (this.viewMode === 'simple' || isParentKey) {
            // In simple mode OR when clicking a parent group header in advanced mode,
            // toggle ALL children of the parent group
            const children = SIMPLE_TO_ADVANCED_MAP[muscleKey] || [muscleKey];
            const allSelected = children.every(child => this.selectedMuscles.has(child));
            
            if (allSelected) {
                // Deselect all children
                children.forEach(child => this.selectedMuscles.delete(child));
            } else {
                // Select all children
                children.forEach(child => this.selectedMuscles.add(child));
            }
        } else {
            // In advanced mode, toggle individual sub-muscle
            if (this.selectedMuscles.has(muscleKey)) {
                this.selectedMuscles.delete(muscleKey);
            } else {
                this.selectedMuscles.add(muscleKey);
            }
        }
        
        this.updateAllRegionStates();
        this.renderLegend();
        this.updateSummary();
    }

    /**
     * Check if a muscle is selected
     * For simple keys: returns true if ALL children are selected
     * For advanced keys: returns true if that specific key is selected
     */
    isMuscleSelected(muscleKey) {
        // Check if it's a simple (parent) key
        const children = SIMPLE_TO_ADVANCED_MAP[muscleKey];
        if (children && children.length > 0) {
            // Parent key: check if ALL children are selected
            return children.every(child => this.selectedMuscles.has(child));
        }
        // Advanced key or no children: check directly
        return this.selectedMuscles.has(muscleKey);
    }

    /**
     * Check if a simple muscle group is partially selected
     * (some but not all children selected)
     */
    isMusclePartiallySelected(muscleKey) {
        const children = SIMPLE_TO_ADVANCED_MAP[muscleKey];
        if (!children || children.length === 0) return false;
        
        const selectedCount = children.filter(child => this.selectedMuscles.has(child)).length;
        return selectedCount > 0 && selectedCount < children.length;
    }

    /**
     * Update the visual state of all muscle regions.
     * Uses regionVisualState() so multi-key regions (BACK) honour the
     * full advanced-children flatten before deciding selected/partial.
     */
    updateAllRegionStates() {
        const regions = this.container.querySelectorAll('.muscle-region:not(.non-selectable)');

        regions.forEach(region => {
            const state = this.regionVisualState(region);
            region.classList.toggle('selected', state === 'selected');
            region.classList.toggle('partial', state === 'partial');

            if (this.debugMode) {
                region.style.strokeWidth = '0.5';
            } else {
                region.style.strokeWidth = '';
            }
        });
    }

    /**
     * Render the legend/checklist
     * Simple mode: shows parent muscle groups
     * Advanced mode: shows sub-muscles grouped under parents
     */
    renderLegend() {
        const legendContainer = this.container.querySelector('#muscle-legend');
        if (!legendContainer) return;
        
        // Save scroll position before re-rendering
        const legendItems = legendContainer.querySelector('.legend-items');
        const scrollTop = legendItems ? legendItems.scrollTop : 0;
        
        // Get muscles for current body side
        const musclesForSide = MUSCLES_BY_SIDE[this.bodySide] || [];
        
        let legendHTML = `
            <div class="legend-header">
                <span class="legend-title">${this.bodySide === 'front' ? 'Front' : 'Back'} Muscles</span>
                <span class="legend-mode-badge">${this.viewMode === 'simple' ? 'Simple' : 'Advanced'}</span>
            </div>
            <div class="legend-items">
        `;
        
        if (this.viewMode === 'simple') {
            // Simple mode: show parent groups only
            const muscleKeys = musclesForSide.filter(key => MUSCLE_LABELS[key]);
            legendHTML += muscleKeys.map(key => this.renderSimpleLegendItem(key)).join('');
        } else {
            // Advanced mode: show sub-muscles grouped under parents
            musclesForSide.forEach(parentKey => {
                const children = SIMPLE_TO_ADVANCED_MAP[parentKey];
                if (children && children.length > 0) {
                    legendHTML += this.renderAdvancedLegendGroup(parentKey, children);
                }
            });
        }
        
        legendHTML += '</div>';
        legendContainer.innerHTML = legendHTML;
        
        // Attach legend item event listeners
        legendContainer.querySelectorAll('.legend-item').forEach(item => {
            const muscleKey = item.dataset.muscle;
            const parentKey = item.dataset.parent;
            
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMuscle(muscleKey);
            });
            
            // Hover highlights the SVG region (parent key for advanced items)
            const hoverKey = parentKey || muscleKey;
            item.addEventListener('mouseenter', () => this.handleMuscleHover(hoverKey, true));
            item.addEventListener('mouseleave', () => this.handleMuscleHover(hoverKey, false));
        });
        
        // Attach parent header click handlers (select all children)
        legendContainer.querySelectorAll('.legend-group-header').forEach(header => {
            const parentKey = header.dataset.parent;
            header.addEventListener('click', () => this.toggleMuscle(parentKey));
            header.addEventListener('mouseenter', () => this.handleMuscleHover(parentKey, true));
            header.addEventListener('mouseleave', () => this.handleMuscleHover(parentKey, false));
        });
        
        // Restore scroll position after re-rendering
        const newLegendItems = legendContainer.querySelector('.legend-items');
        if (newLegendItems && scrollTop > 0) {
            newLegendItems.scrollTop = scrollTop;
        }
    }

    /**
     * Render a simple mode legend item (parent muscle group)
     */
    renderSimpleLegendItem(parentKey) {
        const isSelected = this.isMuscleSelected(parentKey);
        const isPartial = this.isMusclePartiallySelected(parentKey);
        const label = MUSCLE_LABELS[parentKey] || parentKey;
        
        let checkboxClass = 'legend-checkbox';
        let checkboxIcon = '';
        
        if (isSelected) {
            checkboxClass += ' checked';
            checkboxIcon = '<i class="fas fa-check"></i>';
        } else if (isPartial) {
            checkboxClass += ' partial';
            checkboxIcon = '<i class="fas fa-minus"></i>';
        }
        
        return `
            <label class="legend-item" data-muscle="${parentKey}">
                <span class="${checkboxClass}">${checkboxIcon}</span>
                <span class="legend-label">${label}</span>
                ${this.debugMode ? `<code class="legend-key">${parentKey}</code>` : ''}
            </label>
        `;
    }

    /**
     * Render an advanced mode legend group (parent + children)
     */
    renderAdvancedLegendGroup(parentKey, children) {
        const parentLabel = MUSCLE_LABELS[parentKey] || parentKey;
        const isParentSelected = this.isMuscleSelected(parentKey);
        const isParentPartial = this.isMusclePartiallySelected(parentKey);
        
        let parentCheckClass = 'legend-checkbox small';
        let parentCheckIcon = '';
        if (isParentSelected) {
            parentCheckClass += ' checked';
            parentCheckIcon = '<i class="fas fa-check"></i>';
        } else if (isParentPartial) {
            parentCheckClass += ' partial';
            parentCheckIcon = '<i class="fas fa-minus"></i>';
        }
        
        let html = `
            <div class="legend-group">
                <div class="legend-group-header" data-parent="${parentKey}">
                    <span class="${parentCheckClass}">${parentCheckIcon}</span>
                    <span class="legend-group-title">${parentLabel}</span>
                </div>
                <div class="legend-group-children">
        `;
        
        children.forEach(childKey => {
            const isSelected = this.selectedMuscles.has(childKey);
            const childLabel = MUSCLE_LABELS[childKey] || childKey;
            
            let checkboxClass = 'legend-checkbox';
            let checkboxIcon = '';
            if (isSelected) {
                checkboxClass += ' checked';
                checkboxIcon = '<i class="fas fa-check"></i>';
            }
            
            html += `
                <label class="legend-item legend-child" data-muscle="${childKey}" data-parent="${parentKey}">
                    <span class="${checkboxClass}">${checkboxIcon}</span>
                    <span class="legend-label">${childLabel}</span>
                    ${this.debugMode ? `<code class="legend-key">${childKey}</code>` : ''}
                </label>
            `;
        });
        
        html += '</div></div>';
        return html;
    }

    /**
     * Switch view mode (simple/advanced).
     *
     * Simple and Advanced load DIFFERENT SVG art (workout-cool vs
     * react-body-highlighter — see SVG_PATHS), so we must reload the SVG
     * here. Selection state in `selectedMuscles` is preserved verbatim
     * across the swap; updateAllRegionStates() re-derives the visual state
     * from it after the new SVG mounts.
     */
    async switchViewMode(newMode) {
        if (newMode === this.viewMode) return;
        this.viewMode = newMode;

        this.container.querySelectorAll('[data-view]').forEach(btn => {
            const isActive = btn.dataset.view === newMode;
            btn.classList.toggle('btn-primary', isActive);
            btn.classList.toggle('btn-outline-secondary', !isActive);
        });

        await this.loadAndRenderSVG();
        this.updateSummary();
    }

    /**
     * Switch body side (front/back)
     */
    async switchBodySide(newSide) {
        this.bodySide = newSide;
        
        // Update tab states
        this.container.querySelectorAll('[data-side]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.side === newSide);
        });
        
        await this.loadAndRenderSVG();
    }

    /**
     * Select all muscles visible in current view
     * Always selects at advanced (sub-muscle) level
     */
    selectAll() {
        const musclesForSide = MUSCLES_BY_SIDE[this.bodySide] || [];
        musclesForSide.forEach(parentKey => {
            const children = SIMPLE_TO_ADVANCED_MAP[parentKey] || [parentKey];
            children.forEach(child => this.selectedMuscles.add(child));
        });
        
        this.updateAllRegionStates();
        this.renderLegend();
        this.updateSummary();
    }

    /**
     * Clear all selections
     */
    clearAll() {
        this.selectedMuscles.clear();
        this.updateAllRegionStates();
        this.renderLegend();
        this.updateSummary();
    }

    /**
     * Update the selection summary text
     */
    updateSummary() {
        const summaryEl = this.container.querySelector('#selection-summary-text');
        if (!summaryEl) return;
        
        if (this.selectedMuscles.size === 0) {
            summaryEl.textContent = 'None – balanced volume across all muscles';
            return;
        }
        
        // Get unique display names
        const displayNames = [];
        this.selectedMuscles.forEach(key => {
            const label = MUSCLE_LABELS[key];
            if (label && !displayNames.includes(label)) {
                displayNames.push(label);
            }
        });
        
        displayNames.sort();
        let muscleText;
        if (displayNames.length <= 3) {
            muscleText = displayNames.join(', ');
        } else {
            muscleText = `${displayNames.slice(0, 2).join(', ')} +${displayNames.length - 2} more`;
        }
        summaryEl.textContent = `${muscleText} – will get extra sets`;
    }

    /**
     * Show tooltip
     */
    showTooltip(event, canonicalKey) {
        const tooltip = this.container.querySelector('#muscle-tooltip');
        if (!tooltip) return;
        
        const label = MUSCLE_LABELS[canonicalKey] || canonicalKey;
        tooltip.querySelector('.tooltip-label').textContent = label;
        tooltip.querySelector('.tooltip-key').textContent = this.debugMode ? canonicalKey : '';
        tooltip.classList.add('visible');
        this.moveTooltip(event);
    }

    /**
     * Move tooltip to follow cursor
     */
    moveTooltip(event) {
        const tooltip = this.container.querySelector('#muscle-tooltip');
        if (!tooltip || !tooltip.classList.contains('visible')) return;
        
        const wrapperRect = this.container.querySelector('.body-diagram-wrapper').getBoundingClientRect();
        const x = event.clientX - wrapperRect.left + 15;
        const y = event.clientY - wrapperRect.top - 35;
        
        tooltip.style.left = `${Math.max(5, x)}px`;
        tooltip.style.top = `${Math.max(5, y)}px`;
    }

    /**
     * Hide tooltip
     */
    hideTooltip() {
        const tooltip = this.container.querySelector('#muscle-tooltip');
        if (tooltip) {
            tooltip.classList.remove('visible');
        }
    }

    // ========================================================================
    // PUBLIC API
    // ========================================================================

    /**
     * Get selected muscle canonical keys
     */
    getSelectedMuscleIds() {
        return Array.from(this.selectedMuscles);
    }

    /**
     * Get selected muscle display names
     */
    getSelectedMuscleNames() {
        return this.getSelectedMuscleIds().map(id => MUSCLE_LABELS[id] || id);
    }

    /**
     * Get selected muscles mapped to backend names
     */
    getSelectedMusclesForBackend() {
        const backendMuscles = new Set();
        this.selectedMuscles.forEach(id => {
            const backendName = MUSCLE_TO_BACKEND[id];
            if (backendName) {
                backendMuscles.add(backendName);
            }
        });
        return Array.from(backendMuscles);
    }

    /**
     * Get current view mode
     */
    getViewMode() {
        return this.viewMode;
    }

    /**
     * Set selections programmatically
     */
    setSelection(muscleIds) {
        this.selectedMuscles = new Set(muscleIds);
        this.updateAllRegionStates();
        this.renderLegend();
        this.updateSummary();
    }

    /**
     * Enable/disable debug mode
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        this.updateAllRegionStates();
        this.renderLegend();
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

window.MuscleSelector = MuscleSelector;
window.MUSCLE_LABELS = MUSCLE_LABELS;
window.MUSCLE_TO_BACKEND = MUSCLE_TO_BACKEND;
window.SIMPLE_TO_ADVANCED_MAP = SIMPLE_TO_ADVANCED_MAP;
window.ADVANCED_TO_SIMPLE_MAP = ADVANCED_TO_SIMPLE_MAP;
window.VENDOR_SLUG_TO_CANONICAL = VENDOR_SLUG_TO_CANONICAL;
