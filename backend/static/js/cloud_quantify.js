// Cloud Quantify Logic - Clean Rewrite
const API_BASE = "/api/plugin/cloud";

// --- GLOBAL STATE ---
let SESSION_ID = "";
let REVIT_DATA = null;
let CURRENT_TAB = 'todo';
let CURRENT_SHEET_ID = 'sheet1';
let DETAIL_STATE = {
    cardId: null,
    rows: [], // Original rows
    displayRows: [], // Processed rows
    cols: [], // All available cols
    groupBy: [], // { field, header, footer }
    sort: [], // { field, asc }
    filters: [], // { field, op, val }
    columnFormats: {}, // { colName: 'text'|'number'|'currency'|'percent' }
    itemize: true,
    activeSidebarTab: 'fields'
};

const DEFAULT_GROUPS = [
    { id: 'g00', name: '00-Arquitectura', icon: 'fa-building', subgroups: [] },
    { id: 'g01', name: '01-Estructuras', icon: 'fa-cubes', subgroups: [] },
    { id: 'g02', name: '02-Sanitario', icon: 'fa-tint', subgroups: [] },
    { id: 'g03', name: '03-Pluvial', icon: 'fa-cloud-rain', subgroups: [] },
    { id: 'g04', name: '04-AguaPotable', icon: 'fa-faucet', subgroups: [] },
    { id: 'g05', name: '05-Electricidad', icon: 'fa-bolt', subgroups: [] },
    { id: 'g06', name: '06-Especiales', icon: 'fa-star', subgroups: [] }
];

let groups = JSON.parse(JSON.stringify(DEFAULT_GROUPS));
let selectedSubgroupId = null;
let activeCards = [];
let sheets = [
    { id: 'sheet1', name: '01_Arquitectura', sections: [], rows: [] },
    { id: 'sheet2', name: '02_Estructura', sections: [], rows: [] },
    { id: 'sheet3', name: '03_Movimiento_Tierras', sections: [], rows: [] },
    { id: 'sheet4', name: '04_Electrico', sections: [], rows: [] },
    { id: 'sheet5', name: '05_Hidrosanitario', sections: [], rows: [] },
    { id: 'sheet90', name: '90_Resumen', sections: [], rows: [] },
    { id: 'sheet99', name: '99_Control', sections: [], rows: [] }
    // Rows initialized later
];

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    // Inject Modal Template
    if (!document.getElementById('create-card-modal')) {
        document.body.insertAdjacentHTML('beforeend', CARD_MODAL_TEMPLATE);
    }

    // Get Session
    const params = new URLSearchParams(window.location.search);
    SESSION_ID = params.get('session_id');

    if (SESSION_ID) {
        await loadSessionData();
    } else {
        updateStatus("Desconectado", "red");
    }

    // Init UI
    renderGroups();
    // renderSheetsList(); // If function exists
    // loadSheet(CURRENT_SHEET_ID);
    // switchTab('todo');
    // Ensure tabs work (assuming global handlers or inline onclicks exist in HTML)
});

async function loadSessionData() {
    updateStatus("Conectando...", "emerald");
    try {
        const res = await fetch(`${API_BASE}/session/${SESSION_ID}`);
        if (!res.ok) throw new Error("Server Error");

        const payload = await res.json();

        // 1. Revit Data
        if (payload.data) REVIT_DATA = payload.data;

        // 2. Saved Data
        if (payload.savedData) {
            activeCards = payload.savedData.cards || [];
            if (payload.savedData.groups && payload.savedData.groups.length > 0) {
                groups = payload.savedData.groups;
            }
            if (payload.savedData.sheets && payload.savedData.sheets.length > 0) {
                sheets = payload.savedData.sheets;
            }
        }

        // 3. Project Name
        if (payload.project_name && document.getElementById('project-name-input')) {
            document.getElementById('project-name-input').value = payload.project_name;
        }

        updateStatus("Conectado", "emerald");
    } catch (e) {
        console.error(e);
        updateStatus("Offline", "red");
    }

    // Initial Render
    renderTodo();
    renderGroups();
    renderKanbanBoard();
    switchTab('compilation'); // Default view for testing
}

// 4. Tab Logic
function switchTab(tabId) {
    CURRENT_TAB = tabId;

    // 1. Update Buttons
    ['todo', 'groups', 'compilation'].forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (!btn) return;

        if (t === tabId) {
            btn.classList.remove('text-slate-400', 'bg-transparent');
            btn.classList.add('text-white', 'bg-indigo-600', 'shadow-lg');
        } else {
            btn.classList.remove('text-white', 'bg-indigo-600', 'shadow-lg');
            btn.classList.add('text-slate-400', 'bg-transparent');
        }
    });

    // 2. Update Views
    ['view-todo', 'view-groups', 'view-compilation'].forEach(v => {
        const el = document.getElementById(v);
        if (el) el.classList.add('hidden');
    });

    const activeView = document.getElementById(`view-${tabId}`);
    if (activeView) {
        activeView.classList.remove('hidden');
        if (tabId === 'compilation') {
            activeView.classList.add('flex'); // Ensure flex display for sidebar layout
        } else {
            activeView.classList.remove('flex');
        }
    }

    // 3. Tab Specific Logic
    if (tabId === 'todo') {
        renderTodo(document.getElementById('search-input')?.value || "");
    } else if (tabId === 'groups') {
        renderKanbanBoard();
    } else if (tabId === 'compilation') {
        setupCompilationView();
    }
}


// EXPORT
// EXPORT - Legacy function removed. 
// New exportToExcel implementation is located in the AUTOMATIC COMPILATION section.
// EXPORT - Legacy function removed. 
// New exportToExcel implementation is located in the AUTOMATIC COMPILATION section.

function updateStatus(text, color) {
    const el = document.getElementById('connection-status');
    if (el) {
        el.innerText = text;
        el.parentElement.className = `flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-slate-700 text-${color}-400`;
    }
}

// --- GROUPS LOGIC ---
function renderGroups() {
    const container = document.getElementById('groups-list');
    if (!container) return;

    container.innerHTML = groups.map(g => `
        <div class="mb-2">
            <div class="group-item p-3 rounded-lg hover:bg-slate-800 cursor-pointer transition-colors flex items-center justify-between text-slate-300 hover:text-white" 
                 onclick="toggleGroupAccordion('${g.id}')">
                <div class="flex items-center gap-3">
                    <i class="fas ${g.icon} text-slate-500 w-5 text-center"></i>
                    <span class="font-bold text-sm tracking-wide">${g.name}</span>
                </div>
                <div class="flex items-center gap-2">
                     <span class="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-500">${g.subgroups.length}</span>
                     <button onclick="createNewSubgroup(event, '${g.id}')" class="text-slate-600 hover:text-emerald-400 p-1"><i class="fas fa-plus"></i></button>
                </div>
            </div>
            
            <div id="subgroups-${g.id}" class="ml-4 border-l border-slate-800 pl-2 mt-1 space-y-1 ${g.open ? '' : 'hidden'}">
                ${g.subgroups.map(sg => `
                    <div class="p-2 rounded hover:bg-slate-800/50 cursor-pointer text-xs flex items-center justify-between ${selectedSubgroupId === sg.id ? 'bg-indigo-900/30 text-indigo-300 border-l-2 border-indigo-500' : 'text-slate-400'}"
                         onclick="selectSubgroup('${sg.id}')">
                        <span>${sg.name}</span>
                        <div class="flex gap-1">
                             <span class="text-[9px] bg-slate-800 px-1 rounded">${activeCards.filter(c => c.subgroupId === sg.id).length}</span>
                             <button onclick="deleteSubgroup(event, '${g.id}', '${sg.id}')" class="text-red-900 hover:text-red-400 p-0.5"><i class="fas fa-times"></i></button>
                        </div>
                    </div>
                `).join('')}
                ${g.subgroups.length === 0 ? '<div class="p-2 text-[10px] text-slate-600 italic pl-4">Sin subgrupos</div>' : ''}
            </div>
        </div>
    `).join('');
}

function toggleGroupAccordion(groupId) {
    const g = groups.find(x => x.id === groupId);
    if (g) {
        g.open = !g.open;
        renderGroups();
    }
}

function createNewSubgroup(e, groupId) {
    e.stopPropagation();
    const name = prompt("Nombre del Subgrupo:");
    if (!name) return;
    const g = groups.find(x => x.id === groupId);
    g.subgroups.push({ id: `sg${Date.now()}`, name: name });
    g.open = true;
    renderGroups();
}

function deleteSubgroup(e, groupId, subgroupId) {
    e.stopPropagation();
    if (!confirm("¿Eliminar Subgrupo?")) return;
    const g = groups.find(x => x.id === groupId);
    g.subgroups = g.subgroups.filter(sg => sg.id !== subgroupId);
    if (selectedSubgroupId === subgroupId) {
        selectedSubgroupId = null;
        renderKanbanBoard();
    }
    renderGroups();
}

function selectSubgroup(subgroupId) {
    selectedSubgroupId = subgroupId;
    renderGroups();
    renderKanbanBoard();
}

// --- KANBAN LOGIC ---
function renderKanbanBoard() {
    const container = document.getElementById('cards-grid');
    if (!container) return;

    if (!selectedSubgroupId) {
        container.innerHTML = `<div class="flex-1 flex flex-col items-center justify-center text-slate-500 opacity-50"><i class="fas fa-layer-group text-6xl mb-4"></i><h3 class="text-xl">Selecciona un Subgrupo</h3></div>`;
        return;
    }

    const cards = activeCards.filter(c => c.subgroupId === selectedSubgroupId);
    const processCards = cards.filter(c => c.status !== 'done');
    const doneCards = cards.filter(c => c.status === 'done');

    container.innerHTML = `
        <!-- EN PROCESO -->
        <div class="flex-1 flex flex-col min-w-[300px] bg-[#0f111a] rounded-xl border border-dashed border-slate-800">
            <div class="p-4 border-b border-slate-800 flex justify-between items-center">
                <span class="font-bold text-slate-300">EN PROCESO</span>
                <span class="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded">${processCards.length}</span>
            </div>
            <div class="flex-1 overflow-y-auto p-3 space-y-3" ondrop="dropCard(event, 'process')" ondragover="allowDrop(event)">
                ${processCards.map(c => renderKanbanCard(c)).join('')}
            </div>
        </div>

        <!-- LISTAS -->
        <div class="flex-1 flex flex-col min-w-[300px] bg-[#0f111a] rounded-xl border border-dashed border-slate-800">
            <div class="p-4 border-b border-slate-800 flex justify-between items-center">
                <span class="font-bold text-slate-300">LISTAS</span>
                <span class="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded">${doneCards.length}</span>
            </div>
            <div class="flex-1 overflow-y-auto p-3 space-y-3" ondrop="dropCard(event, 'done')" ondragover="allowDrop(event)">
                ${doneCards.map(c => renderKanbanCard(c)).join('')}
            </div>
        </div>
    `;
}

// Helper to process rows (Formula + Filter) for Summary Calculation
function getProcessedRowsForCard(c) {
    if (!c.rows || c.rows.length === 0) return [];

    // Quick clone to avoid mutations on original data during calculation
    // Limitations: Deep clone is expensive. Shallow clone of rows array, but objects are shared.
    // If we modify objects (add formula cols), we mutate original.
    // BETTER: JSON parse/stringify for safety in this "view" logic.
    let data = JSON.parse(JSON.stringify(c.rows));

    // 0. Formulas
    const formulas = c.formulas || {};
    const formulaKeys = Object.keys(formulas);
    if (formulaKeys.length > 0) {
        data.forEach(row => {
            formulaKeys.forEach(resCol => {
                let eq = formulas[resCol];
                eq = eq.replace(/(\d+(?:\.\d+)?)\s*%/g, '($1/100)');
                const matches = eq.match(/\[(.*?)\]/g);
                if (matches) {
                    matches.forEach(m => {
                        const colName = m.replace('[', '').replace(']', '').trim();
                        let rawVal = row[colName];
                        let val = 0;
                        if (typeof rawVal === 'number') val = rawVal;
                        else if (typeof rawVal === 'string') val = parseFloat(rawVal.replace(/[^0-9.-]/g, '')) || 0;
                        eq = eq.replace(m, val);
                    });
                }
                try {
                    if (/^[0-9+\-*/().\sEe]*$/.test(eq)) {
                        let res = eval(eq);
                        if (!isFinite(res) || isNaN(res)) res = 0;
                        row[resCol] = res;
                    } else {
                        row[resCol] = 0;
                    }
                } catch (e) {
                    row[resCol] = 0; // Silent fail for summary
                }
            });
        });
    }

    // 1. Filters
    const filters = c.filters || [];
    if (filters.length > 0) {
        data = data.filter(row => {
            return filters.every(f => {
                // Ensure field exists
                const val = (row[f.field] || '').toString().toLowerCase();
                const filterVal = f.val.toLowerCase();

                if (f.op === 'contains') return val.includes(filterVal);
                if (f.op === 'equals') return val === filterVal;
                if (f.op === 'startswith') return val.startsWith(filterVal);

                const numVal = parseFloat(val);
                const numFilter = parseFloat(filterVal);
                if (!isNaN(numVal) && !isNaN(numFilter)) {
                    if (f.op === 'gt') return numVal > numFilter;
                    if (f.op === 'lt') return numVal < numFilter;
                }
                return true;
            });
        });
    }

    return data;
}

// Helper to calculate output summary
function getCardOutputSummary(c) {
    if (!c.outputCols || c.outputCols.length === 0) return '';

    // Use Processed Rows (Filtered & Formulas) for total
    const rows = getProcessedRowsForCard(c);

    // Sum numeric output columns
    const summary = c.outputCols.map(col => {
        let total = 0;
        let count = 0;

        rows.forEach(r => {
            const val = parseFloat(r[col]);
            if (!isNaN(val)) total += val;
            else if (r[col]) count++;
        });

        // Format based on column format
        const fmt = (c.columnFormats || {})[col];
        let displayTotal = '';

        if (fmt === 'currency') displayTotal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(total);
        else if (fmt === 'percent') displayTotal = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 2 }).format(total); // Logic might differ for sum of percents, but summing them for now
        else if (fmt === 'weight') displayTotal = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(total) + ' kg';
        else if (fmt === 'number') displayTotal = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(total);
        else displayTotal = count > 0 ? `${count} items` : '-';

        return `<div class="text-[10px] text-slate-400 flex justify-between"><span>${col}</span> <span class="text-white font-mono">${displayTotal}</span></div>`;
    }).join('');

    return `<div class="mt-3 pt-2 border-t border-slate-700/50 space-y-1">${summary}</div>`;
}

