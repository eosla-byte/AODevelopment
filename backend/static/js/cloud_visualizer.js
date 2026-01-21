/**
 * Cloud Visualizer
 * Logic to communicate with Revit Plugin for Element Isolation/Coloring
 */

const VISUALIZER = {

    /**
     * Send command to Revit Plugin WebView Bridge
     * @param {string} action - 'select', 'color', 'clean'
     * @param {object} payload - Data to send
     */
    sendToRevit: function (action, payload) {
        // Bridge Object might be 'window.chrome.webview' (WebView2) or 'window.external' (Old)
        // or a custom injected object 'RevitPlugin'.

        const message = {
            action: action,
            payload: payload
        };

        console.log("Sending to Revit:", message);

        try {
            if (window.chrome && window.chrome.webview) {
                window.chrome.webview.postMessage(message);
            } else if (window.external && window.external.notify) {
                window.external.notify(JSON.stringify(message));
            } else {
                console.warn("Revit Bridge not found. Are you running in Browser?");
                // Mock behavior for browser testing
                // showToast(`Revit Command: ${action}`, "info");
            }
        } catch (e) {
            console.error("Failed to send to Revit:", e);
        }
    },

    /**
     * Clear all overrides in Revit View
     */
    cleanView: function () {
        this.sendToRevit('clean', {});
    },

    /**
     * Visualize Elements from a Card
     * @param {string} cardId 
     */
    visualizeCard: function (cardId) {
        // 1. Find Card
        const card = activeCards.find(c => c.id === cardId);
        if (!card) return console.error("Card not found");

        // 2. Get Processed Rows (Filtered)
        // We reuse the logic from cloud_quantify.js if available
        let rows = [];
        if (typeof getProcessedRowsForCard === 'function') {
            rows = getProcessedRowsForCard(card);
        } else {
            rows = card.rows || [];
        }

        // 3. Extract IDs
        // Element IDs usually come as "Id", "ElementId", or "id"
        // We scan keys to find a likely ID candidate if not explicit
        if (rows.length === 0) {
            alert("La tarjeta no tiene elementos para visualizar.");
            return;
        }

        const idKey = Object.keys(rows[0]).find(k => k.toLowerCase() === 'id' || k.toLowerCase().includes('elementid') || k === 'GUID');

        if (!idKey) {
            alert("No se encontró columna de ID (ElementId) en esta tabla.");
            return;
        }

        const ids = rows.map(r => r[idKey]).filter(val => val);

        if (ids.length === 0) {
            alert("No hay IDs validos found.");
            return;
        }

        // 4. Generate Random Color
        const color = this.getRandomColor();

        // 5. Send Command
        this.sendToRevit('visualize', {
            elementIds: ids,
            color: color, // Hex format #RRGGBB
            cardName: card.name
        });
    },

    getRandomColor: function () {
        // Robust random color (avoid too dark/light)
        const letters = '456789ABC'; // Limit range to pastel/vibrant keys
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * letters.length)];
        }
        return color;
    }
};

// Expose globally
window.VISUALIZER = VISUALIZER;
