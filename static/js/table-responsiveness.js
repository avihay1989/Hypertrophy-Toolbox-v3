const TABLE_RESPONSIVENESS_DEBUG = false;
const tableDebugLog = (...args) => {
  if (TABLE_RESPONSIVENESS_DEBUG) {
    console.log(...args);
  }
};
const tableDebugTrace = (...args) => {
  if (TABLE_RESPONSIVENESS_DEBUG) {
    console.trace(...args);
  }
};

tableDebugLog('[TableResponsiveness] Version 2024-11-11-03 loaded');

/**
 * Table Responsiveness JavaScript
 * 
 * Provides:
 * - Column visibility toggles with localStorage persistence (Simple/Advanced mode)
 * - ResizeObserver-based dynamic rows-per-page calculation
 * - Accessibility-compliant interactions
 * 
 * Usage:
 *   TableResponsiveness.initColumnChooser(tableElement, 'workout_plan');
 *   TableResponsiveness.fitRowsToViewport('.tbl-wrap', { onPageSize: (rows) => updatePagination(rows) });
 */

(function () {
  'use strict';

  // Track last time any column chooser menu opened to avoid instant auto-close
  let lastMenuOpenTimestamp = 0;

  // ============================================================
  // UTILITY FUNCTIONS
  // ============================================================

  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const STORAGE_KEY = 'hypertrophy_tbl_prefs';
  const WORKOUT_PLAN_TABLE_KEY = 'workout_plan';

  /**
   * Get preferences from localStorage
   * @returns {Object} Preferences object
   */
  function getPrefs() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.warn('Failed to parse table preferences from localStorage:', error);
      return {};
    }
  }

  /**
   * Save preferences to localStorage
   * @param {Object} prefs - Preferences to save
   */
  function setPrefs(prefs) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch (error) {
      console.warn('Failed to save table preferences to localStorage:', error);
    }
  }

  /**
   * Debounce function to limit execution rate
   * @param {Function} func - Function to debounce
   * @param {number} wait - Wait time in milliseconds
   * @returns {Function} Debounced function
   */
  function debounce(func, wait = 250) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Ensure a shared controls container exists for the responsive table
   * @param {HTMLElement} wrapper - The table wrapper element
   * @returns {HTMLElement|null} Controls container element
   */
  function getOrCreateControlsContainer(wrapper) {
    if (!wrapper) {
      return null;
    }

    // Prefer controls container inside the wrapper so it stays visually tied to the table
    let controls = qs('.tbl-controls', wrapper);

    // If an older container exists on the parent, move it inside the wrapper
    if (!controls && wrapper.parentElement) {
      const parentControls = qs('.tbl-controls', wrapper.parentElement);
      if (parentControls) {
        controls = parentControls;
        wrapper.insertBefore(controls, wrapper.firstChild);
      }
    }

    if (!controls) {
      controls = document.createElement('div');
      controls.className = 'tbl-controls';
      wrapper.insertBefore(controls, wrapper.firstChild);
    }

    if (!controls.getAttribute('role')) {
      controls.setAttribute('role', 'toolbar');
      controls.setAttribute('aria-label', 'Table controls');
    }

    return controls;
  }

  // ============================================================
  // COLUMN CHOOSER (Simple/Advanced View Mode)
  // ============================================================

  // Columns to HIDE in Simple mode (these are shown only in Advanced mode)
  const ADVANCED_ONLY_COLUMNS = [
    'Tertiary Muscle',
    'Utility',
    'Movement Pattern',
    'Movement Subpattern',
    'Stabilizers',
    'Synergists'
  ];

  function normalizeViewMode(mode) {
    return mode === 'advanced' ? 'advanced' : 'simple';
  }

  function persistViewMode(pageKey, mode) {
    if (!pageKey) {
      return;
    }

    const prefs = getPrefs();
    if (!prefs[pageKey]) {
      prefs[pageKey] = {};
    }
    prefs[pageKey].viewMode = normalizeViewMode(mode);
    setPrefs(prefs);
  }

  function getEffectiveViewMode(pageKey) {
    if (
      pageKey === WORKOUT_PLAN_TABLE_KEY &&
      window.FilterViewMode &&
      typeof window.FilterViewMode.getViewMode === 'function'
    ) {
      return normalizeViewMode(window.FilterViewMode.getViewMode());
    }

    const prefs = getPrefs();
    return normalizeViewMode(prefs[pageKey]?.viewMode);
  }

  function getToggleElement(tableEl, pageKey) {
    const wrapper = tableEl?.closest('.tbl-wrap');
    if (!wrapper) {
      return null;
    }

    return qs('.tbl-view-mode-toggle[data-table-key="' + pageKey + '"]', wrapper);
  }

  /**
   * Initialize column chooser for a table (Simple/Advanced mode toggle)
   * @param {HTMLElement} tableEl - Table element
   * @param {string} pageKey - Unique identifier for the page (e.g., 'workout_plan')
   */
  function initColumnChooser(tableEl, pageKey) {
  tableDebugLog('[initColumnChooser] Starting for pageKey:', pageKey);
    
    if (!tableEl || !pageKey) {
      console.warn('initColumnChooser: tableEl and pageKey are required');
      return;
    }

    const wrapper = tableEl.closest('.tbl-wrap');
    if (!wrapper || !wrapper.parentElement) {
      console.warn('[initColumnChooser] No wrapper found');
      return;
    }

  // Check if already initialized for this specific table
  const existingChooser = qs('.tbl-view-mode-toggle[data-table-key="' + pageKey + '"]', wrapper);
    if (existingChooser) {
  tableDebugLog('[initColumnChooser] Already initialized for', pageKey, '- exiting');
      return; // Already initialized
    }
    
  tableDebugLog('[initColumnChooser] Creating new view mode toggle for', pageKey);
  tableDebugTrace('[initColumnChooser] Called from:');

    // Create view mode toggle UI
    const toggleEl = createViewModeToggleUI(tableEl, pageKey);
    if (!toggleEl) return;

    // Mark with page key to prevent duplicate initialization
    toggleEl.dataset.tableKey = pageKey;

    // Keep the workout-plan table synced with the global muscle naming mode.
    bindExternalViewModeSync(tableEl, pageKey);

    // Load preferences - default to 'simple' mode
    const currentMode = getEffectiveViewMode(pageKey);

    // Apply initial mode
    syncViewMode(tableEl, currentMode, pageKey, toggleEl);
  }

  /**
   * Create view mode toggle UI (Simple/Advanced button)
   * @param {HTMLElement} tableEl - Table element
   * @param {string} pageKey - Page identifier
   * @returns {HTMLElement} Toggle element
   */
  function createViewModeToggleUI(tableEl, pageKey) {
    const wrapper = tableEl.closest('.tbl-wrap');
    if (!wrapper) return null;

    const controls = getOrCreateControlsContainer(wrapper);
    if (!controls) return null;

    // Create toggle button
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'tbl-view-mode-toggle';
    toggle.setAttribute('data-view-mode-toggle', '');
    toggle.setAttribute('aria-pressed', 'false');
    toggle.innerHTML = '<i class="fas fa-columns" aria-hidden="true"></i> <span class="mode-text">Simple</span>';

    // Click handler
    toggle.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const currentMode = getEffectiveViewMode(pageKey);
      const newMode = currentMode === 'simple' ? 'advanced' : 'simple';
      
      tableDebugLog('[View Mode] Switching from', currentMode, 'to', newMode);

      // On workout plan, the global filter/muscle mode is the source of truth.
      if (
        pageKey === WORKOUT_PLAN_TABLE_KEY &&
        window.FilterViewMode &&
        typeof window.FilterViewMode.setViewMode === 'function'
      ) {
        window.FilterViewMode.setViewMode(newMode);
        return;
      }

      syncViewMode(tableEl, newMode, pageKey, toggle);
    });

    controls.appendChild(toggle);
    return toggle;
  }

  /**
   * Update view mode button appearance
   * @param {HTMLElement} button - Toggle button element
   * @param {string} mode - Current mode ('simple' or 'advanced')
   */
  function updateViewModeButton(button, mode) {
    if (!button) {
      return;
    }

    const modeText = button.querySelector('.mode-text');
    const icon = button.querySelector('i');
    const normalizedMode = normalizeViewMode(mode);
    
    button.dataset.viewMode = normalizedMode;

    if (normalizedMode === 'advanced') {
      if (modeText) modeText.textContent = 'Advanced';
      if (icon) {
        icon.className = 'fas fa-th';
      }
      button.setAttribute('aria-pressed', 'true');
      button.classList.add('active');
    } else {
      if (modeText) modeText.textContent = 'Simple';
      if (icon) {
        icon.className = 'fas fa-columns';
      }
      button.setAttribute('aria-pressed', 'false');
      button.classList.remove('active');
    }
  }

  function syncViewMode(tableEl, mode, pageKey, button = null) {
    const normalizedMode = normalizeViewMode(mode);
    persistViewMode(pageKey, normalizedMode);
    applyViewMode(tableEl, normalizedMode, pageKey);
    updateViewModeButton(button || getToggleElement(tableEl, pageKey), normalizedMode);
  }

  function bindExternalViewModeSync(tableEl, pageKey) {
    if (!tableEl || pageKey !== WORKOUT_PLAN_TABLE_KEY || tableEl.dataset.filterViewModeSync === 'true') {
      return;
    }

    tableEl.dataset.filterViewModeSync = 'true';
    document.addEventListener('filterViewModeChanged', (event) => {
      const mode = normalizeViewMode(event.detail?.mode);
      syncViewMode(tableEl, mode, pageKey);
    });
  }

  /**
   * Apply view mode to table (show/hide columns based on mode)
   * Uses CSS class on table so dynamically added rows inherit visibility
   * @param {HTMLElement} tableEl - Table element
   * @param {string} mode - View mode ('simple' or 'advanced')
   * @param {string} pageKey - Page identifier
   */
  function applyViewMode(tableEl, mode, pageKey) {
    tableDebugLog('[applyViewMode] Applying mode:', mode);
    
    // Use CSS class for column visibility so dynamic rows inherit it
    if (mode === 'simple') {
      tableEl.classList.add('tbl--view-simple');
      tableEl.classList.remove('tbl--view-advanced');
    } else {
      tableEl.classList.remove('tbl--view-simple');
      tableEl.classList.add('tbl--view-advanced');
    }
  }

  // Keep legacy function for backward compatibility (no-op for click handlers)
  function toggleColumn(tableEl, colIdentifier, show, pageKey) {
    tableDebugLog('[toggleColumn] Legacy call ignored - use view mode toggle instead');
  }

  /**
   * Apply column visibility to table
   * @param {HTMLElement} tableEl - Table element
   * @param {string} colIdentifier - Column identifier (data-label value)
   * @param {boolean} show - Whether to show the column
   */
  function applyColumnVisibility(tableEl, colIdentifier, show) {
  tableDebugLog('[applyColumnVisibility] Called with:', { colIdentifier, show });
    
    // Find the column index by matching the data-label in the header
    const headers = qsa('th[data-label]', tableEl);
    let columnIndex = -1;
    
    headers.forEach((th, index) => {
      if (th.getAttribute('data-label') === colIdentifier) {
        columnIndex = index;
  tableDebugLog('[applyColumnVisibility] Found column at index:', index, 'Header text:', th.textContent.trim());
      }
    });
    
    if (columnIndex === -1) {
      console.warn(`[applyColumnVisibility] Column with data-label "${colIdentifier}" not found`);
      return;
    }
    
    // Hide/show the header cell
    const header = headers[columnIndex];
    if (header) {
      header.style.display = show ? '' : 'none';
  tableDebugLog('[applyColumnVisibility] Header display set to:', header.style.display || 'default');
    }
    
    // Hide/show all corresponding body cells using nth-child selector
    // Note: nth-child is 1-indexed, and we need to account for the drag handle column
    const nthChildIndex = columnIndex + 2; // +1 for nth-child indexing, +1 for drag handle
  tableDebugLog('[applyColumnVisibility] Using nth-child selector:', nthChildIndex);
  const bodyCells = qsa(`tbody tr td:nth-child(${nthChildIndex})`, tableEl);
  tableDebugLog('[applyColumnVisibility] Found', bodyCells.length, 'body cells to toggle');
    bodyCells.forEach(cell => {
      cell.style.display = show ? '' : 'none';
    });
  }

  // ============================================================
  // DYNAMIC ROWS PER PAGE (ResizeObserver)
  // ============================================================

  /**
   * Automatically calculate optimal rows per page based on container height
   * @param {string|HTMLElement} containerSel - Container selector or element
   * @param {Object} opts - Options
   * @param {string} opts.headerSel - Header selector
   * @param {string} opts.toolbarSel - Toolbar selector
   * @param {string} opts.footerSel - Footer selector
   * @param {string} opts.rowSel - Row selector
   * @param {number} opts.rowHeight - Approximate row height in pixels
   * @param {number} opts.minRows - Minimum rows to show
   * @param {number} opts.maxRows - Maximum rows to show
   * @param {Function} opts.onPageSize - Callback when page size changes
   */
  function fitRowsToViewport(containerSel, opts = {}) {
    const {
      headerSel = '[data-tbl-header]',
      toolbarSel = '[data-tbl-toolbar]',
      footerSel = '[data-tbl-footer]',
      rowSel = 'tbody tr',
      rowHeight = 42,
      minRows = 10,
      maxRows = 100,
      onPageSize = null
    } = opts;

    const container = typeof containerSel === 'string' ? qs(containerSel) : containerSel;
    if (!container) {
      console.warn('fitRowsToViewport: container not found');
      return;
    }

    const calculatePageSize = debounce(() => {
      const containerHeight = container.clientHeight || container.offsetHeight;

      // Calculate fixed heights
      const headerEl = qs(headerSel, container);
      const toolbarEl = qs(toolbarSel, container);
      const footerEl = qs(footerSel, container);

      const headerHeight = headerEl?.offsetHeight || 0;
      const toolbarHeight = toolbarEl?.offsetHeight || 0;
      const footerHeight = footerEl?.offsetHeight || 0;

      // Calculate available height
      const availableHeight = containerHeight - headerHeight - toolbarHeight - footerHeight;

      // Calculate rows
      const calculatedRows = Math.floor(availableHeight / rowHeight);
      const optimalRows = Math.max(minRows, Math.min(maxRows, calculatedRows));

      // Call callback
      if (typeof onPageSize === 'function') {
        onPageSize(optimalRows);
      }
    }, 250);

    // Setup ResizeObserver
    const resizeObserver = new ResizeObserver(calculatePageSize);
    resizeObserver.observe(container);

    // Initial calculation
    calculatePageSize();

    // Return cleanup function
    return () => {
      resizeObserver.disconnect();
    };
  }

  // ============================================================
  // AUTO-INITIALIZATION
  // ============================================================

  /**
   * Auto-initialize responsive features on tables with data attributes
   */
  function autoInit() {
    // Find all tables with data-responsive attribute
    const tables = qsa('[data-table-responsive]');
    
    tables.forEach(table => {
      const pageKey = table.dataset.tableResponsive;
      if (!pageKey) return;

      // Initialize column chooser (Simple/Advanced mode)
      initColumnChooser(table, pageKey);

      // Initialize dynamic rows (if callback provided)
      const onPageSize = table.dataset.tableOnPageSize;
      if (onPageSize && window[onPageSize]) {
        const wrapper = table.closest('.tbl-wrap');
        if (wrapper) {
          fitRowsToViewport(wrapper, {
            onPageSize: window[onPageSize]
          });
        }
      }
    });
  }

  // Auto-init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  // ============================================================
  // PUBLIC API
  // ============================================================

  window.TableResponsiveness = {
    initColumnChooser,
    fitRowsToViewport,
    getPrefs,
    setPrefs,
    autoInit
  };

})();
