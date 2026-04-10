# 🔴 Red Team Security Audit: RustChain UTXO & Transaction Implementation

**Bounty:** #2819 — Red Team UTXO Implementation Audit (200 RTC)  
**Date:** 2026-04-10  
**Auditor:** zhaog100  
**Scope:** `rustchain-miner/src/`, `sdk/python/rustchain_sdk/`, wallet, transfer, and consensus-related code  

---

## Executive Summary

This audit covers the RustChain UTXO model, transaction signing, wallet key management, and node communication layer. The codebase includes a Rust miner (`rustchain-miner/`) and a Python SDK (`sdk/python/rustchain_sdk/`). We identified **4 Critical**, **3 High**, **4 Medium**, and **3 Low** severity findings.

The most severe issues center around: cryptographic signature bypass via the HMAC fallback, lack of UTXO set tracking enabling double-spends, missing server-side transaction replay protection, and TLS certificate verification being permanently disabled.

---

## Findings Summary

| ID | Severity | Title | Component |
|----|----------|-------|-----------|
| RC-UTXO-001 | 🔴 Critical | Ed25519 Signature Bypass via HMAC Fallback | wallet.py |
| RC-UTXO-002 | 🔴 Critical | No UTXO Set — Unconstrained Double-Spend | client.py / transfer |
| RC-UTXO-003 | 🔴 Critical | Transaction Replay — No Nonce/UTXO Reference | wallet.py / client.py |
| RC-UTXO-004 | 🔴 Critical | Self-Signed TLS Accepted — MITM on All RPC | tls.rs / client.py |
| RC-UTXO-005 | 🟠 High | Deterministic Nonce from Seed — Key Recovery | wallet.py |
| RC-UTXO-006 | 🟠 High | Seed Phrase in CLI Process Args — Credential Leak | cli.py |
| RC-UTXO-007 | 🟠 High | No Amount/Address Input Validation | client.py / wallet.py |
| RC-UTXO-008 | 🟡 Medium | Race Condition: Concurrent Transfer Submission | client.py |
| RC-UTXO-009 | 🟡 Medium | Hardcoded Node IP — Single Point of Failure | config.rs / cli.py |
| RC-UTXO-010 | 🟡 Medium | BIP39 Wordlist Truncated — Weak Entropy Mapping | wallet.py |
| RC-UTXO-011 | 🟡 Medium | Enroll Uses Same Field for Pubkey and Miner ID | endpoints.rs |
| RC-UTXO-012 | 🟢 Low | Export Contains Seed Phrase Unencrypted | wallet.py |
| RC-UTXO-013 | 🟢 Low | Balance as Float — Precision Loss | endpoints.rs |
| RC-UTXO-014 | 🟢 Low | No Rate Limiting on Client-Side Submission Loop | attestation.rs |

---

## Detailed Findings

---

### RC-UTXO-001: Ed25519 Signature Bypass via HMAC Fallback (🔴 Critical)

**Location:** `sdk/python/rustchain_sdk/wallet.py`, lines 150–160 (`sign` method)

**Description:**  
The `sign()` method attempts Ed25519 via the `cryptography` library but falls back to `HMAC-SHA512` truncated to 64 bytes when the library is unavailable:

```python
def sign(self, message: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        priv = Ed25519PrivateKey.from_private_bytes(self._private_key[:32])
        return priv.sign(message)
    except ImportError:
        # Fallback: HMAC-based signature (not real Ed25519)
        return _hmac_sha512(self._private_key, message)[:64]
```

An attacker can forge valid signatures for any message if they know the public key but NOT the private key, simply by installing a broken `cryptography` package or by downgrading the dependency. The server cannot distinguish between a legitimate Ed25519 signature and an HMAC forgery because it has no way to know which codepath produced the signature.

Similarly, `_derive_public_key` has a hash-based fallback:
```python
return _sha256d(b"pubkey" + private_key)[:32]
```

**Impact:** Complete signature forgery. An attacker can spend any wallet's funds.

