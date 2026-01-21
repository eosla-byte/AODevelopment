import './style.css';

// Client Portal Javascript with Real API Integration

const API_BASE_URL = "http://localhost:8000/api";

document.addEventListener('DOMContentLoaded', () => {
    const loginSection = document.getElementById('login-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const loginForm = document.getElementById('login-form');
    const logoutBtn = document.getElementById('logout-btn');

    // 1. Check for valid token on load
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('force_login') === 'true') {
        localStorage.removeItem('ao_token');
        // Clear param to clean URL? Optional, but safer to keep visual confirmation.
        // history.replaceState(null, '', 'clients.html'); 
    }

    const token = localStorage.getItem('ao_token');
    if (token) {
        loadDashboard(token);
    }

    // Custom Cursor Logic
    const cursorDot = document.querySelector('[data-cursor-dot]');
    const cursorOutline = document.querySelector('[data-cursor-outline]');
    if (cursorDot && cursorOutline) {
        window.addEventListener('mousemove', function (e) {
            const posX = e.clientX;
            const posY = e.clientY;
            cursorDot.style.left = `${posX}px`;
            cursorDot.style.top = `${posY}px`;
            cursorOutline.animate({
                left: `${posX}px`,
                top: `${posY}px`
            }, { duration: 500, fill: "forwards" });
        });
    }

    // Login Handler
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            try {
                const response = await fetch(`${API_BASE_URL}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: email, password: password })
                });

                if (!response.ok) {
                    throw new Error('Credenciales inválidas');
                }

                const data = await response.json();

                // Store Token
                localStorage.setItem('ao_token', data.access_token);

                // Load Dashboard
                loadDashboard(data.access_token);

            } catch (err) {
                alert(err.message);
            }
        });
    }

    // Logout Handler
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('ao_token');
            dashboardSection.style.display = 'none';
            loginSection.style.display = 'flex';
            loginForm.reset();
        });
    }

    async function loadDashboard(token) {
        try {
            const response = await fetch(`${API_BASE_URL}/client/dashboard`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                // Token invalid or expired
                localStorage.removeItem('ao_token');
                loginSection.style.display = 'flex';
                dashboardSection.style.display = 'none';
                return;
            }

            const data = await response.json();

            // Switch Views
            loginSection.style.display = 'none';
            dashboardSection.classList.remove('dashboard-hidden');
            dashboardSection.style.display = 'block';

            // Populate User Info
            document.getElementById('user-name-display').textContent = `Bienvenido, ${data.user.name}`;

            // Populate Projects
            const select = document.getElementById('project-select');
            select.innerHTML = '';

            if (data.projects.length === 0) {
                const option = document.createElement('option');
                option.textContent = "No tienes proyectos asignados";
                select.appendChild(option);
            } else {
                data.projects.forEach((p, index) => {
                    const option = document.createElement('option');
                    option.value = index;
                    option.textContent = p.name;
                    select.appendChild(option);
                });

                // Load first project data
                loadProjectData(data.projects[0]);

                // Listener for change
                select.addEventListener('change', (e) => {
                    const projectIndex = e.target.value;
                    if (data.projects[projectIndex]) {
                        loadProjectData(data.projects[projectIndex]);
                    }
                });
            }

        } catch (err) {
            console.error("Error loading dashboard", err);
            // Optional: fallback to login if fetch fails completely (e.g. server down)
            if (confirm("No se puede conectar al servidor. ¿Cargar modo demo?")) {
                localStorage.setItem('ao_token', 'demo_mode');
                loadDashboard('demo_mode');
            }
        }
    }

    function loadProjectData(project) {
        const formatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

        // Financials - check if present (controlled by permissions backend side)
        if (project.budget !== undefined) {
            document.getElementById('total-budget').textContent = formatter.format(project.budget);
            document.getElementById('executed-budget').textContent = formatter.format(project.executed);

            let financialPercent = 0;
            if (project.budget > 0) {
                financialPercent = (project.executed / project.budget) * 100;
            }
            document.getElementById('financial-progress-bar').style.width = `${financialPercent}%`;
            document.getElementById('financial-percentage').textContent = `${financialPercent.toFixed(1)}% Ejecutado`;
            document.querySelector('.metric-card').style.display = 'block';
        } else {
            // Hide financial card if no data
            // Or set to "Restricted"
            document.getElementById('total-budget').textContent = "---";
            document.getElementById('executed-budget').textContent = "---";
            document.getElementById('financial-percentage').textContent = "No disponible";
        }

        // Progress
        document.getElementById('projected-progress').textContent = `${project.projectedProgress}%`;
        document.getElementById('real-progress').textContent = `${project.realProgress}%`;

        // Chart Bars
        document.getElementById('chart-bar-projected').style.height = `${Math.min(project.projectedProgress, 100)}%`;
        document.getElementById('chart-bar-real').style.height = `${Math.min(project.realProgress, 100)}%`;

        // Details
        const detailsContainer = document.getElementById('project-details');
        // Handle potentially missing fields
        const location = project.location || "N/A";
        const status = project.status || "Activo";

        detailsContainer.innerHTML = `
      <p><strong>Ubicación/Legal:</strong> ${location}</p>
      <p><strong>Estado:</strong> <span class="status-tag">${status}</span></p>
      <p><strong>Inicio:</strong> ${project.start_date || '---'}</p>
      <p class="small-note">Datos actualizados al ${new Date().toLocaleDateString()}</p>
    `;

        // Load 3D Model
        // Trigger Viewer with full project data
        if (project.acc_config && project.acc_config.project) {
            initViewer(project);
        } else if (project.name) {
            // Fallback
            initViewer({ name: project.name });
        }
    }

    // ==========================================
    // AUTODESK VIEWER LOGIC
    // ==========================================
    let viewer;

    async function initViewer(projectData) {
        // 1. Get Token
        try {
            const tokenRes = await fetch('http://localhost:3000/api/aps/token');
            if (!tokenRes.ok) throw new Error("Viewer Token Service unavailable");
            const tokenData = await tokenRes.json();
            const accessToken = tokenData.access_token;

            let documentId = '';

            // 2. Resolve URN
            // If we have explicit config from DB
            if (projectData.acc_config && projectData.acc_config.project) {
                const conf = projectData.acc_config;
                // Fetch URN using specific coordinates
                const qs = new URLSearchParams({
                    hub: conf.hub,
                    project: conf.project,
                    folder: conf.folder,
                    file: conf.file
                }).toString();

                try {
                    const urnRes = await fetch(`http://localhost:3000/api/aps/urn?${qs}`);
                    if (urnRes.ok) {
                        const urnData = await urnRes.json();
                        documentId = 'urn:' + urnData.urn;
                    }
                } catch (e) { console.warn("Failed to fetch custom URN", e); }
            }

            // Fallback if no specific config or fetch failed
            if (!documentId) {
                // Fallback to project name search
                const urnRes = await fetch(`http://localhost:3000/api/aps/urn?project=${encodeURIComponent(projectData.name)}`);
                if (urnRes.ok) {
                    const urnData = await urnRes.json();
                    documentId = 'urn:' + urnData.urn;
                } else {
                    // Final Fallback Demo
                    documentId = 'urn:dXJuOmFkc2sub2JqZWN0czpvcy5vYmplY3Q6bXktYnVja2V0L215LW1vZGVsLnJ2dA';
                }
            }

            const options = {
                env: 'AutodeskProduction',
                accessToken: accessToken,
            };

            Autodesk.Viewing.Initializer(options, () => {
                const viewerDiv = document.getElementById('forge-viewer');
                if (viewerDiv) {
                    viewerDiv.innerHTML = ''; // Clear placeholder text

                    viewer = new Autodesk.Viewing.GuiViewer3D(viewerDiv);
                    viewer.start();

                    // Load Document
                    Autodesk.Viewing.Document.load(documentId, (doc) => {
                        const defaultModel = doc.getRoot().getDefaultGeometry();
                        viewer.loadDocumentNode(doc, defaultModel);

                        viewer.loadExtension('Autodesk.DocumentBrowser');
                        viewer.loadExtension('Autodesk.VisualClusters');
                    }, (errorCode) => {
                        console.error("Viewer Load Error", errorCode);
                        viewerDiv.innerHTML = `<div class="viewer-message"><p style="color:red">Error cargando modelo ACC.</p><small>Code: ${errorCode}</small></div>`;
                    });
                }
            });

        } catch (err) {
            console.log("APS Service not running or error: ", err);
            const viewerDiv = document.getElementById('forge-viewer');
            if (viewerDiv) viewerDiv.innerHTML = `<div class="viewer-message"><p>Conexión APS Inactiva</p><small>Inicia el servicio Node.js en puerto 3000</small></div>`;
        }
    }
});
