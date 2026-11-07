# PL Code Store · Provider sync

```bash
cp config.example.json config.json
# edit provider owner/api_url/token_env
plcodestore sync --config config.json --dry-run
plcodestore sync --config config.json
plcodestore review
```

`sync` reads only `vitrine/meta.json` from opted-in repositories. It never modifies external repositories. No source-code execution or screenshot capture. The per-provider `token_env` points to an environment variable; never paste a personal token into JSON.

Public repositories can be discovered without authentication where API limits allow. Private repository listing requires a suitable token and `include_private` set explicitly, but **does not allow publication**. Published private metadata additionally requires `public_private_approved: true` and checklist approval.

Default configuration is illustrative; any unsupported provider error is reported. Current adapters need live provider integration tests before production use.

The Studio is local-only: `http://127.0.0.1:8077`. Do not expose it via internet-facing reverse proxy without authentication and CSRF controls.