function renderKanbanCard(c) {
    // State Classes
    const isLocked = c.isLocked;
    const hasChanges = c.hasChanges; // Yellow warning

    let borderClass = "border-slate-700 hover:border-indigo-500";
    let bgClass = "bg-[#1e2230]";

    if (hasChanges) {
        borderClass = "border-yellow-500 shadow-[0_0_15px_-3px_rgba(234,179,8,0.3)]";
        bgClass = "bg-[#1e2230]"; // Keeping dark bg, but border highlights
    }

    // Output Summary
    const outputSummary = getCardOutputSummary(c);

    return `
        <div draggable="${!isLocked}" ondragstart="dragCardStart(event, '${c.id}')" onclick="openCardDetails('${c.id}')"
             class="${bgClass} p-4 rounded-lg border ${borderClass} shadow-lg cursor-pointer group/card relative transition-all">
            
            <!-- Top Right Actions (Sync, Hold, Duplicate, Delete) -->
            <div class="absolute top-2 right-2 flex gap-1 opacity-0 group-hover/card:opacity-100 transition-opacity z-10">
                <button onclick="syncCardData(event, '${c.id}')" class="w-6 h-6 flex items-center justify-center rounded bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700" title="Sincronizar Tabla"><i class="fas fa-sync-alt text-[10px]"></i></button>
                <button onclick="toggleCardLock(event, '${c.id}')" class="w-6 h-6 flex items-center justify-center rounded ${isLocked ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'}" title="${isLocked ? 'Desbloquear' : 'Congelar Data (Hold)'}"><i class="fas ${isLocked ? 'fa-lock' : 'fa-lock-open'} text-[10px]"></i></button>
                <button onclick="openDuplicateCardModal(event, '${c.id}')" class="w-6 h-6 flex items-center justify-center rounded bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700" title="Duplicar Tarjeta"><i class="fas fa-copy text-[10px]"></i></button>
                <button onclick="deleteCard('${c.id}', event)" class="w-6 h-6 flex items-center justify-center rounded bg-slate-800 text-red-400 hover:text-red-300 hover:bg-slate-700" title="Eliminar"><i class="fas fa-trash text-[10px]"></i></button>
            </div>

            <!-- Header -->
            <div class="flex justify-between items-start mb-2">
                <span class="text-[10px] uppercase font-bold text-slate-500">${c.source || 'ITEM'}</span>
                 ${hasChanges ? '<i class="fas fa-exclamation-triangle text-yellow-500 text-xs animate-pulse" title="Cambios detectados en el modelo"></i>' : ''}
            </div>
            
            <h4 class="font-bold text-white mb-2 pr-6">${c.name}</h4>
            
            <!-- Metadata -->
            <div class="flex gap-2 items-center">
               <span class="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-mono">${c.rows ? c.rows.length : 0} Rows</span>
               <span class="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-mono">${c.selectedParams ? c.selectedParams.length : 0} Cols</span>
            </div>

            <!-- Output Summary -->
            ${outputSummary}
        </div>
    `;
}

// --- DRAG DROP ---
function allowDrop(ev) { ev.preventDefault(); }
function dragCardStart(ev, id) { ev.dataTransfer.setData("text", id); }
function dropCard(ev, status) {
    ev.preventDefault();
    const id = ev.dataTransfer.getData("text");
    const card = activeCards.find(c => c.id === id);
    if (card) {
        card.status = status;
        renderKanbanBoard();
        saveProject(); // Just stub
    }
}
function deleteCard(id, e) {
    e.stopPropagation();
    if (confirm("Confirmar borrado")) {
        activeCards = activeCards.filter(c => c.id !== id);
        renderKanbanBoard();
    }
}

