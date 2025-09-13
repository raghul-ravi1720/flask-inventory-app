// Main JavaScript for Inventory Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert')
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert)
            bsAlert.close()
        }, 5000)
    })
    
    // Confirm before delete actions
    const deleteForms = document.querySelectorAll('form[action*="delete"]')
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault()
            }
        })
    })
    
    // Enable live search
    const searchInputs = document.querySelectorAll('input[type="search"]')
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(function() {
            if (this.value.length > 2 || this.value.length === 0) {
                this.form.submit()
            }
        }, 500))
    })
})

// Debounce function to limit how often a function can run
function debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout)
            func.apply(this, args)
        }
        clearTimeout(timeout)
        timeout = setTimeout(later, wait)
    }
}

// Flash message utility
function showFlashMessage(message, category = 'info') {
    // Implementation for showing flash messages
    console.log(`[${category}] ${message}`)
}