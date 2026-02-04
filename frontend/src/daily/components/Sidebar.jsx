import React from 'react';
import { Layout, CheckSquare, MessageSquare, BarChart2, Folder } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
    const navItems = [
        { icon: <CheckSquare size={20} />, label: "My Tasks", path: "/" },
        { icon: <Folder size={20} />, label: "Projects", path: "/board/demo" }, // Demo link
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
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Team: AO Devs</div>
            </div>
        </div>
    );
};

export default Sidebar;
