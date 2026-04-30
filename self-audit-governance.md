# Self-Audit: governance.py (Bounty #6460)

**Auditor:** @zhaog100  
**Module:** `node/governance.py` (614 lines)  
**Date:** 2026-04-30  
**Confidence:** High — on-chain governance system, proposal/voting lifecycle

---

## Executive Summary

This module implements RIP-0002: On-Chain Governance System with proposal creation, ed25519-authenticated voting, antiquity-weighted voting power, quorum enforcement, Sophia AI evaluation, and founder veto. The code is generally well-designed with good cryptographic practices, but several security and correctness issues were found.

**Severity:** 1 High, 2 Medium, 3 Low

---

## 🔴 HIGH: Founder Veto Uses Timing-Vulnerable String Comparison

**Location:** `founder_veto()` line 455

```python
expected_key = os.environ.get("RUSTCHAIN_ADMIN_KEY", "")
if not expected_key or admin_key != expected_key:
    return jsonify({"error": "invalid admin_key"}), 403
```

**Impact:** Unlike the settlement endpoint which uses `hmac.compare_digest()` (timing-attack resistant), the founder veto endpoint uses direct `!=` string comparison. An attacker with network access could measure response times to determine the admin key character-by-character:
- `!=` returns early on the first mismatched character
- Response time reveals how many prefix characters are correct

**Consequence:** A patient attacker with network access could recover `RUSTCHAIN_ADMIN_KEY` through timing analysis, then veto any governance proposal or manipulate the governance system.

**Fix:** Use `hmac.compare_digest()` as in the settlement endpoint:
```python
import hmac
if not expected_key or not hmac.compare_digest(admin_key, expected_key):
    return jsonify({"error": "invalid admin_key"}), 403
```

---

## 🟡 MEDIUM: Vote Upsert Race Condition

**Location:** `cast_vote()` lines 373-397

```python
try:
    conn.execute(
        "INSERT INTO governance_votes (proposal_id, miner_id, vote, weight, voted_at) VALUES (?,?,?,?,?)",
        (proposal_id, miner_id, vote_choice, weight, now)
    )
except sqlite3.IntegrityError:
    # Already voted — update
    old_vote = conn.execute(
        "SELECT vote, weight FROM governance_votes WHERE proposal_id = ? AND miner_id = ?",
        ...
    ).fetchone()
    if old_vote:
        old_col = f"votes_{old_vote[0]}"
        conn.execute(f"UPDATE governance_proposals SET {old_col} = {old_col} - ? WHERE id = ?",
            (old_vote[1], proposal_id))
    conn.execute(
        "UPDATE governance_votes SET vote = ?, weight = ?, voted_at = ? WHERE proposal_id = ? AND miner_id = ?",
        ...
    )
```

**Impact:** The upsert pattern (INSERT → catch IntegrityError → SELECT old → subtract → UPDATE) is not atomic. Between the INSERT failure and the SELECT of the old vote, another transaction could also be processing the same vote change. This creates a window where:

1. Two concurrent vote-change requests from the same miner
2. Both fail the INSERT (IntegrityError)
3. Both read the same old vote value
4. Both subtract the old weight and add the new weight
5. **Result:** Old weight subtracted twice, but new weight added only once (or vice versa)

**Consequence:** Vote tally corruption — the `votes_for`/`votes_against` totals become inaccurate, potentially changing the outcome of close governance votes.

**Fix:** Use SQLite's `INSERT OR REPLACE` with a single atomic UPDATE on the proposal tally, or wrap the entire upsert in a SERIALIZABLE transaction:
```python
conn.execute("BEGIN DEFERRED")
try:
    conn.execute("INSERT OR REPLACE INTO governance_votes ...")
    # Atomic tally update using CASE
    conn.execute("""
        UPDATE governance_proposals SET
            votes_for = votes_for + CASE WHEN ? = 'for' THEN ? - COALESCE((SELECT weight FROM governance_votes WHERE proposal_id=? AND miner_id=?), 0) ELSE 0 END,
            votes_against = votes_against + CASE WHEN ? = 'against' THEN ? - COALESCE((SELECT weight FROM governance_votes WHERE proposal_id=? AND miner_id=?), 0) ELSE 0 END,
            votes_abstain = votes_abstain + CASE WHEN ? = 'abstain' THEN ? - COALESCE((SELECT weight FROM governance_votes WHERE proposal_id=? AND miner_id=?), 0) ELSE 0 END
        WHERE id = ?
    """, (vote_choice, weight, proposal_id, miner_id, ...))
    conn.commit()
except:
    conn.rollback()
    raise
```

---

## 🟡 MEDIUM: `_settle_expired_proposals` Called Without Transaction

**Location:** `_settle_expired_proposals()` lines 177-201, called at the start of every endpoint

