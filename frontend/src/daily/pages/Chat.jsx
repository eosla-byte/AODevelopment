import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
// Imports from 'lucide-react'
import { Send, User, Hash, Paperclip, MessageSquare, Plus, ChevronRight, X, Folder, AlertCircle, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ChatLayout = () => {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const [channels, setChannels] = useState([]);
    const [activeChannelId, setActiveChannelId] = useState(null);

    // Project List State (for Selector)
    const [teams, setTeams] = useState([]); // Reusing team/project structure
    const [loadingProjects, setLoadingProjects] = useState(false);

    // UI State
    const [showThread, setShowThread] = useState(false);
    const [activeThreadMsg, setActiveThreadMsg] = useState(null); // Parent message for thread

    // Loading
    const [loadingChannels, setLoadingChannels] = useState(true);

    // Fetch Projects if no projectId
    useEffect(() => {
        if (!projectId) {
            fetchProjects();
        } else {
            fetchChannels();
        }
    }, [projectId]);

    const fetchProjects = async () => {
        setLoadingProjects(true);
        const orgId = localStorage.getItem("ao_org_id");
        // CORRECT USER ID RETRIEVAL
        let userId = null;
        try {
            const storedUser = JSON.parse(localStorage.getItem("ao_user") || "{}");
            if (storedUser.id && storedUser.id !== 'u123') {
                userId = storedUser.id;
            } else if (storedUser.email) {
                userId = "u123"; // Fallback to trigger resolution
            }
        } catch (e) {
            console.error("Error parsing user", e);
        }

        const rawUserId = userId || "u123";
        let effectiveUserId = rawUserId;

        if (rawUserId === 'u123') {
            try {
                const storedUser = JSON.parse(localStorage.getItem("ao_user") || "{}");
                if (storedUser.email) {
                    const usersRes = await fetch('/org-users', { headers: { 'X-Organization-ID': orgId } });
                    if (usersRes.ok) {
                        const users = await usersRes.json();
                        const found = users.find(u => u.email.toLowerCase() === storedUser.email.toLowerCase());
                        if (found) {
                            effectiveUserId = found.id;
                        }
                    }
                }
            } catch (e) {
                console.error("Error resolving user email", e);
            }
        }

        try {
            const res = await fetch('/init', { headers: { 'X-Organization-ID': orgId, 'X-User-ID': effectiveUserId } });
            if (res.ok) {
                const data = await res.json();
                let teamsData = data.teams || [];
                // Sort projects by created_at desc
                teamsData.forEach(t => {
                    if (t.projects) {
                        t.projects.sort((a, b) => {
                            const dateA = new Date(a.created_at || 0);
                            const dateB = new Date(b.created_at || 0);
                            return dateB - dateA;
                        });
                    }
                });
                setTeams(teamsData);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingProjects(false);
        }
    };

    const handleDeleteProject = async (e, projectId) => {
        e.preventDefault();
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this project?")) return;

        const aoUser = localStorage.getItem("ao_user");
        let userId = "u123";
        if (aoUser) try { userId = JSON.parse(aoUser).id || "u123"; } catch { }

        try {
            const res = await fetch(`/projects/${projectId}`, {
                method: 'DELETE',
                headers: { 'X-User-ID': userId }
            });
            if (res.ok) {
                fetchProjects(); // Refresh list
            } else {
                alert("Failed to delete project");
            }
        } catch (error) {
            console.error("Delete failed", error);
            alert("Error deleting project");
        }
    };

    const fetchChannels = async () => {
        if (!projectId) return;
        try {
            const res = await fetch(`/projects/${projectId}/channels`);
            if (res.ok) {
                const data = await res.json();
                setChannels(data);
                if (data.length > 0 && !activeChannelId) {
                    setActiveChannelId(data[0].id); // Default to first channel (likely general)
                }
            } else {
                // If project not found or permission denied, redirect to selector
                navigate('/chat');
            }
        } catch (e) {
            console.error(e);
            navigate('/chat');
        } finally {
            setLoadingChannels(false);
        }
    };

    const handleCreateChannel = async () => {
        const name = prompt("Enter channel name:");
        if (!name) return;
        try {
            const res = await fetch(`/projects/${projectId}/channels`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.toLowerCase().replace(/\s+/g, '-') })
            });
            if (res.ok) {
                fetchChannels();
            }
        } catch (e) {
            console.error(e);
        }
    };

    if (!projectId) {
        // Project Selector View
        if (loadingProjects) return <div style={{ padding: '2rem' }}>Loading Projects...</div>;
        return (
            <div style={{ padding: '2rem', height: '100%', overflowY: 'auto' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#1e293b', marginBottom: '2rem' }}>Select a Project to Chat</h1>
                {teams.every(t => t.projects.length === 0) ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#64748b', marginTop: '4rem' }}>
                        <Folder size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
                        <p>No projects found. Create one in the Projects tab.</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                        {teams.filter(t => t.projects.length > 0).map(team => (
                            <div key={team.id}>
                                <h3 style={{ fontSize: '1.1rem', color: '#475569', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    {team.name}
                                </h3>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                                    {team.projects.map(p => (
                                        <div
                                            key={p.id}
                                            onClick={() => navigate(`/chat/${p.id}`)}
                                            style={{
                                                background: 'white', padding: '1.5rem', borderRadius: '12px',
                                                boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0',
                                                cursor: 'pointer', transition: 'transform 0.2s', display: 'flex', flexDirection: 'column',
                                                gap: '1rem', position: 'relative'
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    <div style={{ width: '40px', height: '40px', background: '#eff6ff', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3b82f6' }}>
                                                        <MessageSquare size={20} />
                                                    </div>
                                                    <div>
                                                        <h3 style={{ margin: '0', fontSize: '1.1rem', color: '#1e293b' }}>{p.name}</h3>
                                                        <span style={{ fontSize: '0.85rem', color: '#64748b' }}>{team.name}</span>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={(e) => handleDeleteProject(e, p.id)}
                                                    style={{
                                                        background: 'transparent', border: 'none', cursor: 'pointer',
                                                        color: '#cbd5e1', padding: '4px', borderRadius: '4px'
                                                    }}
                                                    onMouseEnter={(e) => { e.target.style.color = '#ef4444'; e.target.style.background = '#fee2e2'; }}
                                                    onMouseLeave={(e) => { e.target.style.color = '#cbd5e1'; e.target.style.background = 'transparent'; }}
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>

                                            <div style={{ display: 'flex', gap: '1.5rem', borderTop: '1px solid #f1f5f9', paddingTop: '1rem', marginTop: 'auto' }}>
                                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                    <span style={{ fontSize: '1.25rem', fontWeight: 600, color: '#0f172a' }}>{p.channel_count || 0}</span>
                                                    <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 500 }}>Channels</span>
                                                </div>
                                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                    <span style={{ fontSize: '1.25rem', fontWeight: 600, color: '#0f172a' }}>-</span>
                                                    <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 500 }}>Threads</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        )
    }

    if (loadingChannels) return <div style={{ padding: '1rem' }}>Loading Chat...</div>;

    return (
        <div style={{ height: '100%', display: 'flex', borderRadius: '0.5rem', overflow: 'hidden', boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)', background: 'white' }}>
            {/* Sidebar: Channels */}
            <div style={{ width: '240px', background: '#f1f5f9', borderRight: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ margin: 0, fontSize: '1rem', color: '#334155' }}>Channels</h3>
                    <button onClick={handleCreateChannel} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b' }}>
                        <Plus size={18} />
                    </button>
                </div>
                <div style={{ flex: 1, padding: '0.5rem', overflowY: 'auto' }}>
                    {channels.map(c => (
                        <div
                            key={c.id}
                            onClick={() => { setActiveChannelId(c.id); setShowThread(false); }}
                            style={{
                                padding: '0.5rem 0.75rem', borderRadius: '6px', cursor: 'pointer',
                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                background: activeChannelId === c.id ? '#e2e8f0' : 'transparent',
                                color: activeChannelId === c.id ? '#1e293b' : '#64748b',
                                marginBottom: '2px'
                            }}
                        >
                            <Hash size={16} />
                            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{c.name}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Chat Area */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                {activeChannelId ? (
                    <ChannelView
                        channelId={activeChannelId}
                        openThread={(msg) => { setActiveThreadMsg(msg); setShowThread(true); }}
                    />
                ) : (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>Select a channel</div>
                )}
            </div>

            {/* Right Sidebar: Thread */}
            {showThread && activeThreadMsg && (
                <div style={{ width: '320px', borderLeft: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', background: 'white' }}>
                    <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0, fontSize: '0.9rem', color: '#334155', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ color: '#94a3b8' }}>Thread</span> <ChevronRight size={14} /> {activeThreadMsg.content.substring(0, 15)}...
                        </h3>
                        <button onClick={() => setShowThread(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b' }}>
                            <X size={18} />
                        </button>
                    </div>
                    {/* Thread View Component would go here. For now, reusing ChannelView logic or similar? */}
                    {/* Since threaded messages are just messages with parent_id, we can reuse logic but need filtering. */}
                    {/* For MVP, let's keep Thread View simple. */}
                    <ThreadView parentMsg={activeThreadMsg} channelId={activeChannelId} />
                </div>
            )}
        </div>
    );
};

// Sub-component: Channel View (Messages List + Input)
const ChannelView = ({ channelId, openThread }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const endRef = useRef(null);

    const fetchMessages = async () => {
        const res = await fetch(`/channels/${channelId}/messages`);
        if (res.ok) setMessages(await res.json());
    };

    useEffect(() => {
        fetchMessages();
        const interval = setInterval(fetchMessages, 3000);
        return () => clearInterval(interval);
    }, [channelId]);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async (file = null) => {
        if ((!input.trim() && !file) || !channelId) return;

        const aoUser = localStorage.getItem("ao_user");
        let userId = "u123";
        if (aoUser) try { userId = JSON.parse(aoUser).id || "u123"; } catch { }

        let attachments = [];
        if (file) {
            // Upload first
            const fd = new FormData();
            fd.append('file', file);
            try {
                const upRes = await fetch('/upload', { method: 'POST', body: fd });
                if (upRes.ok) {
                    const upData = await upRes.json();
                    attachments.push(upData);
                }
            } catch (e) {
                console.error("Upload failed", e);
                return;
            }
        }

        const body = { content: input, attachments };

        await fetch(`/channels/${channelId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
            body: JSON.stringify(body)
        });

        setInput("");
        fetchMessages();
    };

    return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {messages.length === 0 && <div style={{ color: '#94a3b8', textAlign: 'center', marginTop: '2rem' }}>No messages yet.</div>}
                {messages.filter(m => !m.parent_id).map(m => (
                    <MessageItem key={m.id} msg={m} onReply={() => openThread(m)} />
                ))}
                <div ref={endRef} />
            </div>
            <ChatInput onSend={handleSend} placeholder="Type a message..." />
        </div>
    );
};

// Sub-component: Thread View
const ThreadView = ({ parentMsg, channelId }) => {
    const [replies, setReplies] = useState([]);
    const endRef = useRef(null);

    const fetchReplies = async () => {
        const res = await fetch(`/channels/${channelId}/messages`); // Fetch all and filter client side for now (Optimization: Backend filter)
        if (res.ok) {
            const all = await res.json();
            setReplies(all.filter(m => m.parent_id === parentMsg.id));
        }
    };

    useEffect(() => {
        fetchReplies();
        const interval = setInterval(fetchReplies, 3000);
        return () => clearInterval(interval);
    }, [parentMsg]);

    const handleSend = async (file) => {
        // Reuse upload logic... repeated code, should refactor.
        // Quick implement
        const aoUser = localStorage.getItem("ao_user");
        let userId = "u123";
        if (aoUser) try { userId = JSON.parse(aoUser).id || "u123"; } catch { }

        await fetch(`/channels/${channelId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
            body: JSON.stringify({ content: "Replied", parent_id: parentMsg.id }) // Wait, input?
            // Need input state here.
        });
        fetchReplies();
    };

    // Thread Input is slightly different
    return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
            <div style={{ padding: '1rem', borderBottom: '1px solid #e2e8f0', background: 'white' }}>
                <MessageItem msg={parentMsg} isRoot />
            </div>
            <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {replies.map(m => (
                    <MessageItem key={m.id} msg={m} simple />
                ))}
                <div ref={endRef} />
            </div>
            {/* Simple Thread Input */}
            <ChatInput onSend={async (file, text) => {
                const aoUser = localStorage.getItem("ao_user");
                let userId = "u123";
                if (aoUser) try { userId = JSON.parse(aoUser).id || "u123"; } catch { }

                let attachments = [];
                if (file) {
                    const fd = new FormData(); fd.append('file', file);
                    const up = await fetch('/upload', { method: 'POST', body: fd });
                    if (up.ok) attachments.push(await up.json());
                }

                await fetch(`/channels/${channelId}/messages`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-User-ID': userId },
                    body: JSON.stringify({ content: text, parent_id: parentMsg.id, attachments })
                });
                fetchReplies();
            }} placeholder="Reply to thread..." />
        </div>
    );
};

const MessageItem = ({ msg, onReply, isRoot, simple }) => {
    return (
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'start' }}>
            <div style={{ minWidth: simple ? '24px' : '32px', height: simple ? '24px' : '32px', background: '#e2e8f0', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                <User size={simple ? 12 : 16} />
            </div>
            <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, color: '#334155' }}>{msg.sender_id || "User"}</span>
                    <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <div style={{ background: isRoot ? '#fff' : '#f1f5f9', padding: '0.5rem 0.75rem', borderRadius: '0px 8px 8px 8px', fontSize: '0.9rem', color: '#1e293b', border: isRoot ? 'none' : '1px solid transparent' }}>
                    {msg.content}
                    {msg.attachments && msg.attachments.length > 0 && (
                        <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            {msg.attachments.map((att, i) => (
                                <a key={i} href={att.url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', maxWidth: '200px' }}>
                                    {att.type.startsWith('image/') ? (
                                        <img src={att.url} alt={att.name} style={{ width: '100%', borderRadius: '4px' }} />
                                    ) : (
                                        <div style={{ padding: '0.5rem', background: '#e2e8f0', borderRadius: '4px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                            <Paperclip size={14} /> {att.name}
                                        </div>
                                    )}
                                </a>
                            ))}
                        </div>
                    )}
                </div>
                {!simple && !isRoot && (
                    <div style={{ marginTop: '0.25rem' }}>
                        <button onClick={onReply} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <MessageSquare size={14} /> Reply
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}

const ChatInput = ({ onSend, placeholder }) => {
    const [text, setText] = useState("");
    const fileInput = useRef(null);

    const handleKey = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    }

    const send = () => {
        if (!text.trim()) return;
        onSend(null, text);
        setText("");
    }

    const handleFile = (e) => {
        if (e.target.files[0]) {
            onSend(e.target.files[0], text); // Send file immediately (simple UX)
            setText(""); // Clear text if any? Or keep?
            // Usually Discord sends file separately or with text. 
            // Here let's assume immediate file upload.
            e.target.value = null;
        }
    }

    return (
        <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0', background: 'white', display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
            <button onClick={() => fileInput.current.click()} style={{ padding: '0.5rem', background: '#f1f5f9', border: 'none', borderRadius: '50%', cursor: 'pointer', color: '#64748b' }}>
                <Paperclip size={18} />
            </button>
            <input type="file" ref={fileInput} style={{ display: 'none' }} onChange={handleFile} />

            <div style={{ flex: 1, position: 'relative' }}>
                <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder={placeholder}
                    style={{
                        width: '100%', padding: '0.75rem', paddingRight: '3rem', borderRadius: '8px',
                        border: '1px solid #e2e8f0', outline: 'none', resize: 'none', minHeight: '44px', fontFamily: 'inherit'
                    }}
                />
                <button onClick={send} style={{ position: 'absolute', right: '0.5rem', bottom: '0.5rem', background: '#3b82f6', color: 'white', border: 'none', padding: '0.4rem', borderRadius: '6px', cursor: 'pointer' }}>
                    <Send size={16} />
                </button>
            </div>
        </div>
    )
}

export default ChatLayout;
