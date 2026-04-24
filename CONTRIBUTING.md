# Contributing

Thanks for your interest. This is a hobby project — contributions are welcome, but please read this first.

## Expectations

This is maintained in spare time. Response times on issues and PRs may be slow (days to weeks). There is no SLA. If something is urgent for you, fork it.

## Reporting issues

Open a GitHub issue with:
- What you were trying to do
- What happened (error message, unexpected output)
- Your OS, Python version, and which LLM provider you configured

## Submitting a PR

Good candidates for PRs:
- New ATS provider support (Workday, SmartRecruiters, Taleo, etc.)
- Bug fixes with a clear reproduction case
- Documentation improvements

Before opening a PR:
1. Check existing issues and PRs to avoid duplicates
2. For non-trivial changes, open an issue first to discuss the approach
3. Keep changes focused — one thing per PR
4. Existing tests should pass (`uv run pytest`)

## What's out of scope

- Changes that require modifying `configs/profile.yaml` structure in a breaking way
- UI redesigns without prior discussion
- Dependencies on paid external services

## License

By contributing, you agree your contributions will be licensed under the MIT License.
