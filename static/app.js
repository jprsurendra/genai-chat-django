const chatBox   = document.getElementById("chatBox");
const form      = document.getElementById("chatForm");
const input     = document.getElementById("userInput");
const sendBtn   = document.getElementById("sendBtn");
const clearBtn  = document.getElementById("clearBtn");
const modelSel  = document.getElementById("modelSelect");
const uploadBtn = document.getElementById("uploadBtn");
const fileUpload = document.getElementById("fileUpload");

let history = [];
let isBusy = false;

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

  try {
    const resp = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history, use_fast: useFast }),
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
          if (data.delta) {
            full += data.delta;
            bubble.innerHTML = renderMarkdown(full);
            chatBox.scrollTop = chatBox.scrollHeight;
          }
        } catch (_) { /* skip malformed chunk */ }
      }
    }

    bubble.classList.remove("typing");

    if (full) {
      history.push({ role: "user",      content: text });
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

// ---- Document upload (PDF / TXT) ----
const ALLOWED_EXT = [".pdf", ".txt"];

uploadBtn.addEventListener("click", () => {
  if (isBusy) return;
  fileUpload.click();
});

fileUpload.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || isBusy) return;

  const name = file.name.toLowerCase();
  if (!ALLOWED_EXT.some((ext) => name.endsWith(ext))) {
    addMessage("assistant", `Only ${ALLOWED_EXT.join(" and ")} files are supported.`);
    fileUpload.value = "";
    return;
  }

  isBusy = true;
  sendBtn.disabled = true;
  uploadBtn.disabled = true;

  addMessage("user", `📎 ${file.name}`);
  const bubble = addMessage("assistant", "Uploading and indexing document...", true);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const resp = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.detail || data.error || `Upload failed (${resp.status})`);

    bubble.classList.remove("typing");
    bubble.innerHTML = renderMarkdown(data.message || "Document uploaded.");
  } catch (err) {
    bubble.classList.remove("typing");
    bubble.classList.add("error");
    bubble.textContent = `Error: ${err.message}`;
  } finally {
    fileUpload.value = "";          // allow re-uploading the same file
    isBusy = false;
    sendBtn.disabled = false;
    uploadBtn.disabled = false;
    input.focus();
  }
});

clearBtn.addEventListener("click", () => {
  if (isBusy) return;
  history = [];
  chatBox.innerHTML = `
    <div class="welcome text-center text-muted py-5">
      <i class="bi bi-chat-dots display-4"></i>
      <p class="mt-2 mb-0">Ask anything to get started.</p>
    </div>`;
  input.focus();
});

input.focus();