function saveProject() {
    // Basic Stub for saving
    const payload = {
        session_id: SESSION_ID,
        project_name: document.getElementById('project-name-input')?.value || "Sin Nombre",
        cards: activeCards,
        groups: groups,
        sheets: sheets
    };
    fetch(`${API_BASE}/save-project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(r => {
        if (r.ok) showToast("Proyecto Guardado");
        else console.error("Error saving");
    });
}

// --- MODAL LOGIC (FIXED) ---
function openCardModal(categoryName, count) {
    const modal = document.getElementById('create-card-modal');
    if (!modal) return;

    document.getElementById('modal-category-name').innerText = categoryName || "General";
    document.getElementById('modal-element-count').innerText = count || 0;

    // Groups Selector
    const sel = document.getElementById('card-group-select');
    if (sel) {
        sel.innerHTML = groups.map(g => {
            if (g.subgroups.length === 0) return '';
            return `<optgroup label="${g.name}">
                ${g.subgroups.map(sg => `<option value="${sg.id}" ${selectedSubgroupId === sg.id ? 'selected' : ''}>${sg.name}</option>`).join('')}
            </optgroup>`;
        }).join('');
    }

    // Parameters Injection
    // Parameters Injection
    const builtinContainer = document.getElementById('modal-params-builtin');
    const sharedContainer = document.getElementById('modal-params-shared');

    if (builtinContainer && sharedContainer) {
        builtinContainer.innerHTML = '<p class="text-slate-500 text-xs italic">Cargando...</p>';
        sharedContainer.innerHTML = '<p class="text-slate-500 text-xs italic">Cargando...</p>';

        let params = [];
        let categoryData = null;
        if (REVIT_DATA && REVIT_DATA.categories && Array.isArray(REVIT_DATA.categories)) {
            categoryData = REVIT_DATA.categories.find(c => c.name === categoryName);
        } else if (REVIT_DATA && REVIT_DATA[categoryName]) {
            categoryData = { rows: REVIT_DATA[categoryName] };
        }

        if (categoryData && categoryData.rows && categoryData.rows.length > 0) {
            params = Object.keys(categoryData.rows[0]);
        }

        if (params.length > 0) {
            // Heuristic Separation
            const builtIns = ["id", "name", "category", "family", "type", "family and type", "type id", "element id", "design option", "workset", "material", "level", "top level", "base level", "area", "volume", "length", "width", "height", "comments", "mark", "image", "count", "type name", "family name", "ifc predefined type", "export to ifc as", "export to ifc", "structural", "enable analytical model", "related to mass", "phase created", "phase demolished"];

            const bParams = params.filter(p => builtIns.includes(p.toLowerCase()));
            const sParams = params.filter(p => !builtIns.includes(p.toLowerCase()));

            const renderCheckboxes = (list) => list.map(p => `
                <label class="flex items-center gap-2 p-2 rounded hover:bg-slate-800 cursor-pointer">
                    <input type="checkbox" value="${p}" class="modal-param-checkbox accent-indigo-500 w-4 h-4" checked>
                    <span class="text-slate-300 text-xs truncate" title="${p}">${p}</span>
                </label>
            `).join('');

            builtinContainer.innerHTML = bParams.length ? renderCheckboxes(bParams) : '<p class="text-slate-500 text-xs italic">Ninguno</p>';
            sharedContainer.innerHTML = sParams.length ? renderCheckboxes(sParams) : '<p class="text-slate-500 text-xs italic">Ninguno</p>';
        } else {
            builtinContainer.innerHTML = '<p class="text-slate-500 text-xs italic">No info</p>';
            sharedContainer.innerHTML = '<p class="text-slate-500 text-xs italic">No info</p>';
        }
    }

    modal.classList.remove('hidden');
}

function createCardFromModal(e) {
    if (e) e.stopPropagation();
    console.log("createCardFromModal called");
    const nameEl = document.getElementById('card-name-input');
    const name = nameEl ? nameEl.value.trim() : "";
    console.log("Card Name Value:", name);
    const sgId = document.getElementById('card-group-select').value; // Subgroup ID
    const catNameEl = document.getElementById('modal-category-name');
    const catName = catNameEl ? catNameEl.innerText : "General";

    if (!name) {
        alert("Por favor ingrese un nombre para la tarjeta.");
        return;
    }

    // Get selected parameters
    const checkboxes = document.querySelectorAll('.modal-param-checkbox:checked');
    const selectedParams = Array.from(checkboxes).map(cb => cb.value);

    const newCard = {
        id: "c" + Date.now(),
        name: name,
        status: 'process',
        source: catName === "General" ? "MANUAL" : catName,
        subgroupId: sgId,
        selectedParams: selectedParams // Save user selection
    };

    console.log("Pushing new card:", newCard);
    activeCards.push(newCard);

    document.getElementById('create-card-modal').classList.add('hidden');

    // Feedback
    showToast("Tarjeta creada con éxito");
    saveProject();

    // Optional: Auto-switch to see it? Maybe not yet, let user decide.
    if (selectedSubgroupId === sgId) {
        renderKanbanBoard();
    }
}

// --- TEMPLATES ---
const CARD_MODAL_TEMPLATE = `
<div id="create-card-modal" class="fixed inset-0 bg-black/90 backdrop-blur-sm z-[80] flex items-center justify-center hidden animate-fade-in p-4">
    <div class="bg-[#1e2230] rounded-2xl border border-slate-700 shadow-2xl w-full max-w-6xl flex flex-col max-h-[90vh]">
        <!-- Header -->
        <div class="p-6 border-b border-slate-700 flex justify-between items-center bg-[#13151f] rounded-t-2xl">
            <div>
                 <h3 class="text-2xl font-bold text-white mb-1">Crear Tarjeta</h3>
                 <div class="inline-flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-slate-700">
                    <span class="text-slate-400 text-sm" id="modal-category-name">Categoría</span>
                    <span class="bg-indigo-500 text-white text-xs font-bold px-2 py-0.5 rounded-full" id="modal-element-count">0</span>
                </div>
            </div>
            <button onclick="document.getElementById('create-card-modal').classList.add('hidden')" class="text-slate-400 hover:text-white"><i class="fas fa-times text-xl"></i></button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-6 custom-scrollbar">
            <!-- Top Section: General Info -->
            <div class="grid grid-cols-2 gap-8 mb-8">
                <div>
                     <label class="block text-slate-400 text-sm mb-2 font-medium">Nombre de la Tarjeta</label>
                     <input type="text" id="card-name-input" class="w-full bg-[#0b0c12] border border-slate-700 rounded-lg px-4 py-3 text-white focus:border-indigo-500 outline-none" placeholder="Ej. Muros Interiores Nivel 2">
                </div>
                <div>
                     <label class="block text-slate-400 text-sm mb-2 font-medium">Asignar a Subgrupo (Kanban)</label>
                     <select id="card-group-select" class="w-full bg-[#0b0c12] border border-slate-700 rounded-lg px-4 py-3 text-white focus:border-indigo-500 outline-none"></select>
                </div>
            </div>

            <!-- Bottom Section: Parameters -->
             <div class="flex justify-between items-end mb-4 border-b border-slate-700 pb-2">
                <h4 class="text-lg font-bold text-indigo-400"><i class="fas fa-list-check mr-2"></i>Selección de Parámetros</h4>
                <div class="flex gap-2">
                    <button onclick="toggleModalParams(true)" class="text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-3 py-1.5 rounded border border-indigo-500/30">Seleccionar Todo</button>
                    <button onclick="toggleModalParams(false)" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 px-3 py-1.5 rounded border border-slate-700">Deseleccionar</button>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-8 h-[400px]">
                <!-- Column 1: Built-in Parameters -->
                <div class="flex flex-col h-full bg-[#13151f] rounded-xl border border-slate-800 overflow-hidden">
                    <div class="p-3 bg-slate-800/50 border-b border-slate-800 font-bold text-slate-300 text-sm flex justify-center">
                        <i class="fas fa-cube mr-2"></i>Parámetros Revit (Nativos)
                    </div>
                    <div id="modal-params-builtin" class="flex-1 overflow-y-auto p-3 grid grid-cols-2 gap-1 content-start custom-scrollbar">
                         <!-- Injected -->
                    </div>
                </div>

                <!-- Column 2: Shared/Other Parameters -->
                <div class="flex flex-col h-full bg-[#13151f] rounded-xl border border-slate-800 overflow-hidden">
                     <div class="p-3 bg-slate-800/50 border-b border-slate-800 font-bold text-slate-300 text-sm flex justify-center">
                        <i class="fas fa-project-diagram mr-2"></i>Otros / Compartidos
                    </div>
                    <div id="modal-params-shared" class="flex-1 overflow-y-auto p-3 grid grid-cols-2 gap-1 content-start custom-scrollbar">
                         <!-- Injected -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="p-6 border-t border-slate-700 bg-[#13151f] flex justify-end gap-3 rounded-b-2xl">
            <button onclick="document.getElementById('create-card-modal').classList.add('hidden')" class="px-6 py-2.5 text-slate-400 font-bold hover:text-white hover:bg-slate-800 rounded-lg transition-all">Cancelar</button>
            <button onclick="createCardFromModal(event)" class="px-8 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg shadow-lg shadow-indigo-900/40 transition-all transform hover:scale-105">Crear Tarjeta</button>
        </div>
    </div>
</div>
`;

function toggleModalParams(check) {
    document.querySelectorAll('.modal-param-checkbox').forEach(cb => cb.checked = check);
}

const DETAIL_MODAL_TEMPLATE = `
<div id="card-detail-modal" class="fixed inset-0 bg-black/95 z-[90] hidden flex flex-col animate-fade-in text-white">
    <!-- Header -->
    <div class="h-14 border-b border-slate-700 bg-[#0f111a] flex items-center justify-between px-6 shadow-lg">
        <div class="flex items-center gap-4">
             <button onclick="document.getElementById('card-detail-modal').classList.add('hidden')" class="text-slate-400 hover:text-white transition-colors"><i class="fas fa-arrow-left"></i></button>
             <input type="text" id="detail-card-title" class="bg-transparent border border-transparent hover:border-slate-700 focus:border-indigo-500 rounded px-2 py-1 text-lg font-bold text-white outline-none transition-colors w-96 placeholder-slate-600" placeholder="Nombre de la Tarjeta">
             <span class="bg-indigo-500/20 text-indigo-300 px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider" id="detail-card-source">SOURCE</span>
        </div>
        <div>
            <button id="btn-ack-changes" onclick="acknowledgeCardChanges()" class="hidden mr-2 bg-yellow-600 hover:bg-yellow-500 text-white px-4 py-1.5 rounded text-xs font-bold shadow-lg shadow-yellow-500/20 animate-pulse">Aprobar Cambios</button>
            <button onclick="saveCardDetails()" class="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded text-xs font-bold shadow-lg shadow-indigo-500/20">Guardar Cambios</button>
        </div>
    </div>

    <!-- Content Split -->
    <div class="flex-1 flex overflow-hidden">
        <!-- LEFT: Data Table -->
        <div class="flex-1 bg-[#13151f] flex flex-col relative border-r border-slate-700">
             <div class="flex-1 overflow-auto custom-scrollbar" id="detail-table-container">
                <table class="w-full text-left text-xs whitespace-nowrap">
                    <thead class="bg-slate-800 text-slate-300 font-bold uppercase sticky top-0 z-10" id="detail-table-head"></thead>
                    <tbody class="divide-y divide-slate-700/50 text-slate-400" id="detail-table-body"></tbody>
                </table>
             </div>
             <!-- Status Bar -->
             <div class="h-8 bg-[#0f111a] border-t border-slate-700 flex items-center px-4 text-[10px] text-slate-500 justify-between">
                <span id="detail-row-count">0 Elementos</span>
                <span>Cloud Quantify v2.0</span>
             </div>
        </div>

        <!-- RIGHT: Controls Sidebar -->
        <div class="w-96 bg-[#0f111a] flex flex-col border-l border-slate-800">
            <!-- Sidebar Tabs -->
            <div class="flex border-b border-slate-800">
                <button onclick="switchSidebarTab('fields')" id="stab-fields" class="flex-1 py-3 text-center text-[10px] font-bold text-indigo-400 border-b-2 border-indigo-500 bg-slate-800/30">CAMPOS</button>
                <button onclick="switchSidebarTab('filter')" id="stab-filter" class="flex-1 py-3 text-center text-[10px] font-bold text-slate-500 hover:text-slate-300 hover:bg-slate-800/30">FILTROS</button>
                <button onclick="switchSidebarTab('sort')" id="stab-sort" class="flex-1 py-3 text-center text-[10px] font-bold text-slate-500 hover:text-slate-300 hover:bg-slate-800/30">CLASIF.</button>
                <button onclick="switchSidebarTab('format')" id="stab-format" class="flex-1 py-3 text-center text-[10px] font-bold text-slate-500 hover:text-slate-300 hover:bg-slate-800/30">FORMATO</button>
                <button onclick="switchSidebarTab('desc')" id="stab-desc" class="flex-1 py-3 text-center text-[10px] font-bold text-slate-500 hover:text-slate-300 hover:bg-slate-800/30">DESCR.</button>
            </div>

            <!-- Sidebar Content -->
            <div class="flex-1 overflow-y-auto p-4 custom-scrollbar relative">
                
                <!-- VIEW: FIELDS -->
                <div id="sview-fields" class="space-y-4">
                    <p class="text-xs text-slate-400 mb-2">Selecciona columnas visibles y su orden.</p>
                    <div id="fields-list" class="space-y-1"></div>
                    <button onclick="openAddColumnModal()" class="w-full mt-4 py-2 border border-dashed border-slate-600 text-slate-400 text-xs rounded hover:border-indigo-500 hover:text-indigo-400">
                        <i class="fas fa-plus mr-2"></i>Agregar Columna
                    </button>
                </div>

                <!-- VIEW: FILTERS -->
                <div id="sview-filter" class="hidden space-y-4">
                     <p class="text-xs text-slate-400 mb-2">Filtra los elementos por valor.</p>
                     <div id="filters-list" class="space-y-2"></div>
                     <button onclick="addFilter()" class="w-full py-1.5 bg-slate-800 text-indigo-400 text-xs rounded hover:bg-slate-700">Agregar Filtro</button>
                </div>

                <!-- VIEW: SORTING/GROUPING -->
                <div id="sview-sort" class="hidden space-y-4">
                    <div class="space-y-2">
                        <label class="text-xs text-slate-400 block font-bold">Ordenar por</label>
                        <select id="sort-by-select" class="w-full bg-[#13151f] border border-slate-700 text-slate-300 text-xs p-2 rounded" onchange="updateSort()"></select>
                         <label class="flex items-center gap-2 text-xs text-slate-400">
                             <input type="checkbox" id="sort-asc-check" class="accent-indigo-500" checked onchange="updateSort()"> Ascendente
                         </label>
                    </div>
                     <hr class="border-slate-800">
                     <label class="flex items-center gap-2 p-3 bg-slate-800/20 rounded border border-slate-700/50">
                        <input type="checkbox" id="itemize-check" class="accent-indigo-500 w-4 h-4" checked onchange="toggleItemize()">
                        <span class="text-xs text-slate-300 font-bold">Detallar cada ejemplar</span>
                     </label>
                     <p class="text-[10px] text-slate-500 leading-tight">Si se desmarca, agrupa filas idénticas y suma valores numéricos.</p>
                </div>

                <!-- VIEW: FORMAT -->
                <div id="sview-format" class="hidden space-y-4">
                    <p class="text-xs text-slate-400 mb-2">Formato de datos por columna.</p>
                    <div id="format-list" class="space-y-2"></div>
                </div>

                <!-- VIEW: DESCRIPTIONS -->
                <div id="sview-desc" class="hidden space-y-4">
                    <p class="text-xs text-slate-400 mb-2">Información descriptiva de la tarjeta.</p>
                    <div id="desc-list" class="space-y-3"></div>
                    <button onclick="addDescription()" class="w-full py-2 bg-slate-800 text-indigo-400 text-xs rounded hover:bg-slate-700 font-bold border border-slate-700 border-dashed">
                        <i class="fas fa-plus mr-2"></i>Agregar Descripción
                    </button>

                    <hr class="border-slate-800 my-4">

                    <!-- NEW INPUTS -->
                    <div class="space-y-4">
                        <div>
                            <label class="block text-xs uppercase text-indigo-400 font-bold mb-1">Codigo Spectrum</label>
                            <input type="text" id="detail-code-input" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-xs text-white focus:border-indigo-500 outline-none" placeholder="Ingresar código...">
                        </div>
                        <div>
                            <label class="block text-xs uppercase text-indigo-400 font-bold mb-1">Unidad de Medida</label>
                            <select id="detail-unit-select" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-xs text-white focus:border-indigo-500 outline-none">
                                <option value="">Seleccionar Unidad</option>
                                <option value="m2">m2</option>
                                <option value="m3">m3</option>
                                <option value="ml">ml</option>
                                <option value="count">count</option>
                                <option value="kg">kg (Peso)</option>
                                <option value="ton">ton</option>
                                <option value="moneda">Moneda ($)</option>
                                <option value="und">Unidad (Global)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs uppercase text-indigo-400 font-bold mb-1">Sheet Vinculada</label>
                            <select id="detail-sheet-select" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-xs text-white focus:border-indigo-500 outline-none">
                                <option value="">Sin vinculación</option>
                                <!-- Populated by JS -->
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
`;

function openCardDetails(cardId) {
    if (!document.getElementById('card-detail-modal')) {
        document.body.insertAdjacentHTML('beforeend', DETAIL_MODAL_TEMPLATE);
    }
    const modal = document.getElementById('card-detail-modal');
    modal.classList.remove('hidden');

    const card = activeCards.find(c => c.id === cardId);
    if (!card) return;

    // Locked/Unlocked Changes Logic (Moved after card definition)
    const ackBtn = document.getElementById('btn-ack-changes');
    if (ackBtn) {
        if (card.hasChanges) {
            if (card.isLocked) {
                // Locked: Show Approve Button
                ackBtn.classList.remove('hidden');
            } else {
                // Unlocked: Auto-clear changes on open
                card.hasChanges = false;
                ackBtn.classList.add('hidden');
                renderKanbanBoard();
                saveProject();
            }
        } else {
            ackBtn.classList.add('hidden');
        }
    }

    // Load Data
    let originalRows = [];
    if (REVIT_DATA && REVIT_DATA.categories) {
        const cat = REVIT_DATA.categories.find(c => c.name === card.source);
        if (cat) {
            // Deep copy
            let rawRows = JSON.parse(JSON.stringify(cat.rows));
            // Normalize Data (Remove units/prefixes)
            originalRows = normalizeRevitData(rawRows);
        }
    }

    // Init Logic State
    DETAIL_STATE = {
        cardId: cardId,
        rows: originalRows,
        originalCols: originalRows.length > 0 ? Object.keys(originalRows[0]) : [], // Store original Revit columns
        cols: originalRows.length > 0 ? Object.keys(originalRows[0]) : [],
        visibleCols: card.selectedParams || (originalRows.length > 0 ? Object.keys(originalRows[0]).slice(0, 5) : []),
        filters: card.filters || [],
        sort: card.sort || [],
        itemize: card.itemize !== undefined ? card.itemize : true,
        columnFormats: card.columnFormats || {},
        formulas: card.formulas || {},
        outputCols: card.outputCols || [],
        descriptions: card.descriptions || [],
        hasChanges: card.hasChanges || false, // Pass state
        activeSidebarTab: 'fields'
    };

    // Ensure 'Count' field exists
    if (!DETAIL_STATE.cols.includes('Count')) {
        DETAIL_STATE.cols.push('Count');
    }
    // Populate 'Count' in rows if missing
    if (DETAIL_STATE.rows) {
        DETAIL_STATE.rows.forEach(r => {
            if (r.Count === undefined) r.Count = 1;
        });
    }

    // UI Updates
    document.getElementById('detail-card-title').value = card.name;
    document.getElementById('detail-card-source').innerText = card.source;

    // Restore UI State from saved data
    const itemizeCheck = document.getElementById('itemize-check');
    if (itemizeCheck) itemizeCheck.checked = DETAIL_STATE.itemize;

    const sortAscCheck = document.getElementById('sort-asc-check');
    if (sortAscCheck && DETAIL_STATE.sort.length > 0) sortAscCheck.checked = DETAIL_STATE.sort[0].asc;

    // --- NEW FIELDS POPULATION ---

    // 1. Sheets (Only from Revit)
    // Fix: REVIT_DATA contains 'sheets' (Compilation Sheets, Objects) and 'data.sheets' (Revit Sheets, Strings)
    // We must access the strings inside REVIT_DATA.data.sheets
    let availableSheets = [];
    if (REVIT_DATA.data && Array.isArray(REVIT_DATA.data.sheets)) {
        availableSheets = REVIT_DATA.data.sheets;
    } else if (Array.isArray(REVIT_DATA.sheets) && typeof REVIT_DATA.sheets[0] === 'string') {
        // Fallback for flat structure if any
        availableSheets = REVIT_DATA.sheets;
    }

    // 2. Populate Sheet Select
    const sheetSelect = document.getElementById('detail-sheet-select');
    if (sheetSelect) {
        if (availableSheets.length === 0) {
            sheetSelect.innerHTML = '<option value="">(Sincronice para ver Sheets)</option>';
        } else {
            sheetSelect.innerHTML = '<option value="">Sin vinculación</option>' +
                availableSheets.map(s => `<option value="${s}">${s}</option>`).join('');
        }
        sheetSelect.value = card.linkedSheet || "";
    }

    // 3. Populate Code & Unit
    const codeInput = document.getElementById('detail-code-input');
    if (codeInput) codeInput.value = card.code || "";

    const unitSelect = document.getElementById('detail-unit-select');
    if (unitSelect) unitSelect.value = card.unit || "";

    renderDetailSidebar();
    processAndRenderTable();
}

function normalizeRevitData(rows) {
    if (!rows || rows.length === 0) return [];

    const cols = Object.keys(rows[0]);

    cols.forEach(col => {
        // Detect if this column is a "Candidate for Number"
        // We check a sample. If we strip non-numeric chars, do we get valid numbers?
        let numericCount = 0;
        let validCount = 0;

        // Check first 20 rows or all
        const limit = Math.min(rows.length, 20);
        for (let i = 0; i < limit; i++) {
            const val = rows[i][col];
            if (val === null || val === undefined) continue;
            validCount++;

            const str = val.toString();
            // standard numeric check (allowing for units like m2, $, etc)
            // We just strip everything except digits, dots, minus.
            // CAUTION: "Version 1.2" becomes 1.2. "Room 101" becomes 101.
            // We need to be careful not to corrupt Text columns.
            // Text columns usually have alpha chars.
            // If the string contains significant alpha chars (A-Z) distinct from common units (m, ft, in, kg), it's Text.

            // Simpler approach: Check against common unit patterns
            // Match Number followed by Unit OR Symbol followed by Number
            // ^\s*[$€£]?\s*[-]?\d*[.]?\d+\s*[%°mftin²³]*\s*$
            // That's too complex.

            // Let's assume if it contains digits and only specific allowed alphas (m, f, t, i, n, l, b, s, k, g, etc)
            // Better: if the cleaned version parses to a Number, and the original was NOT a simple number.

            const clean = str.replace(/[^0-9.-]/g, '');
            if (clean && !isNaN(parseFloat(clean))) {
                // It has numbers. Does it have letters?
                if (/[a-zA-Z]/.test(str)) {
                    // It has letters. Are they units?
                    // Quick list of likely units suffixes
                    if (/(m|ft|in|mm|cm|kg|lb|%|°|deg|yd)$/i.test(str.trim()) || /m[23²³]/i.test(str)) {
                        numericCount++;
                    }
                } else {
                    // Purely numeric or numeric symbols ($)
                    numericCount++;
                }
            }
        }

        // If high confidence, convert column
        if (validCount > 0 && (numericCount / validCount) > 0.8) {
            rows.forEach(r => {
                const v = r[col];
                if (typeof v === 'string') {
                    const clean = v.replace(/[^0-9.-]/g, '');
                    const num = parseFloat(clean);
                    if (!isNaN(num)) r[col] = num;
                }
            });
        }
    });

    return rows;
}

function saveCardDetails() {
    const card = activeCards.find(c => c.id === DETAIL_STATE.cardId);
    if (card) {
        // Update Name
        const newName = document.getElementById('detail-card-title').value;
        if (newName) card.name = newName;

        card.rows = DETAIL_STATE.rows; // Save Data Rows
        card.selectedParams = DETAIL_STATE.visibleCols;
        card.filters = DETAIL_STATE.filters;
        card.sort = DETAIL_STATE.sort;
        card.itemize = DETAIL_STATE.itemize;
        card.columnFormats = DETAIL_STATE.columnFormats;
        card.formulas = DETAIL_STATE.formulas;
        card.outputCols = DETAIL_STATE.outputCols || [];
        card.descriptions = DETAIL_STATE.descriptions;

        // Save New Fields
        const codeInput = document.getElementById('detail-code-input');
        if (codeInput) card.code = codeInput.value;

        const unitSelect = document.getElementById('detail-unit-select');
        if (unitSelect) card.unit = unitSelect.value;

        const sheetSelect = document.getElementById('detail-sheet-select');
        if (sheetSelect) card.linkedSheet = sheetSelect.value;

        // Logic for Locked Card Warning
        // If card is locked, saving details implies "approving" or "viewing" content? 
        // User said: "advertencias en tarjetas bloqueadas se quedan Fijas, hasta que yo apruebe la advertencia"
        // If I save the card, I should probably clear the warning if the user explicitly acknowledges it.
        // For now, let's clear hasChanges if saving, as that implies user interaction.
        // But user said "unlocked... se quitara solo con abrir".
        // Let's implement specific "Approve" logic in a separate function or button if needed.
        // For now, I will NOT clear hasChanges automatically on save for locked cards unless I add a specific UI text.
        // But wait, if I save value 0.00 -> 10.00, I want the summary to update.
        // Saving `rows` will update the summary in `renderKanbanBoard`.

        renderKanbanBoard();
        saveProject();
        showToast('Cambios guardados exitosamente', 'success');
    }
}

// Acknowledge Changes (for Locked Cards)
function acknowledgeCardChanges() {
    const card = activeCards.find(c => c.id === DETAIL_STATE.cardId);
    if (card) {
        card.hasChanges = false;
        document.getElementById('btn-ack-changes').classList.add('hidden');
        renderKanbanBoard();
        saveProject();
        showToast('Advertencia de cambios aprobada.');
    }
}

function addDescription() {
    DETAIL_STATE.descriptions.push({ id: Date.now(), text: '' });
    renderDetailSidebar();
}

function removeDescription(id) {
    DETAIL_STATE.descriptions = DETAIL_STATE.descriptions.filter(d => d.id !== id);
    renderDetailSidebar();
}

function updateDescriptionVal(id, val) {
    const desc = DETAIL_STATE.descriptions.find(d => d.id === id);
    if (desc) desc.text = val;
}

function deleteColumn(col) {
    if (confirm(`¿Estás seguro de eliminar la columna "${col}"?`)) {
        DETAIL_STATE.cols = DETAIL_STATE.cols.filter(c => c !== col);
        DETAIL_STATE.visibleCols = DETAIL_STATE.visibleCols.filter(c => c !== col);
        delete DETAIL_STATE.columnFormats[col];
        delete DETAIL_STATE.formulas[col];

        // Remove from rows (optional but cleaner)
        DETAIL_STATE.rows.forEach(r => delete r[col]);

        renderDetailSidebar();
        processAndRenderTable();
    }
}

// --- ADD COLUMN MODAL LOGIC ---
function openAddColumnModal(editColName = null) {
    // Remove existing to ensure fresh template (fix z-index issues)
    const existing = document.getElementById('add-column-modal');
    if (existing) existing.remove();

    document.body.insertAdjacentHTML('beforeend', ADD_COLUMN_MODAL_TEMPLATE);

    document.getElementById('add-column-modal').classList.remove('hidden');

    const nameInput = document.getElementById('new-col-name');
    const typeSelect = document.getElementById('new-col-type');
    const formatSelect = document.getElementById('new-col-format');
    const defaultInput = document.getElementById('new-col-default');
    const formulaInput = document.getElementById('new-col-formula');
    const modalTitle = document.querySelector('#add-column-modal h2');
    const createBtn = document.querySelector('#add-column-modal button:last-child');
    const fieldsContainer = document.getElementById('formula-fields-list');

    // Populate Fields List for Formula Builder
    if (fieldsContainer) {
        // Only show visible columns, and exclude self if editing
        const availableCols = DETAIL_STATE.visibleCols.filter(c => c !== editColName);

        fieldsContainer.innerHTML = availableCols.map(c =>
            `<button onclick="insertFormulaToken('[${c}]')" 
                     class="px-2 py-1 bg-indigo-900/50 hover:bg-indigo-600 border border-indigo-700/50 rounded text-[10px] text-indigo-200 truncate max-w-[120px]" 
                     title="${c}">${c}</button>`
        ).join('');
    }

    if (editColName) {
        // Edit Mode
        modalTitle.innerHTML = `<i class="fas fa-edit text-indigo-400 mr-2"></i>Editar Columna`;
        createBtn.innerText = "Actualizar Columna";

        nameInput.value = editColName;
        nameInput.disabled = true; // Cannot rename
        nameInput.classList.add('text-slate-500', 'cursor-not-allowed');

        // Restore format
        formatSelect.value = DETAIL_STATE.columnFormats[editColName] || 'text';

        // Detect Type (Formula vs Value)
        if (DETAIL_STATE.formulas[editColName]) {
            typeSelect.value = 'formula';
            formulaInput.value = DETAIL_STATE.formulas[editColName];
        } else {
            typeSelect.value = 'value';
        }

        // Show update all checkbox if editing
        document.getElementById('update-all-rows-container').classList.remove('hidden');
        document.getElementById('update-all-rows').checked = false;

    } else {
        // Create Mode
        modalTitle.innerHTML = `<i class="fas fa-columns text-indigo-400 mr-2"></i>Nueva Columna`;
        createBtn.innerText = "Crear Columna";
        nameInput.value = '';
        nameInput.disabled = false;
        nameInput.classList.remove('text-slate-500', 'cursor-not-allowed');
        typeSelect.value = 'value';

        // Hide update all checkbox
        document.getElementById('update-all-rows-container').classList.add('hidden');
    }

    toggleNewColInputs();
}

function closeAddColumnModal() {
    const modal = document.getElementById('add-column-modal');
    if (modal) modal.classList.add('hidden');
}

function toggleNewColInputs() {
    const type = document.getElementById('new-col-type').value;
    const valueGroup = document.getElementById('group-col-value');
    const formulaGroup = document.getElementById('group-col-formula');
    const formatGroup = document.getElementById('group-col-format');

    if (type === 'value') {
        valueGroup.classList.remove('hidden');
        formulaGroup.classList.add('hidden');
        formatGroup.classList.remove('hidden');
    } else {
        valueGroup.classList.add('hidden');
        formulaGroup.classList.remove('hidden');
        formatGroup.classList.remove('hidden');
    }
}

function confirmAddColumn() {
    const nameInput = document.getElementById('new-col-name');
    const name = nameInput.value.trim();
    const isEdit = nameInput.disabled; // If disabled, we are editing

    if (!name) { alert("El nombre es obligatorio"); return; }

    if (!isEdit && DETAIL_STATE.cols.includes(name)) {
        alert("Ya existe una columna con ese nombre"); return;
    }

    const type = document.getElementById('new-col-type').value;
    const format = document.getElementById('new-col-format').value;

    if (!isEdit) {
        DETAIL_STATE.cols.push(name);
        DETAIL_STATE.visibleCols.push(name);
    }

    // Always update format
    DETAIL_STATE.columnFormats[name] = format;

    if (type === 'value') {
        const updateAll = document.getElementById('update-all-rows').checked;

        if (!isEdit || updateAll) {
            const defValStr = document.getElementById('new-col-default').value;
            let defVal = defValStr;
            if (defValStr !== '' && !isNaN(Number(defValStr))) {
                defVal = Number(defValStr);
            }
            DETAIL_STATE.rows.forEach(r => r[name] = defVal);
        }

        // If switching from Formula to Value in edit mode, delete the formula
        delete DETAIL_STATE.formulas[name];

    } else { // Formula
        const formula = document.getElementById('new-col-formula').value;
        DETAIL_STATE.formulas[name] = formula;
    }

    renderDetailSidebar();
    processAndRenderTable();
    closeAddColumnModal();
}

const ADD_COLUMN_MODAL_TEMPLATE = `
<div id="add-column-modal" style="z-index: 10000;" class="fixed inset-0 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center">
    <div class="bg-[#1e2230] border border-slate-700 w-full max-w-2xl p-6 rounded-xl shadow-2xl">
        <h2 class="text-xl font-bold text-white mb-6"><i class="fas fa-columns text-indigo-400 mr-2"></i>Nueva Columna</h2>
        
        <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-slate-400 mb-1">Nombre de Columna</label>
                    <input id="new-col-name" type="text" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-white outline-none focus:border-indigo-500">
                </div>

                <div>
                    <label class="block text-xs font-bold text-slate-400 mb-1">Tipo de Dato</label>
                    <select id="new-col-type" onchange="toggleNewColInputs()" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-white outline-none focus:border-indigo-500">
                        <option value="value">Valor Fijo (Texto/Número)</option>
                        <option value="formula">Fórmula Matemática</option>
                    </select>
                </div>
            </div>

            <div id="group-col-value">
                <label class="block text-xs font-bold text-slate-400 mb-1">Valor por Defecto</label>
                <input id="new-col-default" type="text" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-white outline-none focus:border-indigo-500" placeholder="0">
                <div id="update-all-rows-container" class="mt-2 hidden">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" id="update-all-rows" class="scale-125 accent-indigo-500">
                        <span class="text-xs text-indigo-300 font-bold">Actualizar todas las filas</span>
                    </label>
                    <p class="text-[9px] text-slate-500 ml-5">Si se marca, sobrescribirá todos los valores de esta columna.</p>
                </div>
            </div>

            <div id="group-col-formula" class="hidden">
                <label class="block text-xs font-bold text-slate-400 mb-1">Editor de Fórmula</label>
                
                <!-- Formula Input -->
                <textarea id="new-col-formula" rows="3" class="w-full bg-[#0b0c12] border border-slate-700 rounded p-3 text-indigo-300 font-mono text-sm outline-none focus:border-indigo-500 mb-3" placeholder="Ej: [Area] * 1.10"></textarea>
                
                <div class="grid grid-cols-2 gap-4">
                    <!-- Operators -->
                    <div>
                        <p class="text-[10px] text-slate-500 font-bold mb-2 uppercase">Operadores</p>
                        <div class="grid grid-cols-4 gap-2">
                            <button onclick="insertFormulaToken('+')" class="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded text-xs font-bold border border-slate-700">+</button>
                            <button onclick="insertFormulaToken('-')" class="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded text-xs font-bold border border-slate-700">-</button>
                            <button onclick="insertFormulaToken('*')" class="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded text-xs font-bold border border-slate-700">*</button>
                            <button onclick="insertFormulaToken('/')" class="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded text-xs font-bold border border-slate-700">/</button>
                            <button onclick="insertFormulaToken('(')" class="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded text-xs font-bold border border-slate-700">(</button>
                            <button onclick="insertFormulaToken(')')" class="bg-slate-800 hover:bg-slate-700 text-white p-2 rounded text-xs font-bold border border-slate-700">)</button>
                        </div>
                    </div>

                    <!-- Fields -->
                    <div>
                        <p class="text-[10px] text-slate-500 font-bold mb-2 uppercase">Campos Disponibles</p>
                        <div id="formula-fields-list" class="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1 custom-scrollbar">
                            <!-- Filled dynamically -->
                        </div>
                    </div>
                </div>
            </div>

            <div id="group-col-format">
                <label class="block text-xs font-bold text-slate-400 mb-1">Formato Visual</label>
                <select id="new-col-format" class="w-full bg-[#13151f] border border-slate-700 rounded p-2 text-white outline-none focus:border-indigo-500">
                    <option value="text">Texto General</option>
                    <option value="number">Número (2 decimales)</option>
                    <option value="currency">Moneda ($)</option>
                    <option value="percent">Porcentaje (%)</option>
                </select>
            </div>
        </div>

        <div class="flex justify-end gap-3 mt-8 pt-4 border-t border-slate-800">
            <button onclick="closeAddColumnModal()" class="px-4 py-2 text-slate-400 hover:text-white text-sm font-bold">Cancelar</button>
            <button onclick="confirmAddColumn()" class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold rounded shadow-lg shadow-indigo-500/20">Guardar Columna</button>
        </div>
    </div>
</div>
`;

function insertFormulaToken(token) {
    const input = document.getElementById('new-col-formula');
    if (!input) return;

    const start = input.selectionStart;
    const end = input.selectionEnd;
    const val = input.value;

    // Insert text at cursor
    input.value = val.substring(0, start) + (token.startsWith('[') ? token : ` ${token} `) + val.substring(end);

    // Move cursor after insertion
    const newPos = start + token.length + (token.startsWith('[') ? 0 : 2);
    input.selectionStart = newPos;
    input.selectionEnd = newPos;
    input.focus();
}


function handleCellEdit(e, idx, col) {
    const newVal = e.target.innerText;

    // Check if we are in grouped mode
    if (!DETAIL_STATE.itemize) {
        showToast("Debes activar 'Detallar cada ejemplar' para editar.", "warning");
        processAndRenderTable(); // Re-render to revert visual change
        return;
    }

    const row = DETAIL_STATE.displayRows[idx];
    if (row) {
        let finalVal = newVal;
        // Basic type inference or respect valid number
        if (!isNaN(parseFloat(newVal)) && isFinite(newVal)) {
            const fmt = DETAIL_STATE.columnFormats[col];
            if (fmt === 'number' || fmt === 'currency' || fmt === 'percent') {
                finalVal = parseFloat(newVal);
                if (fmt === 'percent') {
                    // Smart Percent: If user types "50" -> 0.50. If types "0.5" -> 0.5. If types "50%", handle it.
                    if (newVal.includes('%')) {
                        finalVal = parseFloat(newVal.replace('%', '')) / 100;
                    } else {
                        // Heuristic: If value > 1, assume it's a percentage point (e.g. 10 = 10%)
                        // If value <= 1, assume it's a decimal (e.g. 0.1 = 10%)
                        // This is a common behavior in spreadsheet software
                        if (Math.abs(finalVal) > 1) {
                            finalVal = finalVal / 100;
                        }
                    }
                }
            } else {
                finalVal = parseFloat(newVal);
            }
        }

        row[col] = finalVal;
        processAndRenderTable();
    }
}

function handleCellKey(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        e.target.blur();
    }
}

function updateColumnFormat(col, type) {
    DETAIL_STATE.columnFormats[col] = type;
    processAndRenderTable();
}

function toggleOutputColumn(col, isChecked) {
    if (!DETAIL_STATE.outputCols) DETAIL_STATE.outputCols = [];

    if (isChecked) {
        if (!DETAIL_STATE.outputCols.includes(col)) {
            DETAIL_STATE.outputCols.push(col);
        }
    } else {
        DETAIL_STATE.outputCols = DETAIL_STATE.outputCols.filter(c => c !== col);
    }

    // Re-render table to show green border
    renderTable(DETAIL_STATE.displayRows);
}

function switchSidebarTab(tab) {
    DETAIL_STATE.activeSidebarTab = tab;
    // Update visual tabs
    ['fields', 'filter', 'sort', 'format', 'desc'].forEach(t => {
        const btn = document.getElementById(`stab-${t}`);
        const view = document.getElementById(`sview-${t}`);
        if (t === tab) {
            btn.className = "flex-1 py-3 text-center text-[10px] font-bold text-indigo-400 border-b-2 border-indigo-500 bg-slate-800/30";
            if (view) view.classList.remove('hidden');
        } else {
            btn.className = "flex-1 py-3 text-center text-[10px] font-bold text-slate-500 hover:text-slate-300 hover:bg-slate-800/30";
            if (view) view.classList.add('hidden');
        }
    });
}

function renderDetailSidebar() {
    // Fields List
    // Fields List
    const fieldsContainer = document.getElementById('fields-list');
    fieldsContainer.innerHTML = DETAIL_STATE.visibleCols.map((c, i) => `
        <div class="flex items-center gap-2 p-2 rounded hover:bg-slate-800 border bg-slate-800/20 border-slate-700 cursor-move" 
             draggable="true" 
             ondragstart="handleDragStartCol(event, '${c}')"
             ondragover="handleDragOverCol(event)"
             ondrop="handleDropCol(event, '${c}')"
             ondragend="handleDragEndCol(event)">
            <i class="fas fa-grip-vertical text-slate-600 text-[10px]"></i>
            <span class="text-xs text-indigo-300 truncate flex-1 font-medium" title="${c}">${c}</span>
             <button onclick="toggleDetailCol('${c}')" class="text-slate-500 hover:text-red-400"><i class="fas fa-eye"></i></button>
        </div>
    `).join('') +
        `<div class="pt-4 border-t border-slate-800 mt-2">
        <p class="text-[10px] text-slate-500 mb-2 uppercase font-bold">Disponibles</p>
        ${DETAIL_STATE.cols.filter(c => !DETAIL_STATE.visibleCols.includes(c)).map(c => `
             <div class="flex items-center gap-2 p-1.5 rounded hover:bg-slate-800 opacity-60 hover:opacity-100">
                <button onclick="toggleDetailCol('${c}')" class="text-slate-500 hover:text-emerald-400"><i class="fas fa-plus-circle"></i></button>
                <span class="text-xs text-slate-400 truncate flex-1" title="${c}">${c}</span>
            </div>
        `).join('')}
    </div>`;

    // Sort Select
    const sortSelect = document.getElementById('sort-by-select');
    // Maintain selection if possible
    const currentSort = sortSelect.value;
    sortSelect.innerHTML = `<option value="">(Ninguno)</option>` +
        DETAIL_STATE.visibleCols.map(c => `<option value="${c}" ${c === DETAIL_STATE.sort[0]?.field ? 'selected' : ''}>${c}</option>`).join('');

    // Format List
    const formatContainer = document.getElementById('format-list');
    if (formatContainer) {
        formatContainer.innerHTML = DETAIL_STATE.visibleCols.map(c => {
            const fmt = DETAIL_STATE.columnFormats[c] || 'text';
            return `
             <div class="flex items-center gap-2 p-2 bg-slate-800/30 border border-slate-700 rounded text-xs cursor-move"
                  draggable="true" 
                  ondragstart="handleDragStartCol(event, '${c}')"
                  ondragover="handleDragOverCol(event)"
                  ondrop="handleDropCol(event, '${c}')"
                  ondragend="handleDragEndCol(event)">
                 <i class="fas fa-grip-vertical text-slate-600 text-[10px]"></i>
                 
                 <!-- Output Checkbox -->
                 <label class="relative flex items-center group cursor-pointer" title="Marcar como Output">
                    <input type="checkbox" 
                           class="peer sr-only" 
                           ${(DETAIL_STATE.outputCols || []).includes(c) ? 'checked' : ''}
                           onchange="toggleOutputColumn('${c}', this.checked)">
                    <div class="w-4 h-4 border-2 border-slate-600 rounded peer-checked:bg-emerald-500 peer-checked:border-emerald-500 transition-colors"></div>
                    <i class="fas fa-check text-white text-[10px] absolute left-0.5 top-0.5 opacity-0 peer-checked:opacity-100"></i>
                 </label>

                 <span class="text-slate-300 truncate flex-1 font-medium ml-1" title="${c}">${c}</span>
                 
                 <select class="bg-[#0b0c12] border border-slate-600 rounded text-slate-300 px-2 py-1 w-24" onchange="updateColumnFormat('${c}', this.value)">
                     <option value="text" ${fmt === 'text' ? 'selected' : ''}>Texto</option>
                     <option value="number" ${fmt === 'number' ? 'selected' : ''}>Número</option>
                     <option value="currency" ${fmt === 'currency' ? 'selected' : ''}>Moneda</option>
                     <option value="percent" ${fmt === 'percent' ? 'selected' : ''}>Porcentaje</option>
                     <option value="weight" ${fmt === 'weight' ? 'selected' : ''}>Peso (kg)</option>
                 </select>
                 <button onclick="openAddColumnModal('${c}')" class="text-slate-500 hover:text-indigo-400 px-1 ml-1 rounded hover:bg-slate-700/50" title="Editar Columna"><i class="fas fa-pencil-alt"></i></button>
                 <button onclick="deleteColumn('${c}')" class="text-slate-500 hover:text-red-500 px-1 ml-1 rounded hover:bg-slate-700/50" title="Eliminar Columna"><i class="fas fa-trash-alt"></i></button>
             </div>
             `;
        }).join('') + `
            <button onclick="openAddColumnModal()" class="w-full mt-4 py-2 border border-dashed border-slate-600 text-slate-400 text-xs rounded hover:border-indigo-500 hover:text-indigo-400">
                <i class="fas fa-plus mr-2"></i>Agregar Columna
            </button>
        `;
    }

    // Descriptions List
    const descContainer = document.getElementById('desc-list');
    if (descContainer) {
        descContainer.innerHTML = DETAIL_STATE.descriptions.map(d => `
            <div class="relative group">
                <textarea oninput="updateDescriptionVal(${d.id}, this.value)" 
                          class="w-full bg-[#1e2230] border border-slate-700 rounded p-3 text-slate-300 text-xs resize-none focus:border-indigo-500 outline-none" 
                          rows="3" placeholder="Escribe una descripción...">${d.text}</textarea>
                <button onclick="removeDescription(${d.id})" class="absolute top-2 right-2 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 rounded p-1">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }
}


