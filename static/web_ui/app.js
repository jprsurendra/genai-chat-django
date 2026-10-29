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

let history = [];
let isBusy = false;

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

// Helper to get Auth Headers for API requests
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

function addMessage(role, content, streaming = false) {
  clearWelcome();
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble" + (streaming ? " typing" : "");
  bubble.innerHTML = role === "user"
    ? escapeHtml(content).replace(/\n/g, "<br>")
    : renderMarkdown(content);
  wrap.appendChild(bubble);
  chatBox.appendChild(wrap);
  chatBox.scrollTop = chatBox.scrollHeight;
  return bubble;
}

// Auto-resize textarea
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
// 4. Chat Submit (Streaming via SSE)
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
  const bubble = addMessage("assistant", "", true);
  let full = "";
  let sourcesText = "";

  try {
    const resp = await fetch("/api/chat/stream", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ message: text, history: history.slice(-10), use_fast: useFast }),
    });

    if (!resp.ok) {
      if (resp.status === 401) {
         window.location.href = "/login/"; // Token expired
         return;
      }
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

          // Capture Sources
          if (data.sources) {
            sourcesText = data.sources;
          }

          // Stream Text
          if (data.delta) {
            full += data.delta;
            bubble.innerHTML = renderMarkdown(full);
            chatBox.scrollTop = chatBox.scrollHeight;
          }
        } catch (_) { /* skip malformed chunk */ }
      }
    }

    bubble.classList.remove("typing");

    // Append Sources if any
    if (sourcesText) {
      const sourceDiv = document.createElement("div");
      sourceDiv.className = "mt-2";
      sourceDiv.innerHTML = `<small class="text-muted"><i class="bi bi-file-earmark-text"></i> <b>Sources:</b> ${escapeHtml(sourcesText)}</small>`;
      bubble.appendChild(sourceDiv);
    }

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
// 5. Document Upload
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
  const bubble = addMessage("assistant", "Uploading and indexing document...", true);

  try {
    const formData = new FormData();
    formData.append("file", file);

    // Note: Don't use getAuthHeaders() here because it sets 'Content-Type': 'application/json'
    // For FormData, the browser must set the Content-Type automatically (multipart/form-data)
    const resp = await fetch("/api/upload", {
      method: "POST",
      headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
      },
      body: formData
    });
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
        if (resp.status === 401) window.location.href = "/login/";
        throw new Error(data.detail || data.error || `Upload failed (${resp.status})`);
    }

    bubble.classList.remove("typing");
    bubble.innerHTML = renderMarkdown(data.message || "Document uploaded.");
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
// 6. Clear Button (Deletes Server Memory)
// ==========================================
clearBtn.addEventListener("click", async () => {
  if (isBusy) return;

  try {
    await fetch("/api/chat", {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
    });
  } catch (_) { /* ignore offline errors */ }

  history = [];
  chatBox.innerHTML = `
    <div class="welcome text-center text-muted py-5">
      <i class="bi bi-chat-dots display-4"></i>
      <p class="mt-2 mb-0">Ask anything to get started.</p>
    </div>`;
  input.focus();
});

input.focus();