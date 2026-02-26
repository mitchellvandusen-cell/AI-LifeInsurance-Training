/**
 * API client for InsuranceGrokBot Training platform.
 * Handles all HTTP requests and authentication state.
 */

const API = {
    baseUrl: '',  // Same origin
    token: localStorage.getItem('auth_token') || null,

    async request(method, path, body = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        const opts = { method, headers, credentials: 'include' };
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(`${this.baseUrl}${path}`, opts);

        if (res.status === 401) {
            this.token = null;
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || data.message || 'Request failed');
        }
        return data;
    },

    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    put(path, body) { return this.request('PUT', path, body); },
    delete(path) { return this.request('DELETE', path); },

    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    },

    clearToken() {
        this.token = null;
        localStorage.removeItem('auth_token');
    },

    isAuthenticated() {
        return !!this.token;
    },

    // ── Auth ──────────────────────────────────────────────
    async login(email, password) {
        const data = await this.post('/api/auth/login', { email, password });
        this.setToken(data.token);
        return data;
    },

    async register(email, password, name) {
        const data = await this.post('/api/auth/register', { email, password, name });
        this.setToken(data.token);
        return data;
    },

    async logout() {
        await this.post('/api/auth/logout');
        this.clearToken();
        window.location.href = '/login';
    },

    async getMe() {
        return this.get('/api/auth/me');
    },

    // ── Sessions ──────────────────────────────────────────
    async startSession(archetype = null, voice = null) {
        const body = { archetype };
        if (voice) body.voice = voice;
        return this.post('/api/sessions/start', body);
    },

    async endSession(sessionId) {
        return this.post(`/api/sessions/${sessionId}/end`);
    },

    async getSessions(limit = 50) {
        return this.get(`/api/sessions/?limit=${limit}`);
    },

    async getSession(sessionId) {
        return this.get(`/api/sessions/${sessionId}`);
    },

    async getTranscript(sessionId) {
        return this.get(`/api/sessions/${sessionId}/transcript`);
    },

    // ── Analytics ─────────────────────────────────────────
    async getAnalyticsOverview(days = 30) {
        return this.get(`/api/analytics/overview?days=${days}`);
    },

    async getAnalyticsTrends(days = 30) {
        return this.get(`/api/analytics/trends?days=${days}`);
    },

    async getReportCards(limit = 50) {
        return this.get(`/api/analytics/report-cards?limit=${limit}`);
    },

    async getReportCard(reportId) {
        return this.get(`/api/analytics/report-cards/${reportId}`);
    },

    async getReportCardBySession(sessionId) {
        return this.get(`/api/analytics/report-cards/by-session/${sessionId}`);
    },

    // ── Billing ───────────────────────────────────────────
    async getSubscription() {
        return this.get('/api/billing/subscription');
    },

    async createCheckout(plan) {
        return this.post('/api/billing/checkout', { plan });
    },

    async walletTopUp(amountCents) {
        return this.post('/api/billing/wallet/topup', { amount_cents: amountCents });
    },

    async getWalletTransactions() {
        return this.get('/api/billing/wallet/transactions');
    },

    async openBillingPortal() {
        const data = await this.post('/api/billing/portal');
        window.location.href = data.portal_url;
    },

    // ── Recordings ────────────────────────────────────────
    async getRecordings() {
        return this.get('/api/recordings/');
    },

    async syncRecordings() {
        return this.post('/api/recordings/sync');
    },

    // ── Settings ──────────────────────────────────────────
    async getSettings() {
        return this.get('/api/settings');
    },

    async updateSettings(settings) {
        return this.put('/api/settings', settings);
    },

    // ── Training Modules ────────────────────────────────────
    async getModules() {
        return this.get('/api/modules/');
    },

    async startModuleSession(moduleKey, voice = null) {
        const body = { module_key: moduleKey };
        if (voice) body.voice = voice;
        return this.post('/api/modules/start', body);
    },

    async endModuleSession(sessionId) {
        return this.post(`/api/modules/${sessionId}/end`);
    },

    async getModuleHistory(moduleKey = null) {
        const q = moduleKey ? `?module_key=${moduleKey}` : '';
        return this.get(`/api/modules/history${q}`);
    },

    // ── Homework ────────────────────────────────────────────
    async generateHomework() {
        return this.post('/api/modules/homework/generate');
    },

    async getLatestHomework() {
        return this.get('/api/modules/homework/latest');
    },

    async getHomeworkHistory() {
        return this.get('/api/modules/homework/history');
    },
};

// ── Toast notifications ────────────────────────────────────
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Auth guard for protected pages ─────────────────────────
function requireAuth() {
    if (!API.isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// ── Format helpers ─────────────────────────────────────────
function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatMoney(cents) {
    return '$' + (cents / 100).toFixed(2);
}

function gradeClass(letter) {
    if (letter.startsWith('A')) return 'grade-A';
    if (letter.startsWith('B')) return 'grade-B';
    if (letter.startsWith('C')) return 'grade-C';
    if (letter.startsWith('D')) return 'grade-D';
    return 'grade-F';
}
