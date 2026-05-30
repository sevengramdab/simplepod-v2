import * as vscode from 'vscode';
import { SwarmClient } from '../api/client';

interface NodeStatus {
    online?: boolean;
    hostname?: string;
    platform?: string;
    uptime_seconds?: number;
    cpu_percent?: number;
    memory_percent?: number;
    disk_percent?: number;
    kimi_running?: boolean;
    active_tasks?: number;
}

export class KimiBridgePanel {
    public static currentPanel: KimiBridgePanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _disposables: vscode.Disposable[] = [];
    private _client: SwarmClient;
    private _pollTimer: NodeJS.Timeout | null = null;

    public static createOrShow(extensionUri: vscode.Uri, client: SwarmClient): void {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (KimiBridgePanel.currentPanel) {
            KimiBridgePanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'simplepod.kimiBridge',
            '🌉 Kimi Bridge',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        KimiBridgePanel.currentPanel = new KimiBridgePanel(panel, extensionUri, client);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, client: SwarmClient) {
        this._panel = panel;
        this._client = client;
        this._update(extensionUri);

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(
            async (message: any) => {
                switch (message.command) {
                    case 'refreshStatus':
                        await this._refreshStatus(message.target);
                        return;
                    case 'takeScreenshot':
                        await this._takeScreenshot(message.target);
                        return;
                    case 'runShell':
                        await this._runShell(message.target, message.commandText);
                        return;
                    case 'typeText':
                        await this._typeText(message.target, message.text);
                        return;
                    case 'getLogs':
                        await this._getLogs(message.target);
                        return;
                    case 'getProcesses':
                        await this._getProcesses(message.target);
                        return;
                    case 'injectTask':
                        await this._injectTask(message.target, message.task);
                        return;
                    case 'openExternal':
                        vscode.env.openExternal(vscode.Uri.parse(message.url));
                        return;
                }
            },
            null,
            this._disposables
        );

        this._startPolling();
    }

    private _apiPath(target: string, endpoint: string): string {
        if (target === 'remote') {
            // endpoint is like '/remote/status' -> convert to '/mesh/remote/shadow_pc/status'
            const clean = endpoint.replace(/^\/remote\//, '/');
            return `/mesh/remote/shadow_pc${clean}`;
        }
        return endpoint;
    }

    private async _refreshStatus(target: string) {
        const path = this._apiPath(target, '/remote/status');
        const status: NodeStatus | null = await this._client.request(path, { method: 'GET' });
        this._panel.webview.postMessage({
            command: 'statusUpdate',
            target,
            status: status || { online: false },
        });
    }

    private async _takeScreenshot(target: string) {
        const path = this._apiPath(target, '/remote/screenshot');
        const res = await this._client.request(path, { method: 'GET' });
        if (res?.success && res.image_base64) {
            this._panel.webview.postMessage({
                command: 'screenshotResult',
                target,
                image_base64: res.image_base64,
                width: res.width,
                height: res.height,
            });
        } else {
            this._panel.webview.postMessage({
                command: 'screenshotResult',
                target,
                error: 'Screenshot failed or returned no image',
            });
        }
    }

    private async _runShell(target: string, command: string) {
        const path = this._apiPath(target, '/remote/shell');
        const res = await this._client.request(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command, timeout: 30 }),
        });
        this._panel.webview.postMessage({
            command: 'shellResult',
            target,
            output: res?.message || res?.output || JSON.stringify(res, null, 2),
            success: res?.success ?? false,
        });
    }

    private async _typeText(target: string, text: string) {
        const path = this._apiPath(target, '/remote/type');
        const res = await this._client.request(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, interval: 0.01 }),
        });
        this._panel.webview.postMessage({
            command: 'typeResult',
            target,
            success: res?.success ?? false,
            message: res?.success ? `Typed ${text.length} chars` : 'Type failed',
        });
    }

    private async _getLogs(target: string) {
        const path = this._apiPath(target, '/remote/logs');
        const res = await this._client.request(path, { method: 'GET' });
        this._panel.webview.postMessage({
            command: 'logsResult',
            target,
            lines: res?.lines || res?.logs || (typeof res === 'string' ? [res] : []),
        });
    }

    private async _getProcesses(target: string) {
        const path = this._apiPath(target, '/remote/processes');
        const res = await this._client.request(path, { method: 'GET' });
        this._panel.webview.postMessage({
            command: 'processesResult',
            target,
            processes: res?.processes || (Array.isArray(res) ? res : []),
        });
    }

    private async _injectTask(target: string, task: string) {
        const path = this._apiPath(target, '/remote/inject');
        const res = await this._client.request(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task }),
        });
        this._panel.webview.postMessage({
            command: 'injectResult',
            target,
            success: res?.success ?? false,
            message: res?.message || JSON.stringify(res),
        });
    }

    private _startPolling() {
        this._refreshStatus('local');
        this._refreshStatus('remote');
        this._pollTimer = setInterval(() => {
            this._refreshStatus('local');
            this._refreshStatus('remote');
        }, 3000);
    }

    private _update(_extensionUri: vscode.Uri): void {
        this._panel.webview.html = this._getHtml();
    }

    private _getHtml(): string {
        const csp = [
            "default-src 'none'",
            "script-src 'unsafe-inline'",
            "style-src 'unsafe-inline'",
            "img-src 'self' data: blob: *",
        ].join('; ');

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="${csp}">
    <title>Kimi Bridge</title>
    <style>
        :root {
            --bg: #0b0d12;
            --bg-card: #13161f;
            --bg-hover: #1a1e2a;
            --border: #252a3a;
            --text: #e2e8f0;
            --text-dim: #94a3b8;
            --green: #22c55e;
            --red: #ef4444;
            --blue: #3b82f6;
            --yellow: #eab308;
            --radius: 6px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            font-size: 13px;
            line-height: 1.5;
            padding: 12px;
            min-height: 100vh;
        }
        .bridge-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        @media (max-width: 800px) { .bridge-grid { grid-template-columns: 1fr; } }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }
        .card-title {
            font-weight: 600;
            font-size: 13px;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .status-badge {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 2px 8px;
            border-radius: 12px;
            border: 1px solid var(--border);
        }
        .status-badge.online { border-color: var(--green); color: var(--green); background: rgba(34,197,94,0.1); }
        .status-badge.offline { border-color: var(--red); color: var(--red); background: rgba(239,68,68,0.1); }

        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            font-size: 11px;
        }
        .info-item { color: var(--text-dim); }
        .info-item span { color: var(--text); font-weight: 500; }

        .bar-row { display: flex; align-items: center; gap: 8px; font-size: 11px; }
        .bar-label { width: 50px; color: var(--text-dim); flex-shrink: 0; }
        .bar-track {
            flex: 1;
            height: 8px;
            background: var(--bg-hover);
            border-radius: 4px;
            overflow: hidden;
        }
        .bar-fill {
            height: 100%;
            background: var(--blue);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .bar-fill.warn { background: var(--yellow); }
        .bar-fill.crit { background: var(--red); }
        .bar-value { width: 36px; text-align: right; color: var(--text-dim); flex-shrink: 0; }

        .indicator-row {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 11px;
        }
        .dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        .dot.green { background: var(--green); }
        .dot.red { background: var(--red); }
        .dot.gray { background: var(--text-dim); }

        .btn-row { display: flex; gap: 6px; flex-wrap: wrap; }
        .btn {
            background: var(--bg-hover);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 5px 10px;
            border-radius: var(--radius);
            cursor: pointer;
            font-size: 11px;
            transition: all 0.15s;
        }
        .btn:hover { background: var(--border); }
        .btn-green { border-color: var(--green); color: var(--green); }
        .btn-green:hover { background: rgba(34,197,94,0.15); }
        .btn-blue { border-color: var(--blue); color: var(--blue); }
        .btn-blue:hover { background: rgba(59,130,246,0.15); }
        .btn-red { border-color: var(--red); color: var(--red); }
        .btn-red:hover { background: rgba(239,68,68,0.15); }

        .input-row { display: flex; gap: 6px; }
        .input {
            flex: 1;
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 6px 8px;
            border-radius: var(--radius);
            font-family: inherit;
            font-size: 12px;
        }
        .input:focus { outline: none; border-color: var(--blue); }

        .output-box {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 8px;
            min-height: 60px;
            max-height: 160px;
            overflow-y: auto;
            font-size: 11px;
            white-space: pre-wrap;
            word-break: break-word;
            color: var(--text-dim);
        }
        .output-box.error { border-color: var(--red); color: var(--red); }
        .output-box.success { border-color: var(--green); color: var(--text); }

        .screenshot-area {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-dim);
            font-size: 11px;
            overflow: hidden;
        }
        .screenshot-area img {
            max-width: 100%;
            display: block;
        }

        .section-title {
            font-size: 10px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }

        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
    </style>
