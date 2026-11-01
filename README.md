<div align="center">
  <img src="https://avatars.githubusercontent.com/u/317308737?s=200&v=4" width="96" alt="Boxdawn" />
  <h1>Boxdawn</h1>
  <p><strong>Stop AI agent mistakes before they run.</strong></p>
  <p>
    <a href="https://boxdawn.com">Website</a> ·
    <a href="https://github.com/boxdawn/guard">Guard for Claude Code</a> ·
    <a href="https://boxdawn.com/analyze">Analyze a trace</a> ·
    <a href="https://boxdawn.com/privacy">Privacy</a>
  </p>
</div>

---

Boxdawn is the safety layer for AI agents: the point between what an agent decides and what it does, where a destructive action is caught before it reaches your data, your systems or your bill.

## Products

| | |
|---|---|
| **[Boxdawn guard](https://github.com/boxdawn/guard)** | A Claude Code plugin that judges every Bash and PowerShell command before it runs and denies or holds for approval the destructive ones. Windows, macOS and Linux. |
| **[Trace analyzer](https://boxdawn.com/analyze)** | Drop a trace file, no account, and get a report from four deterministic detectors with the cost of each, from the trace's real usage fields. |
| **[Dashboard](https://boxdawn.com)** | A daily waste rate per project, keyed on the day your sessions ran, and API keys for CI and scripts, issued and revoked per project. |

Install the guard:

```
claude plugin marketplace add boxdawn/guard
claude plugin install boxdawn-guard@boxdawn
```

## About this repository

This repository holds the source of the trace analyzer up to `0.5.24` (2026-10-27), released on PyPI through `0.5.23`. The analyzer runs at [boxdawn.com/analyze](https://boxdawn.com/analyze).

## License

MIT, for the contents of this repository. Built by **[Boxdawn](https://boxdawn.com)**.
