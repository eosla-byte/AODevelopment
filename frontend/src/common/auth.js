
// SHARED AUTHENTICATION UTILITIES
// Used by Daily, Admin, and Clients apps.

let isRefreshing = false;
let refreshSubscribers = [];

function onRefreshed() {
    refreshSubscribers.forEach(cb => cb());
    refreshSubscribers = [];
}

function subscribeTokenRefresh(cb) {
    refreshSubscribers.push(cb);
}

export async function fetchWithAuth(url, options = {}) {
    options.credentials = "include"; // Always send cookies

    // Ensure Headers exist
    if (!options.headers) options.headers = {};

    // Standard JSON content type if not set (and not FormData)
    if (!(options.body instanceof FormData) && !options.headers["Content-Type"]) {
        options.headers["Content-Type"] = "application/json";
    }

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
                // Redirect to select org or handle via callback?
                // For now, redirect to accounts
                window.location.href = "https://accounts.somosao.com/select-org";
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

export function logout() {
    fetch("https://accounts.somosao.com/auth/logout", {
        method: "POST",
        credentials: "include"
    }).catch(e => console.error("Logout error", e));

    localStorage.clear();
    sessionStorage.clear();
    window.location.href = "https://accounts.somosao.com/login";
}
