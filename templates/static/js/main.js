// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Form validation helpers
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('error');
                    isValid = false;
                } else {
                    field.classList.remove('error');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showError('Please fill all required fields');
            }
        });
    });
    
    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = this.files[0]?.name;
            if (fileName) {
                const label = this.nextElementSibling;
                if (label && label.classList.contains('file-label')) {
                    label.textContent = fileName;
                }
            }
        });
    });
});

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger';
    errorDiv.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        ${message}
        <span class="close-alert">&times;</span>
    `;
    
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertBefore(errorDiv, mainContent.firstChild);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success';
    successDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        ${message}
        <span class="close-alert">&times;</span>
    `;
    
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertBefore(successDiv, mainContent.firstChild);
        
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }
}

// Dashboard chart initialization (if using charts)
function initDashboardCharts() {
    const chartElements = document.querySelectorAll('[data-chart]');
    chartElements.forEach(element => {
        const chartType = element.dataset.chart;
        // You can integrate Chart.js here if needed
        console.log(`Initialize ${chartType} chart`);
    });
}

// Search and filter functionality
function filterTable(searchInput, tableId) {
    const input = document.getElementById(searchInput);
    if (!input) return;
    
    input.addEventListener('keyup', function() {
        const filter = this.value.toLowerCase();
        const table = document.getElementById(tableId);
        const rows = table.getElementsByTagName('tr');
        
        for (let i = 1; i < rows.length; i++) {
            let textContent = rows[i].textContent.toLowerCase();
            rows[i].style.display = textContent.includes(filter) ? '' : 'none';
        }
    });
}

// Confirm deletion
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

// Loader overlay
function showLoader() {
    let loader = document.querySelector('.loader-overlay');
    if (!loader) {
        loader = document.createElement('div');
        loader.className = 'loader-overlay';
        loader.innerHTML = '<div class="loader"></div>';
        document.body.appendChild(loader);
    }
    loader.style.display = 'flex';
}

function hideLoader() {
    const loader = document.querySelector('.loader-overlay');
    if (loader) {
        loader.style.display = 'none';
    }
}