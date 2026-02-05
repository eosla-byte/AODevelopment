import React from 'react';
import { Layout, CheckSquare, MessageSquare, BarChart2, Folder, ArrowLeftRight } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
    const navItems = [
        { icon: <CheckSquare size={20} />, label: "My Tasks", path: "/" },
        { icon: <Folder size={20} />, label: "Projects", path: "/projects" },
        { icon: <MessageSquare size={20} />, label: "Chat", path: "/chat/demo" },
        { icon: <BarChart2 size={20} />, label: "Dashboard", path: "/dashboard" },
    ];

    return (
        <div style={{ width: '240px', background: '#0f172a', color: 'white', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid #1e293b' }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Layout color="#3b82f6" /> Daily
                </h2>
            </div>

            <nav style={{ flex: 1, padding: '1rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {navItems.map((item) => (
                        <NavLink
                            key={item.label}
                            to={item.path}
                            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            style={({ isActive }) => ({
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '0.75rem 1rem',
                                borderRadius: '0.5rem',
                                color: isActive ? 'white' : '#94a3b8',
                                background: isActive ? '#1e293b' : 'transparent',
                                textDecoration: 'none',
                                transition: 'all 0.2s'
                            })}
                        >
                            {item.icon}
                            <span style={{ fontSize: '0.95rem', fontWeight: 500 }}>{item.label}</span>
                        </NavLink>
                    ))}
                </div>
            </nav>

            <div style={{ padding: '1rem', borderTop: '1px solid #1e293b' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Organization</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#e2e8f0' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>
                        {localStorage.getItem("ao_org_id") === 'org_123' ? 'AO Architecture' :
                            localStorage.getItem("ao_org_id") === 'org_456' ? 'Constructora Demo' :
                                'Personal Workspace'}
                    </div>
                    <NavLink to="/select-org" style={{ color: '#94a3b8', transition: 'color 0.2s' }} title="Switch Organization">
                        <ArrowLeftRight size={16} />
                    </NavLink>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
