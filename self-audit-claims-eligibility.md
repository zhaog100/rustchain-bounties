# Self-Audit: claims_eligibility.py (Bounty #6460)

**Auditor:** @zhaog100  
**Module:** `node/claims_eligibility.py` (737 lines)  
**Date:** 2026-04-30  
**Confidence:** High — eligibility gate for reward claims

---

## Executive Summary

This module implements RIP-305 Track D: Claims Eligibility Verification. It validates miner attestations, epoch participation, hardware fingerprints, fleet detection, wallet registration, and duplicate claim prevention before allowing reward claims. The design is sound but several security and robustness issues were found.

**Severity:** 1 High, 3 Medium, 4 Low

---

## 🔴 HIGH: `is_epoch_settled` Uses Heuristic Instead of On-Chain State

**Location:** `is_epoch_settled()` lines 340-347

```python
def is_epoch_settled(db_path, epoch, current_slot):
    settled_epoch = max(0, current_slot // 144 - 2)
    return epoch <= settled_epoch
```

**Impact:** This function doesn't actually check the database for settlement state. It uses a heuristic (`current_slot // 144 - 2`) which means:
1. An epoch is considered "settled" 288 slots (48 hours) after its start, regardless of actual settlement
2. If settlement is delayed (e.g., node downtime, manual intervention), claims could be **approved for unsettled epochs** and miners could be paid prematurely
3. If settlement happens faster than 2 epochs, legitimate claims are **blocked unnecessarily**

**Fix:** Query the actual `epoch_state` table (used by `anti_double_mining.py`):
```python
def is_epoch_settled(db_path, epoch, current_slot):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT settled FROM epoch_state WHERE epoch=?", (epoch,)
        ).fetchone()
        return row is not None and row[0] == 1
```

---

## 🟡 MEDIUM: Race Condition in `check_pending_claim`

**Location:** `check_pending_claim()` lines 285-305

```python
cursor.execute("""
    SELECT claim_id FROM claims
    WHERE miner_id = ? AND epoch = ?
    AND status IN ('pending', 'verifying', 'approved')
    LIMIT 1
""", (miner_id, epoch))
```

**Impact:** The check for pending claims is a read-only query. Between the time this check runs and the time a claim is actually submitted, another process could create a pending claim. This is a classic TOCTOU (time-of-check-time-of-use) race condition.

**Consequence:** Two claims for the same miner/epoch could both pass the eligibility check, leading to duplicate payouts if the claim processing system doesn't have its own deduplication.

**Fix:** Use a unique constraint on `(miner_id, epoch, status)` and handle `IntegrityError` during claim submission, rather than relying on a pre-check:
```sql
CREATE UNIQUE INDEX idx_unique_pending_claim 
ON claims(miner_id, epoch) WHERE status IN ('pending', 'verifying', 'approved');
```

---

## 🟡 MEDIUM: `get_eligible_epochs` Has O(N) Database Connections

**Location:** `get_eligible_epochs()` lines 533-605

```python
for epoch in epochs:
    eligibility = check_claim_eligibility(db_path, miner_id, epoch, ...)
    ...
    with sqlite3.connect(db_path) as conn:
        cursor.execute("SELECT claim_id FROM claims WHERE ...")
```

**Impact:** For each epoch in the history, the function:
1. Calls `check_claim_eligibility()` which opens its own DB connection
2. Then opens another connection to check claim status

For `limit=10`, that's 20+ connections per call. For a miner with a long history, this creates significant I/O overhead.

**Fix:** Accept a shared connection parameter and batch the queries:
```python
def get_eligible_epochs(db_path, miner_id, ..., conn=None, limit=10):
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(db_path)
    try:
        # Single query for all epochs
        conn.execute("SELECT epoch, status FROM claims WHERE miner_id=?", (miner_id,))
        ...
    finally:
        if own_conn:
            conn.close()
```

---

## 🟡 MEDIUM: `calculate_epoch_reward` Falls Back to Equal Share Without Warning

**Location:** `calculate_epoch_reward()` lines 355-389