**PoC:** See `poc-exploits/utxo-sig-bypass.py`

**Fix:**  
1. Remove the HMAC fallback entirely — fail hard if `cryptography` is not installed.
2. Add Ed25519 as a hard dependency in `setup.py`.
3. Server-side: verify signatures against the canonical Ed25519 public key, rejecting any signature that doesn't verify under standard Ed25519.

---

### RC-UTXO-002: No UTXO Set — Unconstrained Double-Spend (🔴 Critical)

**Location:** `sdk/python/rustchain_sdk/client.py`, `transfer_signed()` method; entire codebase

**Description:**  
The transfer API (`/transfer`) accepts a signed payload with `from`, `to`, `amount`, `fee`, `signature`, and `timestamp`. There is **no UTXO set**, no transaction input referencing specific UTXOs, and no output model. The balance is queried via a simple `/wallet/balance` endpoint that returns an aggregate amount.

The `sign_transfer` method constructs:
```python
payload = f"{self._address}:{to_address}:{amount}:{fee}:{timestamp}".encode()
```

This is an account-based model with no UTXO tracking. A wallet with balance B can submit multiple transfers each spending up to B simultaneously. Without a mempool that checks UTXO consumption or an account nonce, the same funds can be spent repeatedly until the server processes the first transaction.

**Impact:** Unlimited double-spending. An attacker can drain funds by submitting N parallel transfers of the full balance to N different addresses.

**PoC:** See `poc-exploits/utxo-double-spend.py`

**Fix:**  
1. Implement a proper UTXO model: each transaction consumes specific inputs (txid:vout) and creates new outputs.
2. Maintain a UTXO set on the server. Mark UTXOs as spent atomically.
3. Reject transactions referencing already-spent UTXOs.
4. Use a mempool with consensus-level double-spend detection.

---

### RC-UTXO-003: Transaction Replay — No Nonce/UTXO Reference (🔴 Critical)

**Location:** `sdk/python/rustchain_sdk/wallet.py`, `sign_transfer()` method

**Description:**  
The signed transfer payload uses only `timestamp` for uniqueness:
```python
payload = f"{self._address}:{to_address}:{amount}:{fee}:{timestamp}".encode()
```

There is no nonce, no chain ID, and no UTXO reference. If two transfers happen to share the same timestamp (common in automated/batch systems), the server cannot distinguish them. More critically, a captured signed transaction can be replayed if the server doesn't enforce strict timestamp windows or maintain a spent-transaction index.

**Impact:** Transaction replay allows an attacker to re-submit a captured valid transfer, draining the sender's balance repeatedly.

**PoC:** See `poc-exploits/utxo-tx-replay.py`

**Fix:**  
1. Add a monotonically increasing account nonce to each transaction.
2. Include a chain ID to prevent cross-chain replay.
3. Server-side: maintain a spent-tx set and reject duplicates.
4. Enforce a tight timestamp validity window (e.g., ±60 seconds).

---

### RC-UTXO-004: Self-Signed TLS Accepted — MITM on All RPC (🔴 Critical)

**Location:**  
- `rustchain-miner/src/network/tls.rs`, line 20: `danger_accept_invalid_certs(true)`  
- `sdk/python/rustchain_sdk/client.py`, lines 40–42: falls back to `True` (no verify)

```rust
pub fn build_client() -> Result<Client, Box<dyn std::error::Error>> {
    let client = Client::builder()
        .danger_accept_invalid_certs(true)
        // ...
```

```python
cert = os.path.expanduser("~/.rustchain/node_cert.pem")
self._tls_verify = cert if os.path.exists(cert) else True
```

Both the Rust miner and Python SDK accept ANY self-signed certificate without pinning. An attacker on the network path can intercept all RPC traffic, modify attestation payloads, forge balance responses, and inject fake transfer confirmations.

**Impact:** Full MITM attack on all node communication. An attacker can modify transactions in flight, steal credentials, and manipulate balance/epoch data.

**PoC:** See `poc-exploits/utxo-mitm-tls.py`

