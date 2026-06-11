/**
 * search.js — Recherche RAG one-shot
 *
 * Fonctionnement :
 *   1. L'utilisateur tape une question et clique sur Rechercher
 *   2. On envoie la question à POST /api/rag/ask
 *   3. Le serveur retourne un flux SSE (Server-Sent Events)
 *   4. On affiche les tokens de réponse au fur et à mesure (streaming)
 *   5. À la fin, on affiche les sources utilisées
 *
 * SSE (Server-Sent Events) = connexion HTTP persistante où le serveur
 * pousse des données vers le client sans que le client rédoive la requête.
 * C'est ce qui donne l'effet "l'IA écrit en direct".
 */

// ── Rendu Markdown ─────────────────────────────────────────────────────
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

const searchInput = document.getElementById('search-input');
const searchBtn   = document.getElementById('search-btn');
const nResults    = document.getElementById('n-results');
const nResultsVal = document.getElementById('n-results-val');
const answerCard  = document.getElementById('answer-card');
const aiResponse  = document.getElementById('ai-response');
const sourcesSection = document.getElementById('sources-section');
const sourcesList    = document.getElementById('sources-list');
const chunksCard     = document.getElementById('chunks-card');
const chunksList     = document.getElementById('chunks-list');

// Synchronise l'affichage du nombre de chunks
nResults.addEventListener('input', () => { nResultsVal.textContent = nResults.value; });

// Soumet aussi avec la touche Entrée
searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') askQuestion();
});

// ── Fonction principale ────────────────────────────────────────────────

async function askQuestion() {
    const query = searchInput.value.trim();
    if (!query) return;

    // Réinitialise l'affichage
    searchBtn.disabled = true;
    searchBtn.textContent = '⏳ Recherche...';
    answerCard.style.display = 'block';
    aiResponse.textContent   = '';
    aiResponse.dataset.raw   = '';
    aiResponse.classList.add('streaming');
    sourcesSection.style.display = 'none';
    chunksCard.style.display     = 'none';
    chunksList.innerHTML         = '';

    try {
        // Appel SSE : POST /api/rag/ask
        const res = await fetch('/api/rag/ask', {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify({ query, n_results: parseInt(nResults.value) }),
        });

        if (!res.ok) {
            aiResponse.textContent = '❌ Erreur serveur. Vérifie qu\'Ollama est en cours d\'exécution.';
            aiResponse.classList.remove('streaming');
            return;
        }

        // Lecture du flux SSE
        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = '';
        let   currentEvent = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                // Ligne d'événement SSE (event: sources / event: context)
                if (line.startsWith('event:')) {
                    currentEvent = line.slice(6).trim();
                    continue;
                }

                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6);

                if (data === '[DONE]') {
                    aiResponse.classList.remove('streaming');
                    break;
                }

                // Événement "sources" → liste des noms de fichiers
                if (currentEvent === 'sources') {
                    try { renderSources(JSON.parse(data)); } catch {}
                    currentEvent = null;
                    continue;
                }

                // Événement "context" → extraits bruts
                if (currentEvent === 'context') {
                    try { renderChunks(JSON.parse(data)); } catch {}
                    currentEvent = null;
                    continue;
                }

                // Token de texte → rendu Markdown en temps réel
                const token = data.replace(/\\n/g, '\n');
                aiResponse.dataset.raw = (aiResponse.dataset.raw || '') + token;
                aiResponse.innerHTML   = renderMarkdown(aiResponse.dataset.raw);
            }
        }

    } catch (err) {
        aiResponse.textContent = `❌ Erreur : ${err.message}`;
        aiResponse.classList.remove('streaming');
    } finally {
        searchBtn.disabled    = false;
        searchBtn.textContent = '🔍 Rechercher';
    }
}

// ── Affichage des sources ──────────────────────────────────────────────

function renderSources(sources) {
    if (!sources || sources.length === 0) return;
    sourcesSection.style.display = 'block';
    sourcesList.innerHTML = sources
        .map(s => `<span class="source-badge">📄 ${s}</span>`)
        .join('');
}

// ── Affichage des extraits bruts ──────────────────────────────────────

function renderChunks(chunks) {
    if (!chunks || chunks.length === 0) return;
    chunksCard.style.display = 'block';
    chunksList.innerHTML = chunks.map((c, i) => `
        <div class="chunk-item">
            <div class="chunk-meta">
                Extrait ${i + 1} — ${c.original_name} (chunk #${c.chunk_index + 1}) — ${c.score_pct}%
            </div>
            ${c.text.substring(0, 500)}${c.text.length > 500 ? '…' : ''}
        </div>
    `).join('');
}
