# Self-Audit: rustchain-health.py (Bounty #6460)

**Auditor:** @zhaog100  
**Module:** `tools/rustchain-health.py` (378 lines)  
**Date:** 2026-04-30  
**Confidence:** Medium — CLI tool, not consensus-critical, but has security implications

---

## Executive Summary

`rustchain-health.py` is a well-structured CLI health monitoring tool. Clean single-file design, no external deps, supports watch mode + JSON output. However, several security and robustness issues were identified.

**Severity:** 1 High, 2 Medium, 3 Low

---

## 🔴 HIGH: SSL Verification Disabled (MITM Vulnerability)

**Location:** `_ssl_ctx()` lines 53-57

```python
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
```

**Impact:** All HTTP requests vulnerable to MITM. An attacker could intercept and fake "healthy" responses, creating false sense of security for operators making trust decisions.

**Fix:** Verify certificates by default, add `--insecure` CLI flag for local dev.

---

## 🟡 MEDIUM: No Backoff on Watch Mode Failures

**Location:** `main()` watch loop lines 343-352

```python
while True:
    run_once()
    time.sleep(args.watch)
```

**Impact:** If node is down, hammers it at configured interval without backoff. For `--watch 1`, that's 60 req/min to an unresponsive endpoint.

**Fix:** Exponential backoff on consecutive failures, max 5 minutes.

---

## 🟡 MEDIUM: Global State Mutation

**Location:** `main()` line 319, `global _COLOR`

**Impact:** If imported as a module, `--no-color` flag mutates global `_COLOR`, affecting all subsequent calls in the same process.

**Fix:** Use local variable or pass color state through parameters.

---

## 🟢 LOW: No SIGTERM Handling

Watch loop only catches `KeyboardInterrupt`. SIGTERM (systemd/Docker) kills immediately without clean exit. Can leave JSON output file with incomplete lines.

**Fix:** `signal.signal(signal.SIGTERM, handler)`

---

## 🟢 LOW: No Type Validation on API Responses

Code assumes API responses are `dict`/`list`. If node returns error page (HTML), could produce misleading output (e.g., `miner_count` = 0 when API is actually returning 500).

**Fix:** Add type checking with warning logs.

---

## 🟢 LOW: Hardcoded 2MB Response Limit Without Warning

```python
body = resp.read(2 * 1024 * 1024)
```

Responses >2MB silently truncated. If `/api/miners` returns large list, JSON parse fails with confusing error.

**Fix:** Warn when truncation occurs.

---

## Positive Observations

- ✅ Clean single-file design, zero external dependencies
- ✅ Proper `NO_COLOR` env var support
- ✅ Good `argparse` with helpful examples
- ✅ JSON output mode for scripting
- ✅ Latency measurement on all requests
- ✅ Windows color support via `SetConsoleMode`

---

**wallet:** _(provide your RTC wallet)_
