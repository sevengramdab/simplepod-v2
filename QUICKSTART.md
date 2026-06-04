# SimplePod Unified — User Quickstart

## What Is This?

SimplePod is a **20-node AI swarm** that runs on your computer. Think of it like a team of 20 specialist robots that can:

- Analyze your phone messages for red flags
- Generate smart replies to texts
- Fix broken Python code automatically
- Take screenshots and click buttons for you
- Monitor your computer's health

---

## Start the Server (Do This First)

### Option 1: Desktop Shortcut
Double-click the **"SimplePod Unified"** icon on your desktop.

A PowerShell window opens, the server boots, and your browser auto-opens to `http://127.0.0.1:8000`.

### Option 2: Command Line
```bash
make dev
```

Or manually:
```bash
cd "interfaces/web_ui"
set PYTHONPATH=../..
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**To stop:** Press `Ctrl+C` in the terminal window.

---

## Open the Dashboard

Once the server is running, go to:

```
http://127.0.0.1:8000
```

You'll see the main dashboard with a sidebar. Click around:

| Page | What It Does |
|------|-------------|
| **Dashboard** | Overview of your swarm |
| **OrbitScribe** | Analyze relationships from phone data |
| **Chat** | Talk to the AI swarm |
| **Swarm** | See all 20 workers running |
| **Tools** | All the built-in tools (GitPod, LogMedic, etc.) |

---

## OrbitScribe — Relationship Analysis

This reads fake phone data and tells you what's happening in someone's relationships.

### Web Browser
1. Go to `http://127.0.0.1:8000/orbitscribe`
2. Pick a mode:
   - **Instant Demo** — results in 1 second (fake but realistic)
   - **Auto** — tries real AI first, falls back to instant
   - **Full LLM** — uses your local Ollama (takes 2-5 minutes)
3. Click **"Run Analysis"**

### VS Code Extension
1. Press `Ctrl+Shift+P`
2. Type `OrbitScribe`
3. Select **"OrbitScribe: Relationship Analysis"**
4. Pick a mode
5. Results open in a text document

### Direct Link (Bookmark This)
```
http://127.0.0.1:8000/unified/demo/orbitscribe/report?mode=synthetic
```

---

## VS Code Extension Commands

Press `Ctrl+Shift+P` and type any of these:

| Command | What It Does |
|---------|-------------|
| `SimplePod: Open Control Panel` | Main swarm dashboard |
| `SimplePod: Start Unified Pipeline` | Wake up the 20 workers |
| `SimplePod: Stop Unified Pipeline` | Put workers to sleep |
| `OrbitScribe: Relationship Analysis` | Run relationship analysis |
| `Demo: Analyze Phone Extraction` | Basic phone data report |
| `Demo: Test Free LLM Fallback` | Test AI without signup |

**Status bar:** Look for "SimplePod: Online" at the bottom-left of VS Code.

---

## Android App

The Android app is in `android/SimplePodUnified/`.

### To Build & Install
1. Open `android/SimplePodUnified` in **Android Studio**
2. Click **Run** (green triangle)
3. The app installs on your phone/emulator

### Features
- **Floating ChatHead** — a bubble that floats over any app
- **Conversation Analysis** — reads SMS and finds red flags
- **Reply Generator** — AI suggests replies with tone control
- **Swarm Status** — watch the 20 workers live
- **OrbitScribe** — relationship analysis on your phone

### Backend Connection
- **Emulator:** Already set to `http://10.0.2.2:8000` (works automatically)
- **Real phone:** Change `baseUrl` in `LLMClient.kt` to your PC's WiFi IP

---

## Common Tasks

### Run Tests
```bash
make test
```

### Check Server Health
```bash
curl http://127.0.0.1:8000/health
```

### Run OrbitScribe from Terminal
```bash
simplepod orbitscribe --mode synthetic
```

### Build Everything
```bash
make build
```

### Docker (Run Everything in Containers)
```bash
cp .env.example .env
make docker-run
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Port 8000 already in use" | Kill the old server: `make stop` or restart your PC |
| "Backend not responding" | Make sure Ollama is running: `curl http://127.0.0.1:11434/api/tags` |
| "TypeScript errors" | `cd interfaces/vscode_extension && npx tsc --noEmit` |
| "React won't build" | `cd interfaces/web_ui/frontend && npm install && npm run build` |
| OrbitScribe takes forever | Use `?mode=synthetic` for instant results |
| Desktop shortcut won't open | Right-click → "Run with PowerShell" |

---

## File Cheat Sheet

| File | What It Is |
|------|-----------|
| `QUICKSTART.md` | This file — how to use it |
| `PYPI_SETUP.md` | How to publish to PyPI (developers only) |
| `AGENTS.md` | Coding standards (developers only) |
| `Makefile` | Common commands (`make test`, `make dev`, etc.) |
| `core/unified/orbitscribe_demo.py` | The relationship engine |
| `android/SimplePodUnified/` | Android app source |
| `interfaces/web_ui/frontend/` | React dashboard source |
| `interfaces/vscode_extension/` | VS Code extension source |

---

**Questions?** Check the GitHub repo: https://github.com/sevengramdab/simplepod-v2
