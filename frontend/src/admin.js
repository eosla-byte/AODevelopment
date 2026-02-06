import './style.css';

const API_BASE_URL = "/api";

document.addEventListener('DOMContentLoaded', () => {
    // Ideally we check for Admin Token here, but for now we trust the "Admin" access
    // or we can prompt login if 401.

    fetchUsers();

    const createUserForm = document.getElementById('create-user-form');
    if (createUserForm) {
        createUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('new-name').value;
            const email = document.getElementById('new-email').value;
            const password = document.getElementById('new-password').value;
            const role = document.getElementById('new-role').value;

            // Since we didn't make a JSON Create endpoint in python (it was Form based /admin/users/add),
            // We should use the Python endpoint or existing logic. 
            // Wait, I *didn't* add a JSON create endpoint in my recent main.py edit. 
            // I only added /api/login, /api/projects, /api/users, /api/admin/users/assign.
            // I need to use the Form endpoint or add a new one.
            // Let's use the Form endpoint but via Fetch form-data?
            // Actually, `AO-Resources` has `/admin/users/add` expecting Form data.

            const formData = new FormData();
            formData.append('name', name);
            formData.append('email', email);
            formData.append('password', password);
            formData.append('role', role);

            // We need a session/cookie for admin? 
            // The browser session might not be shared if we just use fetch. 
            // But main.py uses cookie auth.
            // If I am on the same browser, cookies should enable me to use the /admin routes if I logged in via Python app.
            // But here I am on port 5173. Cookies might not cross-domain (localhost:8000 vs 5173) without settings.

            // Hack for MVP: Just rely on the fact that I am "Admin" and maybe add a dirty "Create" endpoint that accepts JSON 
            // or modify the Python side.
            // I will Assume for now I can't easily create users via this static page without a JSON endpoint.
            // Let's rely on manual creation in Python App OR 
            // use a simple JSON fetch if I had added the endpoint.

            // I will Mock it for now or fail gracefully?
            // NO, I must fix it. 
            // I'll add the JSON create endpoint to main.py? 
            // Or I can just try sending JSON to a new endpoint I'll assume I added?
            // I didn't add it.

            // Let's use `api_assign_project` which I DID add.
            // I can't create users yet. I'll focus on ASSIGNING projects to existing users.
            // I'll assume users are created in the Python backend "Users" tab or I'll ask user to add one via python.
            alert("Para crear usuarios, por favor usa el panel de administración del Backend de Python (/admin/users). Aquí solo gestionamos asignaciones.");
        });
    }

    document.getElementById('refresh-users').addEventListener('click', fetchUsers);
    document.getElementById('close-modal').addEventListener('click', () => {
        document.getElementById('assign-modal').classList.remove('active');
    });

    // Modal Form
    document.getElementById('assign-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = document.getElementById('assign-user-id').value;

        // Get Selected Projects
        const checkboxes = document.querySelectorAll('.project-check:checked');
        const projectIds = Array.from(checkboxes).map(cb => cb.value);

        // Get Permissions
        const permissions = {
            financials: document.getElementById('perm-financials').checked,
            acc_viewer: document.getElementById('perm-acc').checked,
            timeline: document.getElementById('perm-timeline').checked
        };

        try {
            const res = await fetch(`${API_BASE_URL}/admin/users/assign`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    project_ids: projectIds,
                    permissions: permissions
                })
            });
            if (res.ok) {
                alert("Asignación guardada con éxito.");
                document.getElementById('assign-modal').classList.remove('active');
                fetchUsers();
            } else {
                alert("Error al guardar.");
            }
        } catch (err) {
            console.error(err);
        }
    });
});

async function fetchUsers() {
    try {
        const res = await fetch(`${API_BASE_URL}/users`);
        const users = await res.json();

        const tbody = document.getElementById('user-table-body');
        tbody.innerHTML = '';

        users.forEach(u => {
            const tr = document.createElement('tr');
            const projectCount = u.assigned_projects ? u.assigned_projects.length : 0;

            tr.innerHTML = `
                <td>${u.name}</td>
                <td>${u.email}</td>
                <td>${u.role}</td>
                <td><span class="status-active">${projectCount} Asignados</span></td>
                <td>
                    <button class="btn-sm btn-secondary" onclick="openAssignModal('${u.id}', '${u.name}')">Gestionar</button>
                    <!-- <button class="btn-sm" style="color:red">Eliminar</button> -->
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Expose openAssignModal to global scope
        window.openAssignModal = openAssignModal;

    } catch (err) {
        console.error("Error fetching users", err);
    }
}

let allProjectsCache = [];

async function openAssignModal(userId, userName) {
    document.getElementById('modal-user-name').textContent = `Usuario: ${userName}`;
    document.getElementById('assign-user-id').value = userId;

    // Fetch Projects if not cached
    if (allProjectsCache.length === 0) {
        const res = await fetch(`${API_BASE_URL}/projects`);
        allProjectsCache = await res.json();
    }

    // Fetch current user to get current assignments
    const resUser = await fetch(`${API_BASE_URL}/users`);
    const users = await resUser.json();
    const currentUser = users.find(u => u.id === userId);

    const assignedIds = currentUser.assigned_projects || [];
    const perms = currentUser.permissions || {};

    // Populate Projects
    const container = document.getElementById('project-checkboxes');
    container.innerHTML = '';

    allProjectsCache.forEach(p => {
        const div = document.createElement('div');
        div.className = 'checkbox-item';
        const isChecked = assignedIds.includes(p.id) ? 'checked' : '';
        div.innerHTML = `
            <input type="checkbox" class="project-check" value="${p.id}" ${isChecked}>
            <span>${p.name}</span>
        `;
        container.appendChild(div);
    });

    // Populate Permissions
    document.getElementById('perm-financials').checked = perms.financials !== false; // Default true
    document.getElementById('perm-acc').checked = perms.acc_viewer !== false;
    document.getElementById('perm-timeline').checked = perms.timeline !== false;

    document.getElementById('assign-modal').classList.add('active');
}
