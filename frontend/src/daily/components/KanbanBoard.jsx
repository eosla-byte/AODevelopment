import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { api } from '../services/api';
import { Plus, MoreHorizontal } from 'lucide-react';

const TaskCard = ({ task, index }) => {
    return (
        <Draggable draggableId={task.id} index={index}>
            {(provided, snapshot) => (
                <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                    className="card"
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
                            {task.priority}
                        </span>
                        <MoreHorizontal size={14} color="#94a3b8" />
                    </div>
                    <div style={{ fontWeight: 500, fontSize: '0.95rem', marginBottom: '0.75rem' }}>{task.title}</div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: '#cbd5e1', border: '2px solid white' }}></div>
                    </div>
                </div>
            )}
        </Draggable>
    );
};

const KanbanColumn = ({ column }) => {
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
                <div style={{ fontWeight: 600, color: '#334155' }}>
                    {column.title} <span style={{ color: '#94a3b8', fontSize: '0.8rem', marginLeft: '0.5rem' }}>{column.tasks.length}</span>
                </div>
                <button className="btn" style={{ padding: '0.25rem' }}><Plus size={16} /></button>
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
                                <TaskCard key={task.id} task={task} index={index} />
                            ))}
                            {provided.placeholder}
                        </div>
                    )}
                </Droppable>
            </div>
            <div style={{ padding: '0.75rem' }}>
                <button className="btn" style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748b', justifyContent: 'center' }}>
                    <Plus size={16} /> Add Task
                </button>
            </div>
        </div>
    );
};

const KanbanBoard = ({ projectId }) => {
    const [board, setBoard] = useState(null);

    useEffect(() => {
        api.getBoard(projectId).then(setBoard);
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

    if (!board) return <div>Loading Board...</div>;

    return (
        <DragDropContext onDragEnd={onDragEnd}>
            <div style={{ display: 'flex', gap: '1.5rem', height: '100%', alignItems: 'flex-start' }}>
                {board.columns.map(col => (
                    <KanbanColumn key={col.id} column={col} />
                ))}
            </div>
        </DragDropContext>
    );
};

export default KanbanBoard;
