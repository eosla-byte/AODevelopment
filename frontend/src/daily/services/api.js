
const API_BASE = ""; // Relative path for production

// Mock Data
const MOCK_BOARD = {
    id: "demo",
    name: "Demo Project",
    columns: [
        {
            id: "col-1",
            title: "To Do",
            tasks: [
                { id: "t-1", title: "Research Competitors", priority: "Low", assignees: ["u1"] },
                { id: "t-2", title: "Design Homepage", priority: "High", assignees: ["u1"] }
            ]
        },
        {
            id: "col-2",
            title: "In Progress",
            tasks: [
                { id: "t-3", title: "Setup Database", priority: "Urgent", assignees: ["u1"] }
            ]
        },
        {
            id: "col-3",
            title: "Done",
            tasks: []
        }
    ]
};

// INTERCEPTOR HELPER
async function fetchWithAuth(url, options = {}) {
    try {
        const response = await fetch(url, options);

        if (response.status === 401) {
            // Clone to read body safely
            const body = await response.clone().json().catch(() => ({}));
            const error = body.detail || body.error; // Support both FastAPI default and custom

            if (error === "token_expired" || error === "token_invalid" || error === "token_invalid_signature") {
                console.error("🔒 Session Expired/Invalid. Reprompting login...");

                // 1. CLEAR SESSION
                localStorage.removeItem("ao_user_id");
                localStorage.removeItem("ao_user_name");
                localStorage.removeItem("ao_org_id"); // Optional: clear org context too? Maybe keep it.

                // 2. REDIRECT
                // Encode current URL to return after login
                const currentUrl = window.location.href;
                window.location.href = "https://accounts.somosao.com/login?redirect=" + encodeURIComponent(currentUrl);

                // 3. THROW to stop downstream logic
                throw new Error("SESSION_EXPIRED");
            }
        }

        if (!response.ok) {
            // Pass through other errors normally
            // Maybe parse body to throw better error message?
            // const errBody = await response.clone().json().catch(() => ({}));
            // throw new Error(errBody.detail || response.statusText);
            // detailed handling left to caller or generic error
        }

        return response;
    } catch (e) {
        if (e.message === "SESSION_EXPIRED") throw e; // Propagate redirect break
        throw e;
    }
}


// INTERCEPTOR HELPER
async function fetchWithAuth(url, options = {}) {
    const response = await fetch(url, options);

    if (response.status === 401) {
        // Clone response to read body
        const body = await response.clone().json().catch(() => ({}));

        if (body.detail === "token_expired" || body.detail === "token_invalid") {
            console.error("🔒 Session Expired. Redirecting to login...");

            // CLEAR SESSION
            localStorage.removeItem("ao_user_id");
            localStorage.removeItem("ao_user_name");

            // Optional: Call logout endpoint to clear cookie
            // await fetch("/auth/logout");

            // Redirect
            window.location.href = "https://accounts.somosao.com/login?redirect=" + encodeURIComponent(window.location.href);

            // Throw error to stop flow
            throw new Error("Session Expired");
        }
    }

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response;
}


export const api = {
    getHeaders() {
        const headers = { "Content-Type": "application/json" };
        const orgId = localStorage.getItem("ao_org_id");
        if (orgId) {
            headers["X-Organization-ID"] = orgId;
        }

        // REFACTOR: Strict Cookie Auth. 
        // We do NOT send X-User-ID or X-User-Name from localStorage for authenticated users.
        // The backend must rely on the httpOnly cookie.

        // GUEST HANDLING
        // If the user explicitly wants to be a guest (no ao_user logged in),
        // we might send a guest label.
        // But for now, let's just NOT send false identities.

        // Exception: If we want to support "Guest Mode" where the user types a name without account,
        // that name should be passed in the BODY of the comment request, not headers.

        return headers;
    },

    async getBoard(projectId) {
        // return MOCK_BOARD;
        try {
            const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/board`, {
                headers: this.getHeaders(),
                credentials: "include"
            });
            return await res.json();
        } catch (e) {
            console.warn("API Error, using mock", e);
            return MOCK_BOARD;
        }
    },

    async moveTask(taskId, columnId, index) {
        try {
            await fetchWithAuth(`${API_BASE}/tasks/${taskId}/move`, {
                method: "PUT",
                headers: this.getHeaders(),
                body: JSON.stringify({ column_id: columnId, index }),
                credentials: "include"
            });
        } catch (e) {
            console.error(e);
        }
    },

    async getTask(taskId) {
        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}`, {
            headers: this.getHeaders(),
            credentials: "include"
        });
        return await res.json();
    },

    async updateTask(taskId, updates) {
        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}`, {
            method: "PATCH",
            headers: this.getHeaders(),
            body: JSON.stringify(updates),
            credentials: "include"
        });
        return await res.json();
    },

    async addComment(taskId, content) {
        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}/comments`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ content }),
            credentials: "include"
        });
        return await res.json();
    },

    async getProjectMembers(projectId) {
        try {
            const res = await fetchWithAuth(`${API_BASE}/projects/${projectId}/members`, {
                headers: this.getHeaders(),
                credentials: "include"
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
            body: JSON.stringify({ column_id: columnId, title, priority: "Medium" }),
            credentials: "include"
        });
        return await res.json();
    },

    async uploadAttachment(taskId, file) {
        const formData = new FormData();
        formData.append("file", file);

        // Note: Do NOT set Content-Type header for FormData, browser does it with boundary
        const headers = this.getHeaders();
        delete headers["Content-Type"];

        const res = await fetchWithAuth(`${API_BASE}/tasks/${taskId}/attachments`, {
            method: "POST",
            headers: headers,
            body: formData,
            credentials: "include"
        });
        return await res.json();
    }
};
