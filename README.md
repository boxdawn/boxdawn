# Boxdawn

**Open your AI agents' black box. Stop the next mistake before it runs.**

Boxdawn is building the safety and security layer for AI agents: the point between what an agent decides and what it does, where a mistake can be caught, stopped, reported and fixed before it reaches your data, your systems or your bill.

**Try it on one trace**, no account: **[boxdawn.com/analyze](https://boxdawn.com/analyze)**

---

## The chain

**monitor → detect → block → alert → fix → govern**

Detection is the link that runs today, as a service on the traces you upload. The rest is being built.

## Running today

- **Hosted analyzer, no account.** Drop a trace file at [boxdawn.com/analyze](https://boxdawn.com/analyze) and get a report.
- **Four deterministic detectors** over the trace files your agents already write.
- **Cost from real usage fields**, with per-model rates pinned to their sources.
- **Accounts and per-project history.** Project history keeps derived numbers, not the trace file.
- **Daily waste rate by session date**, so a backfill of old traces lands on the days they ran.
- **API keys for CI and scripts**, issued and revoked per project.

## Building next

- Blocking destructive actions before they run
- Stopping agent errors before they spread to other agents
- Block alerts (email, Slack)
- Auto-fix
- Policy and governance
- Stopping runaway loops
- Budget guard for Claude Code
- Real-time monitoring

---

## About this repository

Released on PyPI through `0.5.23`. The source here stops at `0.5.24` (2026-10-27); development continues privately, and [boxdawn.com](https://boxdawn.com) is where the product runs.

## License

MIT, for the contents of this repository. Built by **Boxdawn**.
