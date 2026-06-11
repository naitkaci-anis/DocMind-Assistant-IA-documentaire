/**
 * upload-widget.js — Widget upload réutilisable
 * Inclus sur les pages Recherche, Chat et Résumés.
 *
 * Fonctionnement :
 *   - Clic sur "Ajouter un document" → ouvre/ferme le widget
 *   - Drag & drop ou clic → upload vers /api/upload/
 *   - Polling du statut jusqu'à indexation complète
 *   - Callback onDocumentIndexed() optionnel à définir dans la page
 */

(function () {

    // ── Ouvre / ferme le widget ────────────────────────────────────────
    window.toggleUploadWidget = function () {
        const body = document.getElementById('upload-widget-body');
        const icon = document.getElementById('widget-toggle-icon');
        const open = body.style.display === 'none';
        body.style.display = open ? 'block' : 'none';
        icon.textContent   = open ? '▲' : '▼';
    };

    // ── Éléments DOM ──────────────────────────────────────────────────
    const dropZone    = document.getElementById('drop-zone-mini');
    const fileInput   = document.getElementById('widget-file-input');
    const progressDiv = document.getElementById('widget-progress');
    const progressFill  = document.getElementById('widget-progress-fill');
    const progressLabel = document.getElementById('widget-progress-label');
    const resultDiv   = document.getElementById('widget-result');

    if (!dropZone) return;  // Widget non présent sur cette page

    // ── Drag & Drop ───────────────────────────────────────────────────
    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) uploadFile(file);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) {
            uploadFile(fileInput.files[0]);
            fileInput.value = '';
        }
    });

    // ── Upload + polling ──────────────────────────────────────────────
    async function uploadFile(file) {
        showProgress(10, `Envoi de "${file.name}"...`);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res  = await fetch('/api/upload/', { method: 'POST', body: formData });
            const data = await res.json();

            if (!res.ok) {
                showResult('error', `❌ ${data.detail || 'Erreur upload'}`);
                hideProgress();
                return;
            }

            showProgress(50, `Indexation de "${file.name}"...`);

            // Polling du statut
            for (let i = 0; i < 40; i++) {
                await sleep(2000);
                const sr   = await fetch(`/api/upload/${data.doc_id}/status`);
                const info = await sr.json();

                if (info.status === 'indexed') {
                    showProgress(100, `✅ "${file.name}" indexé !`);
                    setTimeout(() => {
                        hideProgress();
                        showResult('success', `✅ "${file.name}" prêt — pose tes questions !`);
                        // Callback optionnel (utilisé par résumés pour recharger la liste)
                        if (typeof onDocumentIndexed === 'function') onDocumentIndexed();
                    }, 600);
                    return;
                }

                if (info.status === 'error') {
                    hideProgress();
                    showResult('error', `❌ Erreur d'indexation de "${file.name}"`);
                    return;
                }

                showProgress(50 + i, `Indexation de "${file.name}"...`);
            }

            hideProgress();
            showResult('error', '⏱️ Timeout — réessaie avec un fichier plus petit');

        } catch (err) {
            hideProgress();
            showResult('error', `❌ Erreur réseau : ${err.message}`);
        }
    }

    // ── Utilitaires ───────────────────────────────────────────────────
    function showProgress(pct, label) {
        progressDiv.style.display   = 'block';
        progressFill.style.width    = `${Math.min(pct, 100)}%`;
        progressLabel.textContent   = label;
    }

    function hideProgress() { progressDiv.style.display = 'none'; }

    function showResult(type, msg) {
        resultDiv.innerHTML = `<div class="alert alert-${type === 'success' ? 'success' : 'error'}" style="margin-top:0.75rem">${msg}</div>`;
        setTimeout(() => { resultDiv.innerHTML = ''; }, 6000);
    }

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

})();
