import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, HashRouter } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import MyTasks from './pages/MyTasks';
import ProjectBoard from './pages/ProjectBoard';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import InitLoading from './components/InitLoading';

// Mock Data for Dev until Backend connects
const MOCK_USER = {
    id: "u123",
    name: "Arquitecto",
    email: "arqui@somosao.com"
};

function App() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // 1. Capture Organization Context from URL
        const params = new URLSearchParams(window.location.search);
        const orgIdParam = params.get("orgId");

        if (orgIdParam) {
            console.log("AO Daily: Setting Organization Context to", orgIdParam);
            localStorage.setItem("ao_org_id", orgIdParam);
        }

        // Simulate Init
        setTimeout(() => {
            setUser(MOCK_USER);
            setLoading(false);
        }, 1000);
    }, []);

    if (loading) return <InitLoading />;

    return (
        <HashRouter> {/* HashRouter easier for static file serving via backend if needed */}
            <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
                <Sidebar />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <Topbar user={user} />
                    <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem', background: '#f1f5f9' }}>
                        <Routes>
                            <Route path="/" element={<MyTasks />} />
                            <Route path="/board/:projectId" element={<ProjectBoard />} />
                            <Route path="/dashboard" element={<Dashboard />} />
                            <Route path="/chat/:projectId" element={<Chat />} />
                        </Routes>
                    </div>
                </div>
            </div>
        </HashRouter>
    );
}

export default App;
