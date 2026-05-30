import * as vscode from 'vscode';
import { DashboardPanel } from './panels/DashboardPanel';
import { ControlPanel } from './panels/ControlPanel';
import { AgentTreeProvider } from './providers/AgentTreeProvider';
import { NodeTreeProvider } from './providers/NodeTreeProvider';
import { TransferTreeProvider } from './providers/TransferTreeProvider';
import { KimiBridgePanel } from './panels/KimiBridgePanel';
import { SwarmClient } from './api/client';

const STATE_KEYS = {
    API_URL: 'simplepod.apiUrl',
    DASHBOARD_OPEN: 'simplepod.dashboardOpen',
    CONTROL_OPEN: 'simplepod.controlOpen',
    LAST_STATUS: 'simplepod.lastStatus',
    AUTO_RESUME: 'simplepod.autoResume',
};

let client: SwarmClient;
let statusBarItem: vscode.StatusBarItem;
let reconnectTimer: NodeJS.Timeout | null = null;
let agentProvider: AgentTreeProvider;
let nodeProvider: NodeTreeProvider;
let transferProvider: TransferTreeProvider;
let keepAliveTimer: NodeJS.Timeout | null = null;
let shadowWatcherTimer: NodeJS.Timeout | null = null;
let lastRecoveryTimestamp: string | null = null;

export function activate(context: vscode.ExtensionContext): void {
    const savedUrl = context.globalState.get<string>(STATE_KEYS.API_URL, 'http://localhost:8000');
    const wasDashboardOpen = context.globalState.get<boolean>(STATE_KEYS.DASHBOARD_OPEN, false);
    const wasControlOpen = context.globalState.get<boolean>(STATE_KEYS.CONTROL_OPEN, false);
    const autoResume = context.globalState.get<boolean>(STATE_KEYS.AUTO_RESUME, true);

    client = new SwarmClient(savedUrl);

    agentProvider = new AgentTreeProvider();
    nodeProvider = new NodeTreeProvider();
    transferProvider = new TransferTreeProvider();

    agentProvider.setClient(client);
    nodeProvider.setClient(client);
    transferProvider.setClient(client);
    agentProvider.startPolling();
    nodeProvider.startPolling();
    transferProvider.startPolling();

    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = 'simplepod.openControlPanel';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    vscode.window.registerTreeDataProvider('simplepod.agents', agentProvider);
    vscode.window.registerTreeDataProvider('simplepod.nodes', nodeProvider);
    vscode.window.registerTreeDataProvider('simplepod.transfers', transferProvider);
    vscode.commands.executeCommand('setContext', 'simplepod:enabled', true);

    if (autoResume && wasControlOpen) {
        setTimeout(() => {
            ControlPanel.createOrShow(context.extensionUri, client);
            vscode.window.showInformationMessage('SimplePod Swarm: Auto-resumed control panel');
        }, 1500);
    }

    startHealthPolling(context);
    startShadowWatcher(context);
    registerCommands(context);
}

