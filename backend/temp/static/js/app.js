class ChatApp {
    constructor() {
        this.currentSessionId = null;
        this.initializeElements();
        this.attachEventListeners();
        this.loadSessions();
    }

    initializeElements() {
        this.newChatBtn = document.getElementById('newChatBtn');
        this.chatList = document.getElementById('chatList');
        this.messages = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
    }

    attachEventListeners() {
        this.newChatBtn.addEventListener('click', () => this.createNewSession());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async createNewSession() {
        try {
            const response = await fetch('/deepseek_backend/create_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_name: 'New Chat'
                })
            });
            const data = await response.json();
            this.currentSessionId = data.session_id;
            this.loadSessions();
            this.clearMessages();
        } catch (error) {
            console.error('Error creating session:', error);
        }
    }

    async loadSessions() {
        try {
            const response = await fetch('/deepseek_backend/get_session');
            const sessions = await response.json();
            this.renderSessions(sessions);
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    renderSessions(sessions) {
        this.chatList.innerHTML = '';
        sessions.forEach(session => {
            const chatItem = document.createElement('div');
            chatItem.className = `chat-item ${session.session_id === this.currentSessionId ? 'active' : ''}`;
            chatItem.textContent = session.session_name;
            chatItem.addEventListener('click', () => this.loadChat(session.session_id));
            this.chatList.appendChild(chatItem);
        });
    }

    async loadChat(sessionId) {
        this.currentSessionId = sessionId;
        this.loadSessions();
        try {
            const response = await fetch(`/deepseek_backend/load_chat/${sessionId}`);
            const messages = await response.json();
            this.renderMessages(messages);
        } catch (error) {
            console.error('Error loading chat:', error);
        }
    }

    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message) return;

        if (!this.currentSessionId) {
            await this.createNewSession();
        }

        this.addMessage('user', message);
        this.userInput.value = '';

        try {
            const response = await fetch('/deepseek_backend/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.currentSessionId,
                    query: message
                })
            });
            const data = await response.json();
            this.addMessage('assistant', data.message.content);
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('assistant', 'Sorry, there was an error processing your request.');
        }
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.textContent = content;
        this.messages.appendChild(messageDiv);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    clearMessages() {
        this.messages.innerHTML = '';
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
}); 