import * as vscode from 'vscode';
import { SwarmClient } from '../api/client';

export class TransferTreeProvider implements vscode.TreeDataProvider<TransferItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<TransferItem | undefined | void> = new vscode.EventEmitter<TransferItem | undefined | void>();
    readonly onDidChangeTreeData: vscode.Event<TransferItem | undefined | void> = this._onDidChangeTreeData.event;
    private _client?: SwarmClient;
    private _timer?: NodeJS.Timeout;

    setClient(client: SwarmClient) {
        this._client = client;
        this.refresh();
    }

    startPolling(intervalMs: number = 5000) {
        if (this._timer) { clearInterval(this._timer); }
        this._timer = setInterval(() => this.refresh(), intervalMs);
    }

    stopPolling() {
        if (this._timer) { clearInterval(this._timer); }
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: TransferItem): vscode.TreeItem {
        return element;
    }

    async getChildren(): Promise<TransferItem[]> {
        if (!this._client) {
            return [new TransferItem('Not connected', '', 'offline', '$(plug)')];
        }
        const transfers = await this._client.getTransfers();
        if (!transfers || !transfers.length) {
            return [new TransferItem('No transfers', '', 'idle', '$(info)')];
        }
        return transfers.map((t: any) => new TransferItem(
            t.id || t.transfer_id || 'unknown',
            t.target || t.node_id || 'unknown',
            t.status || 'unknown',
            t.status === 'completed' ? '$(check)' : t.status === 'failed' ? '$(error)' : '$(sync~spin)'
        ));
    }
}

class TransferItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly target: string,
        public readonly status: string,
        public readonly icon: string,
    ) {
        super(label, vscode.TreeItemCollapsibleState.None);
        this.tooltip = target ? `${label} → ${target}` : label;
        this.description = target ? `${status} → ${target}` : status;
        this.iconPath = new vscode.ThemeIcon(icon.replace('$(', '').replace(')', ''));
        this.contextValue = 'transfer';
    }
}
