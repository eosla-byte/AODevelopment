import React, { useState, useEffect } from 'react';
import { Calendar, Clock, AlertCircle } from 'lucide-react';

const MyTasks = () => {
    // Mock Data
    const [tasks, setTasks] = useState([
        { id: '1', title: 'Implement Login Flow', project: 'AO Auth', priority: 'High', due: 'Today' },
        { id: '2', title: 'Fix CSS Bug', project: 'Daily App', priority: 'Medium', due: 'Tomorrow' },
        { id: '3', title: 'Review PR #42', project: 'AO Auth', priority: 'Low', due: 'Next Week' },
    ]);

    return (
        <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ fontSize: '1.8rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>My Tasks</h1>
                    <p style={{ color: '#64748b' }}>Here's what you need to focus on today.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn" style={{ background: 'white', border: '1px solid #e2e8f0' }}>Filter</button>
                    <button className="btn btn-primary">+ Add Direct Task</button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
                {/* Main List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#334155' }}>Today</h3>
                    {tasks.map(task => (
                        <div key={task.id} className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', transition: 'transform 0.1s' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{ width: '20px', height: '20px', borderRadius: '50%', border: '2px solid #cbd5e1', cursor: 'pointer' }}></div>
                                <div>
                                    <div style={{ fontWeight: 500 }}>{task.title}</div>
                                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{task.project} • {task.due}</div>
                                </div>
                            </div>
                            <span style={{
                                padding: '0.25rem 0.75rem',
                                borderRadius: '1rem',
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                background: task.priority === 'High' ? '#fee2e2' : '#f1f5f9',
                                color: task.priority === 'High' ? '#ef4444' : '#475569'
                            }}>
                                {task.priority}
                            </span>
                        </div>
                    ))}
                </div>

                {/* Plan of Day / Stats */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div className="card">
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Plan for Today</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#ef4444' }}>
                                <AlertCircle size={16} /> <span style={{ fontSize: '0.9rem' }}>2 Overdue Tasks</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f59e0b' }}>
                                <Clock size={16} /> <span style={{ fontSize: '0.9rem' }}>3 Due Today</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#3b82f6' }}>
                                <Calendar size={16} /> <span style={{ fontSize: '0.9rem' }}>2 Upcoming</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MyTasks;
