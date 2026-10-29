// ==========================================
// 1. DOM Elements
// ==========================================
const chatBox   = document.getElementById("chatBox");
const form      = document.getElementById("chatForm");
const input     = document.getElementById("userInput");
const sendBtn   = document.getElementById("sendBtn");
const clearBtn  = document.getElementById("clearBtn");
const modelSel  = document.getElementById("modelSelect");
const uploadBtn = document.getElementById("uploadBtn");
const fileUpload = document.getElementById("fileUpload");
const logoutBtn = document.getElementById("logoutBtn");
const navUsername = document.getElementById("navUsername");
const historyList = document.getElementById("historyList");
const newChatBtn  = document.getElementById("newChatBtn");

let history = [];
let isBusy = false;
let currentSessionId = null;

// ==========================================
// 2. Authentication (JWT) Check
// ==========================================
const accessToken = localStorage.getItem("access_token");
const username = localStorage.getItem("username");

// If no token, redirect to login page immediately
if (!accessToken) {
    window.location.href = "/login/";
} else {
    if (navUsername) navUsername.textContent = username;
}

// Handle Logout
logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
    window.location.href = "/login/";
});

// Fetch Wrapper to handle token expiration automatically
async function fetchWithAuth(url, options = {}) {
    options.headers = options.headers || {};
    const token = localStorage.getItem("access_token");
    if (token) {
        options.headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, options);

    if (response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("username");
        window.location.href = "/login/";
        throw new Error("Session expired");
    }

    return response;
}

