import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const CreateProjectModal = ({ onClose, onCreated, teams }) => {
    const [name, setName] = useState("");
    const [teamId, setTeamId] = useState(teams[0]?.id || "");
    const [isNewTeam, setIsNewTeam] = useState(false);
    const [newTeamName, setNewTeamName] = useState("");
    const [orgUsers, setOrgUsers] = useState([]);
    const [selectedMembers, setSelectedMembers] = useState([]);

    const [bimProjectId, setBimProjectId] = useState("");
    const [bimProjects, setBimProjects] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const orgId = localStorage.getItem("ao_org_id");
        if (!orgId) return;

        // Fetch BIM Projects
        const fetchBimProjects = async () => {
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
            }
        };

        // Fetch Org Users for Team Creation
        const fetchOrgUsers = async () => {
            try {
                const response = await fetch('/org-users', {
                    headers: { 'X-Organization-ID': orgId }
                });
                if (response.ok) {
                    const data = await response.json();
                    setOrgUsers(data);
                }
            } catch (error) {
                console.error("Failed to fetch Org users", error);
            }
        };

        fetchBimProjects();
        fetchOrgUsers();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        const orgId = localStorage.getItem("ao_org_id");

        // Resolve Real User ID
        // The Mock Login stores "u123", which is invalid in the DB.
        // We match the logged-in email against the fetched Organization Users to find the REAL ID.
        let userId = null;
        try {
            const storedUser = JSON.parse(localStorage.getItem("ao_user") || "{}");
            const email = storedUser.email;
            if (email && orgUsers.length > 0) {
                const found = orgUsers.find(u => u.email.toLowerCase() === email.toLowerCase());
                if (found) userId = found.id;
            }
            // Fallback: Use the first user if match fails (desperate measure for dev) or keep null
            if (!userId && orgUsers.length > 0) {
                console.warn("Could not match logged in email to Org Users. Using first user as fallback.");
                userId = orgUsers[0].id;
            }
        } catch (e) {
            console.error("Error resolving user ID", e);
        }

        if (!userId) {
            alert("Error: Could not identify current user. Please reload.");
            setLoading(false);
            return;
        }

        try {
            const payload = {
                name: name,
                bim_project_id: bimProjectId || null
            };

            if (isNewTeam) {
                payload.new_team_name = newTeamName;
                payload.members = selectedMembers;
            } else {
                payload.team_id = teamId;
            }

            const response = await fetch('/projects', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Organization-ID': orgId,
                    'X-User-ID': userId
                },
                body: JSON.stringify(payload)
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
                            value={isNewTeam ? "NEW" : teamId}
                            onChange={e => {
                                console.log("Team Selection Change:", e.target.value);
                                if (e.target.value === "NEW") {
                                    setIsNewTeam(true);
                                    setTeamId("");
                                } else {
                                    setIsNewTeam(false);
                                    setTeamId(e.target.value);
                                }
                            }}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                        >
                            <option value="" disabled>-- Select a Team --</option>
                            {teams.map(t => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                            <option value="NEW">+ Create New Team</option>
                        </select>
                    </div>

                    {isNewTeam && (
                        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                            <label style={{ display: 'block', fontSize: '0.8rem', marginBottom: '0.5rem', fontWeight: 600 }}>New Team Name</label>
                            <input
                                type="text"
                                value={newTeamName}
                                onChange={e => setNewTeamName(e.target.value)}
                                required={isNewTeam}
                                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', marginBottom: '0.75rem' }}
                                placeholder="e.g. Frontend Squad"
                            />

                            <label style={{ display: 'block', fontSize: '0.8rem', marginBottom: '0.5rem', fontWeight: 600 }}>Add Members</label>
                            <div style={{ maxHeight: '100px', overflowY: 'auto', border: '1px solid #e2e8f0', background: 'white', padding: '0.5rem', borderRadius: '4px' }}>
                                {orgUsers.length === 0 ? <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>No users found</p> :
                                    orgUsers.map(u => (
                                        <div key={u.id} style={{ display: 'flex', alignItems: 'center', marginBottom: '0.25rem' }}>
                                            <input
                                                type="checkbox"
                                                value={u.id}
                                                checked={selectedMembers.includes(u.id)}
                                                onChange={e => {
                                                    if (e.target.checked) setSelectedMembers([...selectedMembers, u.id]);
                                                    else setSelectedMembers(selectedMembers.filter(id => id !== u.id));
                                                }}
                                                style={{ marginRight: '0.5rem' }}
                                            />
                                            <span style={{ fontSize: '0.85rem' }}>{u.name || u.email}</span>
                                        </div>
                                    ))
                                }
                            </div>
                        </div>
                    )}

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