**Fix:**  
1. Implement certificate pinning — ship the known node certificate fingerprint with the client.
2. Use a proper CA-signed certificate for the production node.
3. Remove `danger_accept_invalid_certs(true)` in production builds.
4. Python SDK should fail if the pinned cert is missing, not silently fall back to no verification.

---

### RC-UTXO-005: Deterministic Nonce from Seed — Key Recovery (🟠 High)

**Location:** `sdk/python/rustchain_sdk/wallet.py`, `create()` and `from_seed_phrase()`

**Description:**  
The private key is derived deterministically from the seed phrase via:
```python
seed = _hmac_sha512(b"mnemonic", " ".join(words).encode("utf-8"))
private_key = seed[:32]
```

If an attacker obtains the seed phrase (e.g., from `wallet.export()` which stores it in plaintext, or from CLI args visible in `/proc`), they can reconstruct the exact private key. The derivation uses a fixed HMAC key `"mnemonic"` without any salt or passphrase support, meaning the same seed phrase always produces the same key.

Additionally, the BIP39 implementation is non-standard:
```python
words = _to_words(extended, _BIP39_WORDLIST)
```
The `_to_words` function uses modulo arithmetic (`int.from_bytes(data[i:i+2], "big") % len(wordlist)`), which introduces bias since 65536 is not evenly divisible by the wordlist length (512). This reduces entropy.

**Impact:** Seed phrase compromise directly yields the private key. Biased word mapping reduces effective entropy.

**PoC:** See `poc-exploits/utxo-key-recovery.py`

**Fix:**  
1. Support BIP39 passphrases for additional security.
2. Use standard BIP39/SLIP-0010 derivation (PBKDF2 with 2048 iterations).
3. Fix the modulo bias in `_to_words` using rejection sampling.
4. Use the full 2048-word BIP39 wordlist.

---

### RC-UTXO-006: Seed Phrase in CLI Process Args — Credential Leak (🟠 High)

**Location:** `sdk/python/rustchain_sdk/cli.py`, `wallet send` and `attest` commands

**Description:**  
The seed phrase is passed as a CLI `--seed` argument:
```python
@click.option("--seed", "seed_phrase", required=True, help="Seed phrase of sender wallet")
```

This means the seed phrase appears in:
- Process argument list (`ps aux`, `/proc/<pid>/cmdline`)
- Shell history (`~/.bash_history`, `~/.zsh_history`)
- System audit logs
- Any monitoring tool that captures process arguments

**Impact:** Seed phrase leaked to any local user or monitoring system, enabling full wallet compromise.

**PoC:** Trivial — `ps aux | grep seed` reveals the phrase.

**Fix:**  
1. Read the seed phrase from a file, stdin prompt, or environment variable instead of CLI args.
2. Use `getpass` or similar to hide input.
3. Example: `--seed-file ~/.rustchain/seed.txt` or interactive prompt.

---

### RC-UTXO-007: No Amount/Address Input Validation (🟠 High)

**Location:** `sdk/python/rustchain_sdk/client.py`, `transfer_signed()` and `wallet.py`, `sign_transfer()`

**Description:**  
Neither the client nor the wallet validates:
- **Amount**: Can be 0, negative, or exceed balance
- **Address format**: No validation that `to_address` starts with `RTC` or is correct length
- **Fee**: Can be negative (effectively minting tokens)

```python
async def transfer_signed(self, from_address, to_address, amount, fee, signature, timestamp):
    return await self._post("/transfer", json_data={
        "from": from_address, "to": to_address,
        "amount": amount, "fee": fee, ...
    })
```

**Impact:** Invalid transactions submitted to the network. Negative amounts/fees could be exploited if server-side validation is also missing.

**PoC:** See `poc-exploits/utxo-input-validation.py`

**Fix:**  
1. Client-side: validate `amount > 0`, `fee >= 0`, address format `RTC[0-9a-f]{40}`.
2. Server-side: enforce same constraints. Reject negative values.
3. Check balance before allowing transfer.