```python
def _settle_expired_proposals(db_path: str):
    now = int(time.time())
    with sqlite3.connect(db_path) as conn:
        active = conn.execute(
            "SELECT id, votes_for, votes_against, votes_abstain FROM governance_proposals "
            "WHERE status = ? AND expires_at <= ?",
            (STATUS_ACTIVE, now)
        ).fetchall()
        for (pid, v_for, v_against, v_abstain) in active:
            ...
            conn.execute("UPDATE governance_proposals SET status = ?, quorum_met = ? WHERE id = ?",
                (new_status, 1 if quorum_met else 0, pid))
        conn.commit()
```

**Impact:** This function opens its own connection and commits independently of the caller's transaction. If a caller is in the middle of a vote (inside a `with sqlite3.connect(db_path) as conn:` block), this function opens a *separate* connection and modifies the same rows. This can cause:

1. **Database locking** — SQLite's default behavior may block the caller's transaction
2. **Inconsistent state** — The caller reads the proposal status before `_settle_expired_proposals` runs, but after it commits, the status may have changed
3. **Quorum miscalculation** — `_count_active_miners(db_path)` is called inside the settle function using the current time, but the vote being cast uses a potentially different timestamp

**Fix:** Accept an optional connection parameter and use the caller's transaction when available:
```python
def _settle_expired_proposals(db_path: str, conn=None):
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(db_path)
    try:
        ...
    finally:
        if own_conn:
            conn.close()
```

---

## 🟢 LOW: `_get_miner_antiquity_weight` Queries Wrong Table

**Location:** `_get_miner_antiquity_weight()` line 158

```python
row = conn.execute(
    "SELECT antiquity_multiplier FROM miners WHERE wallet_name = ?",
    (miner_id,)
).fetchone()
```

**Impact:** The query uses `miners.wallet_name = ?` but throughout the codebase, `miner_id` is used as the identifier (not `wallet_name`). The `miner_attest_recent` table uses `miner` as the column name. If the `miners` table schema doesn't match, or if `miner_id` doesn't correspond to `wallet_name`, this query silently returns `None` and defaults to `1.0`.

**Consequence:** All miners get weight `1.0` regardless of their actual antiquity multiplier, nullifying the time-aged voting system. Old-hardware miners (who should have higher multipliers) get the same voting power as new miners.

**Fix:** Query the correct table/column:
```python
row = conn.execute(
    "SELECT antiquity_multiplier FROM miner_attest_recent WHERE miner = ? ORDER BY ts_ok DESC LIMIT 1",
    (miner_id,)
).fetchone()
```

---

## 🟢 LOW: `_is_active_miner` and `_count_active_miners` Use Different Tables

**Location:** `_is_active_miner()` line 172, `_count_active_miners()` line 183

```python
# _is_active_miner:
"SELECT COUNT(*) FROM attestations WHERE miner_id = ? AND timestamp >= ?"

# _count_active_miners:
"SELECT COUNT(DISTINCT miner_id) FROM attestations WHERE timestamp >= ?"
```

**Impact:** Both functions query the `attestations` table, but the rest of the codebase (RIP-200 modules) uses `miner_attest_recent`. If these tables aren't kept in sync (e.g., `attestations` is a log table while `miner_attest_recent` is the current state), the governance module could have inconsistent data about which miners are active.

**Consequence:** Quorum calculations could be wrong — either too high or too low — causing proposals to pass or fail incorrectly.

**Fix:** Use the same data source as the reward system (`miner_attest_recent`).

---

## 🟢 LOW: No Validation on `parameter_value`

**Location:** `create_proposal()` line 283

```python
parameter_value = str(data.get("parameter_value", "")).strip() or None
```

**Impact:** `parameter_value` is converted to string with no length limit, type validation, or sanitization. A proposer could set:
- A very long string (megabytes) consuming database storage
- SQL special characters (though parameterized queries prevent injection, the stored value could be used in dynamic SQL elsewhere)
- Malicious HTML/JavaScript if the value is ever rendered in a UI

**Fix:** Add length limit and type validation:
```python
MAX_PARAM_VALUE_LEN = 1000
parameter_value = str(data.get("parameter_value", ""))[:MAX_PARAM_VALUE_LEN].strip() or None
```

---

## Positive Observations

- ✅ Ed25519 signature verification for proposal creation and voting — prevents spoofing
- ✅ 5-minute signature window — prevents replay attacks
- ✅ `hmac.compare_digest()` for settlement key (but NOT for veto key — see HIGH)
- ✅ MAX_PROPOSALS_PER_MINER (10) anti-spam limit
- ✅ Input validation on title/description length
- ✅ Proposal type enum validation
- ✅ Vote choice whitelist before SQL column construction
- ✅ DEFERRED transaction on expired proposal settlement
- ✅ Sophia AI evaluation is deterministic (no external API dependency)
- ✅ Founder veto has a 2-year expiry window
- ✅ Proper error logging with `log.debug()` for sensitive details

---

**wallet:** _(provide your RTC wallet)_
