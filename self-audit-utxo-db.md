# Self-Audit: utxo_db.py (Bounty #6460)

**Auditor:** @zhaog100  
**Module:** `node/utxo_db.py` (898 lines)  
**Date:** 2026-04-30  
**Confidence:** High — core UTXO state machine, double-spend prevention, mempool management

---

## Executive Summary

This module implements the RustChain UTXO Database Layer: a SQLite-backed UTXO set with atomic transaction application, Merkle state roots, mempool management, and coin selection. The code is generally well-engineered with strong double-spend prevention and defense-in-depth patterns. Several bugs and security concerns were identified.

**Severity:** 1 High, 2 Medium, 3 Low

---

## 🔴 HIGH: `mempool_add` References Undefined `manage_tx` Variable

**Location:** `mempool_add()` lines ~710-760 (multiple sites)

```python
def mempool_add(self, tx: dict) -> bool:
    conn = self._conn()
    try:
        # ... validation ...
        conn.execute("BEGIN IMMEDIATE")
        
        # Check for double-spend in mempool
        for inp in inputs:
            existing = conn.execute(...).fetchone()
            if existing:
                if manage_tx:           # ← NameError!
                    conn.execute("ROLLBACK")
                return False
```

**Impact:** The variable `manage_tx` is **never defined** in `mempool_add()`. It exists in `apply_transaction()` (line ~400: `manage_tx = own or not conn.in_transaction`) but was not carried over when the mempool code was written. Every code path that hits a double-spend, missing box, negative fee, or invalid output will raise a `NameError` instead of cleanly rolling back:

```python
NameError: name 'manage_tx' is not defined
```

**Consequence:** When any validation fails after `BEGIN IMMEDIATE`:
1. `NameError` is raised
2. The `except Exception` block catches it
3. `conn.execute("ROLLBACK")` in the except block also references `manage_tx` → another `NameError`
4. The `finally` block closes the connection
5. The transaction may **remain locked** if the ROLLBACK never executes

This creates a **database lock leak** that could cause subsequent operations to hang (30-second timeout) or fail.

**Fix:** Define `manage_tx` at the top of `mempool_add()`:
```python
def mempool_add(self, tx: dict) -> bool:
    conn = self._conn()
    own_conn = True  # mempool_add always owns its connection
    manage_tx = True  # always manages its own transaction
    try:
        # ... or simply remove the `if manage_tx:` guards since it's always True
```

Or better: since `mempool_add()` always opens its own connection and always manages its own transaction, remove the `if manage_tx:` guards entirely and just call `conn.execute("ROLLBACK")` unconditionally.

---

## 🟡 MEDIUM: `address_to_proposition` Has No Input Length Validation

**Location:** `address_to_proposition()` line 70

```python
def address_to_proposition(address: str) -> str:
    prop = P2PK_PREFIX + address.encode('utf-8')
    return prop.hex()
```

**Impact:** No maximum length is enforced on the `address` parameter. An attacker could pass a multi-megabyte string:
- `address.encode('utf-8')` creates a large bytes object
- `.hex()` doubles the size
- Stored in `utxo_boxes.proposition` TEXT column

**Consequence:** 
- Memory exhaustion (OOM) during box creation
- Database bloat — a single proposition could consume megabytes of storage
- If propositions are ever transmitted over the network, this becomes a bandwidth amplification vector

**Fix:** Add a maximum address length:
```python
MAX_ADDRESS_LEN = 256

def address_to_proposition(address: str) -> str:
    if len(address) > MAX_ADDRESS_LEN:
        raise ValueError(f"address too long: {len(address)} > {MAX_ADDRESS_LEN}")
    prop = P2PK_PREFIX + address.encode('utf-8')
    return prop.hex()
```

---

## 🟡 MEDIUM: `integrity_check` Is Not Atomic

**Location:** `integrity_check()` lines ~650-680

```python
def integrity_check(self, expected_total: Optional[int] = None) -> dict:
    conn = self._conn()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(value_nrtc), 0) AS total, COUNT(*) AS cnt
             FROM utxo_boxes WHERE spent_at IS NULL"
        ).fetchone()
        total = row['total']
        cnt = row['cnt']
        root = self.compute_state_root()  # ← Opens a SECOND connection!
```

**Impact:** `integrity_check()` opens one connection to compute the total balance and box count, then calls `compute_state_root()` which opens a **second** connection to scan all unspent box IDs. Between these two queries, another transaction could spend or create boxes, meaning:

- `total_unspent_nrtc` reflects state at time T1
- `state_root` reflects state at time T2
- If T1 ≠ T2, the integrity check may report an inconsistent snapshot

**Consequence:** A monitoring system relying on `integrity_check()` could report false positives (or miss real inconsistencies) because the two values come from different database snapshots.

