# Security Policy

## Supported Versions
We provide security updates for the versions below.

| Version | Supported                 |
|--------:|---------------------------|
| main    | ✅                        |
| 18.x    | ✅                        |
| 17.x    | ⚠️  Critical fixes only   |
| < 17    | ❌                        |

> Mapping:
> - `main` = active development.
> - `18.x` = latest stable release line.
> - `17.x` = maintenance only; no feature work.

---

## Reporting a Vulnerability
**Do not open a public issue or PR.**  
Use GitHub’s private reporting:

- 👉 **[Open a private report](/security/advisories/new)** (maintainers are notified)
- If GitHub is unavailable, email **security@example.com**

### Please include (Angular specifics)
- Minimal steps to reproduce (ideally a tiny repro repo).
- **Angular version** (`ng version`), **Node.js** and **npm/pnpm/yarn** versions.
- Your package manager and lockfile (`package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`).
- Build target (browser, SSR, standalone), relevant config (`angular.json`, environment).
- Any known workarounds or mitigations.

### Response targets
- Acknowledgement: **48 hours**
- Triage & severity: **≤ 5 business days**
- Fix window (after confirmation):
  - Critical: **≤ 7 days**
  - High: **≤ 14 days**
  - Medium: **≤ 30 days**
  - Low: **≤ 60 days**

We follow **coordinated disclosure**. We’ll publish an advisory and credit you (or keep you anonymous if preferred).
