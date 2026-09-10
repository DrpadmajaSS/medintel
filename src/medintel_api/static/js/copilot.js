/**
 * MedIntel Copilot ("Ask MedIntel") Sidebar Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const minBtn = document.getElementById('btn-minimize-copilot');
  const panel = document.getElementById('copilot-panel');

  if (minBtn && panel) {
    minBtn.addEventListener('click', () => {
      panel.classList.toggle('active-drawer');
    });
  }
});

async function handleCopilotSubmit() {
  const input = document.getElementById('copilot-input');
  if (!input) return;
  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = '';
  await sendCopilotQuery(prompt);
}

// Conversation State Tracking for Contextual Follow-ups
let copilotHistory = [];
let currentContextMedicationId = null;

async function sendCopilotQuery(prompt) {
  const panel = document.getElementById('copilot-panel');
  if (panel && window.innerWidth <= 1120) {
    panel.classList.add('active-drawer');
  }

  const container = document.getElementById('copilot-messages-container');
  if (!container) return;

  // Append user message
  const userMsgEl = document.createElement('div');
  userMsgEl.className = 'chat-bubble-msg msg-user';
  userMsgEl.textContent = prompt;
  container.appendChild(userMsgEl);
  container.scrollTop = container.scrollHeight;

  // Append loading indicator
  const loadingEl = document.createElement('div');
  loadingEl.className = 'chat-bubble-msg msg-assistant';
  loadingEl.innerHTML = `<span class="text-muted"><i data-lucide="loader" class="rotating"></i> Consulting MedIntel intelligence engine...</span>`;
  container.appendChild(loadingEl);
  if (window.lucide) lucide.createIcons();
  container.scrollTop = container.scrollHeight;

  try {
    const payload = {
      prompt: prompt,
      conversation_history: copilotHistory.slice(-6),
      focused_medication_id: state.selectedMedDetail ? state.selectedMedDetail.medication_id : null,
      focused_location_id: state.currentModalFacility ? state.currentModalFacility.location_id : (state.currentFacility || null),
      context_medication_id: currentContextMedicationId || (state.selectedMedDetail ? state.selectedMedDetail.medication_id : null)
    };

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    loadingEl.remove();

    // Update contextual medication tracking
    if (data.mentioned_medication_id) {
      currentContextMedicationId = data.mentioned_medication_id;
    }
    copilotHistory.push({ role: 'user', content: prompt });
    copilotHistory.push({ role: 'assistant', content: data.response });

    // Render tool badges if tools were used
    let toolsHtml = '';
    if (data.tools_used && data.tools_used.length > 0) {
      toolsHtml = `
        <div style="margin-bottom: 0.35rem; display: flex; gap: 0.3rem; flex-wrap: wrap;">
          ${data.tools_used.map(t => `<span class="badge badge-primary" style="font-size: 0.65rem;">⚙️ ${t.tool_name}</span>`).join('')}
        </div>
      `;
    }

    // Format markdown text simply
    const formattedContent = parseMarkdown(data.response);

    const assistantMsgEl = document.createElement('div');
    assistantMsgEl.className = 'chat-bubble-msg msg-assistant';
    assistantMsgEl.innerHTML = `
      ${toolsHtml}
      ${formattedContent}
    `;
    container.appendChild(assistantMsgEl);
    if (window.lucide) lucide.createIcons();
    container.scrollTop = container.scrollHeight;

  } catch (err) {
    loadingEl.remove();
    const errorEl = document.createElement('div');
    errorEl.className = 'chat-bubble-msg msg-assistant';
    errorEl.innerHTML = `<span style="color: var(--color-act);">Error connecting to MedIntel Copilot. Please try again.</span>`;
    container.appendChild(errorEl);
  }
}

function parseMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/^### (.*$)/gim, '<h4 style="font-size:0.85rem; font-weight:700; margin:0.3rem 0 0.15rem;">$1</h4>')
    .replace(/^#### (.*$)/gim, '<h5 style="font-size:0.78rem; font-weight:700; margin:0.25rem 0 0.15rem;">$1</h5>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/^> (.*$)/gim, '<blockquote style="border-left: 2.5px solid var(--primary-blue); padding-left: 0.45rem; margin: 0.3rem 0; font-style: italic;">$1</blockquote>')
    .replace(/^\- (.*$)/gim, '<li style="margin-left: 1rem;">$1</li>')
    .replace(/\n\n/gim, '<p style="margin-bottom:0.25rem;"></p>')
    .replace(/\n/gim, '<br>');
  return html;
}
