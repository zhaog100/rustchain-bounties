# Self-Audit: node/utxo_db.py

## Wallet
RTC019e78d600fb3131c29d7ba80aba8fe644be426e

## Module reviewed
- Path: `node/utxo_db.py`
- Commit: `Scottcjn/Rustchain` HEAD (2026-04-30)
- Lines reviewed: 1–898 (full file)

## Deliverable: 3 specific findings

1. **`mempool_add` references undefined `manage_tx` variable causing NameError and DB lock leak**
   - Severity: high
   - Location: `utxo_db.py:710–760` (mempool_add function, multiple rollback sites)
   - Description: The variable `manage_tx` is never defined in `mempool_add()`. It exists in `apply_transaction()` (line ~400) but was not carried over. Every validation failure after `BEGIN IMMEDIATE` raises `NameError` instead of rolling back. The `except Exception` block also references `manage_tx`, causing a second `NameError`, so `ROLLBACK` never executes.
   - Reproduction: Submit a mempool transaction with a duplicate input box_id: the double-spend check finds an existing entry, tries `if manage_tx: conn.execute("ROLLBACK")` → `NameError: name 'manage_tx' is not defined`. The transaction lock is not released, causing subsequent operations to hang (30s timeout).

2. **`address_to_proposition` has no input length validation — OOM and DB bloat risk**
   - Severity: medium
   - Location: `utxo_db.py:70` (address_to_proposition function)
   - Description: No maximum length is enforced on the `address` parameter. An attacker can pass a multi-megabyte string: `address.encode('utf-8')` creates a large bytes object, `.hex()` doubles it, and it's stored in `utxo_boxes.proposition` TEXT column.
   - Reproduction: Call `add_box({"address": "A" * 10_000_000, ...})` — the proposition becomes a 20MB hex string stored in the database.

3. **`integrity_check` is not atomic — opens second connection for state root**
   - Severity: medium
   - Location: `utxo_db.py:650–680` (integrity_check calls compute_state_root)
   - Description: `integrity_check()` opens one connection to compute total balance and box count, then calls `compute_state_root()` which opens a second connection. Between these queries, another transaction could spend/create boxes, meaning the two values come from different database snapshots.
   - Reproduction: Start `integrity_check()`, concurrently apply a transaction that spends 10 boxes. The `total_unspent_nrtc` reflects pre-spend state, while `state_root` reflects post-spend state. The integrity check reports inconsistent data.

## Known failures of this audit
- Did not verify the Merkle tree implementation against the specification in the Rust-based `rustchain-core/ledger/utxo_ledger.py` — cross-language parity is assumed correct
- The `coin_select()` function at module level is not integrated with the UtxoDB class; I did not trace all callers to determine if stale UTXO selection is a real issue
- Did not test concurrent mempool operations under high load — the `BEGIN IMMEDIATE` usage in mempool is correct but performance under contention is unknown
- Confidence on the `proposition_to_address` `errors='ignore'` finding is lower — this is a display/UI concern, not a consensus-level vulnerability

## Confidence
- Overall confidence: 0.80
- Per-finding confidence: [0.95, 0.80, 0.70]

## What I would test next
- Write a concurrent test: 10 threads calling `mempool_add` simultaneously with overlapping inputs, verify no deadlocks or double-spend acceptance
- Test the NameError fix: after defining `manage_tx`, verify mempool rejection properly rolls back and releases locks
- Verify `compute_state_root()` produces identical results across all nodes with the same UTXO set (determinism test)
