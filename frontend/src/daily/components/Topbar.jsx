import React from 'react';
import { Search, Bell, User } from 'lucide-react';

const Topbar = ({ user }) => {
    return (
        <div style={{
            height: '64px',
            background: 'white',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 1.5rem'
        }}>
            {/* Search */}
            <div style={{ position: 'relative', width: '300px' }}>
                <Search size={18} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                <input
                    type="text"
                    placeholder="Search tasks, projects..."
                    style={{
                        width: '100%',
                        padding: '0.5rem 0.5rem 0.5rem 2.5rem',
                        borderRadius: '0.375rem',
                        border: '1px solid #e2e8f0',
                        fontSize: '0.9rem',
                        outline: 'none'
                    }}
                />
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <button className="btn" style={{ background: 'transparent', color: '#64748b' }}>
                    <Bell size={20} />
                </button>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{user?.name || 'User'}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{user?.email || 'user@example.com'}</div>
                    </div>
                    <div style={{
                        width: '36px',
                        height: '36px',
                        background: '#e2e8f0',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#64748b'
                    }}>
                        <User size={20} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Topbar;
