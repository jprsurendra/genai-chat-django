// Login and registration page logic.
// Kept in a static file (not inline) so the Content-Security-Policy can forbid inline scripts.
// --- Login Logic ---
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');

    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.error || 'Login failed');

        // Save tokens and redirect
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('username', data.username);
        window.location.href = '/';

    } catch (err) {
        errorDiv.textContent = err.message;
    }
});

// --- Register Logic (Updated) ---
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;
    const errorDiv = document.getElementById('regError');

    // Frontend validation for password match
    if (password !== confirmPassword) {
        errorDiv.textContent = "Passwords do not match!";
        return;
    }

    try {
        const resp = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username,
                email: email,
                password: password,
                confirm_password: confirmPassword
            })
        });
        const data = await resp.json();

        if (!resp.ok) throw new Error(data.error || 'Registration failed');

        alert('Registration successful! Please login.');
        document.getElementById('login-tab').click(); // Switch to login tab

    } catch (err) {
        errorDiv.textContent = err.message;
    }
});
