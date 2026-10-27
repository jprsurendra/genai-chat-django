# GenAI Chat 🚀 (Django + DRF)

A minimal, fully local **GenAI chat application** built with **Django**, **Django REST Framework (APIView)**, **Bootstrap 5**, and **Ollama** (LLM runtime).

Runs entirely on your machine — no cloud, no API keys, no cost.

---

## ✨ Features

- 📡 **Streaming responses** via Server-Sent Events (SSE) — tokens appear one by one using true ASGI streaming.
- 💬 **Multi-turn memory** — last 10 turns of history are sent with each request.
- 🎨 **Markdown + code block rendering** — with DOMPurify XSS sanitization.
- 🔀 **Dual-model selector** — swap between a fast and a quality model per message.
- 🛡️ **Per-IP rate limiting** — 20 requests / 60 seconds.
- 🔒 **Env-driven config** — swap LLM provider without code changes.
- 🧱 **Isolated virtualenv** — outside the repo, one venv per app.
- 🐍 **Python 3.14 compatible** — pinned to versions with prebuilt wheels.

---

## 🧰 Tech Stack

| Layer        | Choice                  | Why                                                    |
|--------------|-------------------------|--------------------------------------------------------|
| Backend      | Django 5.x + DRF        | Async views, native ASGI support, class-based APIViews |
| Server       | Uvicorn                 | ASGI server required for true token streaming          |
| LLM runtime  | Ollama                  | Local, free, no API key                                |
| LLM client   | `openai` SDK ≥ 2.7.2    | Ollama exposes OpenAI-compatible `/v1`                 |
| Validation   | pydantic ≥ 2.13         | Python 3.14 wheels available                           |
| Config       | python-dotenv           | Simple `.env` loading                                  |
| Frontend     | Bootstrap 5 + vanilla JS| No build step, CDN-only                                |
| Static Files | WhiteNoise              | Serves CSS/JS under Uvicorn/ASGI seamlessly            |

---

