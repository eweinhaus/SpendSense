/**
 * Consent toggle functionality for SpendSense MVP
 */

function toggleConsent(userId) {
    const checkbox = document.getElementById('consent-checkbox');
    const consent = checkbox.checked;
    const originalState = !consent; // Store original state in case of error
    
    // Show loading state (optional)
    checkbox.disabled = true;
    
    fetch(`/consent/${userId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({consent: consent})
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Show success message
            showMessage('Consent status updated successfully', 'success');
            
            // Reload page after short delay to show updated state
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            // Revert checkbox on failure
            checkbox.checked = originalState;
            showMessage('Failed to update consent status', 'error');
        }
    })
    .catch(error => {
        console.error('Error updating consent:', error);
        // Revert checkbox on error
        checkbox.checked = originalState;
        showMessage('Error updating consent status. Please try again.', 'error');
    })
    .finally(() => {
        checkbox.disabled = false;
    });
}

function showMessage(message, type) {
    // Simple alert for MVP - can be enhanced with toast notifications
    // For MVP, we'll just log to console
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Optional: Create a temporary alert banner
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