function toggleDetailCol(col) {
    if (DETAIL_STATE.visibleCols.includes(col)) {
        DETAIL_STATE.visibleCols = DETAIL_STATE.visibleCols.filter(c => c !== col);
    } else {
        DETAIL_STATE.visibleCols.push(col);
    }
    renderDetailSidebar(); // Re-render sidebar to update visuals if needed
    processAndRenderTable();
}

function toggleItemize() {
    DETAIL_STATE.itemize = document.getElementById('itemize-check').checked;
    processAndRenderTable();
}

// --- FILTERS LOGIC ---
function addFilter() {
    DETAIL_STATE.filters.push({ field: DETAIL_STATE.visibleCols[0] || '', op: 'contains', val: '' });
    renderFilters();
    processAndRenderTable();
}

function removeFilter(index) {
    DETAIL_STATE.filters.splice(index, 1);
    renderFilters();
    processAndRenderTable();
}

function updateFilter(index, key, val) {
    DETAIL_STATE.filters[index][key] = val;
    processAndRenderTable();
}

function renderFilters() {
    const container = document.getElementById('filters-list');
    if (!container) return;
    container.innerHTML = DETAIL_STATE.filters.map((f, i) => `
        <div class="bg-slate-800/50 p-2 rounded border border-slate-700 space-y-2">
            <div class="flex gap-1">
                <select class="bg-[#0b0c12] text-xs text-white border border-slate-600 rounded flex-1" onchange="updateFilter(${i}, 'field', this.value)">
                    ${DETAIL_STATE.cols.map(c => `<option value="${c}" ${c === f.field ? 'selected' : ''}>${c}</option>`).join('')}
                </select>
                <button onclick="removeFilter(${i})" class="text-slate-500 hover:text-red-400 px-1"><i class="fas fa-times"></i></button>
            </div>
            <div class="flex gap-1">
                <select class="bg-[#0b0c12] text-xs text-white border border-slate-600 rounded w-1/3" onchange="updateFilter(${i}, 'op', this.value)">
                    <option value="contains" ${f.op === 'contains' ? 'selected' : ''}>Contiene</option>
                    <option value="equals" ${f.op === 'equals' ? 'selected' : ''}>Igual</option>
                    <option value="startswith" ${f.op === 'startswith' ? 'selected' : ''}>Empieza</option>
                    <option value="gt" ${f.op === 'gt' ? 'selected' : ''}>Mayor q</option>
                    <option value="lt" ${f.op === 'lt' ? 'selected' : ''}>Menor q</option>
                </select>
                <input type="text" class="bg-[#0b0c12] text-xs text-white border border-slate-600 rounded flex-1 px-2" 
                       value="${f.val}" oninput="updateFilter(${i}, 'val', this.value)" placeholder="Valor...">
            </div>
        </div>
    `).join('');
}


