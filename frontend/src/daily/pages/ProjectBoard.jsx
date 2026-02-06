import React from 'react';
import { useParams } from 'react-router-dom';
import KanbanBoard from '../components/KanbanBoard';

const ProjectBoard = () => {
    const { projectId } = useParams();

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>Project: {projectId}</h1>
                    <p style={{ color: '#64748b' }}>Task Board</p>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn" style={{ background: 'white' }}>Members</button>
                        <button className="btn" style={{ background: 'white' }}>Settings</button>
                    </div>
                </div>
            </div>

            {/* View Area */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ height: '100%', overflowX: 'auto' }}>
                    <KanbanBoard projectId={projectId} />
                </div>
            </div>
        </div>
    );
};

export default ProjectBoard;
