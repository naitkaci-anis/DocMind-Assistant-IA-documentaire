/**
 * chat.js — Interface de chat premium v4
 * Structure : conv-panel (gauche) + chat-core (droite)
 */

let currentConvId = null;

/* ── DOM refs ──────────────────────────────────────────────────── */
const convList     = document.getElementById('conv-list');
const newConvBtn   = document.getElementById('new-conv-btn');
const chatEmpty    = document.getElementById('chat-empty');
const messagesArea = document.getElementById('messages-area');
const chatInput    = document.getElementById('chat-input');
const sendBtn      = document.getElementById('send-btn');
const attachBtn    = document.getElementById('attach-btn');
const fileInput    = document.getElementById('chat-file-input');
const uploadStatus = document.getElementById('chat-upload-status');
const uploadLabel  = document.getElementById('chat-upload-label');

/* ── Username initial (for user avatar) ────────────────────────── */
const _uname = document.querySelector('.user-name')?.textContent?.trim() || '?';
const _uInitial = _uname[0].toUpperCase();

/* ══════════════════════════════════════════════════════════════════
   MARKDOWN RENDERER — rich formatting
   ══════════════════════════════════════════════════════════════════ */
function renderMarkdown(raw) {
    let t = String(raw)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Fenced code blocks
    t = t.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
        `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`);

    // Inline code
    t = t.replace(/`([^`\n]+)`/g,
        '<code>$1</code>');

    // Headers (###, ##, #)
    t = t.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    t = t.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
    t = t.replace(/^# (.+)$/gm,   '<h1>$1</h1>');

    // Horizontal rule
    t = t.replace(/^---+$/gm, '<hr>');

    // Bold **text**
    t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    t = t.replace(/\*(?!\*)(.+?)\*/g, '<em>$1</em>');

    // Blockquote
    t = t.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

    // Ordered lists: 1. item
    t = t.replace(/^(\d+\. .+(\n\d+\. .+)*)/gm, block => {
        const items = block.replace(/^\d+\. (.+)/gm, '<li>$1</li>');
        return `<ol>${items}</ol>`;
    });

    // Unordered lists: - item or * item
    t = t.replace(/^([*\-] .+(\n[*\-] .+)*)/gm, block => {
        const items = block.replace(/^[*\-] (.+)/gm, '<li>$1</li>');
        return `<ul>${items}</ul>`;
    });

    // Paragraphs — split on double newlines
    const parts = t.split(/\n{2,}/);
    t = parts.map(p => {
        p = p.trim();
        if (!p) return '';
        if (/^<(h[1-6]|ul|ol|pre|hr|blockquote)/.test(p)) return p;
        return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
    }).join('\n');

    return t;
}

/* ══════════════════════════════════════════════════════════════════
   HTML BUILDERS
   ══════════════════════════════════════════════════════════════════ */

/* Source badge SVG */
const fileSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>`;

function buildSourcesHtml(sources) {
    if (!sources || sources.length === 0) return '';
    return `
        <div class="ai-srcs">
            <span class="ai-srcs-lbl">Sources</span>
            ${sources.map(s => `<span class="src-badge">${fileSvg}${escapeHtml(s)}</span>`).join('')}
        </div>`;
}

function buildAiCard(content, sources = [], streaming = false) {
    return `
        <div class="mrow assistant">
            <div class="mav ai-av">🧠</div>
            <div class="ai-card">
                <div class="ai-hdr">
                    <span class="ai-hdr-name">DocMind AI</span>
                    <span class="ai-hdr-badge"><span class="ai-dot"></span>IA</span>
                </div>
                <div class="ai-body${streaming ? ' streaming' : ''}" ${streaming ? 'id="streaming-bubble"' : ''}>
                    ${streaming ? '' : renderMarkdown(content)}
                </div>
                ${streaming ? '' : buildSourcesHtml(sources)}
            </div>
        </div>`;
}

function buildUserMsg(content) {
    return `
        <div class="mrow user">
            <div class="usr-bubble">${escapeHtml(content)}</div>
            <div class="mav usr-av">${_uInitial}</div>
        </div>`;
}

function buildSystemMsg(text) {
    return `<div class="sys-msg">${renderMarkdown(text)}</div>`;
}

/* Conversation card */
function buildConvCard(conv) {
    const active  = conv.id === currentConvId ? 'active' : '';
    const time    = formatTime(conv.created_at || '');
    const preview = escapeHtml(conv.preview || '');
    return `
        <div class="cc-card ${active}" id="cc-card-${conv.id}"
             onclick="selectConversation(${conv.id})"
             ondblclick="startRenameConv(event, ${conv.id}, this)">
            <div class="cc-icon">💬</div>
            <div class="cc-body">
                <div class="cc-title">${escapeHtml(conv.title)}</div>
                <div class="cc-preview">${preview || 'Pas encore de messages'}</div>
            </div>
            <div class="cc-meta">
                <span class="cc-time">${time}</span>
                <button class="cc-del"
                        onclick="event.stopPropagation();deleteConversation(${conv.id})"
                        title="Supprimer">✕</button>
            </div>
        </div>`;
}

