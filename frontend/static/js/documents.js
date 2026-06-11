/**
 * documents.js — Gestion des documents indexés
 *
 * Fonctionnalités :
 *   - Afficher tous les documents avec leur statut
 *   - Filtrer la liste par nom
 *   - Supprimer un document (avec confirmation)
 *   - Actualisation automatique toutes les 10s si un doc est en cours d'indexation
 */

let allDocs = [];
let refreshTimer = null;

// ── Chargement ─────────────────────────────────────────────────────────

async function loadDocuments() {
    try {
        const res  = await fetch('/api/upload/');
        const data = await res.json();
        allDocs = data.documents || [];
        renderTable(allDocs);
        updateCount(allDocs);

        // Auto-refresh si des docs sont en cours d'indexation
        const hasPending = allDocs.some(d => d.status === 'pending');
        clearTimeout(refreshTimer);
        if (hasPending) {
            refreshTimer = setTimeout(loadDocuments, 5000);
        }
    } catch (err) {
        document.getElementById('docs-tbody').innerHTML =
            `<tr><td colspan="6" class="empty-state">❌ Erreur : ${err.message}</td></tr>`;
    }
}

// ── Filtrage ───────────────────────────────────────────────────────────

function filterDocuments(query) {
    const filtered = allDocs.filter(d =>
        d.original_name.toLowerCase().includes(query.toLowerCase())
    );
    renderTable(filtered);
    updateCount(filtered);
}

// ── Rendu du tableau ───────────────────────────────────────────────────

function renderTable(docs) {
    const tbody = document.getElementById('docs-tbody');

    if (docs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    Aucun document trouvé. Utilise le widget ci-dessus pour en ajouter.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = docs.map(doc => {
        const badge   = statusBadge(doc.status);
        const size    = doc.file_size_kb < 1024
            ? `${doc.file_size_kb.toFixed(0)} Ko`
            : `${(doc.file_size_kb / 1024).toFixed(1)} Mo`;
        const date    = new Date(doc.created_at + 'Z').toLocaleString('fr-FR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });

        return `
            <tr id="doc-row-${doc.id}" style="transition:opacity .2s">
                <td style="padding-left:1.2rem">
                    <div class="doc-name-cell">
                        <div class="doc-type-icon">${fileIcon(doc.original_name)}</div>
                        <span class="doc-name-text" title="${escapeHtml(doc.original_name)}">
                            ${escapeHtml(doc.original_name)}
                        </span>
                    </div>
                </td>
                <td>${badge}</td>
                <td style="color:var(--text-muted)">${doc.chunks_count > 0 ? doc.chunks_count : '—'}</td>
                <td style="color:var(--text-muted)">${size}</td>
                <td style="color:var(--text-muted)">${date}</td>
                <td>
                    <button class="btn btn-danger btn-sm"
                            onclick="deleteDocument(${doc.id}, '${escapeHtml(doc.original_name)}')"
                            title="Supprimer">
                        🗑
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ── Suppression ────────────────────────────────────────────────────────

async function deleteDocument(docId, name) {
    if (!confirm(`Supprimer « ${name} » ? Cette action est irréversible.`)) return;

    const row = document.getElementById(`doc-row-${docId}`);
    if (row) row.style.opacity = '0.4';

    try {
        const res = await fetch(`/api/upload/${docId}`, { method: 'DELETE' });
        if (!res.ok) {
            const err = await res.json();
            alert(`❌ Erreur : ${err.detail}`);
            if (row) row.style.opacity = '1';
            return;
        }
        // Retire le doc de la liste locale et re-rend
        allDocs = allDocs.filter(d => d.id !== docId);
        renderTable(allDocs);
        updateCount(allDocs);
    } catch (err) {
        alert(`❌ Erreur réseau : ${err.message}`);
        if (row) row.style.opacity = '1';
    }
}

// ── Utilitaires ────────────────────────────────────────────────────────

function updateCount(docs) {
    const indexed = docs.filter(d => d.status === 'indexed').length;
    document.getElementById('docs-count').textContent =
        `${docs.length} document${docs.length !== 1 ? 's' : ''} · ${indexed} indexé${indexed !== 1 ? 's' : ''}`;
}

function statusBadge(status) {
    const map = {
        indexed: '<span class="badge badge-indexed">✅ Indexé</span>',
        pending: '<span class="badge badge-pending">⏳ En cours</span>',
        error  : '<span class="badge badge-error">❌ Erreur</span>',
    };
    return map[status] || `<span class="badge">${status}</span>`;
}

function fileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    const icons = { pdf: '📕', docx: '📘', doc: '📘', txt: '📄', md: '📝', csv: '📊' };
    return icons[ext] || '📄';
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Init ───────────────────────────────────────────────────────────────
loadDocuments();

// Recharge après un nouvel upload via le widget
window.onDocumentIndexed = loadDocuments;
