import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { api } from '../services/api';
import { Plus, MoreHorizontal, MessageSquare, Paperclip } from 'lucide-react';
import TaskDetailModal from './TaskDetailModal';

const TaskCard = ({ task, index, onClick }) => {
    return (
        <Draggable draggableId={task.id} index={index}>
            {(provided, snapshot) => (
                <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                    className="card group cursor-pointer"
                    onClick={(e) => {
                        if (!e.defaultPrevented) {
                            onClick(task);
                        }
                    }}
                    style={{
                        marginBottom: '0.75rem',
                        userSelect: 'none',
                        background: snapshot.isDragging ? '#e2e8f0' : 'white',
                        ...provided.draggableProps.style
                    }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <span style={{
                            fontSize: '0.7rem',
                            padding: '0.1rem 0.5rem',
                            borderRadius: '0.25rem',
                            background: task.priority === 'Urgent' ? '#fee2e2' : '#f1f5f9',
                            color: task.priority === 'Urgent' ? '#ef4444' : '#64748b'
                        }}>
                            {task.priority || 'Medium'}
                        </span>
                        <MoreHorizontal size={14} color="#94a3b8" />
                    </div>
                    <div style={{ fontWeight: 500, fontSize: '0.95rem', marginBottom: '0.75rem', color: '#1e293b' }}>
                        {task.title}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        {/* Indicators */}
                        <div className="flex gap-2 text-gray-400">
                            {(task.comment_count > 0 || task.comments?.length > 0) && (
                                <div className="flex items-center gap-1 text-[10px]">
                                    <MessageSquare size={12} /> {task.comment_count || task.comments?.length}
                                </div>
                            )}
                            {(task.attachment_count > 0 || task.attachments?.length > 0) && (
                                <div className="flex items-center gap-1 text-[10px]">
                                    <Paperclip size={12} /> {task.attachment_count || task.attachments?.length}
                                </div>
                            )}
                        </div>

                        {/* Assignees (Placeholder) */}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginLeft: 'auto' }}>
                            <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] font-bold border-2 border-white">
                                {(task.assignees?.[0] || "U").charAt(0).toUpperCase()}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Draggable>
    );
};

const KanbanColumn = ({ column, onTaskClick }) => {
    return (
        <div style={{
            background: '#f8fafc',
            minWidth: '280px',
            width: '280px',
            borderRadius: '0.5rem',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            maxHeight: 'calc(100vh - 120px)'
        }}>
            {/* Header */}
            <div style={{ padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontWeight: 600, color: '#334155', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {column.title}
                    <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{column.tasks.length}</span>
                    <span className="text-[10px] bg-purple-100 text-purple-700 px-1 rounded border border-purple-200" title="Deployment Version">V7.2-Assign-Retry</span>
                </div>
                <button
                    className="btn p-1 hover:bg-white rounded"
                    onClick={() => onTaskClick({ isNew: true, columnId: column.id })}
                >
                    <Plus size={16} />
                </button>
            </div>

            {/* List */}
            <div style={{ flex: 1, padding: '0 0.75rem', overflowY: 'auto' }}>
                <Droppable droppableId={column.id}>
                    {(provided, snapshot) => (
                        <div
                            {...provided.droppableProps}
                            ref={provided.innerRef}
                            style={{ minHeight: '100px', background: snapshot.isDraggingOver ? '#f1f5f9' : 'transparent', borderRadius: '0.5rem' }}
                        >
                            {column.tasks.map((task, index) => (
                                <TaskCard key={task.id} task={task} index={index} onClick={onTaskClick} />
                            ))}
                            {provided.placeholder}
                        </div>
                    )}
                </Droppable>
            </div>
            <div style={{ padding: '0.75rem' }}>
                <button
                    className="btn w-full flex items-center justify-center gap-2 text-gray-500 hover:bg-white hover:shadow-sm"
                    onClick={() => onTaskClick({ isNew: true, columnId: column.id })}
                >
                    <Plus size={16} /> Add Task
                </button>
            </div>
        </div>
    );
};

const KanbanBoard = ({ projectId }) => {
    const [board, setBoard] = useState(null);
    const [selectedTask, setSelectedTask] = useState(null);

    const fetchBoard = () => {
        api.getBoard(projectId).then(setBoard);
    };

    useEffect(() => {
        fetchBoard();
    }, [projectId]);

    const onDragEnd = (result) => {
        const { destination, source, draggableId } = result;

        if (!destination) return;
        if (destination.droppableId === source.droppableId && destination.index === source.index) return;

        // Optimistic Update
        const newColumns = [...board.columns];
        const sourceColIdx = newColumns.findIndex(c => c.id === source.droppableId);
        const destColIdx = newColumns.findIndex(c => c.id === destination.droppableId);

        const sourceCol = newColumns[sourceColIdx];
        const destCol = newColumns[destColIdx];

        const task = sourceCol.tasks.find(t => t.id === draggableId);

        // Remove from source
        sourceCol.tasks.splice(source.index, 1);
        // Add to dest
        destCol.tasks.splice(destination.index, 0, task);

        setBoard({ ...board, columns: newColumns });

        // API Call
        api.moveTask(draggableId, destCol.id, destination.index);
    };

    const handleTaskClick = async (taskOrEvent) => {
        // Just open the modal (TaskDetailModal handles creation now)
        setSelectedTask(taskOrEvent);
    };

    const handleTaskUpdate = (updatedTask) => {
        // Simple Refresh for now to unsure consistency
        fetchBoard();
        // Or Optimistic update locally if needed
    };

    if (!board) return <div>Loading Board...</div>;

    return (
        <>
            <DragDropContext onDragEnd={onDragEnd}>
                <div style={{ display: 'flex', gap: '1.5rem', height: '100%', alignItems: 'flex-start' }}>
                    {board.columns.map(col => (
                        <KanbanColumn key={col.id} column={col} onTaskClick={handleTaskClick} />
                    ))}
                </div>
            </DragDropContext>

            {/* Modal */}
            {selectedTask && (
                <TaskDetailModal
                    task={selectedTask}
                    onClose={() => setSelectedTask(null)}
                    onUpdate={handleTaskUpdate}
                />
            )}
        </>
    );
};

export default KanbanBoard;
