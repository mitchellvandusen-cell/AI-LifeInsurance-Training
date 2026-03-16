/**
 * Mobile Navigation Component
 * Injects mobile header, bottom nav, and slide-out drawer into the page.
 * Call initMobileNav() after DOM is ready.
 */

function initMobileNav(activePage) {
    // Don't inject on public pages (index, login, register)
    if (!activePage) return;

    // ── Mobile Header (top bar) ────────────────────────────────
    const header = document.createElement('div');
    header.className = 'mobile-header';
    header.innerHTML = `
        <a href="/dashboard" class="mobile-logo"><span class="logo-accent">InsuranceGrokBot</span> Training</a>
        <div style="display:flex;align-items:center;gap:0.5rem;">
            <button class="theme-toggle-btn" onclick="toggleTheme()" aria-label="Toggle theme"></button>
            <button class="mobile-menu-btn" onclick="toggleMobileDrawer()" aria-label="Menu">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            </button>
        </div>
    `;
    document.body.prepend(header);

    // ── Bottom Tab Bar (5 primary tabs) ────────────────────────
    const nav = document.createElement('nav');
    nav.className = 'mobile-nav';
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Main navigation');

    const tabs = [
        { href: '/dashboard', label: 'Home', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>', id: 'dashboard' },
        { href: '/training', label: 'Train', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10,8 16,12 10,16"/></svg>', id: 'training' },
        { href: '/analytics', label: 'Stats', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>', id: 'analytics' },
        { href: '/report-cards', label: 'Reports', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>', id: 'report-cards' },
        { href: '#', label: 'More', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>', id: 'more', onclick: 'toggleMobileDrawer(); return false;' },
    ];

    nav.innerHTML = `<div class="mobile-nav-inner">${tabs.map(t => `
        <a href="${t.href}" class="mobile-nav-item${t.id === activePage ? ' active' : ''}"
           ${t.onclick ? 'onclick="' + t.onclick + '"' : ''}>
            ${t.icon}
            <span>${t.label}</span>
        </a>
    `).join('')}</div>`;
    document.body.appendChild(nav);

    // ── Slide-out Drawer (secondary links) ─────────────────────
    const overlay = document.createElement('div');
    overlay.className = 'mobile-drawer-overlay';
    overlay.id = 'mobileDrawerOverlay';
    overlay.onclick = closeMobileDrawer;

    const drawer = document.createElement('div');
    drawer.className = 'mobile-drawer';
    drawer.id = 'mobileDrawer';

    const drawerLinks = [
        { href: '/dashboard', label: 'Dashboard', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>', id: 'dashboard' },
        { href: '/training', label: 'Start Training', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10,8 16,12 10,16"/></svg>', id: 'training' },
        { href: '/analytics', label: 'Analytics', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>', id: 'analytics' },
        { href: '/report-cards', label: 'Report Cards', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>', id: 'report-cards' },
        { href: '/homework', label: 'Homework', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>', id: 'homework' },
        { href: '/scripts', label: 'Script Practice', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>', id: 'scripts' },
        { href: '/recordings', label: 'Call Recordings', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>', id: 'recordings' },
        { href: '/billing', label: 'Billing', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>', id: 'billing' },
        { href: '/settings', label: 'Settings', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>', id: 'settings' },
    ];

    drawer.innerHTML = `
        <div class="mobile-drawer-header">
            <h3>Menu</h3>
            <button class="mobile-drawer-close" onclick="closeMobileDrawer()" aria-label="Close menu">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        </div>
        <div class="mobile-drawer-links">
            ${drawerLinks.map(l => `
                <a href="${l.href}" class="${l.id === activePage ? 'active' : ''}">
                    ${l.icon}
                    ${l.label}
                </a>
            `).join('')}
        </div>
        <div class="mobile-drawer-footer">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                <div class="sidebar-username" id="mobileUserName"></div>
                <button class="theme-toggle-btn" onclick="toggleTheme()" aria-label="Toggle theme"></button>
            </div>
            <a href="#" onclick="API.logout(); return false;" class="sidebar-signout">Sign out</a>
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(drawer);

    // Sync user name into mobile drawer
    const desktopName = document.getElementById('userName');
    const mobileName = document.getElementById('mobileUserName');
    if (desktopName && mobileName) {
        const observer = new MutationObserver(() => {
            mobileName.textContent = desktopName.textContent;
        });
        observer.observe(desktopName, { childList: true, characterData: true, subtree: true });
    }
}

function toggleMobileDrawer() {
    const overlay = document.getElementById('mobileDrawerOverlay');
    const drawer = document.getElementById('mobileDrawer');
    if (!overlay || !drawer) return;
    const isOpen = drawer.classList.contains('open');
    if (isOpen) {
        closeMobileDrawer();
    } else {
        overlay.classList.add('open');
        drawer.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
}

function closeMobileDrawer() {
    const overlay = document.getElementById('mobileDrawerOverlay');
    const drawer = document.getElementById('mobileDrawer');
    if (overlay) overlay.classList.remove('open');
    if (drawer) drawer.classList.remove('open');
    document.body.style.overflow = '';
}
