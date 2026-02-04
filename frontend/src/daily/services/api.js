
const API_BASE = "http://localhost:8000"; // Adjust port if needed

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

export const api = {
    async getBoard(projectId) {
        // return MOCK_BOARD;
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/board`);
            if (!res.ok) throw new Error("Failed to fetch");
            return await res.json();
        } catch (e) {
            console.warn("API Error, using mock", e);
            return MOCK_BOARD;
        }
    },

    async moveTask(taskId, columnId, index) {
        try {
            await fetch(`${API_BASE}/tasks/${taskId}/move`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ column_id: columnId, index })
            });
        } catch (e) {
            console.error(e);
        }
    }
};
