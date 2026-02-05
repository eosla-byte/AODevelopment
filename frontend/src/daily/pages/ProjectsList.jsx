import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Folder, Calendar, Trash2 } from 'lucide-react';
import CreateProjectModal from '../components/CreateProjectModal';

const ProjectsList = () => {
    const [teams, setTeams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const fetchProjects = async () => {
        const orgId = localStorage.getItem("ao_org_id");
        if (!orgId) return;

        // CORRECT USER ID RETRIEVAL
        let userId = null;
        try {
            // 1. Try 'ao_user' object (set by Login)
            const storedUser = JSON.parse(localStorage.getItem("ao_user") || "{}");
            if (storedUser.id && storedUser.id !== 'u123') {
                userId = storedUser.id;
            } else if (storedUser.email) {
                // 2. Fallback: Try to use email if ID is mock or missing?
                // Actually, backend expects UUID. If we have email only, we might fail unless backend handles email lookup.
                // But init_app does not take email.
                // Let's rely on what CreateProjectModal does: it fetches Org Users to find real ID.
                // But we can't do that easily here without another fetch.

                // QUICK FIX: If 'ao_user' has a real ID (from previous session?), use it.
                // Login.jsx sets MOCK_USER with id="u123". This IS the problem.
                // We need to resolve the real ID via /org-users first or assume the backend can handle something else.

                // Wait, CreateProjectModal fetches /org-users and matches email.
                // We should do the same here or rely on specific backend endpoint that accepts email?
                // Backend has /my-organizations?email=...
                // Let's use the same logic as CreateProjectModal? It's heavy for a list fetch.

                // BETTER FIX: The MOCK LOGIN defaults to u123.
                // We should probably rely on the user manually selecting a real user in a Dev Environment,
                // OR, since this is "Daily Service", we should probably have a real login.

                // For now, let's just grab the BEST GUESS we have.
                // If the user refreshed after Project Creation, they might have a Real ID stored?
                // No, CreateProjectModal doesn't update localStorage 'ao_user'.
                // Determine effective user from email if only email is present
                userId = "u123"; // Temporarily set to fallback to trigger resolution below
            }
        } catch (e) {
            console.error("Error parsing user", e);
        }

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
                        if (found) {
                            effectiveUserId = found.id;
                        }
                    }
                }
            } catch (e) {
                console.error("Error resolving user email", e);
            }
        }

        try {
            const response = await fetch('/init', {
                headers: {
                    'X-Organization-ID': orgId,
                    'X-User-ID': effectiveUserId
                }
            });
            if (response.ok) {
                const data = await response.json();
                setTeams(data.teams);
            }
        } catch (error) {
            console.error("Failed to load projects", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteProject = async (e, projectId) => {
        e.preventDefault(); // Prevent Link navigation
        e.stopPropagation();

        if (!window.confirm("Are you sure you want to delete this project? This action cannot be undone.")) {
            return;
        }

        // Resolve User ID for API (reuse logic or just use stored if available)
        // Ideally we should have a centralized way to get headers.
        const aoUser = localStorage.getItem("ao_user");
        let userId = "u123";
        if (aoUser) {
            const u = JSON.parse(aoUser);
            userId = u.id || "u123";
        }

        try {
            const res = await fetch(`/projects/${projectId}`, {
                method: 'DELETE',
                headers: {
                    'X-User-ID': userId
                }
            });
            if (res.ok) {
                fetchProjects();
            } else {
                alert("Failed to delete project");
            }
        } catch (error) {
            console.error("Delete failed", error);
            alert("Error deleting project");
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
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                        {teams.filter(t => t.projects.length > 0).map(team => (
                            <div key={team.id}>
                                <h3 style={{ fontSize: '1.1rem', color: '#475569', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    {team.name}
                                </h3>

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
                                                height: '100%', display: 'flex', flexDirection: 'column',
                                                position: 'relative'
                                            }}
                                                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                                    <div style={{ background: '#eff6ff', color: '#3b82f6', padding: '0.5rem', borderRadius: '8px' }}>
                                                        <Folder size={20} />
                                                    </div>
                                                    <button
                                                        onClick={(e) => handleDeleteProject(e, project.id)}
                                                        style={{
                                                            background: 'transparent', border: 'none', cursor: 'pointer',
                                                            color: '#94a3b8', padding: '4px', borderRadius: '4px', // Darker gray
                                                            zIndex: 10
                                                        }}
                                                        onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = '#fee2e2'; }}
                                                        onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.background = 'transparent'; }}
                                                        title="Delete Project"
                                                    >
                                                        <Trash2 size={18} />
                                                    </button>
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
