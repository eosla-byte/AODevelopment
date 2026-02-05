import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import KanbanBoard from '../components/KanbanBoard';
import TimelineView from '../components/TimelineView';
import { Layout, Calendar } from 'lucide-react';

const ProjectBoard = () => {
    const { projectId } = useParams();
    const [activeView, setActiveView] = useState('board'); // 'board' | 'timeline'

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>Project: {projectId}</h1>
                    <p style={{ color: '#64748b' }}>
                        {activeView === 'board' ? 'Task Board' : 'Gantt Timeline'}
                    </p>
                </div>

                {/* View Switcher & Actions */}
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {/* View Tabs */}
                    <div className="flex bg-gray-100 p-1 rounded-lg">
                        <button
                            onClick={() => setActiveView('board')}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeView === 'board'
                                    ? 'bg-white text-blue-600 shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            <Layout size={16} />
                            Board
                        </button>
                        <button
                            onClick={() => setActiveView('timeline')}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeView === 'timeline'
                                    ? 'bg-white text-blue-600 shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            <Calendar size={16} />
                            Timeline
                        </button>
                    </div>

                    <div style={{ width: '1px', height: '24px', background: '#e2e8f0' }}></div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn" style={{ background: 'white' }}>Members</button>
                        <button className="btn" style={{ background: 'white' }}>Settings</button>
                    </div>
                </div>
            </div>

            {/* View Area */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
                {activeView === 'board' ? (
                    <div style={{ height: '100%', overflowX: 'auto' }}>
                        <KanbanBoard projectId={projectId} />
                    </div>
                ) : (
                    <TimelineView projectId={projectId} />
                )}
            </div>
        </div>
    );
};

export default ProjectBoard;
