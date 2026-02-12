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
    /**
     * Send command to Revit Plugin via Backend Bridge (Polling)
     * @param {string} action - 'select', 'color', 'clean'
     * @param {object} payload - Data to send
     */
    sendToRevit: async function (action, payload) {
        console.log("Sending to Revit (Bridge):", action, payload);

        if (!SESSION_ID) {
            alert("No hay sesión activa. No se puede comunicar con Revit.");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/command/${SESSION_ID}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action, payload: payload })
            });

            if (res.ok) {
                // console.log("Command queued");
                // Optional: Show toast
            } else {
                console.error("Failed to queue command");
            }

        } catch (e) {
            console.error("Bridge Error:", e);
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
