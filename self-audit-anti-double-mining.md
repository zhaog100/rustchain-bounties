# Self-Audit: anti_double_mining.py (Bounty #6460)

**Auditor:** @zhaog100  
**Module:** `node/anti_double_mining.py` (1,034 lines)  
**Date:** 2026-04-30  
**Confidence:** High — consensus-critical reward distribution logic

---

## Executive Summary

This module enforces the "1 physical machine = 1 reward per epoch" rule by grouping miners via hardware fingerprint identity. The core logic is sound, but several security and robustness issues were found in the reward calculation and settlement paths.

**Severity:** 2 High, 3 Medium, 3 Low

---

## 🔴 HIGH: No Input Validation on Reward Parameters

**Location:** `calculate_anti_double_mining_rewards()` lines 436-530

The function accepts `total_reward_urtc`, `epoch`, and `current_slot` without any validation.

**Impact:**
- `total_reward_urtc < 0` → could create negative rewards, effectively **debiting miner balances**
- `total_reward_urtc = 0` → divides by `total_weight` producing zero shares, but `remaining` stays 0 (silent failure)
- `epoch < 0` → computes nonsensical timestamps, could match wrong attestation windows
- `current_slot` far in the future → `get_chain_age_years()` returns huge values, inflating time-aged multipliers

**Attack scenario:** If the settlement caller passes a negative or zero reward value (due to upstream bug or malicious input), miners could lose balance or receive incorrect rewards.

**Fix:**
```python
if total_reward_urtc <= 0:
    raise ValueError(f"total_reward_urtc must be positive, got {total_reward_urtc}")
if epoch < 0:
    raise ValueError(f"epoch must be non-negative, got {epoch}")
if current_slot < epoch * 144:
    raise ValueError(f"current_slot {current_slot} is before epoch {epoch} start")
```

---

## 🔴 HIGH: SQL Injection via `select_representative_miner` Placeholders

**Location:** `select_represent_miner()` lines 300-320

```python
placeholders = ",".join("?" * len(miner_ids))
cursor.execute(f"""
    SELECT miner, entropy_score, ts_ok
    FROM miner_attest_recent
    WHERE miner IN ({placeholders})
    ORDER BY entropy_score DESC, ts_ok DESC, miner ASC
""", miner_ids)
```

**Analysis:** While the `?` placeholders themselves are safe, the `miner_ids` list is passed directly as parameters. If any miner_id contains a `?` character, the parameter count could mismatch with the placeholder count, causing a runtime error or unexpected query behavior.

**Impact:** An attacker who can register a miner_id containing `?` characters could trigger SQL errors during representative selection, potentially disrupting reward settlement.

**Fix:** Validate miner_ids format before query construction:
```python
import re
VALID_MINER_ID = re.compile(r'^[a-zA-Z0-9_\-]+$')
for mid in miner_ids:
    if not VALID_MINER_ID.match(mid):
        raise ValueError(f"Invalid miner_id format: {mid!r}")
```

---

## 🟡 MEDIUM: Hard Coupling to `rip_200_round_robin_1cpu1vote`

**Location:** Lines 453, 620, 689

```python
from rip_200_round_robin_1cpu1vote import get_time_aged_multiplier, get_chain_age_years
```

**Impact:** The anti-double-mining module is tightly coupled to a specific reward distribution implementation. If that file is missing, renamed, or has different function signatures, reward calculation will fail with `ImportError` at runtime.

**Risk:** Settlement fails silently if the import fails inside the transaction — the `try/except` in `settle_epoch_with_anti_double_mining` re-raises the exception, which could leave the database in an inconsistent state if the `finally` block doesn't close properly.

**Fix:** Import at module level (fail fast on startup, not during settlement), or use a plugin interface:
```python
# At module top
try:
    from rip_200_round_robin_1cpu1vote import get_time_aged_multiplier, get_chain_age_years
except ImportError as e:
    raise RuntimeError(
        "anti_double_mining requires rip_200_round_robin_1cpu1vote.py. "
        f"Import error: {e}"
    ) from e
```

---

## 🟡 MEDIUM: Non-Atomic Settlement Check

**Location:** `settle_epoch_with_anti_double_mining()` lines 544-640

