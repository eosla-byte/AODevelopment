import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

// Mock Orgs
const MOCK_ORGS = [
    { id: "org_123", name: "AO Architecture", logo: null },
    { id: "org_456", name: "Constructora Demo", logo: null },
    { id: "org_personal", name: "Personal Workspace", logo: null }
];

function OrgSelection() {
    const navigate = useNavigate();
    const [orgs, setOrgs] = useState([]);

    useEffect(() => {
        // Here we would fetch the user's organizations from the backend
        // fetch('/api/user/orgs')...
        setOrgs(MOCK_ORGS);
    }, []);

    const handleSelectOrg = (orgId) => {
        console.log("AO Daily: Selected Org", orgId);
        localStorage.setItem("ao_org_id", orgId);
        // Refresh page or navigate effectively to trigger App.jsx context reload
        // For SPA, we can just navigate, but App.jsx might need to listen to storage or we pass a callback.
        // A full reload ensures clean state for now.
        window.location.href = "/#/dashboard";
        window.location.reload();
    };

    return (
        <div style={{ display: 'flex', justifyContent: 'center', itemsAlign: 'center', height: '100vh', background: '#f8fafc' }}>
            <div style={{ marginTop: '100px', width: '500px', padding: '2rem', background: 'white', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
                <h2 style={{ textAlign: 'center', marginBottom: '0.5rem', color: '#1e293b' }}>Select Organization</h2>
                <p style={{ textAlign: 'center', marginBottom: '2rem', color: '#64748b' }}>Choose where you want to work today.</p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {orgs.map(org => (
                        <div
                            key={org.id}
                            onClick={() => handleSelectOrg(org.id)}
                            style={{
                                padding: '1.5rem',
                                border: '1px solid #e2e8f0',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                transition: 'all 0.2s',
                                '&:hover': { borderColor: '#3b82f6', background: '#f8fafc' } // Inline hover pseudo doesn't work in React style, but illustrative
                            }}
                            className="org-card" // Use class for hover if needed
                        >
                            <div style={{ width: '40px', height: '40px', background: '#e2e8f0', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '1rem' }}>
                                {org.name.charAt(0)}
                            </div>
                            <div>
                                <div style={{ fontWeight: 600, color: '#1e293b' }}>{org.name}</div>
                                <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Member</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default OrgSelection;
