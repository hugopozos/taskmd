# Contributing to TaskMD

Thanks for your interest! TaskMD is a small, focused tool and we want to keep it that way.

## How to contribute

### Bug reports

Open an [issue](https://github.com/<your-username>/taskmd/issues/new?template=bug_report.md)
with:

- A clear title and description.
- Steps to reproduce.
- Expected vs actual behaviour.
- Your environment (OS, browser, Docker version if relevant).

### Feature requests

Open an [issue](https://github.com/<your-username>/taskmd/issues/new?template=feature_request.md)
with:

- What problem you're solving (not just a proposed solution).
- Why it fits TaskMD's scope (local-first, markdown-native, AI-friendly).
- A sketch of the implementation if you have one.

### Pull requests

1. Fork the repo.
2. Create a branch: `git checkout -b feature/my-change`.
3. Make your changes. Keep them focused — one PR = one concern.
4. Test that `docker compose up` still works and the frontend loads.
5. Push and open a PR against `master`.
6. In the PR description, link to any related issue.

### Code style

- Python: follow PEP 8. `server.py` is a single file — keep it readable.
- TypeScript/React: use functional components and hooks. No classes.
- Markdown: 4-column format from `SPEC.md` must be preserved.

### Scope

TaskMD is intentionally minimal. If your change adds a database, a build step,
a cloud dependency, or a new configuration language, it probably doesn't belong
here. Consider forking instead.

### License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