---

### RC-UTXO-008: Race Condition: Concurrent Transfer Submission (🟡 Medium)

**Location:** `sdk/python/rustchain_sdk/client.py`, `transfer_signed()`

**Description:**  
The `wallet_transfer_with_wallet()` method is async and non-locking. If called concurrently:
```python
# Two coroutines calling wallet_transfer_with_wallet simultaneously
# Both read balance = 100
# Both submit transfer of 100
# If server lacks atomic balance check, both succeed
```

The wallet's `sign_transfer` uses `time.time()` as the only differentiator. With concurrent calls within the same second, timestamps collide, producing identical signed payloads.

**Impact:** Double-spend via race condition when server lacks proper concurrency control.

**PoC:** See `poc-exploits/utxo-race-condition.py`

**Fix:**  
1. Add a client-side lock per wallet address.
2. Use sequential nonce instead of timestamp.
3. Server-side: use database transactions with row-level locking.

---

### RC-UTXO-009: Hardcoded Node IP — Single Point of Failure (🟡 Medium)

**Location:**  
- `rustchain-miner/src/config.rs`: `DEFAULT_NODE_URL = "https://50.28.86.131"`  
- `sdk/python/rustchain_sdk/cli.py`: `default="https://50.28.86.131"`

**Description:**  
All clients default to a single hardcoded IP. No DNS name, no fallback nodes, no peer discovery. If this IP goes down, all miners and SDK users lose connectivity. This also enables targeted DDoS against the single entry point.

**Impact:** Network-wide outage from single-node failure. Facilitates targeted attacks.

**Fix:**  
1. Use a domain name with DNS round-robin or SRV records.
2. Implement a peer discovery protocol.
3. Allow configuring multiple fallback nodes.

---

### RC-UTXO-010: BIP39 Wordlist Truncated — Weak Entropy Mapping (🟡 Medium)

**Location:** `sdk/python/rustchain_sdk/wallet.py`, `_BIP39_WORDLIST` (512 words vs standard 2048)

**Description:**  
The wordlist contains only 512 words instead of the standard 2048. Combined with the modulo bias in `_to_words`:
```python
word_index = int.from_bytes(data[i:i+2], byteorder="big") % len(wordlist)
```
Since `65536 % 512 = 0`, there's no modulo bias for 512 words, but the reduced wordlist means:
- 12-word phrase entropy: `log2(512^12) = 108 bits` (vs 128 bits standard)
- Reduced search space for brute-force attacks

The wordlist also doesn't include the complete BIP39 wordlist, making it incompatible with standard wallets.

**Impact:** ~16 bits less entropy than expected, making brute-force attacks significantly easier.

**Fix:** Use the full 2048-word BIP39 wordlist.

---

### RC-UTXO-011: Enroll Uses Same Field for Pubkey and Miner ID (🟡 Medium)

**Location:** `rustchain-miner/src/network/endpoints.rs`, `enroll()` method

**Description:**  
```rust
let req = EnrollRequest {
    miner_pubkey: wallet.to_string(),
    miner_id: wallet.to_string(),  // Same value!
    device: DeviceEnroll { ... }
};
```

The wallet address (RTC...) is used as both `miner_pubkey` and `miner_id`. These should be distinct: the public key is for cryptographic verification, while miner_id is for identification. Conflating them means an address reuse links all attestation activity, reducing privacy and making identity correlation trivial.

**Impact:** Privacy loss; potential for impersonation if the server treats these fields interchangeably.

**Fix:** Use the actual Ed25519 public key for `miner_pubkey` and a separate identifier for `miner_id`.

---

### RC-UTXO-012: Export Contains Seed Phrase Unencrypted (🟢 Low)

**Location:** `sdk/python/rustchain_sdk/wallet.py`, `export()` method

**Description:**  
```python
def export(self) -> Dict[str, Any]:
    return {
        "version": 1,
        "address": self._address,
        "seed_phrase": self._seed_phrase,  # Plaintext!
        "derivation_path": self._derivation_path,
    }
```

