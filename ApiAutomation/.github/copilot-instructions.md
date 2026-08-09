# Copilot instructions

- Read the repository `AGENTS.md` before editing.
- Treat `common/` modules as the public test surface; keep pytest files as thin scenario adapters.
- Mark every real external request test with `@pytest.mark.api`. The collection gate only allows them with `--run-api`.
- Keep credentials and input data under ignored `data/local/`; commit only redacted templates under `data/examples/`.
- Read the encryption key with `settings.require_encrypt_key()` and redact responses before logging.
- Use `BatchRunner` for concurrency and retry. POST requests must not gain implicit transport retries.
- Run `pytest` for offline verification and `ruff check .` for static checks. Never claim real API coverage unless `--run-api` actually ran.
