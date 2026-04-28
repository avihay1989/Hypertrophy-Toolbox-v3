export function initializeNavHighlighting() {
    const currentPath = window.location.pathname;
    
    // Normalize path - keep root path as '/' but remove trailing slashes for others
    const normalizedPath = currentPath === '/' ? '/' : 
        (currentPath.endsWith('/') ? currentPath.slice(0, -1) : currentPath);
    
    // Remove active class from all nav items first (scoped to #navbar)
    const navbar = document.getElementById('navbar');
    if (!navbar) return;
    
    navbar.querySelectorAll('.nav-link, .navbar-brand').forEach(link => {
        link.classList.remove('active');
    });
    
    const pathMap = {
        '/': 'nav-brand',
        '/workout_plan': 'nav-workout-plan',
        '/weekly_summary': 'nav-weekly-summary',
        '/session_summary': 'nav-session-summary',
        '/workout_log': 'nav-workout-log',
        '/progression': 'nav-progression-plan',
        '/volume_splitter': 'nav-volume-splitter',
        '/backup': 'nav-backup',
        '/user_profile': 'nav-user-profile'
    };
    
    // Add active class to current page's nav item
    const navId = pathMap[normalizedPath];
    if (navId) {
        const navItem = document.getElementById(navId);
        if (navItem) {
            navItem.classList.add('active');
        }
    }
}

// Initialize navbar highlighting both immediately and after DOM load
export function initializeNavbar() {
    // Initialize immediately if DOM is already loaded
    if (document.readyState === 'loading') {
        // Re-initialize after DOM content is loaded
        document.addEventListener('DOMContentLoaded', initializeNavHighlighting);
    } else {
        initializeNavHighlighting();
    }
    
    // Re-initialize after navigation (SPA or browser back/forward)
    window.addEventListener('popstate', initializeNavHighlighting);
    
    // Add load event listener for final initialization
    window.addEventListener('load', initializeNavHighlighting);
    
    // Optional: Support for programmatic navigation (if using SPA routing)
    // This allows other scripts to trigger navbar updates
    window.addEventListener('hashchange', initializeNavHighlighting);
}
