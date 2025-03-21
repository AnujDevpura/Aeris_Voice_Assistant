// auth.js - JavaScript functions for the auth pages
<script src="/static/js/auth.js"></script>
// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const passwordInput = document.getElementById(inputId);
    const toggleButton = passwordInput.nextElementSibling.querySelector('img');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleButton.src = '/static/img/eye-slash.svg';
        toggleButton.alt = 'Hide password';
    } else {
        passwordInput.type = 'password';
        toggleButton.src = '/static/img/eye.svg';
        toggleButton.alt = 'Show password';
    }
}

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    // Handle signup form submission
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const firstName = document.getElementById('firstName').value.trim();
            const lastName = document.getElementById('lastName').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const termsCheck = document.getElementById('termsCheck').checked;
            
            // Basic validation
            if (!firstName || !lastName) {
                showError('Please enter your first and last name');
                return;
            }
            
            if (!isValidEmail(email)) {
                showError('Please enter a valid email address');
                return;
            }
            
            if (password.length < 8) {
                showError('Password must be at least 8 characters long');
                return;
            }
            
            if (!termsCheck) {
                showError('You must agree to the Terms & Conditions');
                return;
            }
            
            // If all validation passes, submit the form
            this.submit();
        });
    }
    
    // Handle login form submission
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            
            // Basic validation
            if (!isValidEmail(email)) {
                showError('Please enter a valid email address');
                return;
            }
            
            if (!password) {
                showError('Please enter your password');
                return;
            }
            
            // If all validation passes, submit the form
            this.submit();
        });
    }
});

// Helper function to validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Function to show error messages
function showError(message) {
    // Check if an error message already exists
    let errorElement = document.querySelector('.auth-error');
    
    if (!errorElement) {
        // Create a new error element
        errorElement = document.createElement('div');
        errorElement.className = 'auth-error alert alert-danger mt-3';
        
        // Get the form and insert the error before the first input
        const form = document.querySelector('form');
        form.insertBefore(errorElement, form.firstChild);
    }
    
    // Set the error message
    errorElement.textContent = message;
    
    // Automatically remove the error after 5 seconds
    setTimeout(() => {
        errorElement.remove();
    }, 5000);
}

// Social login functions (placeholders)
document.addEventListener('DOMContentLoaded', function() {
    const googleBtn = document.querySelector('.google-btn');
    const appleBtn = document.querySelector('.apple-btn');
    
    if (googleBtn) {
        googleBtn.addEventListener('click', function() {
            // Placeholder for Google OAuth implementation
            console.log('Google login clicked');
            // window.location.href = '/auth/google';
        });
    }
    
    if (appleBtn) {
        appleBtn.addEventListener('click', function() {
            // Placeholder for Apple OAuth implementation
            console.log('Apple login clicked');
            // window.location.href = '/auth/apple';
        });
    }
});