// Helper to get Auth Headers (kept for compatibility)
function getAuthHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("access_token")}`
    };
}

// ==========================================
// 3. UI Helpers
// ==========================================
function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function renderMarkdown(text) {
  try {
    const raw = marked.parse(text, { breaks: true });
    return DOMPurify.sanitize(raw);
  } catch {
    return escapeHtml(text);
  }
}

function clearWelcome() {
  const w = chatBox.querySelector(".welcome");
  if (w) w.remove();
}

function addMessage(role, content, timestamp = null, streaming = false) {
  clearWelcome();
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble" + (streaming ? " typing" : "");

  bubble.innerHTML = role === "user"
    ? escapeHtml(content).replace(/\n/g, "<br>")
    : renderMarkdown(content);

  let timeString = "";
  if (timestamp) {
      const date = new Date(timestamp);
      timeString = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else {
      timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  const timeDiv = document.createElement("div");
  timeDiv.className = "message-time";
  timeDiv.style.fontSize = "0.75rem";
  timeDiv.style.marginTop = "4px";
  timeDiv.style.opacity = "0.7";
  timeDiv.style.textAlign = role === "user" ? "right" : "left";
  timeDiv.textContent = timeString;

  bubble.appendChild(timeDiv);
  wrap.appendChild(bubble);
  chatBox.appendChild(wrap);
  chatBox.scrollTop = chatBox.scrollHeight;

  return bubble;
}

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// ==========================================
// 4. History Management (Sidebar)
// ==========================================
async function loadSidebarHistory() {
    try {
        // Use fetchWithAuth
        const resp = await fetchWithAuth("/api/chat/history");
        if (!resp.ok) return;

        const data = await resp.json();
        historyList.innerHTML = "";

        data.sessions.forEach(session => {
            const item = document.createElement("div");
            item.className = `list-group-item list-group-item-action bg-dark text-white border-secondary d-flex justify-content-between align-items-center ${currentSessionId === session.id ? 'active' : ''}`;
            item.style.cursor = "pointer";

            const titleWrap = document.createElement("span");
            titleWrap.textContent = session.title;
            titleWrap.style.overflow = "hidden";
            titleWrap.style.textOverflow = "ellipsis";
            titleWrap.style.whiteSpace = "nowrap";
            titleWrap.style.flexGrow = "1";

            const actionDiv = document.createElement("div");
            actionDiv.className = "d-flex gap-1";

            const renameBtn = document.createElement("button");
            renameBtn.className = "btn btn-sm btn-outline-light border-0 py-0 px-1";
            renameBtn.innerHTML = '<i class="bi bi-pencil"></i>';
            renameBtn.onclick = async (e) => {
                e.stopPropagation();
                const newTitle = prompt("Enter new chat name:", session.title);
                if (newTitle && newTitle.trim() !== "") {
                    await fetchWithAuth(`/api/chat/history?session_id=${session.id}`, {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ title: newTitle.trim() })
                    });
                    loadSidebarHistory();
                }
            };

            const delBtn = document.createElement("button");
            delBtn.className = "btn btn-sm btn-outline-danger border-0 py-0 px-1";
            delBtn.innerHTML = '<i class="bi bi-trash"></i>';
            delBtn.onclick = async (e) => {
                e.stopPropagation();
                if (confirm("Delete this chat?")) {
                    await fetchWithAuth(`/api/chat/history?session_id=${session.id}`, {
                        method: "DELETE"
                    });
                    if (currentSessionId === session.id) {
                        startNewChat();
                    } else {
                        loadSidebarHistory();
                    }
                }
            };

            actionDiv.appendChild(renameBtn);
            actionDiv.appendChild(delBtn);

            item.appendChild(titleWrap);
            item.appendChild(actionDiv);

            item.onclick = () => loadChatSession(session.id);
            historyList.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to load history:", err);
    }
}

async function loadChatSession(sessionId) {
    try {
        // Use fetchWithAuth
        const resp = await fetchWithAuth(`/api/chat/history?session_id=${sessionId}`);
        if (!resp.ok) return;

        const data = await resp.json();
        currentSessionId = data.id;
        chatBox.innerHTML = "";

        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                addMessage(msg.role, msg.content, msg.created_at);
            });
            history = data.messages.map(m => ({ role: m.role, content: m.content }));
        } else {
            chatBox.innerHTML = `
                <div class="welcome text-center text-muted py-5">
                    <i class="bi bi-chat-dots display-4"></i>
                    <p class="mt-2 mb-0">Ask anything to get started.</p>
                </div>`;
            history = [];
        }

        // Render attached documents for this session
        if (data.documents && data.documents.length > 0) {
            const docWrap = document.createElement("div");
            docWrap.className = "mt-3 p-3 bg-light rounded shadow-sm";
            docWrap.innerHTML = `<h6 class="mb-2"><i class="bi bi-paperclip"></i> Attached Documents:</h6>`;

            data.documents.forEach(doc => {
                const link = document.createElement("a");
                link.href = doc.file;
                link.target = "_blank";
                link.className = "btn btn-sm btn-outline-secondary me-2 mb-2";
                link.innerHTML = `<i class="bi bi-file-earmark-text"></i> ${doc.filename}`;
                docWrap.appendChild(link);
            });

            chatBox.appendChild(docWrap);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        loadSidebarHistory();
    } catch (err) {
        console.error("Failed to load chat:", err);
    }
}

function startNewChat() {
    currentSessionId = null;
    history = [];
    chatBox.innerHTML = `
        <div class="welcome text-center text-muted py-5">
            <i class="bi bi-chat-dots display-4"></i>
            <p class="mt-2 mb-0">Ask anything to get started.</p>
        </div>`;
    loadSidebarHistory();
    input.focus();
}

newChatBtn.addEventListener("click", startNewChat);

// ==========================================
// 5. Chat Submit (Streaming via SSE)
// ==========================================
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (isBusy) return;

  const text = input.value.trim();
  if (!text) return;

  const useFast = modelSel.value === "fast";

  isBusy = true;
  sendBtn.disabled = true;
  input.value = "";
  input.style.height = "auto";

  addMessage("user", text);
  const bubble = addMessage("assistant", "", null, true);

  let full = "";
  let sourcesText = "";

  try {
    // Use fetchWithAuth here as well
    const resp = await fetchWithAuth("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
          message: text,
          history: history.slice(-10),
          use_fast: useFast,
          session_id: currentSessionId
      }),
    });

    if (!resp.ok) {
      const err = await resp.text().catch(() => resp.statusText);
      throw new Error(`${resp.status} ${err}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const payload = part.slice(6).trim();
        if (payload === "[DONE]") continue;

        try {
          const data = JSON.parse(payload);
          if (data.error) throw new Error(data.error);

          if (data.session_id) {
            currentSessionId = data.session_id;
            loadSidebarHistory();
          }

          if (data.sources) {
            sourcesText = data.sources;
          }

          if (data.delta) {
            full += data.delta;
            bubble.innerHTML = renderMarkdown(full);
            chatBox.scrollTop = chatBox.scrollHeight;
          }
        } catch (e) {
            console.error("Error parsing chunk:", e, payload);
        }
      }
    }

    bubble.classList.remove("typing");

    let contentHtml = renderMarkdown(full);

    if (sourcesText) {
      contentHtml += `<div class="mt-2"><small class="text-muted"><i class="bi bi-file-earmark-text"></i> <b>Sources:</b> ${escapeHtml(sourcesText)}</small></div>`;
    }

    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    contentHtml += `<div class="message-time" style="font-size: 0.75rem; margin-top: 4px; opacity: 0.7;">${timeString}</div>`;

    bubble.innerHTML = contentHtml;

    if (full) {
      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: full });
    } else {
      bubble.textContent = "(empty response)";
    }
  } catch (err) {
    bubble.classList.remove("typing");
    bubble.classList.add("error");
    bubble.textContent = `Error: ${err.message}`;
  } finally {
    isBusy = false;
    sendBtn.disabled = false;
    input.focus();
  }
});

