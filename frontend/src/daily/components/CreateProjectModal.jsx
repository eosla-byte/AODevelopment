import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const CreateProjectModal = ({ onClose, onCreated, teams }) => {
    const [name, setName] = useState("");
    const [teamId, setTeamId] = useState(teams[0]?.id || "");
    const [bimProjectId, setBimProjectId] = useState("");
    const [bimProjects, setBimProjects] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Fetch available BIM projects from backend
        // For MVP/Dev, we'll try to fetch, if fail, show empty
        const fetchBimProjects = async () => {
            const orgId = localStorage.getItem("ao_org_id");
            if (!orgId) return;

            try {
                const response = await fetch('/bim-projects', {
                    headers: { 'X-Organization-ID': orgId }
                });
                if (response.ok) {
                    const data = await response.json();
                    setBimProjects(data);
                }
            } catch (error) {
                console.error("Failed to fetch BIM projects", error);
                // Mock for dev if backend not ready
                // setBimProjects([{ id: "bim1", name: "Torre Reforma (BIM)" }]);
            }
        };

        fetchBimProjects();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        const orgId = localStorage.getItem("ao_org_id");
        // Mock User ID for now, or get from context if we had it. Backend dependencies handle it via headers usually or token.
        // But the create_project endpoint uses Depends(get_current_user_id) which reads X-User-ID.
        // We need to ensure we send that.

        try {
            const response = await fetch('/projects', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Organization-ID': orgId,
                    'X-User-ID': "u123" // Mock ID matching App.jsx mock
                },
                body: JSON.stringify({
                    name: name,
                    team_id: teamId,
                    bim_project_id: bimProjectId || null
                })
            });

            if (response.ok) {
                const newProject = await response.json();
                onCreated(newProject);
                onClose();
            } else {
                alert("Error creating project");
            }
        } catch (error) {
            console.error(error);
            alert("Error creating project");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
            background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50
        }}>
            <div style={{ background: 'white', padding: '2rem', borderRadius: '12px', width: '400px', position: 'relative' }}>
                <button onClick={onClose} style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', cursor: 'pointer' }}>
                    <X size={20} />
                </button>

                <h2 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: '1.25rem' }}>Create New Project</h2>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', marginBottom: '0.5rem', fontWeight: 500 }}>Project Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            required
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                            placeholder="e.g. Website Redesign"
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', marginBottom: '0.5rem', fontWeight: 500 }}>Team</label>
                        <select
                            value={teamId}
                            onChange={e => setTeamId(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                        >
                            {teams.map(t => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', marginBottom: '0.5rem', fontWeight: 500 }}>Link to BIM Project (Optional)</label>
                        <select
                            value={bimProjectId}
                            onChange={e => setBimProjectId(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                        >
                            <option value="">-- None --</option>
                            {bimProjects.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                        <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                            Linking allows synchronization with BIM schedules.
                        </p>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            marginTop: '1rem', padding: '0.75rem', background: '#3b82f6', color: 'white',
                            border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600,
                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}
                    >
                        {loading ? "Creating..." : "Create Project"}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default CreateProjectModal;
