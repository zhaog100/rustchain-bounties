import * as vscode from 'vscode';
import axios from 'axios';

interface WalletBalance {
  ok: boolean;
  balance: number;
  error?: string;
}

interface MinerStatus {
  name: string;
  status: string;
  lastSeen?: string;
}

interface EpochInfo {
  epoch: number;
  endTime?: string;
}

interface Bounty {
  number: number;
  title: string;
  reward: string;
  url: string;
}

let walletStatusBar: vscode.StatusBarItem;
let refreshTimer: NodeJS.Timeout | undefined;

export function activate(context: vscode.ExtensionContext) {
  console.log('RustChain Dashboard is now active');

  // Create status bar item
  walletStatusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  walletStatusBar.command = 'rustchain.setWallet';
  context.subscriptions.push(walletStatusBar);

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand('rustchain.refresh', refreshData)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand('rustchain.setWallet', setWallet)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand('rustchain.claimBounty', claimBounty)
  );

  // Register views
  const walletProvider = new WalletProvider();
  vscode.window.registerTreeDataProvider('rustchainWallet', walletProvider);

  const minerProvider = new MinerProvider();
  vscode.window.registerTreeDataProvider('rustchainMiner', minerProvider);

  const bountyProvider = new BountyProvider();
  vscode.window.registerTreeDataProvider('rustchainBounties', bountyProvider);

  const epochProvider = new EpochProvider();
  vscode.window.registerTreeDataProvider('rustchainEpoch', epochProvider);

  // Initial refresh
  refreshData();

  // Auto-refresh
  const interval = vscode.workspace.getConfiguration('rustchain').get('refreshInterval', 60);
  startAutoRefresh(interval * 1000);
}

function getNodeUrl(): string {
  return vscode.workspace.getConfiguration('rustchain').get('nodeUrl', 'https://50.28.86.131:8099');
}

function getWalletName(): string {
  return vscode.workspace.getConfiguration('rustchain').get('walletName', '');
}

async function refreshData() {
  const walletName = getWalletName();
  const nodeUrl = getNodeUrl();

  if (!walletName) {
    walletStatusBar.text = '💰 Set Wallet';
    walletStatusBar.tooltip = 'Click to set your RustChain wallet name';
    walletStatusBar.show();
    return;
  }

  try {
    // Fetch wallet balance
    const balanceResp = await axios.get<WalletBalance>(`${nodeUrl}/wallet/balance`, {
      params: { miner: walletName },
      timeout: 5000
    });

    if (balanceResp.data.ok) {
      const balance = balanceResp.data.balance;
      walletStatusBar.text = `💰 ${balance.toFixed(2)} RTC`;
      walletStatusBar.tooltip = `RustChain Wallet: ${walletName}\nBalance: ${balance} RTC\n≈ $${(balance * 0.10).toFixed(2)} USD`;
      walletStatusBar.show();
    } else {
      walletStatusBar.text = '❌ Error';
      walletStatusBar.tooltip = `Error: ${balanceResp.data.error}`;
    }
  } catch (error: any) {
    walletStatusBar.text = '⚠️ Offline';
    walletStatusBar.tooltip = `Node offline: ${error.message}`;
  }

  // Refresh tree views
  vscode.commands.executeCommand('rustchain.refreshWallet');
  vscode.commands.executeCommand('rustchain.refreshMiner');
  vscode.commands.executeCommand('rustchain.refreshBounties');
  vscode.commands.executeCommand('rustchain.refreshEpoch');
}

async function setWallet() {
  const walletName = await vscode.window.showInputBox({
    prompt: 'Enter your RustChain wallet name',
    placeHolder: 'my-wallet',
    value: getWalletName()
  });

  if (walletName) {
    await vscode.workspace.getConfiguration('rustchain').update('walletName', walletName, vscode.ConfigurationTarget.Global);
    vscode.window.showInformationMessage(`RustChain wallet set to: ${walletName}`);
    refreshData();
  }
}

async function claimBounty() {
  const bountyUrl = 'https://github.com/Scottcjn/rustchain-bounties/issues';
  vscode.env.openExternal(vscode.Uri.parse(bountyUrl));
  vscode.window.showInformationMessage('Opening RustChain bounty board...');
}

