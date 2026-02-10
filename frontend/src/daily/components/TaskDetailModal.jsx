import React, { useState, useEffect } from 'react';
import { X, MessageSquare, Clock, Calendar, Briefcase, Paperclip, Send, CheckCircle, User, Tag, Flag } from 'lucide-react';
import { api } from '../services/api';

const TaskDetailModal = ({ task: initialTask, onClose, onUpdate }) => {
    // If it's a new task, existing fields are empty
    const [task, setTask] = useState(initialTask.isNew ? { ...initialTask, title: "", priority: "Medium", status: "To Do" } : initialTask);
    const [loading, setLoading] = useState(!initialTask.isNew);
    const [comment, setComment] = useState("");
    const [activeTab, setActiveTab] = useState('activity');
    const [members, setMembers] = useState([]);

    useEffect(() => {
        // Fetch project members
        // Fetch project members
        // URL is likely #/board/{id} or #/projects/{id}/board
        const hash = window.location.hash;
        const matches = hash.match(/\/board\/([a-zA-Z0-9-]+)/) || hash.match(/\/projects\/([a-zA-Z0-9-]+)\/board/);
        const pId = matches ? matches[1] : null;
        if (pId) {
            api.getProjectMembers(pId).then(data => {
                if (Array.isArray(data)) setMembers(data);
            });
        }
    }, []);

    // Load full details ONLY if it's an existing task
    useEffect(() => {
        if (initialTask?.id && !initialTask.isNew) {
            api.getTask(initialTask.id)
                .then(data => {
                    setTask(data);
                    setLoading(false);
                })
                .catch(err => console.error(err));
        } else {
            setLoading(false);
        }
    }, [initialTask]);

    if (!task) return null;
    const isNew = !task.id;

    const handleSaveNew = async () => {
        if (!task.title.trim()) return alert("Title is required");
        try {
            const created = await api.createTask(task.columnId, task.title);
            let finalTask = created;
            const updates = {};
            if (task.description) updates.description = task.description;
            if (task.priority !== "Medium") updates.priority = task.priority;
            if (task.started_at) updates.start_date = task.started_at;
            if (task.completed_at) updates.end_date = task.completed_at;

            if (Object.keys(updates).length > 0) {
                finalTask = await api.updateTask(created.id, updates);
            }

            setTask(finalTask);
            if (onUpdate) onUpdate(finalTask);
        } catch (e) {
            console.error(e);
            alert("Failed to create task");
        }
    };

    const handleUpdate = async (field, value) => {
        if (task.isNew || !task.id) {
            setTask(prev => ({ ...prev, [field]: value }));
            return;
        }
        try {
            const updated = await api.updateTask(task.id, { [field]: value });
            setTask(prev => ({ ...prev, ...updated }));
            if (onUpdate) onUpdate(updated);
        } catch (e) {
            console.error("Failed to update " + field);
        }
    };

    const handleCommentSubmit = async () => {
        if (!comment.trim()) return;
        try {
            const newComment = await api.addComment(task.id, comment);
            setTask(prev => ({
                ...prev,
                comments: [newComment, ...(prev.comments || [])]
            }));
            setComment("");
        } catch (e) {
            alert("Failed to post comment");
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
            const newAttach = await api.uploadAttachment(task.id, file);
            setTask(prev => ({
                ...prev,
                attachments: [...(prev.attachments || []), newAttach]
            }));
        } catch (e) {
            console.error("Upload error details:", e);
            alert("Upload failed: " + (e.message || "Unknown error"));
        }
    };

    const getPriorityColor = (p) => {
        switch (p) {
            case 'Urgent': return 'bg-red-50 text-red-600 border-red-200';
            case 'High': return 'bg-orange-50 text-orange-600 border-orange-200';
            case 'Medium': return 'bg-blue-50 text-blue-600 border-blue-200';
            default: return 'bg-gray-50 text-gray-600 border-gray-200';
        }
    };

    const resolveUserName = (id, name) => {
        if (name && name !== `User ${id}`) return name;
        const member = members.find(m => m.id === id);
        return member ? member.name : (id === 'demo-user-id' ? 'Demo User' : `User ${id.substring(0, 5)}...`);
    };

    const formatTime = (isoString, backendFormatted) => {
        if (backendFormatted) return backendFormatted;
        if (!isoString) return 'Just now';
        return new Date(isoString).toLocaleString('en-US', {
            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" onClick={onClose} />

            <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col md:flex-row max-h-[90vh] animate-in fade-in zoom-in duration-200">

                {/* LEFT: Main Content (Feed) */}
                <div className="flex-1 flex flex-col min-w-0 bg-white">
                    {/* Header */}
                    <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-start sticky top-0 bg-white/95 backdrop-blur z-10">
                        <div className="flex-1 mr-4">
                            <input
                                className="text-2xl font-bold text-slate-800 placeholder-slate-300 bg-transparent border-none focus:ring-0 w-full p-0 leading-tight"
                                value={task.title}
                                placeholder="What needs to be done?"
                                autoFocus={isNew}
                                onChange={(e) => setTask({ ...task, title: e.target.value })}
                                onBlur={(e) => handleUpdate('title', e.target.value)}
                            />
                            <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                                <span>in list</span>
                                <span className="font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded text-[10px] uppercase tracking-wide">
                                    {isNew ? (task.columnId === 'col-1' ? 'To Do' : 'Board') : (task.status || 'To Do')}
                                </span>
                            </div>
                        </div>
                        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors">
                            <X size={24} />
                        </button>
                    </div>

                    {/* Scrollable Content */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-8">
                        {/* Description */}
                        <div className="group">
                            <div className="flex items-center gap-2 mb-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                                <Briefcase size={14} /> Description
                            </div>
                            <textarea
                                className="w-full text-base text-slate-700 placeholder-slate-400 border-none bg-slate-50 hover:bg-slate-100 focus:bg-white focus:ring-2 focus:ring-blue-100 rounded-lg p-4 transition-all min-h-[120px] resize-y"
                                placeholder="Add a more detailed description..."
                                value={task.description || ""}
                                onChange={(e) => setTask({ ...task, description: e.target.value })}
                                onBlur={(e) => handleUpdate('description', e.target.value)}
                            />
                        </div>

                        {/* Attachments */}
                        <div>
                            <div className="flex justify-between items-center mb-3">
                                <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                                    <Paperclip size={14} /> Attachments
                                </div>
                                {!isNew && (
                                    <label className="cursor-pointer text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center gap-1 bg-blue-50 px-3 py-1.5 rounded-full hover:bg-blue-100 transition-colors">
                                        <Paperclip size={12} /> Add File
                                        <input type="file" className="hidden" onChange={handleFileUpload} />
                                    </label>
                                )}
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                {task.attachments && task.attachments.length > 0 ? (
                                    task.attachments.map((file, i) => (
                                        <a key={i} href={file.url} target="_blank" rel="noopener noreferrer" className="group block p-3 bg-slate-50 border border-slate-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded bg-white border flex items-center justify-center text-lg">📄</div>
                                                <div className="overflow-hidden">
                                                    <p className="text-sm font-medium text-slate-700 truncate">{file.name}</p>
                                                    <p className="text-[10px] text-slate-400">{new Date(file.uploaded_at).toLocaleDateString()}</p>
                                                </div>
                                            </div>
                                        </a>
                                    ))
                                ) : (
                                    <div className="col-span-full border-2 border-dashed border-slate-200 rounded-lg p-6 flex flex-col items-center justify-center text-slate-400 text-sm">
                                        <p>No files attached properly yet.</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Activity / Comments */}
                        <div className="pt-6 border-t border-slate-100">
                            <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                                <MessageSquare size={14} /> Activity
                            </div>

                            {isNew ? (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400 bg-slate-50 rounded-xl border border-slate-100">
                                    <MessageSquare size={40} className="mb-3 opacity-30" />
                                    <p className="text-sm">Create the task to start the conversation.</p>
                                    <button
                                        onClick={handleSaveNew}
                                        className="mt-4 px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-full hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all flex items-center gap-2"
                                    >
                                        <CheckCircle size={16} /> Create Task
                                    </button>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {/* Composer */}
                                    <div className="flex gap-3">
                                        <div className="w-8 h-8 rounded-full bg-slate-200 border-2 border-white shadow-sm shrink-0 flex items-center justify-center text-slate-500 font-bold text-xs">A</div>
                                        <div className="flex-1">
                                            <div className="bg-white border border-slate-200 rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300 transition-all overflow-hidden">
                                                <textarea
                                                    className="w-full bg-transparent border-none focus:ring-0 text-sm p-3 min-h-[40px] resize-none placeholder-slate-400"
                                                    placeholder="Write a comment..."
                                                    value={comment}
                                                    onChange={(e) => setComment(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleCommentSubmit(); }
                                                    }}
                                                />
                                                <div className="bg-slate-50 px-2 py-1.5 flex justify-end border-t border-slate-100">
                                                    <button
                                                        onClick={handleCommentSubmit}
                                                        disabled={!comment.trim()}
                                                        className="bg-blue-600 text-white rounded-lg px-3 py-1 text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                                                    >
                                                        Post
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Stream */}
                                    <div className="space-y-6">
                                        {task.comments && task.comments.map((c, i) => {
                                            const displayName = resolveUserName(c.user_id, c.user_name);
                                            return (
                                                <div key={i} className="flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300">
                                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center text-sm font-bold shadow-md shrink-0 ring-2 ring-white">
                                                        {displayName.charAt(0).toUpperCase()}
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="flex items-baseline justify-between">
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-sm font-bold text-slate-800">{displayName}</span>
                                                                <span className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">
                                                                    {c.user_id === 'demo-user-id' ? 'Guest' : 'Member'}
                                                                </span>
                                                            </div>
                                                            <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                                                                <Clock size={10} />
                                                                {formatTime(c.created_at, c.formatted_time)}
                                                            </span>
                                                        </div>
                                                        <div className="mt-1 text-sm text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-2xl rounded-tl-none border border-slate-100 shadow-sm">
                                                            {c.content}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* RIGHT: Sidebar (Metadata) */}
                <div className="w-full md:w-80 bg-slate-50 border-l border-slate-200 p-6 space-y-6 overflow-y-auto">
                    {/* Status & Priority */}
                    <div>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Status</h3>
                        <div className="space-y-3">
                            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
                                <label className="text-xs text-slate-500 block mb-1">Current Status</label>
                                <select
                                    className="w-full text-sm font-medium bg-transparent border-none p-0 focus:ring-0 cursor-pointer"
                                    value={task.status}
                                    onChange={(e) => handleUpdate('status', e.target.value)}
                                    disabled={isNew}
                                >
                                    <option>To Do</option>
                                    <option>In Progress</option>
                                    <option>Done</option>
                                </select>
                            </div>

                            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
                                <label className="text-xs text-slate-500 block mb-1">Priority</label>
                                <div className="flex items-center gap-2">
                                    <Flag size={14} className={task.priority === 'Urgent' ? 'text-red-500' : 'text-slate-400'} />
                                    <select
                                        className={`w-full text-sm font-medium bg-transparent border-none p-0 focus:ring-0 cursor-pointer text-slate-700`}
                                        value={task.priority}
                                        onChange={(e) => handleUpdate('priority', e.target.value)}
                                    >
                                        <option>Low</option>
                                        <option>Medium</option>
                                        <option>High</option>
                                        <option>Urgent</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Dates */}
                    <div>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Schedule</h3>
                        <div className="bg-white rounded-lg border border-slate-200 shadow-sm divide-y divide-slate-100">
                            <div className="p-3">
                                <label className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                                    <CheckCircle size={12} /> Due Date
                                </label>
                                <input
                                    type="date"
                                    className="w-full text-sm bg-transparent border-none p-0 text-slate-700 focus:ring-0"
                                    value={task.due_date ? task.due_date.slice(0, 10) : ""}
                                    onChange={(e) => handleUpdate('due_date', e.target.value)}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Assignees */}
                    <div>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Assignees</h3>
                        <div className="flex gap-2 flex-wrap">
                            <button
                                onClick={() => {
                                    const me = "u1"; // fallback if no auth context
                                    const current = task.assignees || [];
                                    if (!current.includes(me)) {
                                        handleUpdate('assignees', [...current, me]);
                                    } else {
                                        handleUpdate('assignees', current.filter(u => u !== me));
                                    }
                                }}
                                className={`h-8 px-3 rounded-full text-xs font-bold border transition-all flex items-center gap-1 ${(task.assignees || []).includes("u1")
                                    ? "bg-indigo-100 text-indigo-700 border-indigo-200"
                                    : "bg-white text-slate-500 border-slate-200 hover:border-indigo-300"
                                    }`}
                            >
                                <User size={12} /> ME
                            </button>

                            {/* Team Members */}
                            {/* Ideally loaded from API, hardcoded demo for now if not fetched */}
                            {members.map(m => (
                                <button
                                    key={m.id}
                                    onClick={() => {
                                        const current = task.assignees || [];
                                        if (!current.includes(m.id)) {
                                            handleUpdate('assignees', [...current, m.id]);
                                        } else {
                                            handleUpdate('assignees', current.filter(u => u !== m.id));
                                        }
                                    }}
                                    className={`h-8 px-3 rounded-full text-xs font-bold border transition-all flex items-center gap-1 ${(task.assignees || []).includes(m.id)
                                        ? "bg-blue-100 text-blue-700 border-blue-200"
                                        : "bg-white text-slate-500 border-slate-200 hover:border-blue-300"
                                        }`}
                                    title={m.email}
                                >
                                    <span className="w-4 h-4 rounded-full bg-slate-200 flex items-center justify-center text-[8px]">{m.name.charAt(0)}</span>
                                    {m.name.split(' ')[0]}
                                </button>
                            ))}

                            <button
                                onClick={() => {
                                    const email = prompt("Enter email to assign:");
                                    if (email) {
                                        handleUpdate('assignees', [...(task.assignees || []), email]);
                                    }
                                }}
                                className="w-8 h-8 rounded-full border border-dashed border-slate-300 flex items-center justify-center text-slate-400 hover:border-slate-400 hover:text-slate-600 transition-all"
                            >
                                <User size={14} /> +
                            </button>
                        </div>
                    </div>

                    {/* Actions */}
                    {isNew && (
                        <div className="pt-6">
                            <button
                                onClick={handleSaveNew}
                                className="w-full py-3 bg-slate-900 text-white rounded-xl shadow-lg hover:shadow-xl hover:bg-slate-800 transition-all font-semibold text-sm flex items-center justify-center gap-2"
                            >
                                <CheckCircle size={16} /> Create Task
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TaskDetailModal;
