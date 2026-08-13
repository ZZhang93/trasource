# Contributing

Thank you for helping improve Trasource.

## Before You Start

- Use an issue to describe substantial behavior or data-format changes before
  implementation.
- Keep user data local and never commit API keys, runtime databases, imported
  documents, or generated sidecar binaries.
- Add a regression test for bug fixes whenever the behavior can be exercised
  without an external AI service.

## Development

Follow the setup instructions in `README.md`, then run:

```bash
npm run check
npm run prepare:sidecar:dev
(cd src-tauri && cargo check --locked)
```

The full check includes TypeScript/Vue compilation, translation parity,
version consistency, frontend tests, and backend tests. AI-provider tests use
mocks and must not require real credentials or network access.

## Pull Requests

- Explain the user-visible outcome and any migration or compatibility impact.
- Keep unrelated formatting and generated artifacts out of the change.
- Update `CHANGELOG.md` under **Unreleased** for notable behavior.
- Confirm all quality checks pass on macOS, Linux, and Windows CI.

By contributing, you agree that your contribution is licensed under the
repository's AGPL-3.0-only license.
