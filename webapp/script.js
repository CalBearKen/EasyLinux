document.addEventListener('DOMContentLoaded', function() {
    const terminal = document.getElementById('output');
    const input = document.getElementById('command-input');
    const loginOverlay = document.getElementById('login-overlay');
    const container = document.querySelector('.container');
    const apiKeyInput = document.getElementById('api-key-input');
    const loginButton = document.getElementById('login-button');
    const loginError = document.getElementById('login-error');
    
    let sessionId = null;

    function appendMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'agent-message');
        
        const prefix = isUser ? '$ ' : '> ';
        messageDiv.textContent = prefix + message;
        
        terminal.appendChild(messageDiv);
        terminal.scrollTop = terminal.scrollHeight;
    }

    async function validateApiKey(key) {
        try {
            const response = await fetch('http://localhost:5000/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key: key }),
                credentials: 'include'  // Include cookies for session
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                console.error('Validation error:', data.error);
                return false;
            }
            
            sessionId = data.session_id;
            return data.valid;
        } catch (error) {
            console.error('Error:', error);
            return false;
        }
    }

    async function handleLogin() {
        const key = apiKeyInput.value.trim();
        if (!key) {
            loginError.textContent = 'Please enter an API key';
            loginError.style.display = 'block';
            return;
        }

        if (!key.startsWith('sk-')) {
            loginError.textContent = 'Invalid API key format. Should start with "sk-"';
            loginError.style.display = 'block';
            return;
        }

        loginButton.disabled = true;
        loginButton.textContent = 'Validating...';
        loginError.style.display = 'none';

        try {
            const isValid = await validateApiKey(key);
            
            if (isValid) {
                loginOverlay.style.display = 'none';
                container.style.display = 'block';
                appendMessage('AI Shell initialized. Type your message or command...');
            } else {
                loginError.textContent = 'Invalid API key. Please check your API key and try again.';
                loginError.style.display = 'block';
            }
        } catch (error) {
            loginError.textContent = 'Error validating API key. Please try again.';
            loginError.style.display = 'block';
            console.error('Login error:', error);
        } finally {
            loginButton.disabled = false;
            loginButton.textContent = 'Connect';
        }
    }

    async function sendMessage(message) {
        try {
            const response = await fetch('http://localhost:5000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message }),
                credentials: 'include'  // Include cookies for session
            });

            if (response.status === 401) {
                // Session expired, show login
                loginOverlay.style.display = 'flex';
                container.style.display = 'none';
                loginError.textContent = 'Session expired. Please login again.';
                loginError.style.display = 'block';
                return;
            }

            const data = await response.json();
            appendMessage(data.response);
        } catch (error) {
            appendMessage('Error: Failed to communicate with the server');
            console.error('Error:', error);
        }
    }

    async function handleLogout() {
        try {
            await fetch('http://localhost:5000/logout', {
                method: 'POST',
                credentials: 'include'
            });
            loginOverlay.style.display = 'flex';
            container.style.display = 'none';
            terminal.innerHTML = '';  // Clear terminal
            sessionId = null;
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    // Add logout button
    const logoutButton = document.createElement('button');
    logoutButton.textContent = 'Logout';
    logoutButton.className = 'logout-button';
    logoutButton.onclick = handleLogout;
    container.appendChild(logoutButton);

    loginButton.addEventListener('click', handleLogin);
    apiKeyInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleLogin();
        }
    });

    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const message = input.value;
            if (message.trim()) {
                appendMessage(message, true);
                sendMessage(message);
                input.value = '';
            }
        }
    });

    // Check session on load
    fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: '' }),
        credentials: 'include'
    }).then(response => {
        if (response.status === 401) {
            loginOverlay.style.display = 'flex';
            container.style.display = 'none';
        } else {
            loginOverlay.style.display = 'none';
            container.style.display = 'block';
        }
    }).catch(error => {
        console.error('Session check error:', error);
        loginOverlay.style.display = 'flex';
        container.style.display = 'none';
    });
}); 