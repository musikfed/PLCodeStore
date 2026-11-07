# PL Code Store 2.0 — scope and architecture

## Manifesto

Marketing is a folder; publication is an author's decision. A Git repository's technical metadata is not marketing consent.

## Data flow

Source repository (read-only) → parser → `vitrine/meta.json` → registry/review store → approved snapshot → static delivery.

- `vitrine/meta.json` is **author-owned**. Generated media and inferred metadata are separate.
- `visibility` indicates source-code visibility. `publication` is explicit publication consent. A private project requires `public_private_approved: true` in addition to general approval.
- Review approvals bind to SHA-256 of exact metadata. A changed draft goes back to `needs_review`.
- Clicking a heart approves one content digest only. Actual publication requires a second action.
- No arbitrary repository code is executed in the MVP.
- The Review Studio is bound to loopback by the CLI. No public exposure without authentication or trusted network policy.
- Provider API tokens are passed via environment variables, never embedded in output.
- Current delivery uses a neutral, simple theme; the existing PEGINELAB design will be ported as a compatibility theme before adoption.

## Review checklist

Identity, description, authentic screenshots, links, privacy, security and SEO. Rejection always requires a comment. Deferral is reversible by restaging a modified project. Decision history is kept in SQLite.

## Deliberate limitations of v0.1

- No automatic Playwright execution or external URL capture (must be sandboxed and authorized first).
- Git provider adapters are read-only and not yet tested against live GitLab/Forgejo.
- No automatic multilingual transformation or reproduction of PEGINELAB's 11 locales.
- No public production deployment, no modification of `view_my_prj` / `my_self`.
- No user authentication beyond loopback-only access; keep private API behind SSH tunnel.
- No versioned undo in the Studio UI yet; history is retained in SQLite.
- The minimum static theme is a technical baseline, not a replacement for the existing portfolio.

## Acceptance gates

- Run tests for parsing, overwrite safety, hash-invalidated approvals, publication privacy and HTML escaping.
- Review three independent project repositories and then perform a parallel visual comparison with current 20-project showcase.
- Verify canonical routes, 11 locales, sitemap, navigation, screenshots and mobile layouts before any eventual migration.
