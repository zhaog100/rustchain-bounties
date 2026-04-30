const core = require('@actions/core');
const github = require('@actions/github');
const https = require('https');

// --- Wallet extraction ---

/**
 * Extract RTC wallet from PR body using multiple patterns.
 * Supports: "wallet: RTC...", "Wallet: RTC...", code blocks, etc.
 */
function extractWalletFromPRBody(body) {
  if (!body) return null;

  const patterns = [
    // Standard: wallet: RTC... or Wallet: RTC...
    /(?:wallet|rtc\s*wallet)\s*[:=]\s*(RTC[0-9a-fA-F]{30,})/gi,
    // Code block: ``` ... RTC... ```
    /```[\s\S]*?(RTC[0-9a-fA-F]{30,})[\s\S]*?```/gi,
    // Inline code: `RTC...`
    /`(RTC[0-9a-fA-F]{30,})`/g,
    // Bare RTC address (42+ chars after RTC prefix)
    /\b(RTC[0-9a-fA-F]{40,})\b/g,
    // Old format: wallet address line
    /wallet\s*address\s*[:=]\s*(RTC[0-9a-fA-F]{30,})/gi,
    // YAML front matter style
    /^wallet:\s*(RTC[0-9a-fA-F]{30,})/gim,
  ];

  for (const pattern of patterns) {
    pattern.lastIndex = 0; // reset
    const match = pattern.exec(body);
    if (match && match[1]) {
      const wallet = match[1].trim();
      // Validate: must start with RTC and have reasonable length
      if (wallet.startsWith('RTC') && wallet.length >= 42 && /^[RTC0-9a-fA-F]+$/.test(wallet)) {
        core.info(`Wallet extracted via pattern: ${pattern.source.substring(0, 40)}...`);
        return wallet;
      }
    }
  }

  return null;
}

/**
 * Sanitize wallet address: strip whitespace, uppercase 'RTC' prefix
 */
function sanitizeWallet(wallet) {
  if (!wallet) return null;
  wallet = wallet.trim();
  if (wallet.startsWith('rtc')) {
    wallet = 'RTC' + wallet.slice(3);
  }
  return wallet;
}

// --- HTTP helper (no external deps) ---

function httpRequest(options, body = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, data });
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(15000, () => { req.destroy(new Error('Request timeout')); });
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

// --- Retry wrapper ---

async function withRetry(fn, maxRetries = 3, baseDelayMs = 1000) {
  let lastError;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      if (attempt < maxRetries) {
        const delay = baseDelayMs * Math.pow(2, attempt - 1);
        core.warning(`Attempt ${attempt}/${maxRetries} failed: ${err.message}. Retrying in ${delay}ms...`);
        await new Promise(r => setTimeout(r, delay));
      }
    }
  }
  throw lastError;
}

// --- RTC transaction ---

async function sendRtcTransaction(nodeUrl, from, to, amount, adminKey) {
  const url = new URL('/api/transfer', nodeUrl);
  
  const payload = {
    from,
    to,
    amount: parseFloat(amount),
    memo: `bounty-reward-pr-merge`
  };

  const response = await withRetry(async () => {
    return httpRequest({
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-admin-key': adminKey,
        'x-wallet-from': from
      },
    }, payload);
  }, 3, 2000);

  if (response.status !== 200) {
    throw new Error(`Node returned ${response.status}: ${JSON.stringify(response.data)}`);
  }

  const txHash = response.data?.tx_hash || response.data?.hash || response.data?.transaction?.hash;
  if (!txHash) {
    throw new Error(`No transaction hash in response: ${JSON.stringify(response.data)}`);
  }

  return txHash;
}

// --- PR Comment ---

async function commentOnPR(octokit, owner, repo, prNumber, body) {
  await octokit.rest.issues.createComment({
    owner,
    repo,
    issue_number: prNumber,
    body
  });
}

// --- Fill comment template ---

function fillTemplate(template, vars) {
  let result = template;
  for (const [key, value] of Object.entries(vars)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), value || '');
  }
  return result;
}

// --- Main ---

