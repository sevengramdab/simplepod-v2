import * as vscode from 'vscode';

export interface SwarmStatus {
    running: boolean;
    agents_total: number;
    agents_active: number;
    agents_idle: number;
    pending_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    uptime_seconds: number;
}

export interface RoutingConfig {
    mode: string;
    threshold: number;
    healthy_tiers: string[];
    tripped_tiers: string[];
}

export interface NodeInfo {
    node_id: string;
    status: string;
    gpu_utilization?: number;
    vram_used_mb?: number;
    vram_total_mb?: number;
    latency_ms: number;
    last_seen: number;
    provider?: string;
    models?: string[];
}

export interface AgentInfo {
    agent_id: string;
    status: string;
    node_id?: string;
    tasks_completed: number;
    tasks_failed: number;
    uptime?: number;
    uptime_seconds?: number;
    alive?: boolean;
    config?: Record<string, unknown>;
}

export interface TaskResult {
    task_id: string;
    status: string;
    result?: {
        response?: string;
        model?: string;
        error?: string;
        status?: string;
    };
    error?: string;
    assigned_agent?: string;
}

export interface SettingsMap {
    [key: string]: unknown;
}

export class SwarmClient {
    private baseUrl: string;
    private _consecutiveFailures = 0;
    private _circuitOpen = false;
    private _circuitResetTimer: NodeJS.Timeout | null = null;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    setBaseUrl(url: string) {
        this.baseUrl = url;
    }

    getBaseUrl(): string {
        return this.baseUrl;
    }

    private _openCircuit(): void {
        this._circuitOpen = true;
        console.warn(`[SwarmClient] Circuit breaker opened after ${this._consecutiveFailures} consecutive failures. Cooling down for 30s.`);
        if (this._circuitResetTimer) {
            clearTimeout(this._circuitResetTimer);
        }
        this._circuitResetTimer = setTimeout(() => {
            this._circuitOpen = false;
            this._consecutiveFailures = 0;
            console.warn('[SwarmClient] Circuit breaker reset. Resuming requests.');
        }, 30000);
    }

    async request(path: string, options?: RequestInit): Promise<any | null> {
        if (this._circuitOpen) {
            console.warn('[SwarmClient] Circuit breaker is OPEN — skipping request to', path);
            return null;
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        try {
            const res = await fetch(`${this.baseUrl}${path}`, {
                cache: 'no-store',
                signal: controller.signal,
                ...options,
            } as any);
            clearTimeout(timeoutId);

            if (!res.ok) {
                this._consecutiveFailures++;
                console.error(`[SwarmClient] HTTP ${res.status} on ${path} (failure ${this._consecutiveFailures})`);
                if (this._consecutiveFailures >= 5) {
                    this._openCircuit();
                }
                return null;
            }

            this._consecutiveFailures = 0;
            return await res.json();
        } catch (err) {
            clearTimeout(timeoutId);
            this._consecutiveFailures++;
            console.error(`[SwarmClient] Exception on ${path}:`, err, `(failure ${this._consecutiveFailures})`);
            if (this._consecutiveFailures >= 5) {
                this._openCircuit();
            }
            return null;
        }
    }

    private async get(path: string): Promise<any | null> {
        return this.request(path, { method: 'GET' });
    }

    private async post(path: string, body?: any): Promise<any | null> {
        return this.request(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined,
        });
    }

