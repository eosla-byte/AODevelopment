import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { BarChart2, CheckCircle, Circle, Clock, User } from 'lucide-react';

const StatCard = ({ title, value, icon, color }) => (
    <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ padding: '0.75rem', background: `${color}20`, borderRadius: '8px', color: color }}>
            {icon}
        </div>
        <div>
            <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 500 }}>{title}</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>{value}</div>
        </div>
    </div>
);

const Dashboard = () => {
    // Ideally we would select a project first or show aggregate? 
    // The user requested "Project Metrics". Let's assume we are in a project context or picking one.
    // However, the router route is "/dashboard" (global) AND "/board/:projectId".
    // If global dashboard, maybe show "Select Project" or Aggregate?
    // User request: "generara un perfil en Dashboard...". This sounds like Per-Project Dashboard.
    // Let's check App.jsx routes.
    // Route "/dashboard" is global.
    // Route "/board/:projectId" is the Kanban.
    // Maybe we need "/dashboard/:projectId"?
    // Or we just show a list of projects to pick stats from?
    // Let's implement a simple project picker if no ID, or if we have one (from URL?)

    // Actually, currently Dashboard is global.
    // Let's make it show stats for ALL projects or allow filtering.
    // For MVP transparency, I'll fetch ALL teams/projects and let user pick, or just show the first one.

    // Wait, the user said "generara un perfil en Dashboard... para entrar a ver las metricas del proyecto".
    // This implies clicking on a project -> Dashboard.
    // Currently clicking project -> Board.
    // Maybe we add a "Dashboard" tab IN the project view? or a separate link.
    // For now, I'll make the main Dashboard page allow selecting a project to view stats.

    const [projects, setProjects] = useState([]);
    const [selectedProjectId, setSelectedProjectId] = useState(null);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Load projects first
        const loadProjects = async () => {
            const orgId = localStorage.getItem("ao_org_id");
            if (!orgId) return;
            // CORRECT USER ID RETRIEVAL
            let userId = null;
            try {
                const storedUser = JSON.parse(localStorage.getItem("ao_user") || "{}");
                if (storedUser.id && storedUser.id !== 'u123') {
                    userId = storedUser.id;
                } else if (storedUser.email) {
                    userId = "u123";
                }
            } catch (e) { console.error(e); }

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
                            if (found) effectiveUserId = found.id;
                        }
                    }
                } catch (e) { console.error(e); }
            }
            try {
                const res = await fetch('/init', {
                    headers: { 'X-Organization-ID': orgId, 'X-User-ID': effectiveUserId }
                });
                if (res.ok) {
                    const data = await res.json();
                    // Flatten projects
                    const all = [];
                    data.teams.forEach(t => all.push(...t.projects));
                    setProjects(all);
                    // if (all.length > 0) setSelectedProjectId(all[0].id); // Removed auto-select
                }
            } catch (e) {
                console.error(e);
            }
        };
        loadProjects();
    }, []);

    useEffect(() => {
        if (!selectedProjectId) return;

        const loadMetrics = async () => {
            setLoading(true);
            try {
                const res = await fetch(`/projects/${selectedProjectId}/metrics`);
                if (res.ok) {
                    const data = await res.json();
                    setMetrics(data);
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        loadMetrics();
    }, [selectedProjectId]);

    if (!selectedProjectId) {
        if (loading && projects.length === 0) return <div style={{ padding: '2rem' }}>Loading Projects...</div>;

        // Group projects by team (Quick grouping since we flattened them earlier? No, projects is flat.
        // Effectively we want the same view as Chat. But here we flattened projects in loadProjects.
        // Let's refactor loadProjects to keep teams structure or just show flat?
        // User asked for "same as Chat". Chat is grouped.
        // I should refactor loadProjects to setTeams too.

        // To stay consistent and fast: I will render a grid of projects (flat or gathered).
        // Since I already have `projects` state, I will render them.
        return (
            <div style={{ padding: '2rem' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#1e293b', marginBottom: '2rem' }}>Select Project for Dashboard</h1>
                {projects.length === 0 ? (
                    <div style={{ textAlign: 'center', marginTop: '4rem', color: '#64748b' }}>
                        <p>No projects found.</p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
                        {projects.map(p => (
                            <div
                                key={p.id}
                                onClick={() => setSelectedProjectId(p.id)}
                                style={{
                                    background: 'white', padding: '1.5rem', borderRadius: '12px',
                                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0',
                                    cursor: 'pointer', transition: 'transform 0.2s', display: 'flex', flexDirection: 'column',
                                    gap: '1rem'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{ background: '#ecfdf5', color: '#10b981', padding: '0.5rem', borderRadius: '8px' }}>
                                        <BarChart2 size={24} />
                                    </div>
                                    <div>
                                        <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#1e293b' }}>{p.name}</h3>
                                        {/* We don't have team name easily here unless we change fetch logic */}
                                    </div>
                                </div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b' }}>
                                    Click to view metrics
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button
                        onClick={() => setSelectedProjectId(null)}
                        style={{ background: 'white', border: '1px solid #cbd5e1', padding: '0.5rem', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                    >
                        ← Back
                    </button>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>
                        {projects.find(p => p.id === selectedProjectId)?.name} Metrics
                    </h1>
                </div>

                {/* Optional Quick Switcher */}
                <select
                    value={selectedProjectId || ""}
                    onChange={e => setSelectedProjectId(e.target.value)}
                    style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                    {projects.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                </select>
            </div>

            {loading || !metrics ? (
                <div>Loading Metrics...</div>
            ) : (
                <>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                        <StatCard
                            title="Total Tasks"
                            value={metrics.total_tasks}
                            icon={<BarChart2 size={24} />}
                            color="#3b82f6"
                        />
                        <StatCard
                            title="Pending"
                            value={metrics.pending}
                            icon={<Circle size={24} />}
                            color="#f59e0b"
                        />
                        <StatCard
                            title="In Progress"
                            value={metrics.in_progress}
                            icon={<Clock size={24} />}
                            color="#8b5cf6"
                        />
                        <StatCard
                            title="Done"
                            value={metrics.done}
                            icon={<CheckCircle size={24} />}
                            color="#10b981"
                        />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                        {/* User Stats */}
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                            <h3 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: '1.1rem', color: '#334155' }}>Team Performance</h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {Object.entries(metrics.user_stats).length === 0 ? (
                                    <p style={{ color: '#94a3b8' }}>No active users.</p>
                                ) : (
                                    Object.entries(metrics.user_stats).map(([uid, count]) => (
                                        <div key={uid} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                <div style={{ width: '32px', height: '32px', background: '#f1f5f9', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                                                    <User size={16} />
                                                </div>
                                                <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>User {uid.substring(0, 5)}...</span>
                                            </div>
                                            <div style={{ background: '#eff6ff', color: '#3b82f6', padding: '0.25rem 0.75rem', borderRadius: '100px', fontSize: '0.85rem', fontWeight: 600 }}>
                                                {count} Tasks
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Top Performer Highlight */}
                        <div style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)', padding: '1.5rem', borderRadius: '12px', color: 'white', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
                            <h3 style={{ margin: 0, opacity: 0.9, fontSize: '1rem' }}>Top Performer</h3>
                            <div style={{ margin: '1.5rem 0', width: '80px', height: '80px', background: 'rgba(255,255,255,0.2)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <User size={40} color="white" />
                            </div>
                            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                                {metrics.top_user_id ? `User ${metrics.top_user_id.substring(0, 5)}` : "None"}
                            </div>
                            <div style={{ opacity: 0.8, fontSize: '0.9rem', marginTop: '0.5rem' }}>
                                Most active contributor
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default Dashboard;
