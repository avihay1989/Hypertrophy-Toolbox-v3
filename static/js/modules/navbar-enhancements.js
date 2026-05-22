/**
 * Navbar Enhancements - Modern 2025 Features
 * - Compact mode on scroll
 * - Mobile menu focus trap
 * - Body scroll lock
 * - Reduced motion support
 */

export function initializeNavbarEnhancements() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;
  
  const mobileMenuToggle = navbar.querySelector('.navbar-toggler, .nb-menu-btn');
  const mobileMenu = navbar.querySelector('#navbarNav');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  initializeDesktopHoverDropdowns(navbar);
  
  // Compact mode on scroll
  let lastScrollY = window.scrollY;
  const scrollThreshold = 80; // px (64-96px range recommended for smooth experience)
  
  function handleScroll() {
    const currentScrollY = window.scrollY;
    
    if (prefersReducedMotion) {
      // Instant toggle for reduced motion
      navbar.classList.toggle('nb-compact', currentScrollY > scrollThreshold);
    } else {
      // Smooth transition
      if (currentScrollY > scrollThreshold && !navbar.classList.contains('nb-compact')) {
        navbar.classList.add('nb-compact');
      } else if (currentScrollY <= scrollThreshold && navbar.classList.contains('nb-compact')) {
        navbar.classList.remove('nb-compact');
      }
    }
    
    lastScrollY = currentScrollY;
  }
  
  // Throttled scroll handler
  let ticking = false;
  function onScroll() {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        handleScroll();
        ticking = false;
      });
      ticking = true;
    }
  }
  
  window.addEventListener('scroll', onScroll, { passive: true });
  
  // Initialize compact state
  handleScroll();
  
  // Mobile menu enhancements
  if (mobileMenuToggle && mobileMenu) {
    // Track menu state
    let isMenuOpen = false;
    let focusableElements = [];
    let firstFocusableElement = null;
    let lastFocusableElement = null;
    
    // Get focusable elements within mobile menu
    function updateFocusableElements() {
      if (!mobileMenu.classList.contains('show')) return;
      
      focusableElements = Array.from(
        mobileMenu.querySelectorAll(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter(el => {
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden';
      });
      
      firstFocusableElement = focusableElements[0] || null;
      lastFocusableElement = focusableElements[focusableElements.length - 1] || null;
    }
    
    // Trap focus within mobile menu
    function trapFocus(e) {
      if (!isMenuOpen || focusableElements.length === 0) return;
      
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          // Shift + Tab (backward)
          if (document.activeElement === firstFocusableElement) {
            e.preventDefault();
            lastFocusableElement?.focus();
          }
        } else {
          // Tab (forward)
          if (document.activeElement === lastFocusableElement) {
            e.preventDefault();
            firstFocusableElement?.focus();
          }
        }
      }
      
      // Close on Escape
      if (e.key === 'Escape' && isMenuOpen) {
        closeMobileMenu();
      }
    }
    
    // Body scroll lock
    function lockBodyScroll() {
      if (isMenuOpen) {
        document.body.style.overflow = 'hidden';
        // Add inert to main content if supported (with fallback)
        const mainContent = document.querySelector('.container-fluid:not(#navbar .container-fluid), main:not(#navbar)');
        if (mainContent) {
          try {
            if ('inert' in mainContent) {
              mainContent.setAttribute('inert', '');
            }
          } catch (e) {
            // Fallback: use aria-hidden instead
            mainContent.setAttribute('aria-hidden', 'true');
          }
        }
      }
    }
    
    function unlockBodyScroll() {
      document.body.style.overflow = '';
      const mainContent = document.querySelector('.container-fluid:not(#navbar .container-fluid), main:not(#navbar)');
      if (mainContent) {
        if (mainContent.hasAttribute('inert')) {
          mainContent.removeAttribute('inert');
        }
        if (mainContent.hasAttribute('aria-hidden')) {
          mainContent.removeAttribute('aria-hidden');
        }
      }
    }
    
    // Make unlockBodyScroll accessible for resize handler
    window.navbarUnlockBodyScroll = unlockBodyScroll;
    
    // Open mobile menu
    function openMobileMenu() {
      isMenuOpen = true;
      mobileMenu.classList.add('show');
      navbar.setAttribute('aria-expanded', 'true');
      mobileMenuToggle.setAttribute('aria-expanded', 'true');
      lockBodyScroll();
      updateFocusableElements();
      
      // Focus first element after a brief delay
      setTimeout(() => {
        firstFocusableElement?.focus();
      }, 100);
      
      // Add event listeners
      mobileMenu.addEventListener('keydown', trapFocus);
      document.addEventListener('keydown', trapFocus);
    }
    
    // Close mobile menu
    function closeMobileMenu() {
      isMenuOpen = false;
      mobileMenu.classList.remove('show');
      navbar.setAttribute('aria-expanded', 'false');
      mobileMenuToggle.setAttribute('aria-expanded', 'false');
      unlockBodyScroll();
      
      // Remove event listeners
      mobileMenu.removeEventListener('keydown', trapFocus);
      document.removeEventListener('keydown', trapFocus);
      
      // Return focus to toggle button
      mobileMenuToggle.focus();
    }
    
    // Handle Bootstrap collapse events (since we're using Bootstrap's collapse)
    mobileMenu.addEventListener('shown.bs.collapse', () => {
      openMobileMenu();
    });
    
    mobileMenu.addEventListener('hidden.bs.collapse', () => {
      closeMobileMenu();
    });
    
    // Close on overlay click (if clicking outside menu content)
    mobileMenu.addEventListener('click', (e) => {
      if (e.target === mobileMenu) {
        closeMobileMenu();
        mobileMenuToggle.click(); // Trigger Bootstrap collapse
      }
    });
    
    // Initial state check
    if (mobileMenu.classList.contains('show')) {
      openMobileMenu();
    }
  }
  
  // Handle window resize - close mobile menu on resize to desktop
  function handleResize() {
    if (window.innerWidth > 992 && mobileMenu && mobileMenu.classList.contains('show')) {
      mobileMenu.classList.remove('show');
      navbar.setAttribute('aria-expanded', 'false');
      mobileMenuToggle?.setAttribute('aria-expanded', 'false');
      if (window.navbarUnlockBodyScroll) {
        window.navbarUnlockBodyScroll();
      }
    }
  }
  
  window.addEventListener('resize', handleResize, { passive: true });
}

