document.addEventListener('DOMContentLoaded', function() {
    const terminal = document.getElementById('output');
    const input = document.getElementById('command-input');
    const loginOverlay = document.getElementById('login-overlay');
    const container = document.querySelector('.container');
    const apiKeyInput = document.getElementById('api-key-input');
    const loginButton = document.getElementById('login-button');
    const loginError = document.getElementById('login-error');
    
    let apiKey = null;

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
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                console.error('Validation error:', data.error);
                return false;
            }
            
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
                apiKey = key;
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
                    'Content-Type': 'application/json',
                    'X-API-Key': apiKey
                },
                body: JSON.stringify({ message: message }),
            });

            const data = await response.json();
            appendMessage(data.response);
        } catch (error) {
            appendMessage('Error: Failed to communicate with the server');
            console.error('Error:', error);
        }
    }

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
}); 