function registerCommands(context: vscode.ExtensionContext): void {
    const openDashboard = vscode.commands.registerCommand('simplepod.openDashboard', () => {
        DashboardPanel.createOrShow(context.extensionUri, client);
        context.globalState.update(STATE_KEYS.DASHBOARD_OPEN, true);
    });

    const openControlPanel = vscode.commands.registerCommand('simplepod.openControlPanel', () => {
        ControlPanel.createOrShow(context.extensionUri, client);
        context.globalState.update(STATE_KEYS.CONTROL_OPEN, true);
        vscode.commands.executeCommand('setContext', 'simplepod:controlVisible', true);
    });

    const captureScreen = vscode.commands.registerCommand('simplepod.captureScreenshot', async () => {
        if (!DashboardPanel.currentPanel) {
            vscode.window.showWarningMessage('Open the SimplePod dashboard first');
            return;
        }
        DashboardPanel.currentPanel.requestCapture();
    });

    const quickChat = vscode.commands.registerCommand('simplepod.quickChat', async () => {
        const prompt = await vscode.window.showInputBox({
            prompt: 'Ask the AI swarm',
            placeHolder: 'e.g. Write a Python function to sort a list',
        });
        if (!prompt) return;

        const models = await client.getModels() || ['llama3.2'];
        const model = await vscode.window.showQuickPick(models, {
            placeHolder: 'Select model',
        }) || models[0];

        const res = await client.infer(prompt, model);
        if (!res || !res.task_id) {
            vscode.window.showErrorMessage('Failed to queue inference');
            return;
        }

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `SimplePod · ${model}`,
            cancellable: false,
        }, async (progress) => {
            progress.report({ message: 'Queued...' });
            for (let i = 0; i < 60; i++) {
                await new Promise(r => setTimeout(r, 2000));
                const task = await client.getTask(res.task_id);
                if (!task) continue;
                if (task.status === 'completed') {
                    const text = task.result?.response || '';
                    const doc = await vscode.workspace.openTextDocument({
                        content: text,
                        language: 'markdown',
                    });
                    await vscode.window.showTextDocument(doc, { preview: true });
                    vscode.window.showInformationMessage(`✅ Response from ${task.assigned_agent || 'agent'}`);
                    return;
                } else if (task.status === 'failed') {
                    const err = task.result?.error || task.error || 'Unknown error';
                    vscode.window.showErrorMessage(`❌ ${err}`);
                    return;
                }
                progress.report({ message: `${task.status} (${i + 1})...` });
            }
            vscode.window.showWarningMessage('⏱ Inference timed out');
        });
    });

    const activateSwarm = vscode.commands.registerCommand('simplepod.activateSwarm', async () => {
        const res = await client.activateSwarm();
        if (res) {
            statusBarItem.text = '$(play) SimplePod: Active';
            vscode.window.showInformationMessage('✅ Swarm activated');
            startKeepAlive();
        } else {
            vscode.window.showErrorMessage('❌ Failed to activate');
        }
    });

    const shutdownSwarm = vscode.commands.registerCommand('simplepod.shutdownSwarm', async () => {
        const res = await client.shutdownSwarm();
        if (res) {
            statusBarItem.text = '$(stop) SimplePod: Offline';
            vscode.window.showInformationMessage('🛑 Swarm shutdown');
            stopKeepAlive();
        }
    });

    const spawnAgents = vscode.commands.registerCommand('simplepod.spawnAgents', async () => {
        const countStr = await vscode.window.showInputBox({
            prompt: 'Number of agents to spawn',
            value: '3',
            validateInput: (text) => {
                const n = parseInt(text);
                if (isNaN(n) || n < 1 || n > 50) return 'Enter 1–50';
                return null;
            }
        });
        if (!countStr) return;
        const res = await client.spawnAgents(parseInt(countStr));
        vscode.window.showInformationMessage(
            res?.success ? `✅ Spawned ${res.spawned?.length || 0} agent(s)` : '❌ Spawn failed'
        );
    });

    const killAgent = vscode.commands.registerCommand('simplepod.killAgent', async (item?: any) => {
        const agentId = item?.agentId || await vscode.window.showInputBox({ prompt: 'Agent ID to kill' });
        if (!agentId) return;
        const res = await client.killAgent(agentId);
        vscode.window.showInformationMessage(res ? `💀 ${agentId} killed` : '❌ Kill failed');
    });

    const removeAgent = vscode.commands.registerCommand('simplepod.removeAgent', async (item?: any) => {
        const agentId = item?.agentId || await vscode.window.showInputBox({ prompt: 'Dead agent ID to remove' });
        if (!agentId) return;
        const res = await client.removeAgent(agentId);
        vscode.window.showInformationMessage(res ? `🗑️ ${agentId} removed` : '❌ Remove failed');
    });

    const setBreaker = vscode.commands.registerCommand('simplepod.setMainBreaker', async () => {
        const value = await vscode.window.showInputBox({
            prompt: 'Main Breaker Threshold (0.0 - 1.0)',
            placeHolder: '0.5',
            validateInput: (text) => {
                const n = Number(text);
                if (isNaN(n) || n < 0 || n > 1) return 'Enter a number between 0.0 and 1.0';
                return null;
            }
        });
        if (value) {
            const res = await client.setThreshold(parseFloat(value));
            if (res) vscode.window.showInformationMessage(`⚖️ Threshold set to ${value}`);
        }
    });

    const reconnect = vscode.commands.registerCommand('simplepod.reconnect', async () => {
        const newUrl = await vscode.window.showInputBox({
            prompt: 'Backend API URL',
            value: client.getBaseUrl(),
        });
        if (newUrl) {
            client.setBaseUrl(newUrl);
            agentProvider.setClient(client);
            nodeProvider.setClient(client);
            await context.globalState.update(STATE_KEYS.API_URL, newUrl);
            vscode.window.showInformationMessage(`🔗 Reconnected to ${newUrl}`);
            startHealthPolling(context);
        }
    });

    // Remote control commands
    const remoteType = vscode.commands.registerCommand('simplepod.remoteType', async () => {
        const text = await vscode.window.showInputBox({ prompt: 'Type text on remote PC' });
        if (!text) return;
        const res = await client.remoteType(text);
        vscode.window.showInformationMessage(res?.success ? `⌨️ Typed ${text.length} chars` : '❌ Type failed');
    });

    const remoteClick = vscode.commands.registerCommand('simplepod.remoteClick', async () => {
        const xy = await vscode.window.showInputBox({
            prompt: 'Click coordinates (x,y)',
            placeHolder: 'e.g. 500,300',
            validateInput: (text) => {
                const parts = text.split(',').map(p => parseInt(p.trim()));
                if (parts.length !== 2 || parts.some(isNaN)) return 'Enter x,y coordinates';
                return null;
            }
        });
        if (!xy) return;
        const [x, y] = xy.split(',').map(p => parseInt(p.trim()));
        const res = await client.remoteClick(x, y);
        vscode.window.showInformationMessage(res?.success ? `🖱️ Clicked (${x}, ${y})` : '❌ Click failed');
    });

    const remoteKeys = vscode.commands.registerCommand('simplepod.remoteKeys', async () => {
        const keys = await vscode.window.showQuickPick([
            'enter', 'tab', 'esc', 'space',
            'ctrl+c', 'ctrl+v', 'ctrl+a', 'ctrl+z',
            'alt+tab', 'win', 'f5', 'print',
        ], { placeHolder: 'Select key or combo to send' });
        if (!keys) return;
        const res = await client.remoteKeys(keys);
        vscode.window.showInformationMessage(res?.success ? `🔑 Sent: ${keys}` : '❌ Keys failed');
    });

    const remoteShell = vscode.commands.registerCommand('simplepod.remoteShell', async () => {
        const command = await vscode.window.showInputBox({
            prompt: 'Shell command on remote PC',
            placeHolder: 'e.g. dir or echo hello',
        });
        if (!command) return;
        const res = await client.remoteShell(command);
        if (res?.success) {
            const output = res.message || '';
            const doc = await vscode.workspace.openTextDocument({ content: output, language: 'plaintext' });
            await vscode.window.showTextDocument(doc, { preview: true });
            vscode.window.showInformationMessage('✅ Shell executed');
        } else {
            vscode.window.showErrorMessage(`❌ ${res?.message || 'Shell failed'}`);
        }
    });

    const remoteScroll = vscode.commands.registerCommand('simplepod.remoteScroll', async () => {
        const amount = await vscode.window.showInputBox({
            prompt: 'Scroll amount (positive = up, negative = down)',
            value: '-3',
            validateInput: (text) => {
                if (isNaN(parseInt(text))) return 'Enter a number';
                return null;
            }
        });
        if (!amount) return;
        const res = await client.remoteScroll(parseInt(amount));
        vscode.window.showInformationMessage(res?.success ? `🖱️ Scrolled ${amount}` : '❌ Scroll failed');
    });

    const remoteDrag = vscode.commands.registerCommand('simplepod.remoteDrag', async () => {
        const coords = await vscode.window.showInputBox({
            prompt: 'Drag coordinates: x1,y1,x2,y2',
            placeHolder: 'e.g. 100,200,300,400',
            validateInput: (text) => {
                const parts = text.split(',').map(p => parseInt(p.trim()));
                if (parts.length !== 4 || parts.some(isNaN)) return 'Enter x1,y1,x2,y2';
                return null;
            }
        });
        if (!coords) return;
        const [x1, y1, x2, y2] = coords.split(',').map(p => parseInt(p.trim()));
        const res = await client.remoteDrag(x1, y1, x2, y2);
        vscode.window.showInformationMessage(res?.success ? `✋ Dragged (${x1},${y1})→(${x2},${y2})` : '❌ Drag failed');
    });

    const remoteScreenshot = vscode.commands.registerCommand('simplepod.remoteScreenshot', async () => {
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Capturing remote screen...',
            cancellable: false,
        }, async () => {
            const res = await client.remoteScreenshot();
            if (!res?.success) {
                vscode.window.showErrorMessage('❌ Screenshot failed');
                return;
            }
            const imgData = res.image_base64;
            const markdown = `![Remote Screenshot](data:image/png;base64,${imgData})\n\n*Size: ${res.width}x${res.height}*`;
            const doc = await vscode.workspace.openTextDocument({ content: markdown, language: 'markdown' });
            await vscode.window.showTextDocument(doc, { preview: true });
            vscode.window.showInformationMessage(`📸 Screenshot ${res.width}x${res.height}`);
        });
    });

    const openKimiBridge = vscode.commands.registerCommand('simplepod.openKimiBridge', () => {
        KimiBridgePanel.createOrShow(context.extensionUri, client);
    });

    const startShadowWatcherCmd = vscode.commands.registerCommand('simplepod.startShadowWatcher', () => {
        startShadowWatcher(context);
        vscode.window.showInformationMessage('🔦 Shadow PC Watcher started');
    });

    // -----------------------------------------------------------------------
    // Cleanup tools
    // ELI5: The maintenance team's dispatch console. They can audit any panel
    //       in the building — local sub-panel OR the remote Shadow PC panel —
    //       and only throw breakers after reading the safety tags.
    // -----------------------------------------------------------------------
    const cleanupAnalyze = vscode.commands.registerCommand('simplepod.cleanupAnalyze', async () => {
        const drive = await vscode.window.showInputBox({ prompt: 'Drive to analyze', value: 'C:/' }) || 'C:/';
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'SimplePod Cleanup: Analyzing disk...',
            cancellable: false,
        }, async () => {
            const res = await client.cleanupAnalyze(drive);
            if (!res) {
                vscode.window.showErrorMessage('❌ Cleanup analysis failed');
                return;
            }
            const disk = res.disk || {};
            const games = res.games || [];
            const total = res.game_total_gb || 0;
            const lines = [
                `📊 ${disk.drive} — ${disk.used_gb} GB used / ${disk.total_gb} GB total (${disk.percent_free}% free)`,
                disk.is_critical ? '⚠️ CRITICAL: Less than 10% free!' : '',
                `🎮 ${games.length} games found (${total} GB)`,
                games.length > 0 ? `   Largest: ${games[0].name} (${games[0].size_gb} GB)` : '',
            ].filter(Boolean);
            vscode.window.showInformationMessage(lines.join(' | '));
        });
    });

    const cleanupGames = vscode.commands.registerCommand('simplepod.cleanupGames', async () => {
        const drive = await vscode.window.showInputBox({ prompt: 'Drive to scan for games', value: 'C:/' }) || 'C:/';
        const res = await client.cleanupGames(drive);
        if (!res || !res.games) {
            vscode.window.showErrorMessage('❌ Game scan failed');
            return;
        }
        const items = res.games.map((g: any) => ({
            label: `${g.name}`,
            description: `${g.platform} · ${g.size_gb} GB`,
            detail: g.path,
            game: g,
        }));
        const picked = await vscode.window.showQuickPick(items, {
            placeHolder: `Found ${res.count} games using ${res.total_gb} GB — select to view path`,
            canPickMany: false,
        });
        if (picked) {
            vscode.window.showInformationMessage(`${picked.game.name}: ${picked.game.path} (${picked.game.size_gb} GB)`);
        }
    });

    const cleanupLargeFiles = vscode.commands.registerCommand('simplepod.cleanupLargeFiles', async () => {
        const drive = await vscode.window.showInputBox({ prompt: 'Drive to scan', value: 'C:/' }) || 'C:/';
        const minSizeStr = await vscode.window.showInputBox({ prompt: 'Minimum file size (MB)', value: '100' }) || '100';
        const minSize = parseInt(minSizeStr);
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Scanning for large files...',
            cancellable: false,
        }, async () => {
            const res = await client.cleanupLargeFiles(drive, minSize);
            if (!res || !res.files) {
                vscode.window.showErrorMessage('❌ Large file scan failed');
                return;
            }
            const safeFiles = res.files.filter((f: any) => f.safety_score >= 70);
            const unsafeFiles = res.files.filter((f: any) => f.safety_score < 50);
            const msg = `Found ${res.files.length} large files (${Math.round(res.total_scanned_mb / 1024)} GB). Safe: ${safeFiles.length} · Dangerous: ${unsafeFiles.length}`;
            const action = await vscode.window.showInformationMessage(msg, 'View Safe Files', 'View All', 'Dismiss');
            if (action === 'View Safe Files' || action === 'View All') {
                const viewSet = action === 'View Safe Files' ? safeFiles : res.files;
                const content = viewSet.map((f: any) =>
                    `[${f.safety_score}/100 ${f.category}] ${f.path} — ${Math.round(f.size_mb)} MB\n   ${f.safety_reason} (modified ${f.last_modified_days} days ago)`
                ).join('\n\n');
                const doc = await vscode.workspace.openTextDocument({ content, language: 'plaintext' });
                await vscode.window.showTextDocument(doc, { preview: true });
            }
        });
    });

    const cleanupSafetyAudit = vscode.commands.registerCommand('simplepod.cleanupSafetyAudit', async () => {
        const drive = await vscode.window.showInputBox({ prompt: 'Drive to audit', value: 'C:/' }) || 'C:/';
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Running safety audit...',
            cancellable: false,
        }, async () => {
            const res = await client.cleanupSafety(drive);
            if (!res) {
                vscode.window.showErrorMessage('❌ Safety audit failed');
                return;
            }
            const recs = res.recommendations || [];
            const content = recs.join('\n\n') + '\n\n---\n\n' + JSON.stringify(res, null, 2);
            const doc = await vscode.workspace.openTextDocument({ content, language: 'json' });
            await vscode.window.showTextDocument(doc, { preview: true });
            vscode.window.showInformationMessage(`Audit complete: ${recs.length} recommendation(s)`);
        });
    });

    const cleanupExecute = vscode.commands.registerCommand('simplepod.cleanupExecute', async () => {
        const input = await vscode.window.showInputBox({
            prompt: 'Paths to delete (comma-separated)',
            placeHolder: 'C:/Temp,C:/Users/.../Downloads/old_installer.exe',
        });
        if (!input) return;
        const paths = input.split(',').map(p => p.trim()).filter(Boolean);
        const force = await vscode.window.showQuickPick(['Safe items only (score >= 50)', 'Force delete (dangerous)'], {
            placeHolder: 'Deletion mode',
        });
        const isForce = force?.includes('Force') ?? false;
        const confirm = await vscode.window.showWarningMessage(
            `Delete ${paths.length} path(s) ${isForce ? 'WITH FORCE' : 'with safety check'}?`,
            { modal: true },
            'Delete',
        );
        if (confirm !== 'Delete') return;
        const targets = paths.map(p => ({ path: p, force: isForce }));
        const res = await client.cleanupExecute(targets);
        if (res?.success) {
            vscode.window.showInformationMessage(`✅ Freed ${res.freed_gb} GB · Deleted ${res.deleted.length} · Failed ${res.failed.length}`);
        } else {
            vscode.window.showErrorMessage(`❌ Cleanup failed: ${res?.message || 'Unknown error'}`);
        }
    });

    // Mesh cleanup commands (remote nodes)
    const meshCleanupAnalyze = vscode.commands.registerCommand('simplepod.meshCleanupAnalyze', async () => {
        const nodes = await client.getNodes() || [];
        const pick = await vscode.window.showQuickPick(
            nodes.map((n: any) => ({ label: n.node_id, description: n.status, node: n })),
            { placeHolder: 'Select remote node to analyze' },
        );
        if (!pick) return;
        const res = await client.meshCleanupAnalyze(pick.node.node_id);
        vscode.window.showInformationMessage(res?.disk ? `${res.disk.drive}: ${res.disk.percent_free}% free` : 'Analysis complete');
    });

    const meshCleanupGames = vscode.commands.registerCommand('simplepod.meshCleanupGames', async () => {
        const nodes = await client.getNodes() || [];
        const pick = await vscode.window.showQuickPick(
            nodes.map((n: any) => ({ label: n.node_id, description: n.status, node: n })),
            { placeHolder: 'Select remote node to scan for games' },
        );
        if (!pick) return;
        const res = await client.meshCleanupGames(pick.node.node_id);
        vscode.window.showInformationMessage(res?.games ? `${res.count} games · ${res.total_gb} GB on ${pick.node.node_id}` : 'Scan complete');
    });

    const meshCleanupLargeFiles = vscode.commands.registerCommand('simplepod.meshCleanupLargeFiles', async () => {
        const nodes = await client.getNodes() || [];
        const pick = await vscode.window.showQuickPick(
            nodes.map((n: any) => ({ label: n.node_id, description: n.status, node: n })),
            { placeHolder: 'Select remote node for large-file scan' },
        );
        if (!pick) return;
        const res = await client.meshCleanupLargeFiles(pick.node.node_id);
        vscode.window.showInformationMessage(res?.files ? `${res.files.length} large files on ${pick.node.node_id}` : 'Scan complete');
    });

    context.subscriptions.push(
        openDashboard, openControlPanel, captureScreen, quickChat,
        activateSwarm, shutdownSwarm, spawnAgents, killAgent, removeAgent,
        setBreaker, reconnect,
        remoteType, remoteClick, remoteKeys, remoteShell,
        remoteScroll, remoteDrag, remoteScreenshot, openKimiBridge, startShadowWatcherCmd,
        cleanupAnalyze, cleanupGames, cleanupLargeFiles, cleanupSafetyAudit, cleanupExecute,
        meshCleanupAnalyze, meshCleanupGames, meshCleanupLargeFiles,
    );
}