function initializeDesktopHoverDropdowns(navbar) {
  if (navbar.dataset.hoverDropdownsInitialized === 'true') return;
  navbar.dataset.hoverDropdownsInitialized = 'true';

  if (typeof bootstrap === 'undefined' || !bootstrap.Dropdown) return;

  const desktopHoverQuery = window.matchMedia('(hover: hover) and (pointer: fine) and (min-width: 992px)');
  const dropdowns = navbar.querySelectorAll('.dropdown');

  dropdowns.forEach((dropdown) => {
    const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
    const menu = dropdown.querySelector('.dropdown-menu');
    if (!toggle || !menu) return;

    const dropdownInstance = bootstrap.Dropdown.getOrCreateInstance(toggle);
    let hideTimer = null;

    function isDesktopHover() {
      return desktopHoverQuery.matches;
    }

    function clearHideTimer() {
      if (hideTimer) {
        window.clearTimeout(hideTimer);
        hideTimer = null;
      }
    }

    function openDropdown() {
      if (!isDesktopHover()) return;

      clearHideTimer();
      dropdown.classList.add('is-hover-open');
      dropdownInstance.show();
      toggle.setAttribute('aria-expanded', 'true');
    }

    function closeDropdown(delay = 160) {
      if (!isDesktopHover()) return;

      clearHideTimer();
      hideTimer = window.setTimeout(() => {
        dropdown.classList.remove('is-hover-open');
        dropdownInstance.hide();
        toggle.setAttribute('aria-expanded', 'false');
      }, delay);
    }

    dropdown.addEventListener('mouseenter', openDropdown);
    dropdown.addEventListener('mouseleave', () => closeDropdown());
    dropdown.addEventListener('focusin', openDropdown);
    dropdown.addEventListener('focusout', (event) => {
      if (!dropdown.contains(event.relatedTarget)) {
        closeDropdown(80);
      }
    });

    toggle.addEventListener('click', (event) => {
      if (!isDesktopHover()) return;

      event.preventDefault();
      event.stopPropagation();
      openDropdown();
    });

    toggle.addEventListener('keydown', (event) => {
      if (!isDesktopHover()) return;

      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openDropdown();
        menu.querySelector('.dropdown-item')?.focus();
      }

      if (event.key === 'Escape') {
        closeDropdown(0);
      }
    });

    menu.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeDropdown(0);
        toggle.focus();
      }
    });

    desktopHoverQuery.addEventListener('change', () => {
      dropdown.classList.remove('is-hover-open');
      dropdownInstance.hide();
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeNavbarEnhancements);
} else {
  initializeNavbarEnhancements();
}