**Fix:** Accept an optional connection parameter in `compute_state_root()` and use the same connection:
```python
def compute_state_root(self, conn: Optional[sqlite3.Connection] = None) -> str:
    own = conn is None
    if own:
        conn = self._conn()
    try:
        # ... existing logic ...
    finally:
        if own:
            conn.close()
```

---

## 🟢 LOW: `proposition_to_address` Uses `errors='ignore'`

**Location:** `proposition_to_address()` line 76

```python
def proposition_to_address(prop_hex: str) -> str:
    raw = bytes.fromhex(prop_hex)
    if raw[:2] == P2PK_PREFIX:
        return raw[2:].decode('utf-8', errors='ignore')
    return f"RTC_UNKNOWN_{prop_hex[:16]}"
```

**Impact:** The `errors='ignore'` parameter silently drops invalid UTF-8 bytes. If a proposition contains non-UTF-8 data (e.g., a smart contract script), the decoded address will silently lose data, potentially creating two different propositions that map to the same address.

**Consequence:** Address collision in display/UI layer — two different spending conditions could appear to have the same owner address.

**Fix:** Use `errors='replace'` to make data loss visible:
```python
return raw[2:].decode('utf-8', errors='replace')
```

---

## 🟢 LOW: `mempool_clear_expired` Deletes Without Transaction

**Location:** `mempool_clear_expired()` lines ~820-835

```python
def mempool_clear_expired(self) -> int:
    conn = self._conn()
    try:
        now = int(time.time())
        expired = conn.execute(
            "SELECT tx_id FROM utxo_mempool WHERE expires_at <= ?", (now,)
        ).fetchall()
        count = 0
        for row in expired:
            conn.execute("DELETE FROM utxo_mempool_inputs WHERE tx_id = ?", (row['tx_id'],))
            conn.execute("DELETE FROM utxo_mempool WHERE tx_id = ?", (row['tx_id'],))
            count += 1
        conn.commit()
```

**Impact:** While the function does commit at the end, if any DELETE fails (e.g., foreign key constraint violation), the partial deletes would be rolled back by the implicit transaction. However, there's no explicit `BEGIN` — it relies on SQLite's autocommit behavior. If `foreign_keys=ON` is not set (it is in `_conn()`, but a future maintainer might remove it), the inputs could be deleted without the parent transaction, leaving orphan `utxo_mempool_inputs` rows.

**Fix:** Explicit transaction:
```python
conn.execute("BEGIN")
try:
    # ... deletes ...
    conn.commit()
except:
    conn.rollback()
    raise
```

---

## 🟢 LOW: `coin_select` Is Module-Level, Not Part of `UtxoDB` Class

**Location:** `coin_select()` lines ~850-898

```python
def coin_select(utxos: List[dict], target_nrtc: int) -> Tuple[List[dict], int]:
```

**Impact:** This is a pure algorithm function that doesn't interact with the database, yet it lives in the UTXO database module. It also doesn't validate that the input UTXOs are actually unspent — it trusts the caller to pass only valid UTXOs.

**Consequence:** If a caller passes stale data (e.g., UTXOs that have since been spent), `coin_select` will include them in the selection, and the subsequent `apply_transaction` will fail. While not a security issue per se, it could cause confusing UX (transactions that appear ready to broadcast but fail on submission).

**Fix:** Document the precondition clearly, or accept a `UtxoDB` instance and verify each UTXO is still unspent.

---

## Positive Observations

- ✅ `BEGIN IMMEDIATE` in `spend_box()` prevents TOCTOU double-spend races
- ✅ Defense-in-depth: duplicate input box_id rejection in `apply_transaction()`
- ✅ Conservation-of-value check: `output_total + fee <= input_total`
- ✅ Positive output value enforcement: rejects zero/negative outputs
- ✅ Coinbase output cap: `MAX_COINBASE_OUTPUT_NRTC` prevents unlimited minting
- ✅ Mining type guard: `_allow_minting` flag prevents arbitrary `mining_reward` transactions
- ✅ Merkle tree with domain-separated padding (not naive duplicate)
- ✅ Leaf cardinality mixed into hashes (binds tree to specific UTXO count)
- ✅ WAL mode + foreign keys enabled in `_conn()`
- ✅ 30-second connection timeout prevents indefinite hangs
- ✅ Mempool double-spend detection via `utxo_mempool_inputs` table
- ✅ Parameterized queries throughout (no SQL injection)
- ✅ Clean layer separation: spending proof verification delegated to endpoint layer
- ✅ Multiple prior fixes already applied (documented in comments: #2207, #2179)

---

**wallet:** _(provide your RTC wallet)_
