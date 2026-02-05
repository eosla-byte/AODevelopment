import React, { useState } from 'react';
import { X, MessageSquare, Clock, Calendar, Briefcase } from 'lucide-react';

const TaskDetailModal = ({ task, onClose, onSave }) => {
    const [comment, setComment] = useState("");
    const [extensionDays, setExtensionDays] = useState(task.extension_days || 0);
    const [isSaving, setIsSaving] = useState(false);

    if (!task) return null;

    const handleSave = async () => {
        setIsSaving(true);
        // Simulate API call or callback
        await onSave({
            ...task,
            extension_days: parseInt(extensionDays),
            new_comment: comment
        });
        setIsSaving(false);
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-lg overflow-hidden">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b">
                    <h2 className="text-xl font-semibold text-gray-800 truncate" title={task.name}>
                        {task.name}
                    </h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-4 space-y-4">
                    {/* Key Info Grid */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="flex items-center gap-2 text-gray-600">
                            <Calendar size={16} />
                            <span>Start: {task.start}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                            <Calendar size={16} />
                            <span>End: {task.end}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                            <Briefcase size={16} />
                            <span>{task.contractor || "No Contractor"}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-600">
                            <div className="w-4 h-4 rounded-full border border-gray-300 flex items-center justify-center text-[10px]">
                                %
                            </div>
                            <span>{task.progress}% Complete</span>
                        </div>
                    </div>

                    {/* Extension Days */}
                    <div className="bg-orange-50 p-3 rounded-md border border-orange-100">
                        <div className="flex items-center gap-2 mb-2">
                            <Clock size={16} className="text-orange-600" />
                            <label className="text-sm font-medium text-orange-900">Extension Days</label>
                        </div>
                        <div className="flex items-center gap-2">
                            <input
                                type="number"
                                min="0"
                                value={extensionDays}
                                onChange={(e) => setExtensionDays(e.target.value)}
                                className="w-20 p-1 border rounded text-sm"
                            />
                            <span className="text-xs text-orange-700">days added to schedule</span>
                        </div>
                    </div>

                    {/* Comments History */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 text-gray-700">
                            <MessageSquare size={16} />
                            <h3 className="font-medium text-sm">Comments</h3>
                        </div>
                        <div className="max-h-32 overflow-y-auto bg-gray-50 rounded p-2 text-sm space-y-2">
                            {task.comments && task.comments.length > 0 ? (
                                task.comments.map((c, i) => (
                                    <div key={i} className="bg-white p-2 rounded shadow-sm border">
                                        <p className="text-gray-800">{c.text || c}</p>
                                        <p className="text-xs text-gray-400 mt-1">{c.date || "Just now"}</p>
                                    </div>
                                ))
                            ) : (
                                <p className="text-gray-400 italic">No comments yet.</p>
                            )}
                        </div>

                        {/* New Comment */}
                        <textarea
                            className="w-full p-2 border rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                            placeholder="Add a comment..."
                            rows="2"
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 bg-gray-50 flex justify-end gap-2 border-t">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                        {isSaving ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default TaskDetailModal;