/* ══════════════════════════════════════════════════════════════════
   CONVERSATIONS
   ══════════════════════════════════════════════════════════════════ */

async function loadConversations() {
    try {
        const res  = await fetch('/api/chat/conversations');
        const data = await res.json();
        renderConvList(data.conversations || []);
    } catch {
        if (convList) convList.innerHTML = '<div style="padding:.5rem;font-size:.78rem;color:var(--red-text)">Erreur de chargement</div>';
    }
}

function renderConvList(conversations) {
    if (!convList) return;
    if (conversations.length === 0) {
        convList.innerHTML = '<div style="padding:.5rem;font-size:.78rem;color:var(--text-faint)">Aucune conversation</div>';
        return;
    }
    convList.innerHTML = conversations.map(buildConvCard).join('');
}

async function createConversation() {
    const res  = await fetch('/api/chat/conversations', {
        method : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body   : JSON.stringify({}),
    });
    const conv = await res.json();
    currentConvId = conv.id;
    await loadConversations();
    await selectConversation(conv.id);
    chatInput?.focus();
}

async function deleteConversation(convId) {
    if (!confirm('Supprimer cette conversation ?')) return;
    await fetch(`/api/chat/conversations/${convId}`, { method: 'DELETE' });
    if (currentConvId === convId) {
        currentConvId = null;
        showChatEmpty();
    }
    loadConversations();
}

async function startRenameConv(e, convId, cardEl) {
    e.stopPropagation();
    const titleEl = cardEl.querySelector('.cc-title');
    const old     = titleEl.textContent;
    titleEl.style.display = 'none';

    const inp = document.createElement('input');
    inp.type = 'text'; inp.value = old; inp.className = 'cc-rename';
    cardEl.querySelector('.cc-body').insertBefore(inp, titleEl);
    inp.focus(); inp.select();

    async function commit() {
        const val = inp.value.trim() || old;
        inp.remove(); titleEl.style.display = '';
        if (val === old) return;
        titleEl.textContent = val;
        await fetch(`/api/chat/conversations/${convId}`, {
            method : 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify({ title: val }),
        });
    }
    inp.addEventListener('blur', commit);
    inp.addEventListener('keydown', e => {
        if (e.key === 'Enter')  { e.preventDefault(); inp.blur(); }
        if (e.key === 'Escape') { inp.value = old; inp.blur(); }
    });
}

async function selectConversation(convId) {
    currentConvId = convId;

    document.querySelectorAll('.cc-card').forEach(el => {
        el.classList.toggle('active', el.id === `cc-card-${convId}`);
    });

    showMessages();
    messagesArea.innerHTML = '<div class="sys-msg" style="align-self:center">⏳ Chargement…</div>';

    try {
        const res  = await fetch(`/api/chat/conversations/${convId}/messages`);
        const data = await res.json();
        renderMessages(data.messages || []);
    } catch {
        messagesArea.innerHTML = '<div class="sys-msg" style="color:var(--red-text)">❌ Erreur de chargement</div>';
    }
}

/* ══════════════════════════════════════════════════════════════════
   MESSAGES
   ══════════════════════════════════════════════════════════════════ */

function renderMessages(messages) {
    const visible = messages.filter(m => m.content?.trim());
    if (visible.length === 0) {
        messagesArea.innerHTML = '<div class="sys-msg" style="align-self:center;opacity:.5">💬 Pose ta première question !</div>';
        return;
    }
    messagesArea.innerHTML = visible.map(m =>
        m.role === 'user'
            ? buildUserMsg(m.content)
            : buildAiCard(m.content, m.sources || [])
    ).join('');
    scrollToBottom();
}

function appendMessage(role, content, sources = []) {
    const empty = messagesArea.querySelector('.sys-msg');
    if (empty?.style.opacity === '0.5') empty.remove();

    const div = document.createElement('div');
    div.innerHTML = role === 'user'
        ? buildUserMsg(content)
        : buildAiCard(content, sources);
    messagesArea.appendChild(div.firstElementChild);
    scrollToBottom();
}

/* ══════════════════════════════════════════════════════════════════
   SEND — SSE streaming
   ══════════════════════════════════════════════════════════════════ */

