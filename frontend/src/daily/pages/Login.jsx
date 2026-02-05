import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const MOCK_USER = {
    id: "u123",
    name: "Arquitecto",
    email: "arqui@somosao.com"
};

function Login({ setUser }) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const navigate = useNavigate();

    const handleLogin = (e) => {
        e.preventDefault();
        console.log("AO Daily: Logging in with", email);

        // Mock Login
        if (email) { // Accept any email for now in Dev
            const user = { ...MOCK_USER, email: email };
            setUser(user);
            localStorage.setItem("ao_user", JSON.stringify(user));
            // In a real app, we'd get a token. Here we rely on the parent state for the session.
            navigate('/select-org');
        }
    };

    return (
        <div style={{ display: 'flex', justifyContent: 'center', itemsAlign: 'center', height: '100vh', background: '#f8fafc' }}>
            <div style={{ marginTop: '100px', width: '400px', padding: '2rem', background: 'white', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
                <h1 style={{ textAlign: 'center', marginBottom: '2rem', color: '#1e293b' }}>AO Daily</h1>
                <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                            placeholder="Enter your email"
                            required
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                            placeholder="••••••••"
                        />
                    </div>
                    <button
                        type="submit"
                        style={{ marginTop: '1rem', padding: '0.75rem', background: '#0f172a', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
                    >
                        Sign In
                    </button>
                    <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.875rem', color: '#64748b' }}>
                        (Dev Mode: Enter any email)
                    </div>
                </form>
            </div>
        </div>
    );
}

export default Login;