```python
st = db.execute("SELECT settled FROM epoch_state WHERE epoch=?", (epoch,)).fetchone()
if st and int(st[0]) == 1:
    ...
    return {"ok": True, "epoch": epoch, "already_settled": True}
# ... then calculates and distributes rewards
```

**Impact:** The check and distribution are not atomic. If two settlement processes run concurrently:
1. Both check `settled=0` → both pass the guard
2. Both calculate rewards → both credit balances
3. **Double payment** — miners receive rewards twice for the same epoch

The `BEGIN IMMEDIATE` helps but doesn't fully prevent this race if the check and distribution happen in separate transactions.

**Fix:** Use `SELECT ... FOR UPDATE` or a unique constraint on `(epoch, miner_id)` in `epoch_rewards` to prevent double-insertion:
```python
# After calculating rewards, use INSERT ... ON CONFLICT DO NOTHING
db.execute(
    "INSERT OR IGNORE INTO epoch_rewards (epoch, miner_id, share_i64) VALUES (?, ?, ?)",
    (epoch, miner_id, share_urtc)
)
# Check if any rows were inserted; if not, epoch was already settled
```

---

## 🟡 MEDIUM: Fallback to `miner_attest_recent` Can Drop Miners

**Location:** `detect_duplicate_identities()` lines 140-170, `get_epoch_miner_groups()` lines 333-360

```python
logger.warning(
    "epoch %d has no epoch_enroll rows, falling back to miner_attest_recent"
)
```

**Impact:** When `epoch_enroll` has no rows (which can happen if enrollment is delayed or the epoch just started), the fallback queries `miner_attest_recent` with a time window. Miners who attested before the window starts or after it ends will be silently excluded from reward calculation.

**Consequence:** Legitimate miners lose rewards without any indication. The warning log is easy to miss in production.

**Fix:** Raise an error instead of silently dropping miners:
```python
if not enrolled:
    raise RuntimeError(
        f"Epoch {epoch} has no enrollment records. "
        f"Cannot safely calculate rewards without epoch_enroll data."
    )
```

---

## 🟢 LOW: Test Code in Production Module

**Location:** `if __name__ == "__main__":` block, lines 934-1034

The module includes `setup_test_scenario()` and test assertions in the same file as production code. Running `python anti_double_mining.py` creates and deletes `/tmp/test_anti_double_mining.db`.

**Risk:** Accidental execution in production could create/modify test databases, potentially confusing operators or triggering alerts.

**Fix:** Move test code to a separate `test_anti_double_mining.py` file.

---

## 🟢 LOW: `GENESIS_TIMESTAMP` Must Match External File

**Location:** Line 33

```python
GENESIS_TIMESTAMP = 1764706927  # Production chain launch (Dec 2, 2025)
```

**Impact:** This constant must exactly match the value in `rip_200_round_robin_1cpu1vote.py`. If they diverge (e.g., one file is updated but not the other), epoch calculations will be off by the timestamp difference, causing miners to be assigned to wrong epochs.

**Fix:** Import from a single source of truth:
```python
# Import from the canonical source instead of duplicating
from rip_200_round_robin_1cpu1vote import GENESIS_TIMESTAMP
```

---

## 🟢 LOW: No Rate Limiting on Duplicate Detection

**Location:** `detect_duplicate_identities()` can be called arbitrarily many times

**Impact:** Each call queries the database for all enrolled miners and their fingerprint history. An attacker could spam this function to create database load, potentially slowing down legitimate reward settlement.

**Fix:** Add a simple cache or rate limit:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def detect_duplicate_identities_cached(conn, epoch, epoch_start_ts, epoch_end_ts):
    ...
```

---

## Positive Observations

- ✅ Core anti-double-mining logic is sound: groups by machine identity, selects one representative
- ✅ Uses `BEGIN IMMEDIATE` for settlement transactions
- ✅ Proper rollback on exception in `settle_epoch_with_anti_double_mining`
- ✅ Good telemetry logging for duplicate detection
- ✅ Representative selection is deterministic (entropy score → timestamp → alphabetical)
- ✅ Test assertions at module bottom verify expected behavior
- ✅ `existing_conn` parameter allows sharing transactions with callers
- ✅ `epoch_rewards` table with composite key prevents duplicate credits (partially addresses race condition)

---

**wallet:** _(provide your RTC wallet)_
