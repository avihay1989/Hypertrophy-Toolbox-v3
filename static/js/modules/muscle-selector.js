/**
 * Muscle Group Selector Module v3.0
 * SVG-based anatomically accurate body diagram for muscle group selection.
 *
 * A single MuscleMap (melihcolpan/MuscleMap, MIT) anatomy figure is used for
 * both front and back; regions ship pre-canonicalized `data-canonical-muscles`.
 *
 * Features:
 * - SVG muscle regions with canonical keys baked into data attributes
 * - Front/Back tab navigation
 * - Bilateral synchronization (both sides highlight/select together)
 * - Group → leaf flattening via SIMPLE_TO_ADVANCED_MAP; backend mapping for the
 *   /generate_starter_plan priority_muscles payload
 * - Debug mode for development
 */

/**
 * Simple → Advanced mapping.
 * When simple group is selected, ALL children become selected.
 * When switching Advanced → Simple, parent shows selected if ANY child is selected.
 */
// Advanced mode uses the MuscleMap (melihcolpan/MuscleMap, MIT) anatomy art.
// Its clean, human-shaped regions are parent-level, so each simple group maps
// to MuscleMap's actual muscle region(s) rather than the old fine-grained
// sub-muscle taxonomy. Leaf keys here MUST match the data-canonical-muscles
// values emitted by scripts/build_musclemap_svgs.py into the advanced SVGs.
// `upper-back` and `hip-abductors` have no distinct MuscleMap geometry (the
// lat-wing/glute regions cover them) so they are legend-only — clickable in
// the checklist, no figure region. See static/bodymaps/hypertrophy-advanced/.
const SIMPLE_TO_ADVANCED_MAP = {
    // Front body - Simple groups
    'front-shoulders': ['front-deltoid'],
    'chest': ['chest'],
    'biceps': ['biceps'],
    'forearms': ['forearms'],
    'abdominals': ['abs'],
    'obliques': ['obliques'],
    'quads': ['quadriceps'],
    'adductors': ['adductors'],  // Inner thigh
    'neck': ['neck'],

    // Back body - Simple groups
    'rear-shoulders': ['rear-deltoid'],
    'traps': ['trapezius'],
    'upper-back': ['upper-back'],      // legend-only (no MuscleMap region)
    'lats': ['lats'],
    'lowerback': ['lower-back'],
    'triceps': ['triceps'],
    'glutes': ['gluteal'],
    'hip-abductors': ['hip-abductors'],  // legend-only (no MuscleMap region)
    'hamstrings': ['hamstring'],

    // Shared
    'calves': ['calves']
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
    
    // ===== ADVANCED VIEW LABELS (MuscleMap leaf keys) =====
    'front-deltoid': 'Front Delts',
    'rear-deltoid': 'Rear Delts',
    'abs': 'Abs',
    'quadriceps': 'Quadriceps',
    'trapezius': 'Trapezius',
    'lower-back': 'Lower Back',
    'gluteal': 'Glutes',
    'hamstring': 'Hamstrings'
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
    
    // Advanced keys → Backend (MuscleMap leaf keys). Display-name style matches
    // the simple keys above so /generate_starter_plan priority targeting is
    // unchanged from the prior taxonomy.
    'front-deltoid': 'Front Delts',
    'rear-deltoid': 'Rear Delts',
    'abs': 'Abs',
    'quadriceps': 'Quads',
    'trapezius': 'Traps',
    'lower-back': 'Lower Back',
    'gluteal': 'Glutes',
    'hamstring': 'Hamstrings'
};

/**
 * SVG file path per body side. A single MuscleMap (melihcolpan/MuscleMap, MIT)
 * anatomy figure is used for both front and back; regions ship
 * pre-canonicalized `data-canonical-muscles` keyed to SIMPLE_TO_ADVANCED_MAP
 * leaves. See static/bodymaps/hypertrophy-advanced/README.md.
 */
const SVG_PATHS = {
    front: '/static/bodymaps/hypertrophy-advanced/body_anterior.svg',
    back: '/static/bodymaps/hypertrophy-advanced/body_posterior.svg'
};

function getSvgPath(side) {
    return SVG_PATHS[side];
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
        this.bodySide = options.bodySide || 'front';
        this.debugMode = options.debug || false;

        // Selections are stored as advanced (leaf) muscle keys.
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
        const svgPath = getSvgPath(this.bodySide);
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
     * Get all canonical keys associated with a region from its
     * `data-canonical-muscles`. MuscleMap regions are single-key; the
     * comma-split also supports multi-key regions generically.
     */
    getCanonicalKeys(region) {
        const plural = region.dataset.canonicalMuscles;
        if (plural) {
            return plural.split(',').map(k => k.trim()).filter(Boolean);
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
     * Attach event listeners to muscle region paths. Clicking and hovering
     * operate on the full key set of a region (arrays are plumbed through
     * everywhere so multi-key regions would also work).
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
        
        if (isParentKey) {
            // Toggle ALL leaf children of the group.
            const children = SIMPLE_TO_ADVANCED_MAP[muscleKey] || [muscleKey];
            const allSelected = children.every(child => this.selectedMuscles.has(child));
            if (allSelected) {
                children.forEach(child => this.selectedMuscles.delete(child));
            } else {
                children.forEach(child => this.selectedMuscles.add(child));
            }
        } else {
            // Leaf key with no children — toggle directly.
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
            </div>
            <div class="legend-items">
        `;

        // Flat list of muscle groups for the current side.
        const muscleKeys = musclesForSide.filter(key => MUSCLE_LABELS[key]);
        legendHTML += muscleKeys.map(key => this.renderSimpleLegendItem(key)).join('');

        legendHTML += '</div>';
        legendContainer.innerHTML = legendHTML;

        // Attach legend item event listeners
        legendContainer.querySelectorAll('.legend-item').forEach(item => {
            const muscleKey = item.dataset.muscle;

            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMuscle(muscleKey);
            });

            item.addEventListener('mouseenter', () => this.handleMuscleHover(muscleKey, true));
            item.addEventListener('mouseleave', () => this.handleMuscleHover(muscleKey, false));
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