// --- DRAG DROP COLUMNS ---
let dragSrcCol = null;
function handleDragStartCol(e, col) {
    dragSrcCol = col;
    e.dataTransfer.effectAllowed = 'move';
    e.target.style.opacity = '0.4';
}
function handleDragOverCol(e) {
    if (e.preventDefault) e.preventDefault();
    return false;
}
function handleDropCol(e, targetCol) {
    e.stopPropagation();
    if (dragSrcCol !== targetCol) {
        const oldIdx = DETAIL_STATE.visibleCols.indexOf(dragSrcCol);
        const newIdx = DETAIL_STATE.visibleCols.indexOf(targetCol);
        if (oldIdx > -1 && newIdx > -1) {
            DETAIL_STATE.visibleCols.splice(oldIdx, 1);
            DETAIL_STATE.visibleCols.splice(newIdx, 0, dragSrcCol);
            renderDetailSidebar();
            processAndRenderTable();
        }
    }
    return false;
}
function handleDragEndCol(e) {
    e.target.style.opacity = '1';
}

function updateSort() {
    const field = document.getElementById('sort-by-select').value;
    const asc = document.getElementById('sort-asc-check').checked;
    DETAIL_STATE.sort = field ? [{ field, asc }] : [];
    processAndRenderTable();
}

function processAndRenderTable() {
    let data = [...DETAIL_STATE.rows];

    // 0. Calculate Formulas
    const formulaKeys = Object.keys(DETAIL_STATE.formulas);
    if (formulaKeys.length > 0) {
        data.forEach(row => {
            formulaKeys.forEach(resCol => {
                let eq = DETAIL_STATE.formulas[resCol];
                // Pre-process percentage literals (e.g. 50% -> 0.50)
                eq = eq.replace(/(\d+(?:\.\d+)?)\s*%/g, '($1/100)');

                // Replace [ColName] with value
                const matches = eq.match(/\[(.*?)\]/g);
                if (matches) {
                    matches.forEach(m => {
                        const colName = m.replace('[', '').replace(']', '').trim();
                        let rawVal = row[colName];

                        // Robust parse for formula
                        let val = 0;
                        if (typeof rawVal === 'number') val = rawVal;
                        else if (typeof rawVal === 'string') {
                            val = parseFloat(rawVal.replace(/[^0-9.-]/g, '')) || 0;
                        }

                        eq = eq.replace(m, val);
                    });
                }

                try {
                    // Safe Eval (Added e/E for scientific notation)
                    if (/^[0-9+\-*/().\sEe]*$/.test(eq)) {
                        let res = eval(eq);
                        if (!isFinite(res) || isNaN(res)) res = 0;
                        row[resCol] = res;
                    } else {
                        console.warn("Formula blocked by safety check:", eq);
                        row[resCol] = 0;
                    }
                } catch (e) {
                    console.error("Formula error:", e, eq);
                    row[resCol] = 0;
                }
            });
        });
    }

    // 1. Filter
    if (DETAIL_STATE.filters.length > 0) {
        data = data.filter(row => {
            return DETAIL_STATE.filters.every(f => {
                const val = (row[f.field] || '').toString().toLowerCase();
                const filterVal = f.val.toLowerCase();
                if (f.op === 'contains') return val.includes(filterVal);
                if (f.op === 'equals') return val === filterVal;
                if (f.op === 'startswith') return val.startsWith(filterVal);
                // Numeric approx
                const numVal = parseFloat(val);
                const numFilter = parseFloat(filterVal);
                if (!isNaN(numVal) && !isNaN(numFilter)) {
                    if (f.op === 'gt') return numVal > numFilter;
                    if (f.op === 'lt') return numVal < numFilter;
                }
                return true;
            });
        });
    }

    // 2. Sort
    if (DETAIL_STATE.sort.length > 0) {
        const { field, asc } = DETAIL_STATE.sort[0];
        data.sort((a, b) => {
            const valA = a[field] || "";
            const valB = b[field] || "";
            // Numeric detection
            const numA = parseFloat(valA);
            const numB = parseFloat(valB);
            if (!isNaN(numA) && !isNaN(numB)) {
                return asc ? numA - numB : numB - numA;
            }
            const comp = valA.toString().localeCompare(valB.toString());
            return asc ? comp : -comp;
        });
    }

    // 3. Group / Itemize
    if (!DETAIL_STATE.itemize && DETAIL_STATE.sort.length > 0) {
        const sortField = DETAIL_STATE.sort[0].field;
        const grouped = {};

        data.forEach(row => {
            const key = row[sortField] || "(Sin Valor)";
            if (!grouped[key]) {
                // Init group leader
                grouped[key] = { ...row, _count: 0 };
                // Zero out numeric fields for accumulation
                DETAIL_STATE.visibleCols.forEach(col => {
                    const val = parseFloat(row[col]);
                    if (!isNaN(val) && col !== sortField) grouped[key][col] = 0;
                });
            }
            grouped[key]._count++;

            // Accumulate Numerics
            DETAIL_STATE.visibleCols.forEach(col => {
                const val = parseFloat(row[col]);
                if (!isNaN(val) && col !== sortField) {
                    grouped[key][col] += val;
                } else if (col !== sortField && grouped[key][col] !== row[col]) {
                    // Varying text
                    grouped[key][col] = "<Varios>";
                }
            });
        });

        // Flatten
        data = Object.values(grouped);
    }

    DETAIL_STATE.displayRows = data;

    // Render
    renderTable(data);
}

