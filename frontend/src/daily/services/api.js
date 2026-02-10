
const API_BASE = ""; // Relative path for production

// Refresh Lock Mechanism
let isRefreshing = false;
let refreshSubscribers = [];

function onRefreshed() {
    refreshSubscribers.forEach(cb => cb());
    refreshSubscribers = [];
}

function subscribeTokenRefresh(cb) {
    refreshSubscribers.push(cb);
}

// INTERCEPTOR HELPER
async function fetchWithAuth(url, options = {}) {
    options.credentials = "include";

    // Ensure Headers exist
    if (!options.headers) options.headers = {};

    // Clean up headers (No X-Org)
    // delete options.headers["X-Organization-ID"]; // If passed explicitly

    let response = await fetch(url, options);

    if (response.status === 401) {
        console.warn("🔒 [Auth] 401 Detected. Attempting Refresh...");

        if (isRefreshing) {
            // Wait for the pending refresh
            return new Promise(resolve => {
                subscribeTokenRefresh(async () => {
                    // Retry the original request
                    resolve(await fetch(url, options));
                });
            });
        }

        isRefreshing = true;

        try {
            // Attempt Refresh against Accounts Service
            const refreshRes = await fetch("https://accounts.somosao.com/auth/refresh", {
                method: "POST",
                credentials: "include"
            });

            if (refreshRes.ok) {
                console.log("✅ [Auth] Refresh Successful. Retrying...");
                isRefreshing = false;
                onRefreshed();
                // Retry original
                return await fetch(url, options);
            }

            // Handle 409 ORG_REQUIRED
            if (refreshRes.status === 409) {
                console.warn("⚠️ [Auth] Org Selection Required.");
                window.location.href = "https://accounts.somosao.com/select-org"; // Or local page?
                // Ideally redirect to Accounts select-org which then redirects back? 
                // Or we implement a local Select Org page provided by Accounts?
                // The plan implies Accounts has /select-org.
                throw new Error("ORG_SELECTION_REQUIRED");
            }

            // Handle 401/403 -> Login
            throw new Error("SESSION_EXPIRED");

        } catch (err) {
            console.error("❌ [Auth] Refresh Failed:", err);
            isRefreshing = false;

            // Complete Logout Logic
            localStorage.clear();
            sessionStorage.clear();

            const currentUrl = encodeURIComponent(window.location.href);
            // Verify we aren't already on login
            if (!window.location.href.includes("accounts.somosao.com/login")) {
                window.location.href = `https://accounts.somosao.com/login?redirect=${currentUrl}`;
            }

            // Block downstream
            throw new Error("AUTH_EXPIRED_REDIRECTING");
        }
    }

    return response;
}


export const api = {
    getHeaders() {
        const headers = { "Content-Type": "application/json" };
        // Strict Auth: No X-Organization-ID header.
        // Context is in the Cookie.
        return headers;
    },

    async getBoard(projectId) {
        // return MOCK_BOARD;
        try {
            const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/board`, {
                headers: this.getHeaders()
            });
            return await res.json();
        } catch (e) {
            console.warn("API Error, using mock", e);
            // Only use mock if not an auth error
            if (e.message === "AUTH_EXPIRED_REDIRECTING") throw e;

            const MOCK_BOARD = {
                id: "demo",
                name: "Demo Project (Offline)",
                columns: []
            };
            return MOCK_BOARD;
        }
    },

    async moveTask(taskId, columnId, index) {
        try {
            await fetchWithAuth(`${API_BASE}/tasks/${taskId}/move`, {
                method: "PUT",
                headers: this.getHeaders(),
                body: JSON.stringify({ column_id: columnId, index })
            });
        } catch (e) {
            console.error(e);
        }
    },

    async getTask(taskId) {
        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}`, {
            headers: this.getHeaders()
        });
        return await res.json();
    },

    async updateTask(taskId, updates) {
        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}`, {
            method: "PATCH",
            headers: this.getHeaders(),
            body: JSON.stringify(updates)
        });
        return await res.json();
    },

    async addComment(taskId, content) {
        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}/comments`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ content })
        });
        return await res.json();
    },

    async getProjectMembers(projectId) {
        try {
            const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/members`, {
                headers: this.getHeaders()
            });
            return await res.json();
        } catch (e) {
            console.warn("Failed to fetch members", e);
            return [];
        }
    },

    async createTask(columnId, title) {
        const res = await fetchWithAuth(`${API_BASE}/tasks`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ column_id: columnId, title, priority: "Medium" })
        });
        return await res.json();
    },

    async uploadAttachment(taskId, file) {
        const formData = new FormData();
        formData.append("file", file);

        // Note: Do NOT set Content-Type header for FormData
        const headers = this.getHeaders();
        delete headers["Content-Type"];

        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}/attachments`, {
            method: "POST",
            headers: headers,
            body: formData
        });
        return await res.json();
    },

    // --- Project Creation ---
    async getBimProjects() {
        const res = await fetchWithAuth(`/bim-projects`, {
            headers: this.getHeaders()
        });
        return await res.json();
    },

    async getOrgUsers() {
        const res = await fetchWithAuth(`/org-users`, {
            headers: this.getHeaders()
        });
        return await res.json();
    },

    async createProject(payload) {
        const res = await fetchWithAuth(`/projects`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Failed to create project");
        return await res.json();
    },

    // --- Session Management ---

    async ping() {
        const res = await fetchWithAuth(`/auth/ping`, {
            headers: this.getHeaders()
        });
        return await res.json();
    },
    async init() {
        const res = await fetchWithAuth(`/init`, {
            headers: this.getHeaders()
        });
        return await res.json();
    },

    async getMyOrganizations(email) {
        // CHANGED: Call Accounts Service directly for global orgs
        // Using credentials: include to pass the HttpOnly cookie
        const res = await fetchWithAuth(`https://accounts.somosao.com/api/my-organizations`, {
            headers: this.getHeaders()
        });
        return await res.json();
    },

    async selectOrganization(orgId) {
        const res = await fetchWithAuth(`https://accounts.somosao.com/auth/select-org`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ org_id: orgId })
        });
        return await res.json();
    },

    async logout() {
        try {
            await fetch("https://accounts.somosao.com/auth/logout", {
                method: "POST",
                credentials: "include"
            });
        } catch (e) { console.error("Logout error", e); }

        localStorage.clear();
        sessionStorage.clear();
        window.location.href = "https://accounts.somosao.com/login";
    }
};
