# PL Code Store — Marketing is a Folder

## Главный режим — GitHub Actions → GitHub Pages (без своего сервера)

**Новая витрина создаётся только из исходных папок `vitrine/`**, а не копированием `view_my_prj`.

- GitHub Actions: `scripts/auto_vitrine.py` — экономный ежедневный поиск репозиториев, создание предложений `vitrine/` через Pull Request.
- Автор: **Approve / Request changes / Merge** внутри GitHub (можно перейти из будущего Review Studio на GitHub Pages).
- GitHub Actions: `scripts/build_pages.py` — статический HTML только из одобренных `vitrine/meta.json`, включая оформленные закрытые проекты без ссылок на код.
- GitHub Pages: `https://musikfed.github.io/PLCodeStore/` — презентация продукта и каталог.
- **Один** `PL_CODESTORE_TOKEN` в Secrets Actions достаточно для выбранных исходных репозиториев; токен не размещается в браузере.
- Встроенный `GITHUB_TOKEN` ограничен одним репозиторием и для управления остальными проектами не подходит.

[Полная инструкция настройки GitHub, токена и правил публикации](docs/GITHUB_AUTOMATION.md).

**Важно:** статическая демонстрация свайпов на Pages не производит Git-операций. Реальное решение принимается в PR, где GitHub предоставляет Approve, Request changes и Merge.

---


**«Маркетинг — это папка. Публикация — это решение автора».**

Local-first, Git-provider-neutral tool for preparing, reviewing, and publishing authentic software-project showcases. An author reviews each version before it can be published.

> **Status: v0.1 MVP on feature branch.** The parser, review storage, local Review Studio and basic static delivery are implemented. This is *not* yet the complete multi-provider marketplace or a replacement for the PEGINELAB showcase.

## Quick start

Python 3.12+ required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
plcodestore init examples/sample_project --dry-run
plcodestore validate examples/sample_project
plcodestore stage examples/sample_project
plcodestore review
```

Open **http://127.0.0.1:8077**. Check all seven criteria and click ❤️ to approve, or 🛑 to request changes with a comment.

**Publication is a separate action**, deliberately not triggered by the approval gesture:

```bash
plcodestore publish demo-camera
plcodestore build --out output
python -m http.server 8088 --directory output
```

Then open http://127.0.0.1:8088. The generated files have no backend dependency.

**Windows**: activate with `.venv\\Scripts\\activate` or run commands through `.venv\\Scripts\\plcodestore.exe`.

### Safely add another project

```bash
plcodestore scan /path/to/project     # read-only inspection
plcodestore init /path/to/project     # writes vitrine/meta.json only if absent
```

The generated metadata begins with `publication: disabled` and `visibility: private`. Check and edit it yourself; approval requires explicit permission. Existing author metadata is never overwritten.

## Portable vitrine standard

```text
your-repository/
└── vitrine/
    ├── meta.json              # author-owned, validated metadata
    ├── screenshots/           # optional authentic media
    ├── changelog.md           # optional
    └── generated/             # optional tool-owned drafts
```

The standard distinguishes code visibility from publication consent and checks an exact SHA-256 content revision during review.

## Architecture

- `parser.py`: safe manifest inspection and non-destructive initialization.
- `providers.py`: read-only GitHub, GitLab and Forgejo REST provider classes (initial implementation).
- `review.py`: SQLite-backed revision-accurate decisions.
- `studio.py`: FastAPI local-only review UI and checklist with swipe gestures.
- `delivery.py`: Jinja2-generated static catalog from published snapshots.
- `cli.py`: init, scan, validate, stage, review, publish, build and status.

See [implementation tracker](docs/TZ_CHECKLIST.md) and [architecture and limitations](docs/ARCHITECTURE.md).

## Privacy and truthfulness

Never execute an untrusted source project to take screenshots. Never publish a private project without an explicit public-metadata approval. Never invent a product UI or features. Never overwrite an existing `vitrine/meta.json`. Access to the Studio is intentionally limited to loopback.

## PEGINELAB compatibility

- [view_my_prj](https://musikfed.github.io/view_my_prj/) remains the existing 20-project showcase and future visual-compatibility benchmark.
- [my_self](https://musikfed.github.io/my_self/) remains a separate résumé.
- [peginelab.ru](https://peginelab.ru/) remains the brand site.

**No existing website is modified by this MVP.**

## Tests

```bash
python -m pytest -q
```

Future work: sandboxed Playwright capture, image review, multilingual pages, import of existing 20 products, provider integration tests, safe deployment and rollback.
