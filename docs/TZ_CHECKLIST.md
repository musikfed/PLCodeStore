# PL Code Store 2.0 · implementation tracker

Legend: [x] implemented and committed; [ ] pending (not advertised as complete).

## A. Standard and Parser
- [x] Vitrine v1.0 metadata contract, JSON Schema validation and inferred sources
- [x] Python/Node/Rust/Go/PlatformIO manifest detection
- [x] Non-destructive init, dry-run, no automatic project-code execution
- [ ] Safe, explicit Playwright capture and media validation
- [ ] Optional Ollama assisted descriptions with human review

## B. Registry and Integrations
- [x] Read-only adapter structure for GitHub/GitLab/Forgejo
- [x] Normalized discovery of `vitrine/meta.json`
- [x] SQLite review/published state
- [ ] Provider API integration tests with live environments, pagination/error handling and caching
- [ ] Incremental synchronization, webhook processing, concurrent duplicate reconciliation

## C. Review Studio
- [x] Local browser UI with cards, swipe and button actions
- [x] Checklist, mandatory rejection comments, review revisions
- [x] Author approval distinct from explicit publishing
- [x] Durable SQLite decisions and history API
- [ ] Undo, drag/mouse interaction, side-by-side diffs
- [ ] Media previews, attachment comments, agent-assisted repair

## D. Delivery
- [x] Static HTML pages and searchable catalog with escaped content
- [x] Safe publication snapshot, no private code links
- [ ] Existing PEGINELAB theme and rich original project previews
- [ ] 11 languages, canonical, hreflang, sitemap, full SEO completeness
- [ ] Deploy to Pages, GitLab Pages and Nginx with atomic rollback

## E. CI and Release
- [x] GitHub tests workflow
- [ ] Tag-based version routing, GitLab CI and Forgejo Actions adapters
- [ ] Cross-repo event triggers and immutable artifact deployment

## F. Existing sites
- [x] PL Code Store kept in a separate repository
- [x] Existing `view_my_prj` and `my_self` untouched
- [ ] Import all 20 existing PEGINELAB projects to review queue
- [ ] Side-by-side visual/SEO regression comparison
- [ ] Author-confirmed, reversible switchover (not automatic)

## G. Product readiness
- [ ] Installation on Windows/Linux/macOS in clean environment
- [ ] Independent developer usability test
- [ ] License and stable public release
