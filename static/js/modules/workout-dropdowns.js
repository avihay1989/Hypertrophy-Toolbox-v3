/**
 * Workout Plan Dropdowns - Progressive Enhancement
 * Modern 2025 dropdown enhancement for native <select> elements
 * Scoped to #workout[data-page="workout-plan"] container
 */

// Global registry to track all enhanced dropdowns
const dropdownRegistry = new Set();

export function initializeWorkoutDropdowns() {
  const workoutContainer = document.getElementById('workout');
  if (!workoutContainer || workoutContainer.getAttribute('data-page') !== 'workout-plan') {
    return;
  }
  
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SELECTOR_SELECT = '.form-select.uniform-dropdown, .filter-dropdown, .routine-dropdown, .exercise-dropdown';
  const selects = workoutContainer.querySelectorAll(SELECTOR_SELECT);
  
  selects.forEach(select => {
    // Skip if already enhanced
    if (select.closest('.wpdd')) {
      return;
    }
    
    enhanceSelect(select, prefersReducedMotion);
  });
}

// Close all open dropdowns except the one specified
function closeAllDropdowns(exceptContainer = null) {
  dropdownRegistry.forEach(dropdownData => {
    if (dropdownData.container !== exceptContainer) {
      dropdownData.closeDropdown(false);
    }
  });
}