async function sendMessage() {
    const content = chatInput.value.trim();
    if (!content) return;
    if (!currentConvId) await createConversation();

    chatInput.value = '';
    chatInput.style.height = 'auto';
    appendMessage('user', content);

    sendBtn.disabled   = true;
    chatInput.disabled = true;

    // Streaming AI card
    const wrapper = document.createElement('div');
    wrapper.innerHTML = buildAiCard('', [], true);
    const rowEl  = wrapper.firstElementChild;
    messagesArea.appendChild(rowEl);
    scrollToBottom();

    const bubble   = rowEl.querySelector('#streaming-bubble');
    let fullText   = '';
    let sources    = [];

    try {
        const res = await fetch(`/api/chat/conversations/${currentConvId}/messages`, {
            method : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body   : JSON.stringify({ content, n_results: 5 }),
        });

        if (!res.ok) {
            bubble.textContent = '❌ Erreur serveur. Vérifie qu\'Ollama est lancé.';
            bubble.classList.remove('streaming');
            return;
        }

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let   buffer  = '';
        let   done    = false;
        let   event   = null;

        while (!done) {
            const { done: d, value } = await reader.read();
            if (d) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('event:')) { event = line.slice(6).trim(); continue; }
                if (!line.startsWith('data: ')) continue;

                const data = line.slice(6);
                if (data === '[DONE]') {
                    done = true;
                    bubble.classList.remove('streaming');
                    bubble.removeAttribute('id');
                    // Inject sources
                    if (sources.length > 0) {
                        const srcEl = document.createElement('div');
                        srcEl.innerHTML = buildSourcesHtml(sources);
                        rowEl.querySelector('.ai-card').appendChild(srcEl.firstElementChild);
                    }
                    break;
                }
                if (event === 'sources') {
                    try { sources = JSON.parse(data); } catch {}
                    event = null; continue;
                }

                fullText += data.replace(/\\n/g, '\n');
                bubble.innerHTML = renderMarkdown(fullText);
                scrollToBottom(true);
            }
        }

    } catch (err) {
        bubble.innerHTML = `❌ Erreur : ${escapeHtml(err.message)}`;
        bubble.classList.remove('streaming');
    } finally {
        sendBtn.disabled   = false;
        chatInput.disabled = false;
        chatInput.focus();
        loadConversations();
    }
}

/* ══════════════════════════════════════════════════════════════════
   FILE UPLOAD IN CHAT
   ══════════════════════════════════════════════════════════════════ */

attachBtn?.addEventListener('click', () => fileInput?.click());

fileInput?.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    fileInput.value = '';
    await uploadFileToChat(file);
});

async function uploadFileToChat(file) {
    uploadLabel.textContent = `⏳ Upload de ${file.name}…`;
    uploadStatus.style.display = 'flex';

    const fd = new FormData();
    fd.append('file', file);

    try {
        const res  = await fetch('/api/upload/', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) { uploadLabel.textContent = `❌ ${data.detail || 'Erreur'}`; return; }

        uploadLabel.textContent = `⏳ Indexation de ${file.name}…`;

        for (let i = 0; i < 30; i++) {
            await sleep(2000);
            const sr   = await fetch(`/api/upload/${data.doc_id}/status`);
            const info = await sr.json();
            if (info.status === 'indexed') {
                uploadLabel.textContent = `✅ ${file.name} indexé (${info.chunks_count} chunks)`;
                if (currentConvId) {
                    const div = document.createElement('div');
                    div.innerHTML = buildSystemMsg(`📄 **${file.name}** indexé avec succès — tu peux maintenant poser des questions dessus.`);
                    messagesArea?.appendChild(div.firstElementChild);
                    scrollToBottom();
                }
                return;
            }
            if (info.status === 'error') { uploadLabel.textContent = `❌ Erreur d'indexation`; return; }
        }
        uploadLabel.textContent = `⏱ Timeout — indexation trop lente`;

    } catch (err) {
        uploadLabel.textContent = `❌ Erreur réseau : ${err.message}`;
    }
}

function cancelUploadStatus() {
    if (uploadStatus) uploadStatus.style.display = 'none';
}

/* ══════════════════════════════════════════════════════════════════
   UTILS
   ══════════════════════════════════════════════════════════════════ */

function showMessages() {
    if (chatEmpty)    chatEmpty.style.display    = 'none';
    if (messagesArea) messagesArea.style.display = 'flex';
}
function showChatEmpty() {
    if (chatEmpty)    chatEmpty.style.display    = 'flex';
    if (messagesArea) messagesArea.style.display = 'none';
}

function scrollToBottom(smooth = false) {
    if (!messagesArea) return;
    messagesArea.scrollTo({ top: messagesArea.scrollHeight, behavior: smooth ? 'smooth' : 'instant' });
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    try {
        const d    = new Date(dateStr.includes('T') ? dateStr : dateStr + 'Z');
        const now  = new Date();
        const diff = now - d;
        if (diff < 60000)    return 'maintenant';
        if (diff < 3600000)  return `${Math.floor(diff / 60000)}m`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
        return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    } catch { return ''; }
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ══════════════════════════════════════════════════════════════════
   EVENTS
   ══════════════════════════════════════════════════════════════════ */

newConvBtn?.addEventListener('click', createConversation);
sendBtn?.addEventListener('click', sendMessage);

chatInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

chatInput?.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
});

/* ── Init ─────────────────────────────────────────────────────── */
loadConversations();
