
// --- FILTER & UTILS ---

let activeFilters = {}; // { cardId: { field: query } }

function filterCardColumn(input, field) {
    if (!expandedCardId) return;
    const query = input.value.toLowerCase();

    if (!activeFilters[expandedCardId]) activeFilters[expandedCardId] = {};
    activeFilters[expandedCardId][field] = query;

    filterEditorTable();
}

function filterEditorTable() {
    if (!expandedCardId) return;
    const filters = activeFilters[expandedCardId] || {};

    const tbody = document.getElementById('editor-tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    const headerCells = Array.from(document.querySelectorAll('#editor-thead-row th'));
    const colIndices = {};
    headerCells.forEach((th, idx) => {
        const span = th.querySelector('span');
        if (span) colIndices[span.innerText] = idx;
    });

    rows.forEach(row => {
        let visible = true;
        Object.keys(filters).forEach(field => {
            const query = filters[field];
            if (!query) return;

            const idx = colIndices[field];
            if (idx !== undefined) {
                const cell = row.children[idx];
                if (cell) {
                    const txt = cell.innerText.toLowerCase();
                    if (!txt.includes(query)) visible = false;
                }
            }
        });

        row.style.display = visible ? '' : 'none';
    });
}
