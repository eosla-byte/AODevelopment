import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Send, User } from 'lucide-react';

const Chat = () => {
    const { projectId } = useParams();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(true);
    const endRef = useRef(null);

    const fetchMessages = async () => {
        if (!projectId) return;
        try {
            const res = await fetch(`/chat/${projectId}`);
            if (res.ok) {
                const data = await res.json();
                setMessages(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMessages();
        const interval = setInterval(fetchMessages, 3000); // Poll every 3s
        return () => clearInterval(interval);
    }, [projectId]);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || !projectId) return;
        const aoUser = localStorage.getItem("ao_user");
        const userId = aoUser ? JSON.parse(aoUser).access_token : "u123"; // TODO: Fix user ID logic

        try {
            const res = await fetch(`/chat/${projectId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': userId
                },
                body: JSON.stringify({ content: input })
            });
            if (res.ok) {
                setInput("");
                fetchMessages();
            }
        } catch (e) {
            console.error(e);
        }
    };

    if (!projectId) return <div style={{ padding: '2rem' }}>Select a project to chat.</div>;

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'white', borderRadius: '0.5rem', boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)' }}>
            <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
                <h3 style={{ margin: 0, color: '#334155' }}>Project Chat</h3>
            </div>
            <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', background: 'white', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {messages.length === 0 ? (
                    <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '2rem' }}>
                        No messages yet. Start the conversation!
                    </div>
                ) : (
                    messages.map(m => (
                        <div key={m.id} style={{ display: 'flex', gap: '0.75rem', alignItems: 'start' }}>
                            <div style={{ minWidth: '32px', height: '32px', background: '#e2e8f0', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                                <User size={16} />
                            </div>
                            <div>
                                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>
                                    {m.sender_id || "User"} • {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                                <div style={{ background: '#f1f5f9', padding: '0.75rem', borderRadius: '0px 12px 12px 12px', fontSize: '0.9rem', color: '#1e293b' }}>
                                    {m.content}
                                </div>
                            </div>
                        </div>
                    ))
                )}
                <div ref={endRef} />
            </div>
            <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '0.5rem', background: '#f8fafc' }}>
                <input
                    type="text"
                    placeholder="Type a message..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                    style={{ flex: 1, padding: '0.75rem', borderRadius: '0.375rem', border: '1px solid #cbd5e1', outline: 'none' }}
                />
                <button
                    onClick={handleSend}
                    style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '0 1rem', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                    <Send size={18} /> Send
                </button>
            </div>
        </div>
    );
};

export default Chat;