## 📋 Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Project Layout](#2-project-layout)
3. [Installation & VS Code Setup](#3-installation--vs-code-setup)
4. [Ollama Setup (Crucial)](#4-ollama-setup-crucial)
5. [Configuration (.env)](#5-configuration-env)
6. [Running the App](#6-running-the-app)
7. [VS Code Debugging (launch.json)](#7-vs-code-debugging-launchjson)
8. [Daily Workflow Shortcut](#8-daily-workflow-shortcut)
9. [Smoke Tests](#9-smoke-tests)
10. [API Reference](#10-api-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [Design Decisions](#12-design-decisions)

---

## 1. System Requirements

**Tested environment** (all commands below are verified on this exact setup):

| Item   | Value                                       |
|--------|---------------------------------------------|
| OS     | Ubuntu 26.04.1 LTS (also works on macOS, WSL2) |
| Python | **3.14.4** (min 3.10)                       |
| VS Code| Latest with Python & GitLens extensions     |
| Ollama | Latest (running on `:11434`)                |

---

## 2. Project Layout

```text
/home/ssr/projects/GenAI/
├── genai-chat-django/                # ← this repo
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                          # local secrets — never commit
│   ├── .gitignore
│   ├── README.md
│   ├── config/                       # Django project settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── asgi.py                   # entry point for Uvicorn
│   ├── chat/                         # Django app
│   │   ├── views.py                  # APIView classes & streaming logic
│   │   ├── llm.py                    # provider-agnostic LLM wrapper
│   │   ├── schemas.py                # Pydantic request/response models
│   │   ├── ratelimit.py              # in-memory rate limiter
│   │   └── urls.py
│   ├── templates/
│   │   └── chat/
│   │       └── index.html            # Bootstrap layout
│   └── static/
│       ├── style.css                 # chat bubbles, code blocks
│       └── app.js                    # SSE consumer + markdown renderer
└── environments/
    └── .venv-genai-chat-django/      # virtualenv lives OUTSIDE the repo
```

> 💡 **Why is the venv outside the repo?**
> Cleaner git tree, no `.gitignore` pitfalls, and it lets you host **multiple app venvs under one `environments/` root**.

---

## 3. Installation & VS Code Setup

### Step 1: Install VS Code Extensions

1. Open VS Code and click the **Extensions** icon (four squares) on the left sidebar.
2. Search for **Python** (by Microsoft) and click **Install**.
3. Search for **GitLens** (by GitKraken) and click **Install** (optional but recommended).

### Step 2: Create Project Directory & Virtual Environment

Open your terminal in VS Code (`` Ctrl + ` ``) and run:

```bash
# Create project folder
mkdir -p /home/ssr/projects/GenAI/genai-chat-django
cd /home/ssr/projects/GenAI/genai-chat-django

# Create the virtual environment OUTSIDE the project folder
python3 -m venv /home/ssr/projects/GenAI/environments/.venv-genai-chat-django

# Activate the virtual environment
source /home/ssr/projects/GenAI/environments/.venv-genai-chat-django/bin/activate
```

> You should see `(.venv-genai-chat-django)` at the start of your terminal prompt.

### Step 3: Select Interpreter in VS Code

1. Press `Ctrl + Shift + P` and type **Python: Select Interpreter**.
2. Choose **Enter interpreter path...** and paste:

```text
/home/ssr/projects/GenAI/environments/.venv-genai-chat-django/bin/python
```

### Step 4: Install Dependencies

```bash
pip install django djangorestframework openai python-dotenv pydantic uvicorn whitenoise
```

### Step 5: Create Django Project Structure

```bash
# Create the project ('config') in the current directory (notice the dot)
django-admin startproject config .

# Create the app ('chat')
python manage.py startapp chat
```

---

## 4. Ollama Setup (Crucial)

Since this app runs 100% locally, you must have Ollama installed and running.

### Install and Start Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

> On macOS, the Ollama.app starts the daemon automatically.

Verify the daemon:

```bash
curl http://localhost:11434/
# → "Ollama is running"
```

### Pull the Required Models

```bash
ollama pull llama3.2:1b          # 1.3 GB — quality model
ollama pull qwen2.5:1.5b         # 986 MB — fast model
```

Verify:

```bash
ollama list
```

> **Optional — better quality model.** If your machine has ≥ 8 GiB free RAM, run `ollama pull llama3.1:8b` (4.7 GB) for noticeably better answers, then set `OLLAMA_MODEL=llama3.1:8b` in `.env`.

---

## 5. Configuration (.env)

Create a file named `.env` in the project root (`/home/ssr/projects/GenAI/genai-chat-django/.env`) and add the following:

```env
# ---- LLM Provider ----
# 'ollama' (default, local, free) or 'openai' (cloud, paid)
LLM_PROVIDER=ollama

# ---- Ollama settings ----
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2:1b
OLLAMA_MODEL_FAST=qwen2.5:1.5b

# ---- OpenAI settings (only used if LLM_PROVIDER=openai) ----
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

> ⚠️ **Never commit `.env`.** Ensure your `.gitignore` contains:

```gitignore
.venv/
__pycache__/
*.pyc
.env
db.sqlite3
```

---

## 6. Running the App

Because we use SSE (Server-Sent Events) for token streaming, you must run Django using **Uvicorn (ASGI)** instead of Django's default `runserver`.

```bash
# Make sure the venv is active, then run:
uvicorn config.asgi:application --reload --port 8000
```

Open in browser:

| URL                            | Purpose      |
|--------------------------------|--------------|
| http://127.0.0.1:8000          | Chat UI      |
| http://127.0.0.1:8000/health   | Health check |

---

### ⚠️ Common Error: `Hop-by-hop header` (500 on `/api/chat/stream`)

If you see this in the terminal:

```text
AssertionError: Hop-by-hop header, 'Connection: keep-alive', not allowed
[27/Oct/2026 06:21:29] "POST /api/chat/stream HTTP/1.1" 500 59
```

**Root cause**

You are running the server with **WSGI** (Django's default `runserver`) instead of **ASGI** (Uvicorn).

- Django's WSGI server (built on `wsgiref`) does not allow *hop-by-hop* headers such as `Connection: keep-alive`.
- `ChatStreamAPIView` sets this header for SSE streaming, so the WSGI server rejects it and returns a `500 Internal Server Error`.

**Fix**

1. Stop the server with `Ctrl + C`.
2. Start it again using Uvicorn:

```bash
uvicorn config.asgi:application --reload --port 8000
```

> 💡 This project uses Uvicorn for streaming (SSE) by design — never use `python manage.py runserver` for this app.

---

## 7. VS Code Debugging (launch.json)

To debug with breakpoints without typing the terminal command every time:

1. Go to the **Run and Debug** view (`Ctrl + Shift + D`).
2. Click **create a launch.json file** and select **Python Debugger > Django**.
3. Replace the generated configuration with this ASGI-compatible one:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Uvicorn (ASGI)",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "config.asgi:application",
                "--reload",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

4. Press `F5` to start debugging. You can now add breakpoints in `chat/views.py`.

---

## 8. Daily Workflow Shortcut

Tired of typing the full `source` command and `cd` path every day? Add a bash alias.

Open `~/.bashrc` and add this line at the bottom:

```bash
alias genai='source /home/ssr/projects/GenAI/environments/.venv-genai-chat-django/bin/activate && cd /home/ssr/projects/GenAI/genai-chat-django'
```

Reload your bash profile:

```bash
source ~/.bashrc
```

Now, every time you open a new terminal, just type:

```bash
genai
uvicorn config.asgi:application --reload
```

---

## 9. Smoke Tests

Run these once to verify every layer end-to-end.

### HTTP Endpoint Tests

With Uvicorn running, open a second terminal:

**Health check**

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

**Non-streaming chat (APIView)**

```bash
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Say hi in 3 words","history":[],"use_fast":true}' \
  | python3 -m json.tool
```

**Streaming SSE** (watch tokens arrive individually, then `[DONE]`)

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Count 1 to 5","history":[],"use_fast":true}'
```

### End-to-End UI Test

1. Open the browser at http://127.0.0.1:8000.
2. Type: `Hi! My name is Sam. What's 2+2?`
3. Follow-up: `What's my name?` → should reply with **Sam**.
4. Toggle the model dropdown in the navbar.
5. Click **🗑 Clear** → chat resets.

---

## 10. API Reference

### `POST /api/chat` — non-streaming

**Request:**

```json
{
  "message": "Explain Python decorators",
  "history": [],
  "use_fast": false
}
```

**Response:**

```json
{ "reply": "Decorators are..." }
```

### `POST /api/chat/stream` — streaming (SSE)

Response is `text/event-stream`:

```text
data: {"delta":"Deco"}
data: {"delta":"rators"}
data: [DONE]
```

### `GET /health`

```json
{ "status": "ok", "provider": "ollama", "model": "llama3.2:1b" }
```

### Rate limiting

- **20 requests / 60 seconds** per IP.
- Exceeding the limit returns `429 Too Many Requests`.
- In-memory only (resets on Uvicorn restart). Bump `RATE_LIMIT` in `chat/utilities/ratelimit.py` for local testing.

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `LookupError: No installed app with label 'admin'` | Django default `urls.py` included admin | Remove `path('admin/', ...)` from `config/urls.py` |
| `404 Not Found` for `/static/style.css` | Uvicorn doesn't serve static files | Install `whitenoise` and add it to `MIDDLEWARE` |
| Browser shows `{"message":"..."}` | Index HTML not rendering | Ensure `chat/views.py` returns `render(request, "chat/index.html")` |
| `ModuleNotFoundError: app` | Wrong working directory | `cd /home/ssr/projects/GenAI/genai-chat-django` before running Uvicorn |
| `pip install` fails on build | Python 3.14 missing wheels | Use pinned versions: `pydantic>=2.13` and `openai>=2.7.2` |
| Ollama connection refused | Daemon not running | `ollama serve &` or `sudo systemctl start ollama` |
| First call takes 10–20 s | Model cold start on CPU | Normal; subsequent calls are fast |
| `429 Too Many Requests` | Rate limit hit during tests | Restart Uvicorn or bump `RATE_LIMIT` |
| Streaming appears all at once | Using WSGI instead of ASGI | Must run `uvicorn config.asgi:application` |
| `AssertionError: Hop-by-hop header` (500 on `/api/chat/stream`) | Server started with `runserver` (WSGI) | Stop it and run `uvicorn config.asgi:application --reload --port 8000` (see [Section 6](#6-running-the-app)) |

---

## 12. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Django `APIView` | Cleaner separation of GET/POST, per-method rate limiting, and easier to extend (auth, throttling) later. |
| Uvicorn over `runserver` | Django's `runserver` buffers streaming. Uvicorn natively supports true ASGI token-by-token streaming. |
| WhiteNoise | Allows Uvicorn to serve CSS/JS safely without configuring Nginx. |
| Pydantic + DRF | DRF handles routing/requests. Pydantic validates the nested `history` list and enforces `max_length=4000`. |
| Ollama as default LLM | $0 cost, 100% local, no API key, no data leaves the machine. |
| OpenAI SDK as client | Ollama exposes an OpenAI-compatible `/v1` endpoint — one client, two providers. |
| venv outside repo | Clean git tree; supports multiple app venvs under `environments/`. |
| In-memory rate limiter | Zero deps; swap for Redis when scaling beyond one process. |

---

## 📜 License

MIT — use it, fork it, ship it. No warranty.

---


*Last verified: Ubuntu 26.04.1 · Python 3.14.4 · Django 5.x · openai 3.x · pydantic 2.14.x · Ollama (llama3.2:1b + qwen2.5:1.5b)*