```python
except Exception as e:
    print(f"[CLAIMS] Error calculating reward: {e}")
    # Fallback: return standard per-miner share
    ...
    return PER_EPOCH_URTC // max(1, miner_count)
```

**Impact:** If the reward calculation module (`rewards_implementation_rip200`) is unavailable or throws an error, the function silently falls back to an equal-share calculation. This could return **incorrect reward amounts** — potentially much higher or lower than the miner is actually owed — without any caller-side indication that the fallback was used.

**Consequence:** A miner could claim a reward based on the fallback amount, which the settlement system might reject (if it uses the real calculation), causing a discrepancy between what the eligibility checker says and what's actually paid.

**Fix:** Return an error status instead of a fallback amount, or include a flag in the result indicating the fallback was used:
```python
return {
    "reward_urtc": PER_EPOCH_URTC // miner_count,
    "fallback_used": True,
    "error": str(e)
}
```

---

## 🟢 LOW: No Input Validation on `epoch` Parameter

**Location:** `check_claim_eligibility()` and all helper functions

**Impact:** Negative epoch values are accepted without validation. A negative epoch would compute nonsensical timestamps via `GENESIS_TIMESTAMP + (epoch * 144 * BLOCK_TIME)`, potentially matching old attestation records that shouldn't be eligible.

**Fix:** `if epoch < 0: raise ValueError(f"epoch must be non-negative")`

---

## 🟢 LOW: Test Code in Production Module

**Location:** `if __name__ == "__main__":` block lines 612-737

The module includes a full test suite inline, using `:memory:` SQLite database. This is convenient for development but:
- Increases module size by ~120 lines
- Could be accidentally executed in production
- Uses hardcoded test data that includes a fake wallet address

**Fix:** Move to `test_claims_eligibility.py`.

---

## 🟢 LOW: `get_wallet_address` Silently Swallows `OperationalError`

**Location:** `get_wallet_address()` lines 240-265

```python
except sqlite3.OperationalError:
    # Table doesn't exist, try miner_attest_recent
    pass
```

**Impact:** The `pass` swallows ALL `OperationalError`s, including ones that indicate real problems (e.g., corrupted database, permission denied). The function then tries `miner_attest_recent` which might also fail, returning `None` — indistinguishable from "wallet not registered."

**Fix:** Log the exception or re-raise if it's not a "table not found" error:
```python
except sqlite3.OperationalError as e:
    if "no such table" not in str(e).lower():
        raise  # Real error, not missing table
    # Continue to fallback
```

---

## 🟢 LOW: Fleet Penalty Flagged as `fingerprint_passed`

**Location:** `check_claim_eligibility()` lines 492-497

```python
if fleet_status.get("penalty_applied") or fleet_status.get("fleet_flagged"):
    result["reason"] = "fleet_penalty"
    result["checks"]["fingerprint_passed"] = False  # Wrong field!
    return result
```

**Impact:** When a fleet penalty is detected, the function incorrectly sets `fingerprint_passed = False` instead of using a dedicated `fleet_penalty` field. This misrepresents the reason for rejection — the miner's fingerprint actually passed, but they're being rejected for fleet detection.

**Consequence:** Debugging becomes harder because the rejection reason doesn't match the actual check that failed. A miner seeing `fingerprint_failed` would try to re-attest, but the real issue is fleet detection.

**Fix:** Add a new check field:
```python
result["checks"] = {
    ...,
    "no_fleet_penalty": False,
}
```

---

## Positive Observations

- ✅ Clean exception hierarchy for different eligibility failures
- ✅ Parameterized SQL queries throughout (no injection risk)
- ✅ Miner ID format validation with regex
- ✅ Graceful fallbacks when optional modules (RIP-200, RIP-0201) are unavailable
- ✅ Detailed result dict with per-check status for debugging
- ✅ TTL-based attestation expiry check
- ✅ Composite key usage prevents duplicate claims at schema level
- ✅ Row factory usage for named column access

---

**wallet:** _(provide your RTC wallet)_
