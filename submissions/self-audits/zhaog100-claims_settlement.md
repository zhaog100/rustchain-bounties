# Self-Audit: node/claims_settlement.py

## Wallet
RTC-prefix-40-hex

## Module reviewed
- Path: `node/claims_settlement.py`
- Commit: latest (2026-04-30)
- Lines reviewed: 1–656 (full file)

## Deliverable: 3 specific findings

1. **`check_rewards_pool_balance` assumes sufficient funds on database error — unlimited payout risk**
   - Severity: high
   - Location: `claims_settlement.py:127–139` (`check_rewards_pool_balance`)
   - Description: When the `rewards_pool` table doesn't exist or any `sqlite3.Error` occurs, the function returns `(True, required_urtc * 10)` — effectively saying "we have 10x the required balance." This means if the database is corrupted, the table is renamed, or the query fails for any reason, settlements proceed without any actual balance check. An attacker who can trigger a database error (e.g., by locking the database with a concurrent transaction) could drain the rewards pool.
   - Reproduction: 1) Start a long-running transaction that locks the `rewards_pool` table: `BEGIN IMMEDIATE; SELECT * FROM rewards_pool;` (don't commit). 2) Call `process_claims_batch()` in another process. 3) `check_rewards_pool_balance` fails with a database error, returns `(True, ...)`. 4) Settlement proceeds without verifying actual balance.

2. **`sign_and_broadcast_transaction` uses `random.choices` for transaction hashes — predictable and forgeable**
   - Severity: high
   - Location: `claims_settlement.py:213–228` (`sign_and_broadcast_transaction`)
   - Description: This is a stub function that should be replaced in production, but if deployed as-is: transaction hashes are generated with `random.choices("0123456789abcdef", k=64)` which uses Python's non-cryptographic Mersenne Twister RNG. An attacker who observes a few transaction hashes can predict future ones. More critically, 10% of transactions randomly fail (`random.random() < 0.9`), causing legitimate claims to be marked as failed.
   - Reproduction: 1) Observe 100 transaction hashes from settlement batches. 2) Use Python's `random` module state recovery to predict the next hash. 3) Forge a fake settlement confirmation with the predicted hash.

3. **`process_claims_batch` updates claims individually — partial settlement on crash**
   - Severity: medium
   - Location: `claims_settlement.py:357–375` (`process_claims_batch` → `update_claims_settled`)
   - Description: After a transaction is "broadcast" (simulated), claims are updated one-by-one via `update_claim_status()` calls. If the process crashes between updates, some claims are marked "settled" while others remain "approved," even though they were all part of the same batch transaction. The transaction hash is the same for all claims, so on restart, it's impossible to determine which claims were actually settled on-chain.
   - Reproduction: 1) Submit 50 claims for settlement. 2) After `sign_and_broadcast_transaction` returns success but before all `update_claim_status` calls complete, kill the process. 3) On restart, 25 claims show "settled" with TX hash, 25 show "approved" with same TX hash. Double-settlement risk if the batch is reprocessed.

## Known failures of this audit
- `sign_and_broadcast_transaction` is explicitly marked as a stub — in production it would be replaced with real signing logic, but the stub being in the main codebase is itself a risk
- Did not verify the `claims_submission.update_claim_status` function — assumed it correctly updates the claims table with proper validation
- The `check_rewards_pool_balance` fallback of `required_urtc * 10` is clearly a placeholder, but I assessed it as if it could be deployed in production
- Did not audit the on-chain transaction format or the actual RustChain network protocol for settlement

## Confidence
- Overall confidence: 0.75
- Per-finding confidence: [0.90, 0.85, 0.80]

## What I would test next
- Test concurrent settlement: two settlement processes running simultaneously, verify no double-settlement
- Test database error handling: corrupt the rewards_pool table, verify settlements halt safely
- Test crash recovery: kill the settlement process mid-batch, verify claims can be reconciled on restart
