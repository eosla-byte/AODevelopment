// Import API
import { api } from '../services/api';

// ... (MOCK_ORGS remains)

function OrgSelection() {
    const navigate = useNavigate();
    const [orgs, setOrgs] = useState([]);

    useEffect(() => {
        const fetchOrgs = async () => {
            const savedUser = localStorage.getItem("ao_user");
            if (!savedUser) return;

            try {
                const user = JSON.parse(savedUser);
                // USE API WRAPPER (Handles 401 Redirects automatically)
                const data = await api.getMyOrganizations(user.email);

                if (data && data.length > 0) {
                    setOrgs(data);
                } else {
                    console.warn("No organizations found for user.");
                    setOrgs([]);
                }
            } catch (error) {
                console.error("Failed to fetch organizations", error);
                // If 401, wrapper already redirected.
            }
        };
        fetchOrgs();
    }, []);

    const handleSelectOrg = async (orgId) => {
        console.log("AO Daily: Selected Org", orgId);
        try {
            // 1. Tell Backend to switch context (Update Token)
            await api.selectOrganization(orgId);

            // 2. Update Local State (Optional, for UI cache)
            localStorage.setItem("ao_org_id", orgId);

            // 3. Navigate
            window.location.href = "/#/dashboard";
            window.location.reload();
        } catch (e) {
            console.error("Failed to select org", e);
            alert("Failed to switch organization. Please try again.");
        }
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
