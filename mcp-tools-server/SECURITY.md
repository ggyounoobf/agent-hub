# Security Policy

## Supported Versions

We provide security updates for the versions below.

| Version  | Supported          |
|----------|--------------------|
| main     | ✅                 |
| 0.3.x    | ✅                 |
| 0.2.x    | ⚠️ Critical fixes only |
| < 0.2    | ❌                 |

> **How this maps to branches/tags**
> - `main` = active development (next minor/patch).
> - `0.3.x` = latest stable line.
> - `0.2.x` = maintenance only; no feature changes.

---

## Reporting a Vulnerability

**Please do _not_ open public issues or PRs for security reports.**  
Use **Private Vulnerability Reporting**:

- 👉 [Open a private report](/security/advisories/new) (GitHub will notify maintainers)
- If GitHub is unavailable, email: **security@example.com** (PGP optional)

### What to include (Python/uv projects)
- A clear description of the issue and potential impact.
- Minimal steps to reproduce (code snippet or repo link).
- Your environment: OS, **Python version**, and **uv** version.
- Relevant files: `pyproject.toml`, `uv.lock` and/or a minimal test environment.
- Any known workarounds.

### Our response targets
- **Acknowledgement:** within **48 hours**.
- **Triage & severity:** within **5 business days** (CVSS-style).
- **Fix or advisory:** target windows after confirmation:
  - Critical: **≤ 7 days**
  - High: **≤ 14 days**
  - Medium: **≤ 30 days**
  - Low: **≤ 60 days**

We’ll keep you updated at each step and credit you in the advisory release (unless you prefer to remain anonymous).

### Disclosure policy
- We follow **coordinated disclosure**. Please do not disclose publicly until a fix is available and our advisory is published.
- If a report is out of scope or a duplicate, we’ll explain why and (when possible) point to mitigation guidance.

### Scope notes
- Vulnerabilities in **direct dependencies** should be reported to their upstreams; we’ll track/mitigate via our dependency policy.
- Supply-chain issues (e.g., malicious release) are in scope when they affect this project’s consumers.

---

## Hardening & Dependency Policy

- Dependencies are locked with **`uv.lock`**; security updates are applied on a regular cadence.
- CI enforces code scanning and secret scanning on PRs.
- We may publish temporary advisories with workarounds when a complete fix needs coordination with upstream.