async function run() {
  try {
    const nodeUrl = core.getInput('node-url') || 'https://50.28.86.131';
    const amount = core.getInput('amount') || '5';
    const walletFrom = core.getInput('wallet-from');
    const adminKey = core.getInput('admin-key');
    const dryRun = core.getInput('dry-run').toLowerCase() === 'true';
    const githubToken = core.getInput('github-token') || process.env.GITHUB_TOKEN;

    // Validate required inputs
    if (!walletFrom) core.setFailed('wallet-from is required');
    if (!adminKey && !dryRun) core.setFailed('admin-key is required (unless dry-run)');

    const context = github.context;
    const pr = context.payload?.pull_request;

    if (!pr) {
      core.info('No pull_request event. Exiting.');
      return;
    }

    if (!pr.merged) {
      core.info('PR not merged. Exiting.');
      return;
    }

    const prNumber = pr.number;
    const repo = context.repo;
    const prBody = pr.body || '';
    const prAuthor = pr.user?.login;

    core.info(`Processing merged PR #${prNumber} by @${prAuthor}`);

    // Extract wallet
    let contributorWallet = sanitizeWallet(extractWalletFromPRBody(prBody));

    // Fallback: try to fetch .rtc-wallet file from PR head
    if (!contributorWallet) {
      try {
        const octo = github.getOctokit(githubToken);
        const { data } = await octo.rest.repos.getContent({
          owner: repo.owner,
          repo: repo.repo,
          path: '.rtc-wallet',
          ref: pr.head.sha
        });
        if (data.content) {
          const decoded = Buffer.from(data.content, 'base64').toString('utf8').trim();
          contributorWallet = sanitizeWallet(decoded);
          if (contributorWallet) {
            core.info(`Wallet found in .rtc-wallet file: ${contributorWallet}`);
          }
        }
      } catch (err) {
        if (err.status !== 404) {
          core.warning(`Failed to fetch .rtc-wallet: ${err.message}`);
        }
      }
    }

    // Fallback: check PR comments for wallet
    if (!contributorWallet && githubToken) {
      try {
        const octo = github.getOctokit(githubToken);
        const { data: comments } = await octo.rest.issues.listComments({
          owner: repo.owner,
          repo: repo.repo,
          issue_number: prNumber
        });
        for (const comment of comments) {
          const wallet = extractWalletFromPRBody(comment.body);
          if (wallet) {
            contributorWallet = sanitizeWallet(wallet);
            if (contributorWallet) {
              core.info(`Wallet found in PR comment: ${contributorWallet}`);
              break;
            }
          }
        }
      } catch (err) {
        core.warning(`Failed to check PR comments: ${err.message}`);
      }
    }

    if (!contributorWallet) {
      core.warning('No contributor wallet found in PR body, .rtc-wallet, or comments');
      const skipComment = fillTemplate(
        core.getInput('comment-on-skip'),
        { pr: String(prNumber) }
      );
      if (skipComment && githubToken) {
        await commentOnPR(github.getOctokit(githubToken), repo.owner, repo.repo, prNumber, skipComment);
      }
      core.setOutput('skipped', 'true');
      core.setOutput('reason', 'no-wallet-found');
      return;
    }

    core.info(`Contributor wallet: ${contributorWallet}`);
    core.info(`Amount: ${amount} RTC`);

    if (dryRun) {
      core.info('🧪 DRY RUN mode — no transaction sent');
      const dryComment = fillTemplate(
        core.getInput('comment-on-dryrun'),
        { amount, wallet: contributorWallet, pr: String(prNumber) }
      );
      if (dryComment && githubToken) {
        await commentOnPR(github.getOctokit(githubToken), repo.owner, repo.repo, prNumber, dryComment);
      }
      core.setOutput('dry-run', 'true');
      core.setOutput('wallet', contributorWallet);
      core.setOutput('amount', amount);
      return;
    }

    // Send transaction
    core.info(`Sending ${amount} RTC from ${walletFrom} to ${contributorWallet}`);
    const txHash = await sendRtcTransaction(nodeUrl, walletFrom, contributorWallet, amount, adminKey);

    core.info(`Transaction successful: ${txHash}`);

    const successComment = fillTemplate(
      core.getInput('comment-on-success'),
      { amount, wallet: contributorWallet, tx: txHash, pr: String(prNumber) }
    );
    if (successComment && githubToken) {
      await commentOnPR(github.getOctokit(githubToken), repo.owner, repo.repo, prNumber, successComment);
    }

    core.setOutput('transaction-hash', txHash);
    core.setOutput('wallet', contributorWallet);
    core.setOutput('amount', amount);
    core.setOutput('pr-number', String(prNumber));
    core.info(`✅ Awarded ${amount} RTC to ${contributorWallet} (tx: ${txHash})`);

  } catch (error) {
    core.setFailed(`rtc-reward-action failed: ${error.message}`);
  }
}

run();
