/**
 * Golden Eye - Auth JavaScript (Legacy - Not Used)
 * This file is kept for compatibility but auth is no longer required
 */

// Redirect to dashboard since we don't need auth
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on an auth page and redirect to dashboard
    const isAuthPage = window.location.pathname.includes('index.html') ||
        window.location.pathname.includes('register.html') ||
        window.location.pathname.includes('forgot-password.html') ||
        window.location.pathname === '/';

    if (isAuthPage) {
        window.location.href = '/dashboard.html';
    }
});