// ==========================================
// 6. Document Upload
// ==========================================
uploadBtn.addEventListener("click", () => {
  if (isBusy) return;
  fileUpload.click();
});

fileUpload.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || isBusy) return;

  isBusy = true;
  sendBtn.disabled = true;
  uploadBtn.disabled = true;

  addMessage("user", `📎 ${file.name}`);
  const bubble = addMessage("assistant", "Uploading and indexing document...", null, true);

  try {
    const formData = new FormData();
    formData.append("file", file);

    // Add session_id to formData if we are in an active session
    if (currentSessionId) {
        formData.append("session_id", currentSessionId);
    }

    // Use fetchWithAuth (Note: Don't set Content-Type manually for FormData)
    const resp = await fetchWithAuth("/api/upload", {
      method: "POST",
      body: formData
    });
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
        throw new Error(data.detail || data.error || `Upload failed (${resp.status})`);
    }

    bubble.classList.remove("typing");

    let successHtml = renderMarkdown(data.message || "Document uploaded.");

    // Add Download Link
    if (data.file_url) {
        successHtml += `<div class="mt-2"><a href="${data.file_url}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-download"></i> Download ${data.filename}</a></div>`;
    }

    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    successHtml += `<div class="message-time" style="font-size: 0.75rem; margin-top: 4px; opacity: 0.7;">${timeString}</div>`;
    bubble.innerHTML = successHtml;

  } catch (err) {
    bubble.classList.remove("typing");
    bubble.classList.add("error");
    bubble.textContent = `Error: ${err.message}`;
  } finally {
    fileUpload.value = "";
    isBusy = false;
    sendBtn.disabled = false;
    uploadBtn.disabled = false;
    input.focus();
  }
});

// ==========================================
// 7. Clear Button (Deletes Server Memory)
// ==========================================
clearBtn.addEventListener("click", async () => {
  if (isBusy) return;

  try {
    await fetchWithAuth("/api/chat", {
      method: "DELETE"
    });
  } catch (_) { /* ignore offline errors */ }

  startNewChat();
});

// Load history on page load
loadSidebarHistory();
input.focus();