function startAutoRefresh(intervalMs: number) {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  refreshTimer = setInterval(refreshData, intervalMs);
}

// Tree Providers
class WalletProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<vscode.TreeItem[]> {
    const walletName = getWalletName();
    if (!walletName) {
      return [new vscode.TreeItem('Set wallet name in settings', vscode.TreeItemCollapsibleState.None)];
    }

    try {
      const resp = await axios.get<WalletBalance>(`${getNodeUrl()}/wallet/balance`, {
        params: { miner: walletName },
        timeout: 5000
      });

      if (resp.data.ok) {
        const balance = resp.data.balance;
        const item = new vscode.TreeItem(`${balance.toFixed(4)} RTC`, vscode.TreeItemCollapsibleState.None);
        item.iconPath = new vscode.ThemeIcon('coin');
        item.description = `≈ $${(balance * 0.10).toFixed(2)} USD`;
        return [item];
      } else {
        return [new vscode.TreeItem(`Error: ${resp.data.error}`, vscode.TreeItemCollapsibleState.None)];
      }
    } catch (error: any) {
      return [new vscode.TreeItem(`Node offline: ${error.message}`, vscode.TreeItemCollapsibleState.None)];
    }
  }
}

class MinerProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<vscode.TreeItem[]> {
    try {
      const resp = await axios.get<{ ok: boolean; miners: MinerStatus[] }>(`${getNodeUrl()}/miners/list`, {
        timeout: 5000
      });

      if (resp.data.ok && resp.data.miners.length > 0) {
        return resp.data.miners.slice(0, 5).map(miner => {
          const item = new vscode.TreeItem(miner.name, vscode.TreeItemCollapsibleState.None);
          item.iconPath = new vscode.ThemeIcon(miner.status === 'online' ? 'debug-start' : 'debug-stop');
          item.description = miner.status;
          return item;
        });
      } else {
        return [new vscode.TreeItem('No active miners', vscode.TreeItemCollapsibleState.None)];
      }
    } catch (error: any) {
      return [new vscode.TreeItem(`Error: ${error.message}`, vscode.TreeItemCollapsibleState.None)];
    }
  }
}

class BountyProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<vscode.TreeItem[]> {
    // Static list of featured bounties (would fetch from API in production)
    const bounties: Bounty[] = [
      { number: 2864, title: 'GitHub Action for RTC Awards', reward: '20 RTC', url: 'https://github.com/Scottcjn/rustchain-bounties/issues/2864' },
      { number: 2869, title: 'Telegram Bot', reward: '10 RTC', url: 'https://github.com/Scottcjn/rustchain-bounties/issues/2869' },
      { number: 2958, title: 'Contributions Showcase', reward: '15 RTC', url: 'https://github.com/Scottcjn/rustchain-bounties/issues/2958' },
    ];

    return bounties.map(bounty => {
      const item = new vscode.TreeItem(`#${bounty.number}: ${bounty.title}`, vscode.TreeItemCollapsibleState.None);
      item.iconPath = new vscode.ThemeIcon('gift');
      item.description = bounty.reward;
      item.command = {
        command: 'vscode.open',
        title: 'Open Bounty',
        arguments: [vscode.Uri.parse(bounty.url)]
      };
      return item;
    });
  }
}

class EpochProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<vscode.TreeItem[]> {
    try {
      const resp = await axios.get<EpochInfo>(`${getNodeUrl()}/epoch/current`, {
        timeout: 5000
      });

      if (resp.data.ok) {
        const item = new vscode.TreeItem(`Epoch ${resp.data.epoch}`, vscode.TreeItemCollapsibleState.None);
        item.iconPath = new vscode.ThemeIcon('clock');
        item.description = resp.data.endTime ? `Ends: ${resp.data.endTime}` : 'Active';
        return [item];
      } else {
        return [new vscode.TreeItem('Epoch info unavailable', vscode.TreeItemCollapsibleState.None)];
      }
    } catch (error: any) {
      return [new vscode.TreeItem(`Error: ${error.message}`, vscode.TreeItemCollapsibleState.None)];
    }
  }
}

export function deactivate() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
}
