import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import MyTasks from './pages/MyTasks';
import ProjectBoard from './pages/ProjectBoard';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Login from './pages/Login';
import OrgSelection from './pages/OrgSelection';
import ProjectsList from './pages/ProjectsList';
import InitLoading from './components/InitLoading';

function AuthGuard({ children, user }) {
    const location = useLocation();
    const orgId = localStorage.getItem("ao_org_id");

    if (!user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!orgId && location.pathname !== "/select-org") {
        return <Navigate to="/select-org" replace />;
    }

    return children;
}

function Layout({ children, user }) {
    return (
        <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
            <Sidebar />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <Topbar user={user} />
                <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem', background: '#f1f5f9' }}>
                    {children}
                </div>
            </div>
        </div>
    );
}

function App() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check for existing session (Mock)
        const savedUser = localStorage.getItem("ao_user");

        setTimeout(() => {
            if (savedUser) {
                setUser(JSON.parse(savedUser));
            }
            setLoading(false);
        }, 500);
    }, []);

    if (loading) return <InitLoading />;

    return (
        <HashRouter>
            <Routes>
                <Route path="/login" element={<Login setUser={setUser} />} />
                <Route path="/select-org" element={
                    user ? <OrgSelection /> : <Navigate to="/login" replace />
                } />

                {/* Protected Routes */}
                <Route path="/*" element={
                    <AuthGuard user={user}>
                        <Layout user={user}>
                            <Routes>
                                <Route path="/" element={<Navigate to="/dashboard" replace />} /> {/* Default to dashboard */}
                                <Route path="/dashboard" element={<Dashboard />} />
                                <Route path="/my-tasks" element={<MyTasks />} />
                                <Route path="/projects" element={<ProjectsList />} />
                                <Route path="/board/:projectId" element={<ProjectBoard />} />
                                <Route path="/chat/:projectId" element={<Chat />} />
                            </Routes>
                        </Layout>
                    </AuthGuard>
                } />
            </Routes>
        </HashRouter>
    );
}

export default App;