function renderTable(data) {
    const head = document.getElementById('detail-table-head');
    const body = document.getElementById('detail-table-body');
    const countEl = document.getElementById('detail-row-count');

    countEl.innerText = `${data.length} Elementos`;

    head.innerHTML = `<tr>
        <th class="px-4 py-3 bg-slate-800 border-b border-slate-700 w-10 text-center text-slate-500">#</th>
        ${DETAIL_STATE.visibleCols.map(c => `<th class="px-4 py-3 border-l border-slate-700 truncate resize-x overflow-hidden hover:bg-slate-700 hover:text-white cursor-pointer transition-colors">${c}</th>`).join('')}
    </tr>`;

    // Calculate Footers (Totals)
    const totals = {};
    DETAIL_STATE.visibleCols.forEach(col => {
        let sum = 0;
        let isNum = true;
        data.forEach(r => {
            const val = parseFloat(r[col]);
            if (isNaN(val)) isNum = false;
            else sum += val;
        });
        totals[col] = isNum ? sum : '';
    });

    const rowsHtml = data.map((r, i) => {
        // Simulation: If card has changes, highlight every 3rd row to demonstrate UI
        const isChanged = DETAIL_STATE.hasChanges && (i % 3 === 0);
        const rowBg = isChanged ? 'bg-yellow-500/10 hover:bg-yellow-500/20' : 'hover:bg-slate-800/50';

        return `
        <tr class="${rowBg} transition-colors group text-[11px]">
             <td class="px-4 py-1.5 border-b border-slate-800 text-center font-mono text-slate-600">${i + 1}</td>
             ${DETAIL_STATE.visibleCols.map(c => {
            let val = r[c];
            const fmt = DETAIL_STATE.columnFormats[c] || 'text';
            let displayVal = val !== undefined && val !== null ? val : '-';
            let rawTitle = displayVal;

            if (typeof val === 'number') {
                if (fmt === 'currency') {
                    displayVal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
                } else if (fmt === 'percent') {
                    // Stored as decimal (0.10 = 10%), so no division needed
                    displayVal = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 2 }).format(val);
                } else if (fmt === 'weight') {
                    displayVal = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val) + ' kg';
                } else {
                    // FORCE 2 DECIMALS GLOBALLY for all other numbers
                    displayVal = val.toFixed(2);
                }
            } else if (fmt === 'currency' && !isNaN(parseFloat(val))) {
                displayVal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(parseFloat(val));
            }

            const isOutput = (DETAIL_STATE.outputCols || []).includes(c);
            // Border Logic:
            // Default: border-b border-slate-800 border-l
            // Output: border-2 border-emerald-500
            const baseClasses = "px-4 py-1.5 truncate max-w-[200px]";
            const borderClasses = isOutput ? "border-2 border-emerald-500 bg-emerald-500/5 text-emerald-100" : "border-b border-slate-800 border-l border-slate-800 text-slate-300";

            const isEditable = DETAIL_STATE.itemize && !DETAIL_STATE.originalCols.includes(c);

            return `<td class="${baseClasses} ${borderClasses} ${isEditable ? 'hover:bg-slate-700/50 cursor-text focus:bg-slate-700 focus:outline-none focus:text-white' : 'cursor-default text-slate-500'}"
                             contenteditable="${isEditable}"
                             onblur="handleCellEdit(event, ${i}, '${c}')"
                             onkeydown="handleCellKey(event)"
                             title="${rawTitle}">${displayVal}</td>`;
        }).join('')}
        </tr>
    `;
    }).join('');

    // Footer Row
    const footerHtml = `
        <tr class="bg-indigo-900/20 font-bold text-indigo-300">
            <td class="px-4 py-2 text-right">TOTAL</td>
            ${DETAIL_STATE.visibleCols.map(c => {
        let val = totals[c];
        const fmt = DETAIL_STATE.columnFormats[c] || 'text';
        let displayVal = '';

        if (typeof val === 'number') {
            if (fmt === 'currency') {
                displayVal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
            } else if (fmt === 'number') {
                displayVal = val.toFixed(2);
            } else {
                displayVal = val.toFixed(2);
            }
        }
        return `<td class="px-4 py-2 border-l border-indigo-500/30">${displayVal}</td>`;
    }).join('')}
        </tr>
    `;

    body.innerHTML = rowsHtml + footerHtml;
}



// --- AUTOMATIC LIVE COMPILATION LOGIC ---

let currentCompilationGroupId = null;

// Initialize the Compilation View
function setupCompilationView() {
    renderCompilationNavigation();

    // Select first group by default if available
    if (groups.length > 0 && !currentCompilationGroupId) {
        renderLiveCompilation(groups[0].id);
    }
}

// 1. Render Navigation (Sidebar)
function renderCompilationNavigation() {
    const container = document.getElementById('compilation-nav-list');
    if (!container) return;

    container.innerHTML = groups.map(g => {
        const isActive = g.id === currentCompilationGroupId;
        const activeClass = isActive ? "bg-indigo-600 text-white shadow-md border-indigo-500" : "text-slate-400 hover:text-indigo-200 hover:bg-slate-800 border-transparent";

        // Calculate Count Dynamically (Safe)
        // Groups -> Subgroups -> Cards
        let count = 0;
        if (g.subgroups && Array.isArray(g.subgroups)) {
            const subgroupIds = g.subgroups.map(sg => sg.id);
            if (typeof activeCards !== 'undefined' && Array.isArray(activeCards)) {
                count = activeCards.filter(c => subgroupIds.includes(c.subgroupId)).length;
            }
        }

        return `
        <div onclick="renderLiveCompilation('${g.id}')" 
             class="cursor-pointer p-3 mb-1 mx-2 rounded border flex items-center justify-between transition-all ${activeClass}">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded bg-slate-900/50 flex items-center justify-center">
                    <i class="fas ${g.icon} ${isActive ? 'text-white' : 'text-indigo-500'}"></i>
                </div>
                <div class="flex flex-col">
                    <span class="text-xs font-bold uppercase tracking-wider">${g.name}</span>
                    <span class="text-[10px] opacity-70">${count} Tarjetas</span>
                </div>
            </div>
            ${isActive ? '<i class="fas fa-chevron-right text-xs"></i>' : ''}
        </div>`;
    }).join('');
}

// 2. Render Main Canvas (Excel Visualizer)
function renderLiveCompilation(groupId) {
    try {
        currentCompilationGroupId = groupId;
        renderCompilationNavigation(); // Update active state

        const group = groups.find(g => g.id === groupId);
        const canvas = document.getElementById('compilation-canvas');
        const titleEl = document.getElementById('current-sheet-title');

        if (!group) {
            console.error("Group not found:", groupId);
            return;
        }
        if (!canvas) {
            console.error("Canvas element not found");
            return;
        }

        // Update Title
        if (titleEl) titleEl.innerText = group.name;

        // --- BUILD THE TABLE HTML ---
        let rowsHtml = '';
        const subgroups = group.subgroups || [];

        if (subgroups.length === 0) {
            rowsHtml = `<tr><td colspan="5" class="p-8 text-center text-slate-500">Este grupo no tiene subgrupos definidos.</td></tr>`;
        }

        // Iterate Subgroups
        subgroups.forEach(sub => {
            // A. Subgroup Header (Black)
            rowsHtml += `
            <tr>
                <td colspan="5" class="bg-black text-white font-bold text-sm uppercase px-4 py-2 border border-slate-600">
                    ${sub.name}
                </td>
            </tr>`;

            // Get Cards in this Subgroup
            const safeActiveCards = (typeof activeCards !== 'undefined') ? activeCards : [];
            const groupCards = safeActiveCards.filter(c => c.subgroupId === sub.id);

            if (groupCards.length === 0) {
                rowsHtml += `<tr><td colspan="5" class="px-4 py-1 text-xs text-slate-500 italic">No hay tarjetas en este subgrupo.</td></tr>`;
            }

            groupCards.forEach((card, index) => {
                // B. Card Header (Gray)
                rowsHtml += `
                <tr>
                    <td colspan="5" class="bg-slate-400 text-slate-900 font-bold text-xs uppercase px-4 py-1.5 border border-slate-600">
                        ${card.name}
                    </td>
                </tr>`;

                // C. Column Headers (Conditionally: Only if it's the FIRST card of the subgroup)
                if (index === 0) {
                    rowsHtml += `
                    <tr class="bg-white text-black font-bold text-[10px] text-center border border-slate-600">
                        <td class="w-24 border-r border-slate-300 px-2 py-1">CODIGO</td>
                        <td class="w-auto border-r border-slate-300 px-2 py-1">DESCRIPCION</td>
                        <td class="w-24 border-r border-slate-300 px-2 py-1">UNIDAD</td>
                        <td class="w-24 border-r border-slate-300 px-2 py-1">TOTAL</td>
                        <td class="w-24 px-2 py-1">HOJA</td>
                    </tr>`;
                }

                // D. Data Rows
                // 1. Calculate Total
                let total = 0;
                if (card.rows && card.rows.length > 0) {
                    const outCol = (card.outputCols && card.outputCols.length > 0) ? card.outputCols[0] : null;

                    if (outCol) {
                        total = card.rows.reduce((sum, r) => {
                            const val = parseFloat(r[outCol]);
                            return sum + (isNaN(val) ? 0 : val);
                        }, 0);
                    }
                }
                const totalFormatted = total.toFixed(2);

                // 2. Format Description
                const desc = (card.descriptions || []).map(d => d.text).join('<br>');

                rowsHtml += `
                <tr class="bg-white text-black text-xs border border-slate-600 hover:bg-slate-50">
                    <td class="px-2 py-1 border-r border-slate-300 align-top text-center">${card.code || '-'}</td>
                    <td class="px-2 py-1 border-r border-slate-300 align-top text-left">${desc || '-'}</td>
                    <td class="px-2 py-1 border-r border-slate-300 align-top text-center">${card.unit || '-'}</td>
                    <td class="px-2 py-1 border-r border-slate-300 align-top text-right font-mono font-bold">${totalFormatted}</td>
                    <td class="px-2 py-1 align-top text-center">${card.linkedSheet || '-'}</td>
                </tr>`;
            });
        });

        // --- RENDER CONTAINER ---
        canvas.innerHTML = `
        <div class="mx-auto max-w-[1000px] bg-white text-black shadow-2xl p-8 min-h-[800px]">
            <!-- Print Header -->
            <div class="border-b-2 border-black mb-4 pb-2 flex justify-between items-end">
                 <h1 class="text-2xl font-bold uppercase">${group.name}</h1>
                 <p class="text-sm text-gray-500">Generado Automáticamente</p>
            </div>

            <table class="w-full border-collapse" id="excel-export-table">
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>`;
    } catch (e) {
        console.error("Error in renderLiveCompilation:", e);
        showToast("Error al renderizar compilación: " + e.message);
    }
}

// 3. Export Logic (Enhanced Modal)
function exportToExcel() {
    openExportModal();
}

