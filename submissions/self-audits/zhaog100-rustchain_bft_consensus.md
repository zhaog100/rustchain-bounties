# Self-Audit: node/rustchain_bft_consensus.py

## Wallet
RTC-prefix-40-hex

## Module reviewed
- Path: `node/rustchain_bft_consensus.py`
- Commit: latest (2026-04-30)
- Lines reviewed: 1–1113 (full file)

## Deliverable: 3 specific findings

1. **`/bft/propose` endpoint has no authentication — anyone can submit epoch settlements**
   - Severity: high
   - Location: `rustchain_bft_consensus.py:1055–1074` (`bft_propose` route)
   - Description: The `/bft/propose` Flask endpoint accepts arbitrary epoch/miners/distribution from any caller with zero auth. It calls `propose_epoch_settlement()` which only checks `is_leader()`, but if the leader node is compromised or an attacker has network access, they can propose fraudulent distributions. No rate limiting, no HMAC, no token.
   - Reproduction: `curl -X POST http://node-131:8099/bft/propose -H 'Content-Type: application/json' -d '{"epoch":999,"miners":[{"miner_id":"attacker","device_arch":"modern","weight":999}],"distribution":{"attacker":1.5}}'` — proposal enters consensus pipeline immediately.

2. **`_apply_settlement` idempotency guard can be bypassed — double-credit risk**
   - Severity: high
   - Location: `rustchain_bft_consensus.py:763–797` (`_apply_settlement`)
   - Description: Idempotency relies solely on checking `SELECT 1 FROM ledger WHERE memo = 'epoch_{epoch}_bft'`. This is fragile because: (a) if a node restarts before the `committed_epochs` set is restored, `_finalize_epoch` → `_apply_settlement` could be called again; (b) the ledger check only looks for *any* entry with that memo — if a manual ledger edit changes the memo format, the guard fails silently; (c) `committed_epochs` is an in-memory set only, not persisted atomically with the settlement.
   - Reproduction: 1) Start node, let epoch 42 settle (ledger entries written). 2) Stop node, manually delete ledger entries for epoch 42. 3) Restart node, `committed_epochs` restored from DB. 4) Trigger epoch 42 again (e.g., via `/bft/propose`). Settlement applies a second time — double-credit.

3. **View-change prepared certificate always `None` — safety violation risk**
   - Severity: medium
   - Location: `rustchain_bft_consensus.py:834` (`_trigger_view_change`) and `rustchain_bft_consensus.py:852–893` (`handle_view_change`)
   - Description: PBFT requires view-change messages to carry a prepared certificate (highest-prepared sequence number + matching PREPARE messages from 2f+1 nodes) so the new leader can reconstruct the correct state. This implementation always sends `prepared_cert=None`. A Byzantine node that becomes leader after a view change has no obligation to honor previously-prepared epochs, enabling it to roll back committed state or forge proposals for epochs that already achieved quorum.
   - Reproduction: In a 4-node network, kill the leader after it sends PRE-PREPARE for epoch 100 but before consensus completes. View change triggers; new leader has no prepared certificate, so it cannot verify what epoch 100's proposal was and can propose a different one.

## Known failures of this audit
- Did not test the Flask integration end-to-end (e.g., whether `create_bft_routes` is actually mounted in the main app)
- Did not verify the HMAC key derivation from `secret_key` — assumed `hmac.new(key, node_id.encode(), hashlib.sha256).digest()` is used consistently
- Did not check for CSRF/XSS on the Flask routes (no CSRF tokens, no Content-Security-Policy headers)
- Network broadcast is synchronous and blocking — if one peer is slow, all others are delayed, but I didn't measure real-world impact

## Confidence
- Overall confidence: 0.72
- Per-finding confidence: [0.92, 0.78, 0.85]

## What I would test next
- Run a 4-node BFT cluster with one Byzantine node proposing fraudulent settlements; verify honest nodes reject it
- Test view-change safety: kill leader mid-consensus, verify new leader proposes the same epoch (or correctly recovers)
- Fuzz the `/bft/message` endpoint with malformed JSON, missing fields, and oversized payloads to find crash vectors
