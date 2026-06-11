/**
 * upload.js — Gestion de l'upload de documents
 *
 * Fonctionnalités :
 *   - Drag & drop sur la zone de dépôt
 *   - Sélection via input file (clic)
 *   - Upload vers POST /api/upload/
 *   - Polling du statut d'indexation (GET /api/upload/:id/status)
 *   - Affichage de la liste des documents
 *   - Suppression de documents
 */

const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const progress   = document.getElementById('upload-progress');
const progressFill  = document.getElementById('progress-fill');
const progressLabel = document.getElementById('progress-label');
const resultDiv  = document.getElementById('upload-result');

// ── Drag & Drop ────────────────────────────────────────────────────────

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files);
    files.forEach(uploadFile);
});

fileInput.addEventListener('change', () => {
    Array.from(fileInput.files).forEach(uploadFile);
    fileInput.value = ''; // Permet de sélectionner le même fichier à nouveau
});

// ── Upload ─────────────────────────────────────────────────────────────

async function uploadFile(file) {
    showProgress('Envoi du fichier...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        setProgressWidth(30);
        const res  = await fetch('/api/upload/', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            showResult('error', `❌ ${data.detail || 'Erreur lors de l\'upload'}`);
            hideProgress();
            return;
        }

        setProgressWidth(60);
        progressLabel.textContent = 'Indexation en cours...';

        // Polling : vérifie le statut jusqu'à ce que l'indexation soit terminée
        await pollStatus(data.doc_id);

    } catch (err) {
        showResult('error', `❌ Erreur réseau : ${err.message}`);
        hideProgress();
    }
}

async function pollStatus(docId) {
    const maxTries = 60;  // 60 tentatives × 2s = 2 minutes max

    for (let i = 0; i < maxTries; i++) {
        await sleep(2000);  // Attend 2 secondes entre chaque vérification

        try {
            const res  = await fetch(`/api/upload/${docId}/status`);
            const data = await res.json();

            if (data.status === 'indexed') {
                setProgressWidth(100);
                progressLabel.textContent = `✅ Indexé ! (${data.chunks_count} chunks)`;
                setTimeout(() => {
                    hideProgress();
                    showResult('success', `✅ Document indexé avec succès (${data.chunks_count} chunks)`);
                    loadDocuments();
                }, 800);
                return;
            }

            if (data.status === 'error') {
                hideProgress();
                showResult('error', '❌ Erreur lors de l\'indexation. Vérifie que le fichier n\'est pas corrompu.');
                loadDocuments();
                return;
            }

            // Toujours en cours (status = 'pending')
            const pct = 60 + Math.min(35, i);
            setProgressWidth(pct);

        } catch (err) {
            // Ignore les erreurs réseau temporaires
        }
    }

    hideProgress();
    showResult('error', '⏱️ Timeout — L\'indexation prend trop de temps.');
}

// ── Liste des documents ─────────────────────────────────────────────────

async function loadDocuments() {
    const container = document.getElementById('documents-list');
    container.innerHTML = '<div class="loading-spinner">Chargement...</div>';

    try {
        const res  = await fetch('/api/upload/');
        const data = await res.json();

        if (!data.documents || data.documents.length === 0) {
            container.innerHTML = '<div class="empty-state">📭 Aucun document — dépose un fichier ci-dessus</div>';
            return;
        }

        container.innerHTML = `
            <table class="docs-table">
                <thead>
                    <tr>
                        <th>Fichier</th>
                        <th>Taille</th>
                        <th>Chunks</th>
                        <th>Statut</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.documents.map(doc => `
                        <tr>
                            <td>📄 ${doc.original_name}</td>
                            <td>${(doc.file_size_kb / 1024).toFixed(2)} Mo</td>
                            <td>${doc.chunks_count || '—'}</td>
                            <td>${badgeHtml(doc.status)}</td>
                            <td>
                                <button class="btn btn-danger btn-sm"
                                        onclick="deleteDocument(${doc.id}, '${doc.original_name}')">
                                    🗑 Supprimer
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (err) {
        container.innerHTML = `<div class="alert alert-error">Erreur de chargement : ${err.message}</div>`;
    }
}

async function deleteDocument(docId, name) {
    if (!confirm(`Supprimer "${name}" ?`)) return;

    try {
        const res = await fetch(`/api/upload/${docId}`, { method: 'DELETE' });
        if (res.ok) {
            showResult('success', `🗑 "${name}" supprimé`);
            loadDocuments();
        }
    } catch (err) {
        showResult('error', `❌ Erreur : ${err.message}`);
    }
}

// ── Utilitaires ────────────────────────────────────────────────────────

function badgeHtml(status) {
    const map = {
        indexed: '<span class="badge badge-indexed">✅ Indexé</span>',
        pending: '<span class="badge badge-pending">⏳ En cours</span>',
        error  : '<span class="badge badge-error">❌ Erreur</span>',
    };
    return map[status] || status;
}

function showProgress(label) {
    progress.style.display = 'block';
    progressLabel.textContent = label;
    setProgressWidth(10);
}

function hideProgress() { progress.style.display = 'none'; }

function setProgressWidth(pct) { progressFill.style.width = `${pct}%`; }

function showResult(type, msg) {
    resultDiv.innerHTML = `<div class="alert alert-${type === 'success' ? 'success' : 'error'}">${msg}</div>`;
    setTimeout(() => { resultDiv.innerHTML = ''; }, 5000);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Init ───────────────────────────────────────────────────────────────
loadDocuments();
