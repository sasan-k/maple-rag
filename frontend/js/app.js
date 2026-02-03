/**
 * Main application JavaScript for the chat interface
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const messagesContainer = document.getElementById('messages-container');
    const welcomeSection = document.getElementById('welcome-section');
    const loadingIndicator = document.getElementById('loading-indicator');
    const exampleBtns = document.querySelectorAll('.example-btn');
    const langEnBtn = document.getElementById('lang-en');
    const langFrBtn = document.getElementById('lang-fr');
    const themeToggle = document.getElementById('theme-toggle');

    // State
    let isLoading = false;
    let currentLanguage = 'en';

    // Initialize
    init();

    function init() {
        // Load saved theme preference
        loadTheme();

        // Fetch last updated date
        fetchLastUpdated();

        // Event listeners
        messageInput.addEventListener('input', handleInputChange);
        messageInput.addEventListener('keydown', handleKeyDown);
        sendBtn.addEventListener('click', sendMessage);
        newChatBtn.addEventListener('click', startNewChat);

        exampleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const question = btn.dataset.question;
                messageInput.value = question;
                handleInputChange();
                sendMessage();
            });
        });

        langEnBtn.addEventListener('click', () => setLanguage('en'));
        langFrBtn.addEventListener('click', () => setLanguage('fr'));
        themeToggle.addEventListener('click', toggleTheme);

        // Auto-resize textarea
        messageInput.addEventListener('input', autoResizeTextarea);
    }

    // Theme Management
    function loadTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else {
            // Default to light theme, or check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
                document.documentElement.setAttribute('data-theme', 'dark');
            }
        }
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        if (newTheme === 'light') {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
        }

        localStorage.setItem('theme', newTheme);
    }

    function handleInputChange() {
        const hasContent = messageInput.value.trim().length > 0;
        sendBtn.disabled = !hasContent || isLoading;
    }

    function handleKeyDown(e) {
        // Send on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                sendMessage();
            }
        }
    }

    function autoResizeTextarea() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
    }

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || isLoading) return;

        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';
        handleInputChange();

        // Hide welcome, show messages
        showMessagesView();

        // Add user message
        addMessage('user', message);

        // Show loading
        setLoading(true);

        try {
            const response = await chatAPI.sendMessage(message);

            // Update language if detected
            if (response.language) {
                setLanguage(response.language);
            }

            // Add assistant message
            addMessage('assistant', response.response, response.sources);

        } catch (error) {
            console.error('Error sending message:', error);
            addMessage('assistant', getErrorMessage(currentLanguage), []);
        } finally {
            setLoading(false);
        }

        // Scroll to bottom
        scrollToBottom();
    }

    function addMessage(role, content, sources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Parse markdown-like content
        contentDiv.innerHTML = parseContent(content);

        // Add sources if present
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            sourcesDiv.innerHTML = `
                <h4>Sources</h4>
                ${sources.map(s => `
                    <a href="${s.url}" target="_blank" rel="noopener" class="source-link">
                        📄 ${s.title}
                    </a>
                `).join('')}
            `;
            contentDiv.appendChild(sourcesDiv);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
    }

    function parseContent(content) {
        // Simple markdown parsing
        let html = content
            // Escape HTML
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
            // Line breaks
            .replace(/\n/g, '<br>')
            // Bullet points
            .replace(/^- (.+)$/gm, '<li>$1</li>');

        // Wrap list items
        if (html.includes('<li>')) {
            html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
        }

        // Wrap in paragraphs
        html = '<p>' + html.replace(/<br><br>/g, '</p><p>') + '</p>';

        return html;
    }

    function showMessagesView() {
        welcomeSection.classList.add('hidden');
        messagesContainer.classList.remove('hidden');
    }

    function showWelcomeView() {
        welcomeSection.classList.remove('hidden');
        messagesContainer.classList.add('hidden');
        messagesContainer.innerHTML = '';
    }

    function setLoading(loading) {
        isLoading = loading;
        loadingIndicator.classList.toggle('hidden', !loading);
        handleInputChange();

        if (loading) {
            scrollToBottom();
        }
    }

    function scrollToBottom() {
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function startNewChat() {
        chatAPI.newSession();
        showWelcomeView();
    }

    function setLanguage(lang) {
        currentLanguage = lang;
        langEnBtn.classList.toggle('active', lang === 'en');
        langFrBtn.classList.toggle('active', lang === 'fr');

        // Update placeholder
        const placeholders = {
            en: 'Ask a question about Canadian taxes...',
            fr: 'Posez une question sur les impôts canadiens...',
        };
        messageInput.placeholder = placeholders[lang] || placeholders.en;

        // Update welcome text if visible
        updateWelcomeText(lang);
    }

    function updateWelcomeText(lang) {
        const h1 = welcomeSection.querySelector('h1');
        const p = welcomeSection.querySelector('.welcome-content > p');
        const h3 = welcomeSection.querySelector('.example-questions h3');

        if (lang === 'fr') {
            if (h1) h1.textContent = "Bienvenue à l'Assistant Fiscal";
            if (p) p.textContent = "Posez-moi des questions sur les impôts canadiens, les déclarations, les crédits, les déductions et plus encore.";
            if (h3) h3.textContent = "Essayez de demander:";
        } else {
            if (h1) h1.textContent = "Welcome to Tax Info Assistant";
            if (p) p.textContent = "Ask me questions about Canadian taxes, filing returns, credits, deductions, and more. I use information from official government sources.";
            if (h3) h3.textContent = "Try asking:";
        }
    }

    function getErrorMessage(lang) {
        const messages = {
            en: "I'm sorry, I encountered an error processing your request. Please try again or visit the official government website directly for information.",
            fr: "Je suis désolé, j'ai rencontré une erreur en traitant votre demande. Veuillez réessayer ou visiter le site officiel du gouvernement.",
        };
        return messages[lang] || messages.en;
    }

    async function fetchLastUpdated() {
        try {
            const response = await fetch(`${chatAPI.baseUrl.replace('/chat', '')}/admin/stats`);
            if (response.ok) {
                const data = await response.json();
                if (data.last_updated) {
                    const lastUpdatedEl = document.getElementById('last-updated');
                    if (lastUpdatedEl) {
                        const date = new Date(data.last_updated);
                        const formatted = date.toLocaleDateString(currentLanguage === 'fr' ? 'fr-CA' : 'en-CA', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                        const label = currentLanguage === 'fr' ? 'Dernière mise à jour' : 'Data last updated';
                        lastUpdatedEl.textContent = `📅 ${label}: ${formatted}`;
                    }
                }
            }
        } catch (error) {
            console.log('Could not fetch last updated date:', error);
        }
    }
});