function enhanceSelect(select, prefersReducedMotion) {
  const container = document.createElement('div');
  container.className = 'wpdd';
  container.setAttribute('data-role', 'dropdown');
  
  // Create button
  const button = document.createElement('button');
  button.className = 'wpdd-button';
  button.type = 'button';
  button.setAttribute('aria-haspopup', 'listbox');
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('id', `${select.id || `wpdd-${Date.now()}`}_button`);
  button.setAttribute('aria-controls', `${button.id}_listbox`);
  
  const buttonText = document.createElement('span');
  buttonText.className = 'wpdd-button-text';
  button.appendChild(buttonText);
  
  // Caret icon (SVG inline)
  const caret = document.createElement('span');
  caret.className = 'wpdd-caret';
  caret.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  caret.setAttribute('aria-hidden', 'true');
  button.appendChild(caret);
  
  // Create popover
  const popover = document.createElement('ul');
  popover.className = 'wpdd-popover';
  popover.setAttribute('role', 'listbox');
  popover.setAttribute('id', `${button.id}_listbox`);
  popover.setAttribute('tabindex', '-1');
  popover.setAttribute('hidden', '');
  
  // Wrap native select and make it hidden but functional
  select.classList.add('wpdd-native');
  select.setAttribute('aria-hidden', 'true');
  
  // Copy classes from select to button for color hints mutation
  if (select.classList.contains('filter-dropdown')) {
    button.classList.add('wpdd-filter');
  }
  if (select.classList.contains('routine-dropdown')) {
    button.classList.add('wpdd-routine');
  }
  if (select.classList.contains('exercise-dropdown')) {
    button.classList.add('wpdd-exercise');
  }
  
  // Insert container before select
  select.parentNode.insertBefore(container, select);
  container.appendChild(button);
  // Append popover to document.body to avoid fixed positioning issues with transformed ancestors
  document.body.appendChild(popover);
  container.appendChild(select);
  
  // Store reference to popover on container for cleanup
  container._popoverElement = popover;
  
  // Build options from select
  const options = buildOptions(select, popover);
  
  // Update button text
  updateButtonText(button, select);
  
  // State
  let activeIndex = -1;
  let searchQuery = '';
  let searchTimeout = null;
  
  // Open/close handlers
  function openDropdown() {
    // Close all other dropdowns first
    closeAllDropdowns(container);
    
    button.setAttribute('aria-expanded', 'true');
    popover.removeAttribute('hidden');
    
    // Focus management
    activeIndex = getSelectedIndex();
    updateActiveOption();
    
    // Position popover
    positionPopover(popover, button);
    
    // Lock body scroll on mobile
    if (window.innerWidth <= 768) {
      document.body.style.overflow = 'hidden';
    }
    
    // Focus first option or search
    const searchInput = popover.querySelector('.wpdd-search');
    if (searchInput) {
      setTimeout(() => searchInput.focus(), 50);
    } else if (options.length > 0) {
      activeIndex = activeIndex >= 0 ? activeIndex : 0;
      updateActiveOption();
    }
  }
  
  function closeDropdown(focusButton = true) {
    button.setAttribute('aria-expanded', 'false');
    popover.setAttribute('hidden', '');
    activeIndex = -1;
    searchQuery = '';
    
    // Unlock body scroll
    document.body.style.overflow = '';
    
    // Clear search if exists
    const searchInput = popover.querySelector('.wpdd-search');
    if (searchInput) {
      searchInput.value = '';
      filterOptions('');
    }
    
    if (focusButton) {
      button.focus();
    }
  }
  
  // Button click
  button.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const isOpen = button.getAttribute('aria-expanded') === 'true';
    if (isOpen) {
      closeDropdown();
    } else {
      openDropdown();
    }
  });
  
  // Keyboard on button
  button.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (button.getAttribute('aria-expanded') === 'false') {
        openDropdown();
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        activeIndex = getSelectedIndex();
        if (e.key === 'ArrowDown') {
          activeIndex = Math.min(activeIndex + 1, options.length - 1);
          while (activeIndex < options.length - 1 && options[activeIndex]?.disabled) {
            activeIndex++;
          }
        } else {
          activeIndex = Math.max(activeIndex - 1, 0);
          while (activeIndex > 0 && options[activeIndex]?.disabled) {
            activeIndex--;
          }
        }
        updateActiveOption();
        scrollToOption(activeIndex);
      }
    } else if (e.key === 'Escape') {
      closeDropdown();
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      // Typeahead
      searchQuery += e.key.toLowerCase();
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => { searchQuery = ''; }, 1000);
      
      const matchingIndex = options.findIndex((opt, idx) => {
        const text = opt.element.textContent.trim().toLowerCase();
        return text.startsWith(searchQuery) && !opt.disabled;
      });
      
      if (matchingIndex >= 0) {
        activeIndex = matchingIndex;
        updateActiveOption();
        scrollToOption(activeIndex);
      }
    }
  });
  
  // Keyboard on popover
  popover.addEventListener('keydown', (e) => {
    // Allow typing in search input (don't intercept space, etc.)
    const isSearchInput = e.target.classList.contains('wpdd-search');
    
    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        closeDropdown();
        break;
      case 'ArrowDown':
        e.preventDefault();
        do {
          activeIndex = Math.min(activeIndex + 1, options.length - 1);
        } while (activeIndex < options.length - 1 && options[activeIndex].disabled);
        updateActiveOption();
        scrollToOption(activeIndex);
        break;
      case 'ArrowUp':
        e.preventDefault();
        do {
          activeIndex = Math.max(activeIndex - 1, 0);
        } while (activeIndex > 0 && options[activeIndex].disabled);
        updateActiveOption();
        scrollToOption(activeIndex);
        break;
      case 'Home':
        // Allow Home key in search input to move cursor
        if (isSearchInput) return;
        e.preventDefault();
        activeIndex = 0;
        while (activeIndex < options.length - 1 && options[activeIndex]?.disabled) {
          activeIndex++;
        }
        updateActiveOption();
        scrollToOption(activeIndex);
        break;
      case 'End':
        // Allow End key in search input to move cursor
        if (isSearchInput) return;
        e.preventDefault();
        activeIndex = options.length - 1;
        while (activeIndex > 0 && options[activeIndex]?.disabled) {
          activeIndex--;
        }
        updateActiveOption();
        scrollToOption(activeIndex);
        break;
      case 'Enter':
        e.preventDefault();
        if (activeIndex >= 0 && options[activeIndex] && !options[activeIndex].disabled) {
          selectOption(options[activeIndex]);
        }
        break;
      case ' ':
        // Allow space in search input for multi-word searches
        if (isSearchInput) return;
        e.preventDefault();
        if (activeIndex >= 0 && options[activeIndex] && !options[activeIndex].disabled) {
          selectOption(options[activeIndex]);
        }
        break;
    }
  });
  
  // Option click
  popover.addEventListener('click', (e) => {
    // Stop propagation to prevent document-level handlers from interfering
    // This ensures the change event and subsequent toast notification work reliably
    e.stopPropagation();
    
    const option = e.target.closest('[role="option"], .wpdd-option');
    if (option && !option.classList.contains('is-disabled')) {
      const index = Array.from(popover.querySelectorAll('[role="option"], .wpdd-option')).indexOf(option);
      if (index >= 0 && options[index]) {
        selectOption(options[index]);
      }
    }
  });
  
  // Register this dropdown in the global registry
  const dropdownData = {
    container: container,
    closeDropdown: closeDropdown,
    button: button,
    popover: popover,
    positionPopover: () => positionPopover(popover, button)
  };
  dropdownRegistry.add(dropdownData);
  
  // Reposition on scroll/resize when open
  const repositionHandler = () => {
    if (button.getAttribute('aria-expanded') === 'true') {
      positionPopover(popover, button);
    }
  };
  
  // Close on outside click - handle globally
  const outsideClickHandler = (e) => {
    if (button.getAttribute('aria-expanded') === 'true' && 
        !container.contains(e.target) && 
        !popover.contains(e.target)) {
      closeDropdown(false);
    }
  };
  
  window.addEventListener('scroll', repositionHandler, true);
  window.addEventListener('resize', repositionHandler);
  document.addEventListener('click', outsideClickHandler);
  
  // Store cleanup handlers
  container._cleanupHandler = () => {
    dropdownRegistry.delete(dropdownData);
    window.removeEventListener('scroll', repositionHandler, true);
    window.removeEventListener('resize', repositionHandler);
    document.removeEventListener('click', outsideClickHandler);
    if (container._optionsObserver) {
      container._optionsObserver.disconnect();
    }
    // Remove popover from document.body
    if (popover.parentNode) {
      popover.parentNode.removeChild(popover);
    }
  };
  
  // Update when native select changes (from outside)
  select.addEventListener('change', () => {
    updateButtonText(button, select);
    activeIndex = getSelectedIndex();
    updateActiveOption();
  });
  
  // Watch for option changes in the native select (e.g., when filters update the dropdown)
  const rebuildOptions = () => {
    // Clear existing options
    popover.innerHTML = '';
    
    // Rebuild options from the updated native select
    const newOptions = buildOptions(select, popover);
    
    // Update options array reference
    options.length = 0;
    options.push(...newOptions);
    
    // Reset active index
    activeIndex = getSelectedIndex();
    updateActiveOption();
    
    // Update button text
    updateButtonText(button, select);
  };
  
  // Listen for custom rebuild event
  select.addEventListener('wpdd-rebuild', rebuildOptions);
  
  // Use MutationObserver to watch for option changes
  const optionsObserver = new MutationObserver((mutations) => {
    let shouldRebuild = false;
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes') {
        shouldRebuild = true;
      }
      if (mutation.type === 'childList' && (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0)) {
        shouldRebuild = true;
      }
    });
    if (shouldRebuild) {
      // Use setTimeout to ensure DOM is fully updated
      setTimeout(rebuildOptions, 0);
    }
  });
  
  // Observe the select element for option changes
  optionsObserver.observe(select, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled'] });
  
  // Store observer for cleanup
  container._optionsObserver = optionsObserver;
  
  // Helper functions
  function buildOptions(select, popover) {
    const options = [];
    let currentOptgroup = null;
    
    Array.from(select.options).forEach((option, index) => {
      if (option.parentElement.tagName === 'OPTGROUP') {
        const optgroup = option.parentElement;
        if (currentOptgroup !== optgroup) {
          currentOptgroup = optgroup;
          const optgroupLabel = document.createElement('li');
          optgroupLabel.className = 'wpdd-optgroup-label';
          optgroupLabel.textContent = optgroup.label;
          optgroupLabel.setAttribute('role', 'presentation');
          popover.appendChild(optgroupLabel);
        }
      }
      
      const li = document.createElement('li');
      li.className = 'wpdd-option';
      li.setAttribute('role', 'option');
      li.setAttribute('id', `opt_${select.id || 'select'}_${index}`);
      
      if (option.disabled) {
        li.classList.add('is-disabled');
        li.setAttribute('aria-disabled', 'true');
      }
      
      // Preserve option classes
      if (option.className) {
        li.classList.add(...option.className.split(' '));
      }
      
      li.textContent = option.textContent.trim();
      li.setAttribute('data-value', option.value);
      
      popover.appendChild(li);
      
      options.push({
        element: li,
        option: option,
        value: option.value,
        text: option.textContent.trim(),
        disabled: option.disabled,
        index: index
      });
    });
    
    // Add search if more than 12 options
    if (options.length > 12) {
      // Create search container with count indicator
      const searchContainer = document.createElement('div');
      searchContainer.className = 'wpdd-search-container';
      
      const searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.className = 'wpdd-search';
      searchInput.setAttribute('placeholder', 'Search...');
      searchInput.setAttribute('aria-label', 'Search options');
      
      // Add count indicator showing total and visible count
      const countIndicator = document.createElement('span');
      countIndicator.className = 'wpdd-count-indicator';
      countIndicator.textContent = `${options.length} total`;
      countIndicator.setAttribute('aria-live', 'polite');
      
      let debounceTimer;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          filterOptions(e.target.value);
          // Update count indicator
          const visibleCount = options.filter(opt => opt.element.style.display !== 'none').length;
          if (e.target.value) {
            countIndicator.textContent = `${visibleCount} of ${options.length}`;
          } else {
            countIndicator.textContent = `${options.length} total`;
          }
        }, 150);
      });
      
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          activeIndex = 0;
          updateActiveOption();
          scrollToOption(activeIndex);
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeDropdown();
        }
      });
      
      searchContainer.appendChild(searchInput);
      searchContainer.appendChild(countIndicator);
      popover.insertBefore(searchContainer, popover.firstChild);
    }
    
    return options;
  }
  
  function filterOptions(query) {
    const normalizedQuery = query.toLowerCase();
    options.forEach(opt => {
      const matches = opt.text.toLowerCase().includes(normalizedQuery);
      opt.element.style.display = matches ? '' : 'none';
      if (!matches) {
        opt.element.classList.remove('is-active');
        opt.element.setAttribute('aria-selected', 'false');
      }
    });
    
    // Update active index
    const visibleOptions = options.filter(opt => opt.element.style.display !== 'none');
    if (visibleOptions.length > 0) {
      activeIndex = visibleOptions[0].index;
      updateActiveOption();
    }
  }
  
  function getSelectedIndex() {
    return Array.from(select.options).findIndex(opt => opt.selected);
  }
  
  function updateButtonText(button, select) {
    const buttonText = button.querySelector('.wpdd-button-text');
    const selectedOption = select.options[select.selectedIndex];
    button.disabled = select.disabled;
    button.setAttribute('aria-disabled', select.disabled ? 'true' : 'false');
    
    if (selectedOption && selectedOption.value && !selectedOption.disabled) {
      buttonText.textContent = selectedOption.textContent.trim();
      buttonText.classList.remove('wpdd-placeholder');
      
      // Sync filter-active class to button for filter dropdowns
      if (button.classList.contains('wpdd-filter')) {
        button.classList.add('filter-active');
      }
    } else {
      // Find first non-disabled option for placeholder, or use default
      const firstOption = Array.from(select.options).find(opt => !opt.disabled);
      buttonText.textContent = firstOption?.textContent || select.options[0]?.textContent || 'Select...';
      buttonText.classList.add('wpdd-placeholder');
      
      // Remove filter-active class when no value selected
      if (button.classList.contains('wpdd-filter')) {
        button.classList.remove('filter-active');
      }
    }
  }
  
  function updateActiveOption() {
    options.forEach((opt, idx) => {
      const isActive = idx === activeIndex;
      const isSelected = opt.option.selected;
      
      opt.element.classList.toggle('is-active', isActive);
      opt.element.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      opt.element.setAttribute('id', `opt_${select.id || 'select'}_${idx}`);
      
      if (isActive) {
        button.setAttribute('aria-activedescendant', opt.element.id);
      }
    });
  }
  
  function scrollToOption(index) {
    if (index >= 0 && options[index]) {
      options[index].element.scrollIntoView({ block: 'nearest', behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    }
  }
  
  function selectOption(opt) {
    select.value = opt.value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
    updateButtonText(button, select);
    closeDropdown();
  }
  
  function positionPopover(popover, button) {
    // Use getBoundingClientRect for positioning relative to viewport
    const buttonRect = button.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const spaceBelow = viewportHeight - buttonRect.bottom;
    const spaceAbove = buttonRect.top;
    
    // Always use fixed positioning to escape overflow:hidden parents
    popover.style.position = 'fixed';
    
    // On mobile, use fixed positioning at bottom
    if (window.innerWidth <= 768) {
      popover.style.bottom = '0';
      popover.style.left = '0';
      popover.style.right = '0';
      popover.style.width = '100%';
      popover.style.maxHeight = '70vh';
      return;
    }
    
    // Desktop: default to positioning below the control for consistency
    popover.style.bottom = '';
    popover.style.right = '';
    
    let openDirection = 'down';
    if (spaceBelow < 140 && spaceAbove > spaceBelow) {
      openDirection = 'up';
    }

    let top;
    let maxHeight;
    if (openDirection === 'up') {
      maxHeight = Math.min(280, Math.max(spaceAbove - 12, 160));
      top = Math.max(10, buttonRect.top - maxHeight - 6);
      if (top === 10) {
        maxHeight = buttonRect.top - top - 6;
      }
      popover.style.marginTop = '0';
      popover.style.marginBottom = '6px';
    } else {
      maxHeight = Math.min(280, Math.max(spaceBelow - 12, 160));
      // Ensure we have a positive height fallback
      if (maxHeight < 160) {
        maxHeight = Math.max(spaceBelow - 12, 120);
      }
      top = Math.max(10, buttonRect.bottom + 6);
      popover.style.marginTop = '6px';
      popover.style.marginBottom = '0';
    }

    popover.style.top = `${top}px`;
    popover.style.left = `${Math.max(10, Math.min(buttonRect.left, viewportWidth - Math.max(220, buttonRect.width) - 10))}px`;
    popover.style.width = `${Math.max(220, Math.min(buttonRect.width, viewportWidth - 20))}px`;
    popover.style.maxHeight = `${Math.max(160, Math.min(320, maxHeight))}px`;
  }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeWorkoutDropdowns);
} else {
  initializeWorkoutDropdowns();
}

// Re-initialize if new selects are added dynamically
const observer = new MutationObserver(() => {
  initializeWorkoutDropdowns();
});

const workoutContainer = document.getElementById('workout');
if (workoutContainer) {
  observer.observe(workoutContainer, { childList: true, subtree: true });
}