function startKeepAlive(): void {
    if (keepAliveTimer) { return; }
    const keepAliveCmd = `powershell -NoProfile -Command "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys('{SCROLLLOCK 2}')"\r\n`;
    keepAliveTimer = setInterval(() => {
        vscode.commands.executeCommand('workbench.action.terminal.sendSequence', { text: keepAliveCmd });
    }, 60000);
}

function stopKeepAlive(): void {
    if (keepAliveTimer) {
        clearInterval(keepAliveTimer);
        keepAliveTimer = null;
    }
}

function startShadowWatcher(context: vscode.ExtensionContext): void {
    if (shadowWatcherTimer) { clearInterval(shadowWatcherTimer); }

    const watcherDir = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
        || context.extensionUri.fsPath.replace(/\\interfaces\\vscode_extension$/, '');
    const recoveryPath = vscode.Uri.file(watcherDir + '/shadow_captures/last_recovery.json').fsPath;

    const check = async () => {
        try {
            const fs = require('fs');
            if (!fs.existsSync(recoveryPath)) { return; }
            const raw = fs.readFileSync(recoveryPath, 'utf-8');
            const data = JSON.parse(raw);
            const ts = data.recovered_at;
            if (!ts || ts === lastRecoveryTimestamp) { return; }

            lastRecoveryTimestamp = ts;
            const downtime = data.downtime_formatted || 'unknown';
            const screenshot = data.screenshot ? data.screenshot.replace(/.*[\\/]/, '') : 'none';

            const action = await vscode.window.showInformationMessage(
                `🔔 Shadow PC back online! Downtime: ${downtime}. Screenshot: ${screenshot}`,
                'Open Kimi Bridge',
                'Dismiss'
            );
            if (action === 'Open Kimi Bridge') {
                KimiBridgePanel.createOrShow(context.extensionUri, client);
            }
        } catch {
            // silently ignore read/parse errors
        }
    };

    check();
    shadowWatcherTimer = setInterval(check, 5000);
}

function startHealthPolling(context: vscode.ExtensionContext): void {
    if (reconnectTimer) { clearInterval(reconnectTimer); }

    const poll = async () => {
        const health = await client.health();
        if (health && health.status === 'healthy') {
            statusBarItem.text = '$(circuit-board) SimplePod: Online';
            statusBarItem.tooltip = `Backend: ${client.getBaseUrl()} | Click to open Control Panel`;
            statusBarItem.backgroundColor = undefined;

            const status = await client.getStatus();
            if (status && status.running) {
                startKeepAlive();
            } else {
                stopKeepAlive();
            }
        } else {
            statusBarItem.text = '$(warning) SimplePod: Disconnected';
            statusBarItem.tooltip = `Backend: ${client.getBaseUrl()} | Check connection`;
            statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            stopKeepAlive();
        }
    };

    poll();
    reconnectTimer = setInterval(poll, 5000);
}

export async function deactivate(): Promise<void> {
    if (reconnectTimer) { clearInterval(reconnectTimer); }
    if (shadowWatcherTimer) { clearInterval(shadowWatcherTimer); }
    agentProvider?.stopPolling();
    nodeProvider?.stopPolling();
    transferProvider?.stopPolling();
    stopKeepAlive();
}
