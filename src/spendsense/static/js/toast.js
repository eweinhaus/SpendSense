/**
 * Toast Notification System - Phase 8D
 * Simple toast notification implementation using design system
 */

(function() {
    'use strict';

    // Create toast container if it doesn't exist
    function getToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Auto-dismiss duration in milliseconds (default: 5000)
     */
    function showToast(message, type = 'info', duration = 5000) {
        const container = getToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
        
        // Toast content
        toast.innerHTML = `
            <span>${escapeHtml(message)}</span>
            <button class="toast-close" aria-label="Close notification" onclick="this.parentElement.remove()">
                ×
            </button>
        `;
        
        container.appendChild(toast);
        
        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.style.animation = 'slideIn 0.3s ease reverse';
                    setTimeout(() => toast.remove(), 300);
                }
            }, duration);
        }
        
        // Focus management for accessibility
        toast.focus();
        
        return toast;
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose to global scope
    window.showToast = showToast;
    
    // Convenience functions
    window.showSuccessToast = (message, duration) => showToast(message, 'success', duration);
    window.showErrorToast = (message, duration) => showToast(message, 'error', duration);
    window.showWarningToast = (message, duration) => showToast(message, 'warning', duration);
    window.showInfoToast = (message, duration) => showToast(message, 'info', duration);
})();

