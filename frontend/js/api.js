/**
 * API client for the Canada.ca Chat Agent
 */

const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';

/**
 * API client class
 */
class ChatAPI {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }

    /**
     * Send a chat message
     * @param {string} message - The user's message
     * @returns {Promise<Object>} - The chat response
     */
    async sendMessage(message) {
        const response = await fetch(`${this.baseUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId,
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Store session ID for continuity
        if (data.session_id) {
            this.sessionId = data.session_id;
        }

        return data;
    }

    /**
     * Get session history
     * @param {string} sessionId - The session ID
     * @returns {Promise<Object>} - The session history
     */
    async getSessionHistory(sessionId) {
        const response = await fetch(`${this.baseUrl}/chat/sessions/${sessionId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    }

    /**
     * Delete a session
     * @param {string} sessionId - The session ID
     * @returns {Promise<Object>} - The deletion result
     */
    async deleteSession(sessionId) {
        const response = await fetch(`${this.baseUrl}/chat/sessions/${sessionId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    }

    /**
     * Start a new session
     */
    newSession() {
        this.sessionId = null;
    }

    /**
     * Health check
     * @returns {Promise<Object>} - Health status
     */
    async healthCheck() {
        const response = await fetch(`${this.baseUrl.replace('/api/v1', '')}/health`);
        return response.json();
    }
}

// Export singleton instance
const chatAPI = new ChatAPI();
