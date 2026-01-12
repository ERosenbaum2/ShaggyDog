// Main JavaScript for Shaggy Dog application

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });

    // File input label click handler
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        const label = input.closest('.form-group')?.querySelector('.file-label');
        if (label) {
            label.addEventListener('click', function(e) {
                if (e.target !== input) {
                    input.click();
                }
            });
        }
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#f8d7da';
                } else {
                    field.style.borderColor = '#e0e0e0';
                }
            });

            // Password confirmation check
            const password = form.querySelector('#password');
            const confirmPassword = form.querySelector('#confirm_password');
            if (password && confirmPassword) {
                if (password.value !== confirmPassword.value) {
                    isValid = false;
                    confirmPassword.style.borderColor = '#f8d7da';
                } else {
                    confirmPassword.style.borderColor = '#e0e0e0';
                }
            }

            if (!isValid) {
                e.preventDefault();
            }
        });
    });
});