function openExportModal() {
    console.log("DEBUG: Attempting to open Export Modal (v2)");
    try {
        // Check if modal template exists, if not, inject it
        if (!document.getElementById('export-modal')) {
            const modalHtml = `
            <div id="export-modal" class="fixed inset-0 bg-black/90 backdrop-blur-sm z-[100] flex items-center justify-center hidden animate-fade-in">
                <div class="bg-[#1e2230] rounded-xl border border-slate-700 shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
                    <div class="p-4 border-b border-slate-700 bg-[#151925] flex justify-between items-center">
                        <h3 class="text-lg font-bold text-white"><i class="fas fa-file-export text-green-500 mr-2"></i>Exportar Compilación</h3>
                        <button onclick="closeExportModal()" class="text-slate-400 hover:text-white"><i class="fas fa-times"></i></button>
                    </div>
                    
                    <div class="p-6 flex-1 overflow-y-auto custom-scrollbar">
                        <p class="text-sm text-slate-400 mb-4">Selecciona los grupos que deseas incluir en el reporte:</p>
                        
                        <div id="export-group-list" class="space-y-2 mb-6">
                            <!-- Injected Checkboxes -->
                        </div>

                        <div class="space-y-3">
                             <label class="block text-xs uppercase text-slate-500 font-bold">Formato de Salida</label>
                             <div class="flex gap-4">
                                 <label class="flex items-center gap-2 cursor-pointer p-3 rounded border border-slate-600 bg-[#0b0c12] hover:border-green-500 flex-1 group">
                                     <input type="radio" name="export-format" value="excel" checked class="accent-green-500">
                                     <div>
                                         <div class="font-bold text-white text-sm group-hover:text-green-400"><i class="fas fa-file-excel text-green-500 mr-2"></i>Excel (.xls)</div>
                                         <div class="text-[10px] text-slate-400">Formato tabular con estilos.</div>
                                     </div>
                                 </label>
                                 <label class="flex items-center gap-2 cursor-pointer p-3 rounded border border-slate-600 bg-[#0b0c12] hover:border-red-500 flex-1 group">
                                     <input type="radio" name="export-format" value="pdf" class="accent-red-500">
                                      <div>
                                         <div class="font-bold text-white text-sm group-hover:text-red-400"><i class="fas fa-file-pdf text-red-500 mr-2"></i>PDF</div>
                                         <div class="text-[10px] text-slate-400">Documento listo para imprimir.</div>
                                     </div>
                                 </label>
                             </div>
                        </div>
                    </div>

                    <div class="p-4 border-t border-slate-700 bg-[#151925] flex justify-end gap-3">
                        <button onclick="closeExportModal()" class="px-4 py-2 text-slate-400 hover:text-white text-sm font-bold">Cancelar</button>
                        <button onclick="confirmExport()" class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded shadow-lg text-sm">
                            Exportar
                        </button>
                    </div>
                </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        const container = document.getElementById('export-group-list');
        if (container) {
            container.innerHTML = groups.map(g => {
                let count = 0;
                // Safe check
                if (g.subgroups && Array.isArray(g.subgroups)) {
                    const subgroupIds = g.subgroups.map(sg => sg.id);
                    const safeCards = (typeof activeCards !== 'undefined' && Array.isArray(activeCards)) ? activeCards : [];
                    count = safeCards.filter(c => subgroupIds.includes(c.subgroupId)).length;
                }

                return `
                <label class="flex items-center gap-3 p-3 rounded-lg bg-[#0b0c12] border border-slate-700 hover:border-indigo-500 cursor-pointer transition-colors">
                    <input type="checkbox" class="export-group-check accent-indigo-500 w-4 h-4" value="${g.id}" ${count > 0 ? 'checked' : ''}>
                    <div class="w-8 h-8 rounded bg-slate-800 flex items-center justify-center text-indigo-400">
                        <i class="fas ${g.icon}"></i>
                    </div>
                    <div class="flex-1">
                        <div class="font-bold text-sm text-white">${g.name}</div>
                        <div class="text-[10px] text-slate-500">${count} Tarjetas</div>
                    </div>
                </label>`;
            }).join('');
        }

        document.getElementById('export-modal').classList.remove('hidden');
    } catch (e) {
        console.error(e);
        showToast("Error opening modal: " + e.message);
    }
}



function closeExportModal() {
    const modal = document.getElementById('export-modal');
    if (modal) modal.classList.add('hidden');
}

function confirmExport() {
    // 1. Get Selected Groups
    const checkboxes = document.querySelectorAll('.export-group-check:checked');
    const selectedIds = Array.from(checkboxes).map(cb => cb.value);

    if (selectedIds.length === 0) {
        alert("Por favor selecciona al menos un grupo.");
        return;
    }

    const format = document.querySelector('input[name="export-format"]:checked').value;
    const selectedGroups = groups.filter(g => selectedIds.includes(g.id));

    // 2. Generate Global HTML
    let fullHtml = '';

    // Determine Global Columns (Union of all columns? Or Standard Report Columns?)
    // Requirement: "Code, Desc, Unit, Total, Sheet" (Standard Compilation View)

    selectedGroups.forEach(group => {
        // Group Header
        fullHtml += `
        <tr>
             <td colspan="5" style="background-color: #000; color: #fff; font-weight: bold; font-size: 14pt; padding: 10px; text-transform: uppercase;">
                ${group.name}
             </td>
        </tr>`;

        const subgroups = group.subgroups || [];
        if (subgroups.length === 0) {
            fullHtml += `<tr><td colspan="5" style="padding: 10px; color: #666; font-style: italic;">Sin subgrupos</td></tr>`;
        }

        subgroups.forEach(sub => {
            const groupCards = activeCards.filter(c => c.subgroupId === sub.id);
            if (groupCards.length === 0) return; // Skip empty subgroups? Or show empty? Let's skip to be clean.

            // Subgroup Header
            fullHtml += `
            <tr>
                <td colspan="5" style="background-color: #e2e8f0; color: #0f172a; font-weight: bold; font-size: 11pt; padding: 5px; text-transform: uppercase; border: 1px solid #cbd5e1;">
                    ${sub.name}
                </td>
            </tr>
            <!-- HEADERS -->
            <tr style="background-color: #fff; color: #000; font-weight: bold; font-size: 10pt; text-align: center;">
                <td style="width: 100px; border: 1px solid #cbd5e1; padding: 5px;">CODIGO</td>
                <td style="border: 1px solid #cbd5e1; padding: 5px;">DESCRIPCION</td>
                <td style="width: 80px; border: 1px solid #cbd5e1; padding: 5px;">UNIDAD</td>
                <td style="width: 100px; border: 1px solid #cbd5e1; padding: 5px;">TOTAL</td>
                <td style="width: 80px; border: 1px solid #cbd5e1; padding: 5px;">HOJA</td>
            </tr>
            `;

            groupCards.forEach(card => {
                // Calculation Logic (Same as Render)
                let total = 0;
                if (card.rows && card.rows.length > 0) {
                    const outCol = (card.outputCols && card.outputCols.length > 0) ? card.outputCols[0] : null;
                    if (outCol) {
                        total = card.rows.reduce((sum, r) => {
                            const val = parseFloat(r[outCol]);
                            return sum + (isNaN(val) ? 0 : val);
                        }, 0);
                    }
                }
                const totalFormatted = total.toFixed(2);
                const desc = (card.descriptions || []).map(d => d.text).join('<br>');

                fullHtml += `
                <tr style="font-size: 10pt; vertical-align: top;">
                    <td style="border: 1px solid #cbd5e1; padding: 5px; text-align: center;">${card.code || '-'}</td>
                    <td style="border: 1px solid #cbd5e1; padding: 5px; text-align: left;">
                         <strong>${card.name}</strong><br>
                         <span style="color: #64748b;">${desc}</span>
                    </td>
                    <td style="border: 1px solid #cbd5e1; padding: 5px; text-align: center;">${card.unit || '-'}</td>
                    <td style="border: 1px solid #cbd5e1; padding: 5px; text-align: right; font-family: monospace; font-weight: bold;">${totalFormatted}</td>
                    <td style="border: 1px solid #cbd5e1; padding: 5px; text-align: center;">${card.linkedSheet || '-'}</td>
                </tr>
                `;
            });
        });

        // Spacer between Groups
        fullHtml += `<tr><td colspan="5" style="height: 20px;"></td></tr>`;
    });

    const finalHtml = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        <meta charset="UTF-8">
        <!--[if gte mso 9]>
        <xml>
            <x:ExcelWorkbook>
                <x:ExcelWorksheets>
                    <x:ExcelWorksheet>
                        <x:Name>Compilacion Master</x:Name>
                        <x:WorksheetOptions>
                            <x:DisplayGridlines/>
                        </x:WorksheetOptions>
                    </x:ExcelWorksheet>
                </x:ExcelWorksheets>
            </x:ExcelWorkbook>
        </xml>
        <![endif]-->
        <style>
            body { font-family: Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; }
        </style>
    </head>
    <body>
        <h1 style="text-transform: uppercase; font-size: 18pt;">Reporte de Compilación Cloud Quantify</h1>
        <p>Generado el: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}</p>
        <br>
        <table>
            ${fullHtml}
        </table>
    </body>
    </html>`;

    if (format === 'excel') {
        const blob = new Blob([finalHtml], { type: 'application/vnd.ms-excel' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `CloudQuantify_Compilacion_${Date.now()}.xls`;
        a.click();
        URL.revokeObjectURL(url);
        showToast("Excel generado correctamente");
    } else {
        // PDF Logic (Print Window)
        const printWindow = window.open('', '', 'height=800,width=1000');
        printWindow.document.write(finalHtml);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => {
            printWindow.print();
            printWindow.close();
        }, 500);
    }

    closeExportModal();
}


// 3. Export Logic (Basic HTML Download)
function exportToExcel() {
    const table = document.getElementById('excel-export-table');
    if (!table) {
        alert("No hay datos para exportar. Seleccione un grupo.");
        return;
    }

    // HTML Table to Excel (Blob trick)
    // This preserves styling (colors) reasonably well in Excel
    const html = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        <meta charset="utf-8">
        <!--[if gte mso 9]>
        <xml>
            <x:ExcelWorkbook>
                <x:ExcelWorksheets>
                    <x:ExcelWorksheet>
                        <x:Name>Hoja 1</x:Name>
                        <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
                    </x:ExcelWorksheet>
                </x:ExcelWorksheets>
            </x:ExcelWorkbook>
        </xml>
        <![endif]-->
    </head>
    <body>
        ${table.outerHTML}
    </body>
    </html>`;

    const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Compilacion_${new Date().toISOString().slice(0, 10)}.xls`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Update switchTab to init view
// --- NAVIGATION ---
function switchTab(tab) {
    // 1. Hide all main views
    const viewIds = ['view-todo', 'view-groups', 'view-compilation'];
    viewIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });

    // 2. Show active view
    const activeView = document.getElementById(`view-${tab}`);
    if (activeView) activeView.classList.remove('hidden');

    // 3. Update Tab Buttons (Navbar)
    ['todo', 'groups', 'compilation'].forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (btn) {
            if (t === tab) {
                btn.className = "px-6 py-2 rounded-md text-sm font-bold text-white bg-indigo-600 shadow-lg transition-all";
            } else {
                btn.className = "px-6 py-2 rounded-md text-sm font-bold text-slate-400 hover:text-white transition-all";
            }
        }
    });

    // 4. Specific Initialization
    if (tab === 'compilation') {
        setupCompilationView();
    }
}
// Removed broken originalSwitchTab override logic


function handleSheetDrop(data) {
    const sheet = compilationSheets.find(s => s.id === currentCompilationSheetId);
    if (!sheet) return;

    if (data.type === 'card') {
        // Add single card
        sheet.items.push({ type: 'card', cardId: data.id });
    } else if (data.type === 'group') {
        // Add all cards in group
        const group = groups.find(g => g.id === data.id);
        if (group && group.cards) {
            group.cards.forEach(cId => {
                sheet.items.push({ type: 'card', cardId: cId });
            });
        }
    }

    renderCompilationSheet();
    saveProject(); // Persist changes
}

function itemMoveUp(index) {
    const i = parseInt(index);
    const sheet = compilationSheets.find(s => s.id === currentCompilationSheetId);
    if (i > 0 && sheet) {
        [sheet.items[i], sheet.items[i - 1]] = [sheet.items[i - 1], sheet.items[i]];
        renderCompilationSheet();
        saveProject();
    }
}

function itemMoveDown(index) {
    const i = parseInt(index);
    const sheet = compilationSheets.find(s => s.id === currentCompilationSheetId);
    if (sheet && i < sheet.items.length - 1) {
        [sheet.items[i], sheet.items[i + 1]] = [sheet.items[i + 1], sheet.items[i]];
        renderCompilationSheet();
        saveProject();
    }
}

function itemRemove(index) {
    const i = parseInt(index);
    const sheet = compilationSheets.find(s => s.id === currentCompilationSheetId);
    if (sheet) {
        sheet.items.splice(i, 1);
        renderCompilationSheet();
        saveProject();
    }
}

function renderTodo(filterText = "") {
    const container = document.getElementById('todo-grid');
    if (!container) return;

    if (!REVIT_DATA) {
        container.innerHTML = `<div class="col-span-4 text-center text-slate-500 py-10">
            <i class="fas fa-box-open text-4xl mb-4 opacity-50"></i>
            <p>No hay datos de Revit disponibles.</p>
        </div>`;
        return;
    }

    let categories = [];

    // Handle C# Extractor Structure: { categories: [ {name:'Walls', rows:[]}, ... ], ... }
    if (REVIT_DATA.categories && Array.isArray(REVIT_DATA.categories)) {
        categories = REVIT_DATA.categories;
    }
    // Fallback: Handle Object Keys Structure (Legacy or simple dict)
    else {
        const ignoredKeys = ['cards', 'groups', 'sheets', 'project_name', 'session_id', 'status', 'savedData'];
        categories = Object.entries(REVIT_DATA).map(([k, v]) => {
            if (ignoredKeys.includes(k)) return null;
            if (Array.isArray(v)) return { name: k, rows: v, count: v.length };
            return null;
        }).filter(x => x);
    }

    // Filter logic
    if (filterText) {
        const lower = filterText.toLowerCase();
        categories = categories.filter(c => c.name.toLowerCase().includes(lower));
    }

    if (categories.length === 0) {
        container.innerHTML = `<div class="col-span-4 text-center text-slate-500 py-10">
            <i class="fas fa-search text-4xl mb-4 opacity-50"></i>
            <p>${filterText ? 'No se encontraron resultados.' : 'Datos de Revit vacíos.'}</p>
        </div>`;
        return;
    }

    container.innerHTML = categories.map(cat => {
        const count = cat.count || (cat.rows ? cat.rows.length : 0);
        return `
        <div class="bg-[#1e2230] p-6 rounded-xl border border-slate-700 hover:border-indigo-500 transition-colors group">
            <div class="flex justify-between items-start mb-4">
                <div class="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                    <i class="fas fa-cube text-xl"></i>
                </div>
                <span class="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-1 rounded uppercase">REVIT</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-1 truncate" title="${cat.name}">${cat.name}</h3>
            <p class="text-slate-400 text-sm mb-4 font-mono">${count} Elementos</p>
            <button onclick="openCardModal('${cat.name}', ${count})" 
                    class="w-full py-2 rounded-lg bg-slate-800 text-slate-300 font-bold text-sm hover:bg-indigo-600 hover:text-white transition-all shadow-lg hover:shadow-indigo-500/30">
                <i class="fas fa-plus mr-2"></i>Crear Tarjeta
            </button>
        </div>
        `;
    }).join('');
}