</head>
<body>
    <div class="bridge-grid">
        <!-- LOCAL NODE -->
        <div class="card" id="local-card">
            <div class="card-header">
                <div class="card-title">🖥️ Local Node <span style="font-size:11px;color:var(--text-dim)">localhost:8000</span></div>
                <div class="status-badge offline" id="local-status">Offline</div>
            </div>

            <div class="info-grid">
                <div class="info-item">Host: <span id="local-hostname">—</span></div>
                <div class="info-item">Platform: <span id="local-platform">—</span></div>
                <div class="info-item">Uptime: <span id="local-uptime">—</span></div>
                <div class="info-item">Tasks: <span id="local-tasks">—</span></div>
            </div>

            <div class="bar-row">
                <div class="bar-label">CPU</div>
                <div class="bar-track"><div class="bar-fill" id="local-cpu-bar" style="width:0%"></div></div>
                <div class="bar-value" id="local-cpu-val">0%</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Mem</div>
                <div class="bar-track"><div class="bar-fill" id="local-mem-bar" style="width:0%"></div></div>
                <div class="bar-value" id="local-mem-val">0%</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Disk</div>
                <div class="bar-track"><div class="bar-fill" id="local-disk-bar" style="width:0%"></div></div>
                <div class="bar-value" id="local-disk-val">0%</div>
            </div>

            <div class="indicator-row">
                <div><span class="dot gray" id="local-kimi-dot"></span> Kimi <span id="local-kimi-text">—</span></div>
            </div>

            <div class="section-title">Actions</div>
            <div class="btn-row">
                <button class="btn btn-green" id="local-btn-screenshot">📸 Screenshot</button>
                <button class="btn btn-blue" id="local-btn-logs">📄 Logs</button>
                <button class="btn btn-blue" id="local-btn-processes">⚙️ Processes</button>
                <button class="btn btn-red" id="local-btn-inject">💉 Inject</button>
            </div>

            <div class="section-title">Shell</div>
            <div class="input-row">
                <input class="input" id="local-shell-input" placeholder="Enter command..." />
                <button class="btn btn-blue" id="local-btn-shell">Run</button>
            </div>
            <div class="output-box" id="local-shell-output">Output will appear here...</div>

            <div class="section-title">Type Text</div>
            <div class="input-row">
                <input class="input" id="local-type-input" placeholder="Text to type..." />
                <button class="btn btn-blue" id="local-btn-type">Send</button>
            </div>

            <div class="section-title">Screenshot</div>
            <div class="screenshot-area" id="local-screenshot">
                <span>No screenshot captured</span>
            </div>
        </div>

        <!-- REMOTE (SHADOW) NODE -->
        <div class="card" id="remote-card">
            <div class="card-header">
                <div class="card-title">☁️ Shadow Node <span style="font-size:11px;color:var(--text-dim)">100.64.0.2:8002</span></div>
                <div class="status-badge offline" id="remote-status">Offline</div>
            </div>

            <div class="info-grid">
                <div class="info-item">Host: <span id="remote-hostname">—</span></div>
                <div class="info-item">Platform: <span id="remote-platform">—</span></div>
                <div class="info-item">Uptime: <span id="remote-uptime">—</span></div>
                <div class="info-item">Tasks: <span id="remote-tasks">—</span></div>
            </div>

            <div class="bar-row">
                <div class="bar-label">CPU</div>
                <div class="bar-track"><div class="bar-fill" id="remote-cpu-bar" style="width:0%"></div></div>
                <div class="bar-value" id="remote-cpu-val">0%</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Mem</div>
                <div class="bar-track"><div class="bar-fill" id="remote-mem-bar" style="width:0%"></div></div>
                <div class="bar-value" id="remote-mem-val">0%</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Disk</div>
                <div class="bar-track"><div class="bar-fill" id="remote-disk-bar" style="width:0%"></div></div>
                <div class="bar-value" id="remote-disk-val">0%</div>
            </div>

            <div class="indicator-row">
                <div><span class="dot gray" id="remote-kimi-dot"></span> Kimi <span id="remote-kimi-text">—</span></div>
            </div>

            <div class="section-title">Actions</div>
            <div class="btn-row">
                <button class="btn btn-green" id="remote-btn-screenshot">📸 Screenshot</button>
                <button class="btn btn-blue" id="remote-btn-logs">📄 Logs</button>
                <button class="btn btn-blue" id="remote-btn-processes">⚙️ Processes</button>
                <button class="btn btn-red" id="remote-btn-inject">💉 Inject</button>
            </div>

            <div class="section-title">Shell</div>
            <div class="input-row">
                <input class="input" id="remote-shell-input" placeholder="Enter command..." />
                <button class="btn btn-blue" id="remote-btn-shell">Run</button>
            </div>
            <div class="output-box" id="remote-shell-output">Output will appear here...</div>

            <div class="section-title">Type Text</div>
            <div class="input-row">
                <input class="input" id="remote-type-input" placeholder="Text to type..." />
                <button class="btn btn-blue" id="remote-btn-type">Send</button>
            </div>

            <div class="section-title">Screenshot</div>
            <div class="screenshot-area" id="remote-screenshot">
                <span>No screenshot captured</span>
            </div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        function fmtUptime(sec) {
            if (!sec && sec !== 0) return '—';
            const h = Math.floor(sec / 3600);
            const m = Math.floor((sec % 3600) / 60);
            const s = Math.floor(sec % 60);
            return \`\${h}h \${m}m \${s}s\`;
        }

        function setBar(target, type, pct) {
            const val = Math.max(0, Math.min(100, pct || 0));
            const bar = document.getElementById(\`\${target}-\${type}-bar\`);
            const txt = document.getElementById(\`\${target}-\${type}-val\`);
            if (bar) bar.style.width = val + '%';
            if (txt) txt.textContent = val.toFixed(0) + '%';
            if (bar) {
                bar.classList.remove('warn', 'crit');
                if (val >= 90) bar.classList.add('crit');
                else if (val >= 70) bar.classList.add('warn');
            }
        }

        function bindActions(target) {
            document.getElementById(\`\${target}-btn-screenshot\`).addEventListener('click', () => {
                vscode.postMessage({ command: 'takeScreenshot', target });
            });
            document.getElementById(\`\${target}-btn-logs\`).addEventListener('click', () => {
                vscode.postMessage({ command: 'getLogs', target });
            });
            document.getElementById(\`\${target}-btn-processes\`).addEventListener('click', () => {
                vscode.postMessage({ command: 'getProcesses', target });
            });
            document.getElementById(\`\${target}-btn-inject\`).addEventListener('click', () => {
                const task = prompt('Enter task to inject:');
                if (task) vscode.postMessage({ command: 'injectTask', target, task });
            });
            document.getElementById(\`\${target}-btn-shell\`).addEventListener('click', () => {
                const input = document.getElementById(\`\${target}-shell-input\`);
                const text = input.value.trim();
                if (!text) return;
                vscode.postMessage({ command: 'runShell', target, commandText: text });
            });
            document.getElementById(\`\${target}-shell-input\`).addEventListener('keydown', (e) => {
                if (e.key === 'Enter') document.getElementById(\`\${target}-btn-shell\`).click();
            });
            document.getElementById(\`\${target}-btn-type\`).addEventListener('click', () => {
                const input = document.getElementById(\`\${target}-type-input\`);
                const text = input.value.trim();
                if (!text) return;
                vscode.postMessage({ command: 'typeText', target, text });
            });
            document.getElementById(\`\${target}-type-input\`).addEventListener('keydown', (e) => {
                if (e.key === 'Enter') document.getElementById(\`\${target}-btn-type\`).click();
            });
        }

        bindActions('local');
        bindActions('remote');

        window.addEventListener('message', (event) => {
            const msg = event.data;
            const t = msg.target;
            if (!t) return;

            switch (msg.command) {
                case 'statusUpdate': {
                    const s = msg.status || {};
                    const online = s.online !== false;
                    const badge = document.getElementById(\`\${t}-status\`);
                    badge.textContent = online ? 'Online' : 'Offline';
                    badge.classList.toggle('online', online);
                    badge.classList.toggle('offline', !online);

                    document.getElementById(\`\${t}-hostname\`).textContent = s.hostname || '—';
                    document.getElementById(\`\${t}-platform\`).textContent = s.platform || '—';
                    document.getElementById(\`\${t}-uptime\`).textContent = fmtUptime(s.uptime_seconds);
                    document.getElementById(\`\${t}-tasks\`).textContent = s.active_tasks !== undefined ? s.active_tasks : '—';

                    setBar(t, 'cpu', s.cpu_percent);
                    setBar(t, 'mem', s.memory_percent);
                    setBar(t, 'disk', s.disk_percent);

                    const kimiDot = document.getElementById(\`\${t}-kimi-dot\`);
                    const kimiText = document.getElementById(\`\${t}-kimi-text\`);
                    if (s.kimi_running) {
                        kimiDot.className = 'dot green';
                        kimiText.textContent = 'Running';
                    } else if (online) {
                        kimiDot.className = 'dot red';
                        kimiText.textContent = 'Stopped';
                    } else {
                        kimiDot.className = 'dot gray';
                        kimiText.textContent = 'Unknown';
                    }
                    break;
                }
                case 'screenshotResult': {
                    const area = document.getElementById(\`\${t}-screenshot\`);
                    if (msg.error) {
                        area.innerHTML = \`<span style="color:var(--red)">❌ \${msg.error}</span>\`;
                    } else if (msg.image_base64) {
                        area.innerHTML = \`<img src="data:image/png;base64,\${msg.image_base64}" alt="Screenshot" />\`;
                    }
                    break;
                }
                case 'shellResult': {
                    const box = document.getElementById(\`\${t}-shell-output\`);
                    box.textContent = msg.output || 'No output';
                    box.classList.remove('error', 'success');
                    box.classList.add(msg.success ? 'success' : 'error');
                    break;
                }
                case 'typeResult': {
                    // Optional toast-like feedback; for now we just flash the type input border
                    const input = document.getElementById(\`\${t}-type-input\`);
                    const oldBorder = input.style.borderColor;
                    input.style.borderColor = msg.success ? 'var(--green)' : 'var(--red)';
                    setTimeout(() => { input.style.borderColor = oldBorder; }, 800);
                    break;
                }
                case 'logsResult': {
                    const lbox = document.getElementById(\`\${t}-shell-output\`);
                    const lines = msg.lines || [];
                    lbox.textContent = lines.length ? lines.join('\\n') : 'No logs returned';
                    lbox.classList.remove('error', 'success');
                    lbox.classList.add('success');
                    break;
                }
                case 'processesResult': {
                    const pbox = document.getElementById(\`\${t}-shell-output\`);
                    const procs = msg.processes || [];
                    if (!procs.length) {
                        pbox.textContent = 'No processes returned';
                    } else {
                        const rows = procs.map(p => {
                            const pid = p.pid ?? p.id ?? '?';
                            const name = p.name ?? p.cmdline ?? JSON.stringify(p);
                            const cpu = p.cpu_percent !== undefined ? p.cpu_percent.toFixed(1) + '%' : '—';
                            const mem = p.memory_percent !== undefined ? p.memory_percent.toFixed(1) + '%' : '—';
                            return \`\${pid.padEnd(8)} \${cpu.padEnd(6)} \${mem.padEnd(6)} \${name}\`;
                        });
                        pbox.textContent = ['PID      CPU    MEM    NAME', '—'.repeat(50), ...rows].join('\\n');
                    }
                    pbox.classList.remove('error', 'success');
                    pbox.classList.add('success');
                    break;
                }
                case 'injectResult': {
                    const ibox = document.getElementById(\`\${t}-shell-output\`);
                    ibox.textContent = msg.message || 'Inject completed';
                    ibox.classList.remove('error', 'success');
                    ibox.classList.add(msg.success ? 'success' : 'error');
                    break;
                }
            }
        });

        // Request initial status
        vscode.postMessage({ command: 'refreshStatus', target: 'local' });
        vscode.postMessage({ command: 'refreshStatus', target: 'remote' });
    </script>
</body>
</html>`;
    }

    public dispose(): void {
        if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; }
        KimiBridgePanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) { x.dispose(); }
        }
    }
}