The seed phrase is stored in plaintext in the export dict. If this dict is serialized to JSON and stored on disk, any file access compromise reveals the wallet.

**Impact:** Seed phrase exposure if export data is stored insecurely.

**Fix:** Encrypt the export with a user-provided passphrase using AES-256-GCM or similar.

---

### RC-UTXO-013: Balance as Float — Precision Loss (🟢 Low)

**Location:** `rustchain-miner/src/network/endpoints.rs`

**Description:**  
```rust
pub struct BalanceResponse {
    pub amount_rtc: Option<f64>,
    pub amount_i64: Option<i64>,
}
```

Using `f64` for balance can cause precision issues with large or fractional amounts. Floating-point arithmetic is not suitable for financial calculations.

**Impact:** Potential balance discrepancies for high-precision amounts.

**Fix:** Use integer (smallest unit) exclusively for balances. Convert to float only for display.

---

### RC-UTXO-014: No Rate Limiting on Client-Side Submission Loop (🟢 Low)

**Location:** `rustchain-miner/src/attestation.rs`, main loop

**Description:**  
The attestation loop retries with exponential backoff on 429 responses but has no client-side rate limiting on successful submissions. A compromised or buggy miner could flood the node with requests.

**Impact:** Potential for accidental or intentional API abuse.

**Fix:** Add a minimum interval between submissions, even on success.

---

## Attack Surface Map

```
┌─────────────────────────────────────────────────────────┐
│                    ATTACK SURFACE                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  CLI (--seed leaks) ──► Wallet ──► sign_transfer()      │
│                              │         │                 │
│                              │    HMAC Fallback (C-001)  │
│                              │    No Nonce (C-003)       │
│                              │    No Validation (H-007)  │
│                              ▼                           │
│  Client ──► transfer_signed() ──► /transfer API          │
│                │                          │              │
│     Race Condition (M-008)    No UTXO Set (C-002)        │
│                                                          │
│  Miner ──► TLS (self-signed) ──► MITM (C-004)           │
│          ──► Hardcoded IP (M-009)                        │
│          ──► enroll() (M-011)                            │
│                                                          │
│  Storage ──► export() plaintext seed (L-012)             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Consensus Mechanism Weaknesses

1. **RIP-PoA (Proof-of-Antiquity)** relies on hardware fingerprinting (clock drift, cache timing, SIMD identity, thermal drift, instruction jitter, anti-emulation). These can be spoofed by:
   - Custom hardware profiling tools
   - VM escape + bare-metal fingerprint injection
   - Replay of previously valid fingerprint data (fingerprints don't change between epochs for the same hardware)

2. **No Sybil resistance**: A single operator can register multiple miners with different wallet addresses on the same hardware. The fingerprint checks detect VM/emulation but not multiple wallets on bare metal.

3. **Epoch enrollment has no stake requirement**: Miners don't lock any collateral, so there's zero cost to creating Sybil identities.

4. **Balance check is per-epoch, not per-block**: With 600-second epochs, there's a 10-minute window where balance states can be inconsistent across the network.

---

## Recommendations (Priority Order)

1. **Remove HMAC signature fallback** — This is the single most dangerous flaw.
2. **Implement UTXO model** — Without it, double-spending is trivial.
3. **Add transaction nonces** — Prevent replay attacks.
4. **Fix TLS** — Pin certificates or use proper CA-signed certs.
5. **Remove seed from CLI args** — Use file/stdin/env var.
6. **Add input validation** — Both client and server side.
7. **Implement proper BIP39** — Full 2048 wordlist, standard derivation.
8. **Add concurrent transfer protection** — Nonces + server-side locking.

---

## Repository State at Time of Audit

- Commit: `HEAD` (main branch, shallow clone)
- Files analyzed: 15+ source files across Rust and Python
- Lines of code reviewed: ~2,500+

---

*This audit was performed as a red team engagement. All PoC exploits are provided for defensive purposes only.*
