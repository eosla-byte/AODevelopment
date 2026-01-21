
import os

file_path = "cloud_quantify.js"
safe_marker = "// End of Logic"

template = """
const CARD_MODAL_TEMPLATE = `
<div id="create-card-modal" class="fixed inset-0 bg-black/90 backdrop-blur-sm z-[80] flex items-center justify-center hidden animate-fade-in">
    <div class="bg-[#1e2230] p-8 rounded-2xl border border-slate-700 shadow-2xl w-full max-w-md transform transition-all scale-100">
        <h3 class="text-2xl font-bold text-white mb-2">Crear Tarjeta</h3>
        <div class="inline-flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-slate-700 mb-6">
                <span class="text-slate-400 text-sm" id="modal-category-name">Categoría</span>
                <span class="bg-indigo-500 text-white text-xs font-bold px-2 py-0.5 rounded-full" id="modal-element-count">0</span>
        </div>

        <div class="space-y-4">
            <div>
                <label class="block text-slate-400 text-sm mb-2 font-medium">Nombre</label>
                <input type="text" id="card-name-input" class="w-full bg-[#0b0c12] border border-slate-700 rounded-lg px-4 py-3 text-white focus:border-indigo-500 outline-none" placeholder="Ej. Muros Interiores">
            </div>
            
            <div>
                <label class="block text-slate-400 text-sm mb-2 font-medium">Asignar a Grupo</label>
                <select id="card-group-select" class="w-full bg-[#0b0c12] border border-slate-700 rounded-lg px-4 py-3 text-white focus:border-indigo-500 outline-none">
                    <!-- Options injected -->
                </select>
            </div>
        </div>

        <div class="flex gap-3 mt-8">
            <button onclick="document.getElementById('create-card-modal').classList.add('hidden')" class="flex-1 px-4 py-3 text-slate-400 font-bold hover:text-white hover:bg-slate-800 rounded-lg">Cancelar</button>
            <button onclick="createCardFromModal()" class="flex-1 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg shadow-lg">Crear</button>
        </div>
    </div>
</div>
`;
"""

with open(file_path, 'rb') as f:
    content = f.read().decode('utf-8', errors='ignore')

if safe_marker in content:
    # Truncate
    clean_content = content.split(safe_marker)[0] + safe_marker + "\n" + template
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(clean_content)
    print("FIXED: Successfully restored Javascript file.")
else:
    print("ERROR: Could not find marker '// End of Logic'")
