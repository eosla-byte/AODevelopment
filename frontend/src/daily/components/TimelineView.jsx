import React, { useEffect, useState, useRef } from 'react';
import TaskDetailModal from './TaskDetailModal';

// CONFIG: Determine BIM Service URL
// In production, this might come from env vars or handle relative paths if routed via Nginx.
// For Dev, we assume BIM is on port 8002.
const getBimUrl = () => {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8002';
    }
    // Production / Staging assumption
    return 'https://bim.somosao.com';
};

const TimelineView = ({ projectId }) => {
    const iframeRef = useRef(null);
    const [selectedTask, setSelectedTask] = useState(null);
    const [bimUrl] = useState(getBimUrl());
    const [authToken, setAuthToken] = useState(null);

    // Fetch Auth Token for Iframe
    useEffect(() => {
        const fetchToken = async () => {
            try {
                const res = await fetch('/auth/token');
                const data = await res.json();
                if (data.token) {
                    console.log("TimelineView: Token received for Iframe");
                    setAuthToken(data.token);
                } else {
                    console.warn("TimelineView: No token returned from backend");
                }
            } catch (e) {
                console.error("TimelineView: Failed to fetch auth token", e);
            }
        };
        fetchToken();
    }, []);

    // Message Listener for Iframe Communication
    useEffect(() => {
        const handleMessage = (event) => {
            // Security Check: Ensure origin matches BIM Service
            // if (event.origin !== bimUrl) return; // Strict check recommended in prod

            const { type, payload } = event.data;
            if (type === 'TASK_CLICK') {
                console.log("TimelineView: Task Clicked", payload);
                setSelectedTask(payload);
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, [bimUrl]);

    const handleSaveTask = async (updatedTask) => {
        console.log("Saving Task:", updatedTask);

        // 1. Optimistic UI: Close Modal
        // setSelectedTask(null); // Wait, maybe keep open if error? No, close for fluid UX.

        // 2. Send Update to Backend (BIM API)
        // We can proxy this through Daily or call BIM directly if CORS allowed.
        // For now, let's assume we postMessage back to iframe to refresh or call API directly?
        // Better: Call API directly from here.

        try {
            // NOTE: This endpoint needs to exist in BIM Service or be proxied
            /*
            await fetch(`${bimUrl}/api/projects/${projectId}/tasks/${updatedTask.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comments: updatedTask.new_comment ? [updatedTask.new_comment] : [],
                    extension_days: updatedTask.extension_days
                })
            });
            */

            // 3. Refresh Iframe Content
            if (iframeRef.current && iframeRef.current.contentWindow) {
                iframeRef.current.contentWindow.postMessage({ type: 'REFRESH', payload: {} }, '*');
            }

            alert("Changes saved locally. (Backend integration pending)");

        } catch (error) {
            console.error("Failed to save task", error);
            alert("Failed to save changes.");
        }
    };

    if (!authToken) {
        return <div className="p-4 text-gray-500">Loading secure timeline...</div>;
    }

    return (
        <div className="w-full h-full flex flex-col relative bg-gray-50 border rounded-lg overflow-hidden">
            {/* Iframe Container */}
            <div className="flex-1 w-full bg-white relative">
                <iframe
                    ref={iframeRef}
                    src={`${bimUrl}/projects/${projectId}?embedded=true&token=${authToken}`}
                    title="BIM Timeline"
                    className="w-full h-full border-0"
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups" // Security hardening
                />
            </div>

            {/* Task Details Modal */}
            {selectedTask && (
                <TaskDetailModal
                    task={selectedTask}
                    onClose={() => setSelectedTask(null)}
                    onSave={handleSaveTask}
                />
            )}
        </div>
    );
};

export default TimelineView;
