/**
 * summary.js — Page de résumés automatiques
 *
 * Fonctionnement :
 *   1. Charge la liste des documents indexés via GET /api/summary/documents
 *   2. L'utilisateur choisit un document et un mode (complet / court / points clés)
 *   3. On envoie POST /api/summary/generate
 *   4. La réponse arrive en streaming SSE → affichage token par token
 *   5. Bouton "Copier" pour copier le résumé dans le presse-papier
 */

// ── Rendu Markdown (identique à chat.js) ─────────────────────────────
function renderMarkdown(text) {
    let html = String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(?!\*)(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/^[*\-] (.+)/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

// ── État ──────────────────────────────────────────────────────────────
let currentMode = 'full';
let fullSummaryText = '';
let allSummaryDocs  = [];  // Cache pour le filtre

// ── Chargement des documents ──────────────────────────────────────────

async function loadDocuments() {
    try {
        const res  = await fetch('/api/summary/documents');
        const data = await res.json();
        allSummaryDocs = data.documents || [];
        renderDocSelect(allSummaryDocs);
    } catch (err) {
        document.getElementById('doc-select').innerHTML =
            `<option value="">Erreur de chargement : ${err.message}</option>`;
    }
}

function renderDocSelect(docs) {
    const select = document.getElementById('doc-select');
    if (docs.length === 0) {
        select.innerHTML = "<option value=\"\">Aucun document indexé — importe-en un ci-dessus</option>";
        return;
    }
    select.innerHTML = '<option value="">— Choisir un document —</option>'
        + docs.map(doc =>
            `<option value="${doc.id}">📄 ${doc.original_name} (${doc.chunks_count} chunks)</option>`
        ).join('');
}

function filterDocs(query) {
    const filtered = allSummaryDocs.filter(d =>
        d.original_name.toLowerCase().includes(query.toLowerCase())
    );
    renderDocSelect(filtered);
}

// ── Sélection du mode ─────────────────────────────────────────────────

function selectMode(mode) {
    currentMode = mode;

    // Met à jour les boutons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
}

// ── Génération du résumé ──────────────────────────────────────────────

async function generateSummary() {
    const docId = parseInt(document.getElementById('doc-select').value);
    if (!docId) {
        alert('Sélectionne d\'abord un document.');
        return;
    }

    const generateBtn  = document.getElementById('generate-btn');
    const resultCard   = document.getElementById('result-card');
    const summaryText  = document.getElementById('summary-text');
    const resultTitle  = document.getElementById('result-title');
    const resultMeta   = document.getElementById('result-meta');
    const copyBtn      = document.getElementById('copy-btn');

    // Nom du document sélectionné
    const select   = document.getElementById('doc-select');
    const docName  = select.options[select.selectedIndex].text.replace('📄 ', '').split(' (')[0];

    // Labels selon le mode
    const modeLabels = { full: 'Résumé complet', short: 'Résumé court', points: 'Points clés' };

    const downloadBtn = document.getElementById('download-btn');

    // Réinitialise l'affichage
    generateBtn.disabled   = true;
    generateBtn.textContent = '⏳ Génération...';
    resultCard.style.display  = 'block';
    resultTitle.textContent   = modeLabels[currentMode] || 'Résumé';
    resultMeta.textContent    = `📄 ${docName}`;
    summaryText.innerHTML     = '';
    summaryText.dataset.raw   = '';
    summaryText.classList.add('streaming');
    copyBtn.style.display     = 'none';
    downloadBtn.style.display = 'none';
    fullSummaryText           = '';

    try {
        const res = await fetch('/api/summary/generate', {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify({ doc_id: docId, mode: currentMode }),
        });

        if (!res.ok) {
            const err = await res.json();
            summaryText.textContent = `❌ ${err.detail || 'Erreur serveur'}`;
            summaryText.classList.remove('streaming');
            return;
        }

        // Lecture du flux SSE
        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6);

                if (data === '[DONE]') {
                    summaryText.classList.remove('streaming');
                    copyBtn.style.display     = 'inline-flex';
                    downloadBtn.style.display = 'inline-flex';
                    break;
                }

                // Accumule les tokens et re-rend le Markdown
                const token = data.replace(/\\n/g, '\n');
                fullSummaryText += token;
                summaryText.innerHTML = renderMarkdown(fullSummaryText);

                // Auto-scroll
                resultCard.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        }

    } catch (err) {
        summaryText.textContent = `❌ Erreur : ${err.message}. Vérifie qu'Ollama est lancé.`;
        summaryText.classList.remove('streaming');
    } finally {
        generateBtn.disabled    = false;
        generateBtn.textContent = '✨ Générer le résumé';
    }
}

// ── Copier dans le presse-papier ──────────────────────────────────────

async function copyToClipboard() {
    if (!fullSummaryText) return;
    try {
        await navigator.clipboard.writeText(fullSummaryText);
        const btn = document.getElementById('copy-btn');
        btn.textContent = '✅ Copié !';
        setTimeout(() => { btn.textContent = '📋 Copier'; }, 2000);
    } catch {
        alert('Impossible de copier. Sélectionne le texte manuellement.');
    }
}

// ── Télécharger en .txt ───────────────────────────────────────────────

function downloadSummary() {
    if (!fullSummaryText) return;

    const select  = document.getElementById('doc-select');
    const docName = select.options[select.selectedIndex]?.text
        .replace('📄 ', '').split(' (')[0] || 'résumé';
    const modeLabels = { full: 'complet', short: 'court', points: 'points-clés' };
    const filename = `résumé_${modeLabels[currentMode] || currentMode}_${docName}.txt`
        .replace(/[^a-zA-Z0-9_\-éèêàùûîïôœç. ]/g, '_');

    const blob = new Blob([fullSummaryText], { type: 'text/plain;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Init ──────────────────────────────────────────────────────────────
loadDocuments();

// Recharge la liste quand un fichier vient d'être indexé via le widget
window.onDocumentIndexed = loadDocuments;
