# Self-Audit: node/bridge_api.py

## Wallet
RTC-prefix-40-hex

## Module reviewed
- Path: `node/bridge_api.py`
- Commit: latest (2026-04-30)
- Lines reviewed: 1–875 (full file)

## Deliverable: 3 specific findings

1. **Admin key comparison uses `==` instead of `hmac.compare_digest` — timing attack**
   - Severity: high
   - Location: `bridge_api.py:694` (`initiate_bridge` admin check) and `bridge_api.py:754` (`void_bridge` admin check)
   - Description: Both admin endpoints use plain string equality (`admin_key == os.environ.get("RC_ADMIN_KEY", "")`) to compare the provided key against the expected value. This is vulnerable to timing attacks: `==` returns early on the first mismatched character, so an attacker can determine the admin key one character at a time by measuring response times. The `/api/bridge/void` endpoint can void any bridge transfer and release locks, making this a high-value target.
   - Reproduction: Send 10,000 requests to `/api/bridge/void` with incrementally varying admin keys, measure response times with microsecond precision. The correct first character will have a measurably longer response time. Iterate through all 64 hex characters.

2. **`/api/bridge/update-external` has no authentication when `RC_BRIDGE_API_KEY` is not configured**
   - Severity: high
   - Location: `bridge_api.py:766–770` (`update_external`)
   - Description: The auth check is `if expected_key and api_key != expected_key`. If `RC_BRIDGE_API_KEY` is not set (empty string), `expected_key` is falsy, so the entire check is skipped. Anyone can call this endpoint to: (a) mark any bridge transfer as "completed" by setting `confirmations >= required_confirmations`, releasing the associated lock; (b) set arbitrary external tx hashes, potentially enabling double-spend attacks on the external chain.
   - Reproduction: `curl -X POST http://node:8099/api/bridge/update-external -H 'Content-Type: application/json' -d '{"tx_hash":"<any_pending_tx>","external_tx_hash":"0xfake","confirmations":999}'` — transfer immediately marked as completed, lock released.

3. **Balance check in `create_bridge_transfer` is not atomic — race condition enables double-spend**
   - Severity: medium
   - Location: `bridge_api.py:264–290` (`check_miner_balance` + `create_bridge_transfer`)
   - Description: `check_miner_balance` reads the miner's balance and pending debits, then returns whether sufficient funds exist. But there's no transaction-level lock between the check and the insert. Two concurrent requests for the same miner can both pass the balance check (seeing the same available balance), then both insert bridge transfers, resulting in total debits exceeding the actual balance.
   - Reproduction: 1) Miner has 100 RTC available. 2) Send two simultaneous POST `/api/bridge/initiate` requests for 60 RTC each. 3) Both requests call `check_miner_balance`, both see 100 RTC available. 4) Both insert bridge transfers. 5) Total debits: 120 RTC, but miner only has 100 RTC.

## Known failures of this audit
- Did not verify whether the Flask app wraps these routes with additional middleware (global auth, rate limiting) that would mitigate the identified issues
- Did not test the lock_ledger integration — the `lock_ledger` table schema and release logic is defined elsewhere
- The `check_miner_balance` function queries `bridge_transfers` for pending debits, but I didn't verify that all bridge paths (admin-initiated, etc.) correctly create pending entries
- Did not audit the external chain confirmation oracle that calls `update-external` — trust model for the confirmation source is unclear

## Confidence
- Overall confidence: 0.80
- Per-finding confidence: [0.92, 0.88, 0.75]

## What I would test next
- Write a concurrent test: 10 threads initiating bridge transfers from the same miner simultaneously, verify no double-spend
- Test timing attack on admin key: use statistical analysis of response times to recover key character-by-character
- Test the complete bridge lifecycle: initiate → lock → external confirm → complete → lock release, verify no state leakage