    private async put(path: string, body?: any): Promise<any | null> {
        return this.request(path, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined,
        });
    }

    private async del(path: string): Promise<any | null> {
        return this.request(path, { method: 'DELETE' });
    }

    async health(): Promise<{ status: string } | null> {
        return this.get('/health');
    }

    async getStatus(): Promise<SwarmStatus | null> {
        return this.get('/swarm/status');
    }

    async getRoutingConfig(): Promise<RoutingConfig | null> {
        return this.get('/routing/config');
    }

    async getNodes(): Promise<NodeInfo[] | null> {
        return this.get('/nodes/');
    }

    async getAgents(): Promise<AgentInfo[] | null> {
        return this.get('/swarm/agents');
    }

    async getAgent(agentId: string): Promise<AgentInfo | null> {
        return this.get(`/swarm/agents/${agentId}`);
    }

    async getAgentConfig(agentId: string): Promise<{ config: Record<string, unknown> } | null> {
        return this.get(`/swarm/agents/${agentId}/config`);
    }

    async setAgentConfig(agentId: string, config: Record<string, unknown>): Promise<any | null> {
        return this.put(`/swarm/agents/${agentId}/config`, { config });
    }

    async killAgent(agentId: string): Promise<any | null> {
        return this.post(`/swarm/agents/${agentId}/kill`);
    }

    async removeAgent(agentId: string): Promise<any | null> {
        return this.del(`/swarm/agents/${agentId}`);
    }

    async spawnAgents(count: number, config?: Record<string, unknown>): Promise<any | null> {
        return this.post('/swarm/agents/spawn', { count, config });
    }

    async getTask(taskId: string): Promise<TaskResult | null> {
        return this.get(`/swarm/tasks/${taskId}`);
    }

    async getActiveTasks(): Promise<any[] | null> {
        return this.get('/swarm/tasks/active');
    }

    async getModels(): Promise<string[] | null> {
        return this.get('/swarm/models');
    }

    async getSettings(): Promise<SettingsMap | null> {
        return this.get('/settings');
    }

    async updateSettings(updates: SettingsMap): Promise<SettingsMap | null> {
        return this.put('/settings', updates);
    }

    async resetSettings(): Promise<SettingsMap | null> {
        return this.post('/settings/reset');
    }

    async setThreshold(value: number): Promise<any | null> {
        return this.post('/routing/threshold', { threshold: value });
    }

    async forceLocal(): Promise<any | null> {
        return this.post('/routing/force-local');
    }

    async forceCloud(): Promise<any | null> {
        return this.post('/routing/force-cloud');
    }

    async autoBalance(): Promise<any | null> {
        return this.post('/routing/auto');
    }

    async infer(prompt: string, model?: string, temperature?: number, mode?: string, messages?: any[]): Promise<any | null> {
        return this.post('/routing/infer', {
            prompt,
            model_hint: model,
            temperature: temperature ?? 0.7,
            mode: mode ?? 'agent',
            messages: messages ?? [],
        });
    }

    async activateSwarm(): Promise<any | null> {
        return this.post('/swarm/activate');
    }

    async shutdownSwarm(): Promise<any | null> {
        return this.post('/swarm/shutdown');
    }

    async remoteType(text: string, interval?: number): Promise<any | null> {
        return this.post('/remote/type', { text, interval: interval ?? 0.01 });
    }

    async remoteClick(x: number, y: number, button?: string, clicks?: number): Promise<any | null> {
        return this.post('/remote/click', { x, y, button: button ?? 'left', clicks: clicks ?? 1 });
    }

    async remoteKeys(keys: string): Promise<any | null> {
        return this.post('/remote/keys', { keys });
    }

    async remoteShell(command: string, cwd?: string, timeout?: number): Promise<any | null> {
        return this.post('/remote/shell', { command, cwd, timeout: timeout ?? 30 });
    }

    async remoteScroll(clicks: number, x?: number, y?: number): Promise<any | null> {
        return this.post('/remote/scroll', { clicks, x, y });
    }

    async remoteDrag(x1: number, y1: number, x2: number, y2: number, duration?: number, button?: string): Promise<any | null> {
        return this.post('/remote/drag', { x1, y1, x2, y2, duration: duration ?? 0.5, button: button ?? 'left' });
    }

    async remoteScreenshot(): Promise<{ success: boolean; image_base64: string; width: number; height: number } | null> {
        return this.get('/remote/screenshot');
    }

    async remoteStatus(nodeId?: string): Promise<any | null> {
        return nodeId ? this.get(`/mesh/remote/${nodeId}/status`) : this.get('/remote/status');
    }

    async remoteLogs(nodeId?: string, lines: number = 50, logfile: string = 'backend'): Promise<any | null> {
        return nodeId
            ? this.get(`/mesh/remote/${nodeId}/logs?lines=${lines}&logfile=${logfile}`)
            : this.get(`/remote/logs?lines=${lines}&logfile=${logfile}`);
    }

    async remoteProcesses(nodeId?: string, filter?: string): Promise<any | null> {
        const q = filter ? `?filter=${filter}` : '';
        return nodeId ? this.get(`/mesh/remote/${nodeId}/processes${q}`) : this.get(`/remote/processes${q}`);
    }

    async remoteInject(prompt: string, model?: string, mode?: string, nodeId?: string): Promise<any | null> {
        const body = { prompt, model, mode: mode ?? 'agent' };
        return nodeId
            ? this.post(`/mesh/remote/${nodeId}/inject`, body)
            : this.post('/remote/inject', body);
    }

    async getTransfers(): Promise<any[] | null> {
        return this.get('/transfers');
    }

    // -----------------------------------------------------------------------
    // Cleanup tools
    // ELI5: Like the building maintenance team's work orders.
    //       They audit every floor, find the overloaded circuits,
    //       and only flip breakers after the safety check.
    // -----------------------------------------------------------------------
    async cleanupAnalyze(drive: string = 'C:/'): Promise<any | null> {
        return this.post('/tools/cleanup/analyze', { drive });
    }

    async cleanupGames(drive: string = 'C:/'): Promise<any | null> {
        return this.post('/tools/cleanup/games', { drive });
    }

    async cleanupLargeFiles(drive: string = 'C:/', minSizeMb: number = 100, maxFiles: number = 200): Promise<any | null> {
        return this.post('/tools/cleanup/large-files', { drive, min_size_mb: minSizeMb, max_files: maxFiles });
    }

    async cleanupSafety(drive: string = 'C:/'): Promise<any | null> {
        return this.post('/tools/cleanup/safety', { drive });
    }

    async cleanupExecute(targets: { path: string; force?: boolean }[]): Promise<any | null> {
        return this.post('/tools/cleanup/execute', { targets });
    }

    // Mesh-forwarded cleanup (remote node)
    async meshCleanupAnalyze(nodeId: string, drive: string = 'C:/'): Promise<any | null> {
        return this.post(`/mesh/remote/${nodeId}/cleanup/analyze`, { drive });
    }

    async meshCleanupGames(nodeId: string, drive: string = 'C:/'): Promise<any | null> {
        return this.post(`/mesh/remote/${nodeId}/cleanup/games`, { drive });
    }

    async meshCleanupLargeFiles(nodeId: string, drive: string = 'C:/', minSizeMb: number = 100, maxFiles: number = 200): Promise<any | null> {
        return this.post(`/mesh/remote/${nodeId}/cleanup/large-files`, { drive, min_size_mb: minSizeMb, max_files: maxFiles });
    }

    async meshCleanupSafety(nodeId: string, drive: string = 'C:/'): Promise<any | null> {
        return this.post(`/mesh/remote/${nodeId}/cleanup/safety`, { drive });
    }

    async meshCleanupExecute(nodeId: string, targets: { path: string; force?: boolean }[]): Promise<any | null> {
        return this.post(`/mesh/remote/${nodeId}/cleanup/execute`, { targets });
    }

    // -----------------------------------------------------------------------
    // SimplePod Unified Pipeline
    // ELI5: The new smart-home automation wing of the building.
    //       Control the 20-node swarm, submit goals, and check status.
    // -----------------------------------------------------------------------
    async unifiedStart(): Promise<any | null> {
        return this.post('/unified/pipeline/start');
    }

    async unifiedStop(): Promise<any | null> {
        return this.post('/unified/pipeline/stop');
    }

    async unifiedStatus(): Promise<any | null> {
        return this.get('/unified/pipeline/status');
    }

    async unifiedGoal(goal: string): Promise<any | null> {
        return this.post('/unified/goal', { goal });
    }

    async unifiedWorkers(): Promise<any | null> {
        return this.get('/unified/workers');
    }

    async unifiedSelfHeal(targetPath: string = '.'): Promise<any | null> {
        return this.post('/unified/selfheal/run', { target_path: targetPath });
    }

    async unifiedVisionAnalyze(): Promise<any | null> {
        return this.post('/unified/vision/analyze');
    }

    async unifiedOSClick(x: number, y: number, button: string = 'left'): Promise<any | null> {
        return this.post('/unified/os/click', { x, y, button });
    }

    async unifiedOSType(text: string): Promise<any | null> {
        return this.post('/unified/os/type', { text });
    }

    // -----------------------------------------------------------------------
    // Demo / Test Endpoints (No LLM Required)
    // -----------------------------------------------------------------------
    async demoPhoneContacts(): Promise<any | null> {
        return this.get('/unified/demo/phone/contacts');
    }

    async demoPhoneThreads(): Promise<any | null> {
        return this.get('/unified/demo/phone/threads');
    }

    async demoPhoneThread(threadId: string): Promise<any | null> {
        return this.get(`/unified/demo/phone/thread/${threadId}`);
    }

    async demoPhoneAnalyze(): Promise<any | null> {
        return this.get('/unified/demo/phone/analyze');
    }

    async demoLLMTest(prompt: string): Promise<any | null> {
        return this.post('/unified/demo/llm-test', { prompt, use_fallback: true });
    }

    async orbitscribeAnalyze(mode: string = 'synthetic'): Promise<any | null> {
        return this.get(`/unified/demo/orbitscribe/analyze?mode=${mode}`);
    }
}