function renderSheetsList() {
    const container = document.getElementById('sheets-list');
    if (!container) return;

    container.innerHTML = sheets.map(s => `
        <div onclick="loadSheet('${s.id}')"
             class="p-2 rounded cursor-pointer hover:bg-slate-800 ${s.id === CURRENT_SHEET_ID ? 'bg-indigo-900/40 text-indigo-300' : 'text-slate-400'}">
            <div class="font-medium">${s.name}</div>
        </div>
    `).join('');
}

function loadSheet(sheetId) {
    CURRENT_SHEET_ID = sheetId;
    renderSheetsList();

    const sheet = sheets.find(s => s.id === sheetId);
    if (!sheet) return;

    const container = document.getElementById('sheet-content');
    if (!container) return;

    // Simple Render for now - just title and placeholder
    let html = `
    <div class="bg-white min-h-[800px] w-full max-w-4xl mx-auto shadow-xl p-8 text-black">
        <div class="border-b-2 border-black pb-4 mb-8 text-center">
            <h1 class="text-3xl font-bold uppercase tracking-wider">${sheet.name}</h1>
            <p class="text-sm text-gray-500 mt-2">PRESUPUESTO DE OBRA</p>
        </div>
        
        <div class="space-y-4">
             <div class="p-4 bg-gray-50 border border-dashed border-gray-300 rounded text-center text-gray-400">
                Arrastra tarjetas aquí para agregar a la hoja (Próximamente)
             </div>
        </div>
    </div>
    `;

    container.innerHTML = html;
}

function showToast(msg) {
    const t = document.createElement('div');
    t.className = "fixed bottom-5 right-5 bg-emerald-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-bounce";
    t.innerText = msg;
    document.body.appendChild(t);
    setTimeout(() => {
        t.remove();
    }, 2000);
}

// --- CARD ACTIONS ---

function syncCardData(e, id) {
    if (e) e.stopPropagation();
    const c = activeCards.find(card => card.id === id);
    if (!c) return;

    if (c.isLocked) {
        showToast("La tarjeta está bloqueada (HOLD). No se puede sincronizar.");
        return;
    }

    // Real Sync: Refresh data from Backend
    updateStatus("Sincronizando...", "emerald");
    showToast(`Consultando datos actualizados para ${c.name}...`);

    // Slight delay to allow UI to update
    setTimeout(async () => {
        await loadSessionData();

        // Find card again after reload
        const newCard = activeCards.find(card => card.id === id);
        if (newCard) {
            newCard.hasChanges = false;
        }

        showToast("Tarjeta sincronizada con datos del servidor.");
        saveProject(); // Save the state reset
    }, 500);
}

function toggleCardLock(e, id) {
    if (e) e.stopPropagation();
    const c = activeCards.find(card => card.id === id);
    if (!c) return;

    c.isLocked = !c.isLocked;
    renderKanbanBoard();
    saveProject();
    showToast(c.isLocked ? "Tarjeta Congelada (HOLD)" : "Tarjeta Desbloqueada");
}

// Duplicate Logic
let cardToDuplicateId = null;

// Helper for Simulation
function simulateRevitSync(c) {
    if (!c.rows) c.rows = [];

    // 1. Update Existing Numerics
    if (c.rows.length > 0) {
        c.rows.forEach(r => {
            Object.keys(r).forEach(k => {
                if (k === 'id' || k === 'uid' || k === 'guid') return;
                const val = parseFloat(r[k]);
                if (!isNaN(val)) {
                    // Force a +10% to +50% increase
                    const increase = 1.10 + (Math.random() * 0.40);
                    r[k] = val * increase;
                }
            });
        });
    }

    // 2. Simulate New Elements (Rows)
    // Add 1-2 new rows based on the first row structure
    if (c.rows.length > 0 && Math.random() > 0.5) {
        const template = JSON.parse(JSON.stringify(c.rows[0]));
        template.id = "new_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
        // Randomize values a bit
        Object.keys(template).forEach(k => {
            const v = parseFloat(template[k]);
            if (!isNaN(v)) template[k] = v * 0.8; // New element is smaller?
        });
        c.rows.push(template);
    }

    // 3. Simulate New Shared Parameters (Columns)
    // Add a new column if it doesn't exist
    const newParamName = "Param_Compartido_Simulado";
    if (c.rows.length > 0 && c.rows[0][newParamName] === undefined) {
        c.rows.forEach(r => {
            r[newParamName] = (Math.random() * 100).toFixed(2);
        });
        // Optionally add to available cols for sidebar (this would require updating DETAIL_STATE options list if active, 
        // but here we just update data. The sidebar reads from rows keys so it should appear automatically next time opened)
    }
}

// Helper to Simulate Global Revit Data Refresh (New Categories/Sources)
function simulateFreshRevitData() {
    if (!REVIT_DATA) REVIT_DATA = {};

    // 1. Simulate a completely new Category appearing in the project
    const newCategoryName = `Nuevos Detail Items ${Math.floor(Math.random() * 100)}`;
    if (!REVIT_DATA[newCategoryName]) {
        // Create 10 mock items
        REVIT_DATA[newCategoryName] = Array.from({ length: 10 }).map((_, i) => ({
            id: `new_item_${Date.now()}_${i}`,
            uid: `uid_${i}`,
            'Type': 'Detail Item Type A',
            'Family': 'Detail Item Family',
            'Length': (Math.random() * 5).toFixed(2),
            'Area': (Math.random() * 20).toFixed(2),
            'Comments': 'Synced from Revit'
        }));
    }
}

function syncAllCards() {
    // Real Sync: Refresh data from Backend (which comes from Revit Plugin)
    updateStatus("Sincronizando...", "emerald");
    showToast("Consultando datos del servidor...", "info");

    // Slight delay to allow UI to update
    setTimeout(async () => {
        await loadSessionData();
        showToast("Datos actualizados desde el servidor (Revit).");
    }, 500);
}

function openDuplicateCardModal(e, id) {
    if (e) e.stopPropagation();
    cardToDuplicateId = id;
    const c = activeCards.find(card => card.id === id);
    if (!c) return;

    // Populate Groups
    const sel = document.getElementById('dup-card-group-select');
    if (sel) {
        sel.innerHTML = groups.map(g => {
            if (g.subgroups.length === 0) return '';
            return `<optgroup label="${g.name}">
                ${g.subgroups.map(sg => `<option value="${sg.id}" ${c.subgroupId === sg.id ? 'selected' : ''}>${sg.name}</option>`).join('')}
            </optgroup>`;
        }).join('');
    }

    const modal = document.getElementById('duplicate-card-modal');
    if (modal) modal.classList.remove('hidden');
}

function closeDuplicateModal() {
    const modal = document.getElementById('duplicate-card-modal');
    if (modal) modal.classList.add('hidden');
    cardToDuplicateId = null;
}

function confirmDuplicateCard() {
    if (!cardToDuplicateId) return;
    const c = activeCards.find(card => card.id === cardToDuplicateId);
    if (!c) return;

    const sel = document.getElementById('dup-card-group-select');
    const targetSubgroupId = sel ? sel.value : c.subgroupId;

    // Deep Copy
    const newCard = JSON.parse(JSON.stringify(c));
    newCard.id = Date.now().toString();
    newCard.name = `${c.name} (Copia)`;
    newCard.subgroupId = targetSubgroupId;
    newCard.isLocked = false; // Reset lock on copy
    newCard.hasChanges = false;

    activeCards.push(newCard);

    closeDuplicateModal();
    renderKanbanBoard();
    saveProject();
    showToast("Tarjeta duplicada correctamente");
}

// Append Duplicate Modal if not exists
setTimeout(() => {
    if (!document.getElementById('duplicate-card-modal')) {
        const dupModalHtml = `
        <div id="duplicate-card-modal" style="z-index: 10000;" class="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center hidden">
            <div class="bg-[#1e2230] p-6 rounded-xl border border-slate-700 shadow-xl w-full max-w-md">
                <h3 class="text-xl font-bold text-white mb-4"><i class="fas fa-copy text-indigo-400 mr-2"></i>Duplicar Tarjeta</h3>
                <p class="text-slate-400 text-sm mb-6">Selecciona el grupo de destino para la copia de esta tarjeta.</p>
                
                <div class="mb-6">
                    <label class="block text-xs font-bold text-slate-500 mb-1">Grupo de Destino</label>
                    <select id="dup-card-group-select" class="w-full bg-[#0b0c12] border border-slate-700 rounded p-2 text-white outline-none focus:border-indigo-500">
                        <!-- Filled dynamically -->
                    </select>
                </div>

                <div class="flex justify-end gap-3">
                    <button onclick="closeDuplicateModal()" class="px-4 py-2 text-slate-400 hover:text-white font-bold text-sm">Cancelar</button>
                    <button onclick="confirmDuplicateCard()" class="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded shadow-lg text-sm">Duplicar</button>
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', dupModalHtml);
    }
}, 1000);


// --- IMPORT SCHEDULES LOGIC ---
function openImportScheduleModal() {
    // 1. Check if REVIT_DATA exists
    if (!REVIT_DATA) {
        showToast("No hay datos de Revit disponibles para importar.");
        return;
    }

    // 2. Build Modal HTML
    if (!document.getElementById('import-schedule-modal')) {
        const modalHtml = `
         <div id="import-schedule-modal" class="fixed inset-0 bg-black/90 backdrop-blur-sm z-[100] flex items-center justify-center hidden animate-fade-in">
             <div class="bg-[#1e2230] rounded-xl border border-slate-700 shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
                 <div class="p-4 border-b border-slate-700 bg-[#151925] flex justify-between items-center">
                     <h3 class="text-lg font-bold text-white"><i class="fas fa-file-import text-emerald-400 mr-2"></i>Importar Tabla de Cuantificación</h3>
                     <button onclick="document.getElementById('import-schedule-modal').classList.add('hidden')" class="text-slate-400 hover:text-white"><i class="fas fa-times"></i></button>
                 </div>
                 
                 <div class="p-2 border-b border-slate-700 bg-[#0b0c12]">
                     <input type="text" id="import-search" onkeyup="filterImportList()" placeholder="Buscar tabla..." class="w-full bg-[#1e2230] text-sm text-white px-3 py-2 rounded border border-slate-700 focus:border-emerald-500 outline-none">
                 </div>

                 <div class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1" id="import-list-container">
                     <!-- Items injected here -->
                 </div>

                 <div class="p-4 border-t border-slate-700 bg-[#151925] flex justify-end">
                     <button onclick="document.getElementById('import-schedule-modal').classList.add('hidden')" class="px-4 py-2 text-slate-400 hover:text-white text-sm font-bold">Cancelar</button>
                 </div>
             </div>
         </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    // 3. Render List
    renderImportList();
    document.getElementById('import-schedule-modal').classList.remove('hidden');
}

function renderImportList() {
    const container = document.getElementById('import-list-container');
    const searchVal = document.getElementById('import-search')?.value.toLowerCase() || "";

    // CHANGED: Use 'schedules' key
    const schedules = REVIT_DATA.schedules || [];

    // Check if schedules section is missing
    if (!REVIT_DATA.schedules && REVIT_DATA.categories) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500">
            <i class="fas fa-exclamation-triangle mb-2 text-yellow-500 text-2xl"></i><br>
            <span class="font-bold text-white">No se detectaron Tablas (Schedules).</span><br>
            <span class="text-xs text-slate-400">Verifique que el plugin de Revit esté exportando la sección 'schedules'.</span>
         </div>`;
        console.log("REVIT_DATA keys:", Object.keys(REVIT_DATA));
        return;
    }

    const filtered = schedules.filter(c => c.name.toLowerCase().includes(searchVal));

    if (schedules.length > 0 && filtered.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500"><i class="fas fa-search mb-2"></i><br>No se encontraron tablas con ese nombre.</div>`;
        return;
    }

    if (filtered.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500"><i class="fas fa-box-open mb-2 text-slate-600 text-2xl"></i><br>Sin tablas disponibles.</div>`;
        return;
    }

    container.innerHTML = filtered.map(cat => {
        const count = cat.rows ? cat.rows.length : 0;
        return `
        <div class="flex items-center justify-between p-3 rounded bg-[#13151f] border border-slate-700 hover:border-emerald-500 group transition-all">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded bg-slate-800 flex items-center justify-center text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white transition-colors">
                     <i class="fas fa-table"></i>
                </div>
                <div>
                     <div class="font-bold text-slate-200 text-sm">${cat.name}</div>
                     <div class="text-[10px] text-slate-500">${count} Elementos</div>
                </div>
            </div>
            <button onclick="confirmImportSchedule('${cat.name}')" class="px-3 py-1.5 bg-emerald-900/30 text-emerald-400 border border-emerald-900/50 rounded hover:bg-emerald-600 hover:text-white text-xs font-bold transition-all">
                Importar
            </button>
        </div>`;
    }).join('');
}

function filterImportList() {
    renderImportList();
}

function confirmImportSchedule(catName) {
    const cat = (REVIT_DATA.schedules || []).find(c => c.name === catName);
    if (!cat) return;

    // 1. Create New Card
    const newCard = {
        id: Date.now().toString(),
        name: cat.name, // Rename to Category/Table Name
        source: cat.name,
        rows: normalizeRevitData(JSON.parse(JSON.stringify(cat.rows))), // Deep copy & normalize
        status: 'todo', // Default to TODO
        subgroupId: '', // Or 'default'
        description: `Importado de Revit: ${cat.name}`,
        updatedAt: new Date().toISOString(),
        hasChanges: false,
        isLocked: false,

        // Default Filters/Sorts (Empty but ready)
        filters: [],
        sort: [],
        visibleCols: [], // Will auto-fill in Editor
        outputCols: [],
        descriptions: []
    };

    // Auto-select first 5 cols
    if (newCard.rows.length > 0) {
        newCard.visibleCols = Object.keys(newCard.rows[0]).slice(0, 5);
    }

    activeCards.push(newCard);

    // 2. UI Feedback
    document.getElementById('import-schedule-modal').classList.add('hidden');
    showToast(`Tabla "${cat.name}" importada como tarjeta.`);

    // 3. Switch to TODO view to see it (or ensure we are there)
    switchTab('todo');
    renderTodo();
    saveProject();
}
