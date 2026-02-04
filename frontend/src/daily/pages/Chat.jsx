import React from 'react';
import { useParams } from 'react-router-dom';

const Chat = () => {
    const { projectId } = useParams();

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'white', borderRadius: '0.5rem', boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)' }}>
            <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0' }}>
                <h3 style={{ margin: 0 }}>Chat: {projectId || "General"}</h3>
            </div>
            <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', background: '#f8fafc' }}>
                <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '2rem' }}>
                    No messages yet. Start the conversation!
                </div>
            </div>
            <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '0.5rem' }}>
                <input
                    type="text"
                    placeholder="Type a message..."
                    style={{ flex: 1, padding: '0.75rem', borderRadius: '0.375rem', border: '1px solid #cbd5e1', outline: 'none' }}
                />
                <button className="btn btn-primary">Send</button>
            </div>
        </div>
    );
};

export default Chat;
