# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in SDLC Agentic Harness, please report
it privately rather than opening a public issue.

- Use GitHub's [private vulnerability reporting](https://github.com/peterscheffer/sdlc-agentic-harness/security/advisories/new)
  ("Report a vulnerability" under the Security tab), or
- Open a minimal public issue asking a maintainer to make contact, without
  disclosing details.

Please include:

- A description of the issue and its impact
- Steps to reproduce
- Affected version / commit

You can expect an acknowledgement within a few days. Once a fix is available,
we'll coordinate disclosure with you.

## Scope notes

- This tool reads API keys from environment variables / a local `.env` file.
  Never commit `.env` or paste real keys into issues, PRs, or logs. The LLM
  utility redacts known key patterns from its logs, but treat any captured
  output as potentially sensitive.
- The pipeline executes configured shell commands (test/lint/build) and git
  operations on your behalf. Only run it against repositories and commands you
  trust.
