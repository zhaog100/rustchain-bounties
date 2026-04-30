# Self-Audit: node/beacon_api.py

## Wallet
RTC-prefix-40-hex

## Module reviewed
- Path: `node/beacon_api.py`
- Commit: latest (2026-04-30)
- Lines reviewed: 1–830 (full file)

## Deliverable: 3 specific findings

1. **SSL certificate verification disabled in bounty sync — MITM vulnerability**
   - Severity: high
   - Location: `beacon_api.py:516–517` (`sync_bounties`)
   - Description: `ctx.check_hostname = False` and `ctx.verify_mode = ssl.CERT_NONE` disable all SSL verification for GitHub API requests. An attacker on the network path can intercept and modify bounty data, including injecting bounties with attacker-controlled `github_url` and `reward_rtc` values.
   - Reproduction: 1) Set up a MITM proxy. 2) When `sync_bounties()` calls `urllib.request.urlopen`, the proxy presents any certificate. 3) Python accepts it (verify_mode=CERT_NONE). 4) Attacker returns fake bounty JSON with `reward_rtc: 9999` and a phishing `github_url`.

2. **`/api/bounties/<id>/claim` has no authentication — anyone can claim any bounty**
   - Severity: high
   - Location: `beacon_api.py:636–656` (`claim_bounty`)
   - Description: The claim endpoint only requires `agent_id` in the request body. There is no HMAC signature, no admin key, no proof of ownership. An attacker can claim all open bounties by iterating through bounty IDs, preventing legitimate agents from earning rewards. The `complete_bounty` endpoint correctly requires `X-Admin-Key`, but `claim_bounty` does not.
   - Reproduction: `curl -X POST http://node:8099/api/bounties/gh_rustchain-bounties_2864/claim -H 'Content-Type: application/json' -d '{"agent_id":"attacker-001"}'` — bounty immediately claimed by attacker.

3. **Contract state transitions have no auth or validation — anyone can breach or complete any contract**
   - Severity: high
   - Location: `beacon_api.py:410–440` (`update_contract`)
   - Description: The `/api/contracts/<contract_id>` PUT endpoint accepts any `state` value from `{'offered', 'active', 'renewed', 'completed', 'breached', 'expired'}` with zero authentication. An attacker can change any contract to 'breached' (triggering penalties) or 'completed' (releasing funds) by simply knowing the contract ID. There is no check that the caller is the `from_agent` or `to_agent` of the contract.
   - Reproduction: `curl -X PUT http://node:8099/api/contracts/ctr_12345_abc -H 'Content-Type: application/json' -d '{"state":"breached"}'` — contract marked as breached by anyone.

## Known failures of this audit
- Did not verify whether the Flask blueprint is mounted with additional auth middleware (e.g., `@app.before_request` that checks tokens globally)
- The `bounty_cache` dict is in-memory only — did not test cache poisoning scenarios under concurrent access
- Did not audit the 3D visualization frontend that consumes these API endpoints (XSS/CSRF on the client side)
- The `chat` endpoint returns random mock responses — assumed this is demo-only, but if deployed in production, response leakage could reveal system information

## Confidence
- Overall confidence: 0.78
- Per-finding confidence: [0.95, 0.90, 0.85]

## What I would test next
- Verify whether a global auth middleware exists in the Flask app that wraps this blueprint
- Test concurrent contract state transitions: two clients updating the same contract simultaneously
- Test bounty sync with a malformed GitHub API response (e.g., truncated JSON, Unicode bombs) to find parser crashes
