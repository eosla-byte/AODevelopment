import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Folder, Calendar } from 'lucide-react';
import CreateProjectModal from '../components/CreateProjectModal';

const ProjectsList = () => {
    const [teams, setTeams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const fetchProjects = async () => {
        const orgId = localStorage.getItem("ao_org_id");
        if (!orgId) return;

        try {
            // Re-using /init logic or creating a dedicated /teams endpoint GET
            // For now, let's assume /init gives us everything we need
            const response = await fetch('/init', {
                headers: {
                    'X-Organization-ID': orgId,
                    'X-User-ID': "u123"
                }
            });
            if (response.ok) {
                const data = await response.json();
                setTeams(data.teams); // [{id, name, projects: []}]
            }
        } catch (error) {
            console.error("Failed to load projects", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const handleProjectCreated = (newProject) => {
        // Refresh list
        fetchProjects();
    };

    if (loading) return <div style={{ padding: '2rem' }}>Loading Projects...</div>;

    return (
        <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#1e293b', margin: 0 }}>Projects</h1>
                <button
                    onClick={() => setShowCreateModal(true)}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '0.5rem',
                        padding: '0.75rem 1.25rem', background: '#3b82f6', color: 'white',
                        border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 500
                    }}
                >
                    <Plus size={20} /> New Project
                </button>
            </div>

            {teams.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#64748b', marginTop: '4rem' }}>
                    <Folder size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
                    <p>No teams found. Create a team first.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    {teams.map(team => (
                        <div key={team.id}>
                            <h3 style={{ fontSize: '1.1rem', color: '#475569', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {team.name}
                            </h3>

                            {team.projects.length === 0 ? (
                                <div style={{ padding: '1rem', border: '1px dashed #cbd5e1', borderRadius: '8px', color: '#94a3b8', fontSize: '0.9rem' }}>
                                    No projects in this team yet.
                                </div>
                            ) : (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
                                    {team.projects.map(project => (
                                        <Link
                                            key={project.id}
                                            to={`/board/${project.id}`}
                                            style={{ textDecoration: 'none' }}
                                        >
                                            <div style={{
                                                background: 'white', padding: '1.5rem', borderRadius: '12px',
                                                boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0',
                                                transition: 'transform 0.2s',
                                                height: '100%', display: 'flex', flexDirection: 'column'
                                            }}
                                                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                                    <div style={{ background: '#eff6ff', color: '#3b82f6', padding: '0.5rem', borderRadius: '8px' }}>
                                                        <Folder size={20} />
                                                    </div>
                                                </div>
                                                <h4 style={{ margin: '0 0 0.5rem 0', color: '#1e293b', fontSize: '1.1rem' }}>{project.name}</h4>
                                                <p style={{ margin: 0, color: '#64748b', fontSize: '0.9rem' }}>
                                                    Kanban Board
                                                </p>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {showCreateModal && (
                <CreateProjectModal
                    onClose={() => setShowCreateModal(false)}
                    onCreated={handleProjectCreated}
                    teams={teams}
                />
            )}
        </div>
    );
};

export default ProjectsList;
