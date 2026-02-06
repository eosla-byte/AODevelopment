import React, { useState, useEffect } from 'react';
import { X, MessageSquare, Clock, Calendar, Briefcase, Paperclip, Send, CheckCircle } from 'lucide-react';
import { api } from '../services/api';

const TaskDetailModal = ({ task: initialTask, onClose, onUpdate }) => {
    const [task, setTask] = useState(initialTask);
    const [loading, setLoading] = useState(true);
    const [comment, setComment] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [activeTab, setActiveTab] = useState('details'); // 'details', 'comments'

    // Load full details (comments, attachments, real dates)
    useEffect(() => {
        if (initialTask?.id) {
            api.getTask(initialTask.id)
                .then(data => {
                    setTask(data);
                    setLoading(false);
                })
                .catch(err => console.error(err));
        }
    }, [initialTask]);

    if (!task) return null;

    const handleUpdate = async (field, value) => {
        // Optimistic UI could be here, but for safety we wait
        try {
            const updated = await api.updateTask(task.id, { [field]: value });
            setTask(prev => ({ ...prev, ...updated }));
            if (onUpdate) onUpdate(updated);
        } catch (e) {
            alert("Failed to update " + field);
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
            alert("Upload failed");
        }
    };

    const getPriorityColor = (p) => {
        switch (p) {
            case 'Urgent': return 'bg-red-100 text-red-700';
            case 'High': return 'bg-orange-100 text-orange-700';
            case 'Medium': return 'bg-blue-100 text-blue-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl h-[85vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex justify-between items-start p-5 border-b bg-gray-50">
                    <div className="w-full mr-4">
                        <input
                            className="text-xl font-bold text-gray-800 bg-transparent border-none focus:ring-0 w-full p-0"
                            value={task.title}
                            onChange={(e) => setTask({ ...task, title: e.target.value })}
                            onBlur={(e) => handleUpdate('title', e.target.value)}
                        />
                        <div className="flex gap-2 mt-2">
                            <select
                                className={`text-xs font-semibold px-2 py-1 rounded border-none cursor-pointer ${getPriorityColor(task.priority)}`}
                                value={task.priority}
                                onChange={(e) => handleUpdate('priority', e.target.value)}
                            >
                                <option>Low</option>
                                <option>Medium</option>
                                <option>High</option>
                                <option>Urgent</option>
                            </select>
                            <select
                                className="text-xs font-medium px-2 py-1 rounded bg-white border border-gray-200 text-gray-600 cursor-pointer"
                                value={task.status}
                                onChange={(e) => handleUpdate('status', e.target.value)}
                            >
                                <option>Pending</option>
                                <option>In Progress</option>
                                <option>Done</option>
                            </select>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
                        <X size={24} />
                    </button>
                </div>

                {/* Body - Split View */}
                <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
                    {/* Left: Details */}
                    <div className="flex-1 p-6 overflow-y-auto border-r border-gray-100">
                        <div className="space-y-6">
                            {/* Description */}
                            <div>
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 block">Description</label>
                                <textarea
                                    className="w-full text-sm text-gray-700 border border-transparent hover:border-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-md p-2 transition-all min-h-[100px]"
                                    placeholder="Add a more detailed description..."
                                    value={task.description || ""}
                                    onChange={(e) => setTask({ ...task, description: e.target.value })}
                                    onBlur={(e) => handleUpdate('description', e.target.value)}
                                />
                            </div>

                            {/* Dates Grid */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1 block">Real Start</label>
                                    <input
                                        type="datetime-local"
                                        className="w-full text-sm border rounded p-1.5 text-gray-600"
                                        value={task.started_at ? task.started_at.slice(0, 16) : ""}
                                        onChange={(e) => handleUpdate('start_date', e.target.value)} // API expects start_date
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1 block">Real End</label>
                                    <input
                                        type="datetime-local"
                                        className="w-full text-sm border rounded p-1.5 text-gray-600"
                                        value={task.completed_at ? task.completed_at.slice(0, 16) : ""}
                                        onChange={(e) => handleUpdate('end_date', e.target.value)}
                                    />
                                </div>
                            </div>

                            {/* Attachments */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Attachments</label>
                                    <label className="cursor-pointer text-blue-600 hover:text-blue-700 text-xs flex items-center gap-1">
                                        <Paperclip size={12} /> Add
                                        <input type="file" className="hidden" onChange={handleFileUpload} />
                                    </label>
                                </div>
                                <div className="space-y-2">
                                    {task.attachments && task.attachments.length > 0 ? (
                                        task.attachments.map((file, i) => (
                                            <a
                                                key={i}
                                                href={file.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="block p-2 bg-gray-50 border border-gray-100 rounded flex items-center gap-2 hover:bg-blue-50 transition-colors"
                                            >
                                                <div className="bg-white p-1 rounded border">📄</div>
                                                <div className="overflow-hidden">
                                                    <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
                                                    <p className="text-[10px] text-gray-400">{new Date(file.uploaded_at).toLocaleDateString()}</p>
                                                </div>
                                            </a>
                                        ))
                                    ) : (
                                        <div className="text-sm text-gray-400 italic p-2 border border-dashed rounded text-center">No files attached</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right: Activity/Comments */}
                    <div className="w-full md:w-[320px] bg-gray-50 flex flex-col border-l border-gray-200">
                        {/* Tabs (optional if we want History vs Comments) */}
                        <div className="p-3 border-b border-gray-200 flex gap-4">
                            <button className="text-sm font-semibold text-gray-700 flex items-center gap-1">
                                <MessageSquare size={14} /> Activity
                            </button>
                        </div>

                        {/* List */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {task.comments && task.comments.map((c, i) => (
                                <div key={i} className="flex gap-2">
                                    <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-xs text-white font-bold shrink-0">
                                        {(c.user_id || "U").charAt(0).toUpperCase()}
                                    </div>
                                    <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-100 flex-1">
                                        <p className="text-sm text-gray-800 whitespace-pre-wrap">{c.content}</p>
                                        <p className="text-[10px] text-gray-400 mt-1 text-right">
                                            {c.created_at ? new Date(c.created_at).toLocaleString() : "Just now"}
                                        </p>
                                    </div>
                                </div>
                            ))}
                            {loading && <p className="text-center text-xs text-gray-400">Loading history...</p>}
                        </div>

                        {/* Input */}
                        <div className="p-3 bg-white border-t border-gray-200">
                            <div className="flex items-end gap-2 bg-gray-50 border rounded-lg p-2 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
                                <textarea
                                    className="w-full bg-transparent border-none focus:ring-0 text-sm resize-none p-0 max-h-20"
                                    placeholder="Write a comment... (@mention)"
                                    rows={1}
                                    value={comment}
                                    onChange={(e) => setComment(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleCommentSubmit();
                                        }
                                    }}
                                />
                                <button
                                    onClick={handleCommentSubmit}
                                    disabled={!comment.trim()}
                                    className="p-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                                >
                                    <Send size={14} />
                                </button>
                            </div>
                            <p className="text-[10px] text-gray-400 mt-1 pl-1">Press Enter to send</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TaskDetailModal;
