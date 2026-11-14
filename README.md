# hw-dev-skills

[Claude Code](https://claude.com/claude-code) skills for hardware development work.

| Skill | What it does |
|---|---|
| [`fnb58`](skills/fnb58) | Reads a FNIRSI FNB58 USB power meter over Bluetooth LE: live V/I/P, CSV logging, and energy and charge summaries. Includes a decode of the reverse-engineered BLE protocol. |

## Install

```bash
git clone https://github.com/sulf/hw-dev-skills ~/src/hw-dev-skills
ln -s ~/src/hw-dev-skills/skills/fnb58 ~/.claude/skills/fnb58
```

The scripts are [uv](https://docs.astral.sh/uv/) inline scripts, so dependencies install
automatically on first run. The `fnb58` skill needs Linux/macOS with BlueZ/CoreBluetooth.

## Standalone use

The scripts also work without Claude:

```bash
uv run --script skills/fnb58/scripts/fnb58.py scan
uv run --script skills/fnb58/scripts/fnb58.py log -d 60 -o out.csv
```
