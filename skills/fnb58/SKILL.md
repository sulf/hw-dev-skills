---
name: fnb58
description: >
  Read live voltage, current and power from a FNIRSI FNB58 USB power meter over
  Bluetooth LE, log it to CSV, and summarize (mean/min/max, mWh, mAh). Use when the
  user wants to measure, monitor or log how much power a USB device draws, or mentions
  FNB58, FNIRSI, USB power meter, or USB tester. Triggers: "power draw", "how much
  current", "measure power", "battery life estimate", "log current while I ...".
---

# FNB58 USB power meter (BLE)

The meter sits in-line between the power source and the device under test, and
sends readings over BLE (it advertises as `FNB58-xxxxxx`). It does not need its
USB data port connected, and it does not need pairing. The phone app must not be
connected, because the meter accepts only one BLE client at a time.

## Usage

The script is a uv inline-script (bleak is installed automatically):

```bash
S=~/.claude/skills/fnb58/scripts/fnb58.py
uv run --script $S scan                          # find meters + MAC
uv run --script $S log -d 30 -o /path/out.csv    # 30 s capture + summary
uv run --script $S log -d 0 --live               # stream until Ctrl-C/SIGTERM
uv run --script $S log --address AA:BB:CC:DD:EE:FF -d 60 -o out.csv
```

- Rate is about 4 Hz, so a short spike (TX bursts, boot inrush) can be missed.
  Say so if the user cares about transients.
- The summary gives V/I/P mean, min, max and SD, plus energy (mWh) and charge (mAh)
  integrated over the capture, and the latest D+/D− voltages and load resistance.
- Put CSVs in the scratchpad or a temp dir unless the user names a location.
- For a "measure while I do X" request, run `log -d 0 -o file.csv` with
  `run_in_background`, have the user do X, stop it with TaskStop (SIGTERM saves the
  CSV and prints the summary), then analyze the CSV.
- Chart the CSV when a trend matters (load the dataviz skill first).
- To estimate battery life: battery mAh ÷ mean mA. Note that this measures at 5 V
  USB input, so on-board regulator losses are included.

## Troubleshooting

- "No FNB58 found": the meter is off, Bluetooth is off on the meter, or the phone
  app is holding the connection. Check `bluetoothctl show` (Powered: yes).
- It connects but gets no data: re-run. The init writes are sometimes dropped.

## Protocol (reverse-engineered, verified with V×I = P)

- GATT: notify `0000ffe4-…` (service ffe0), write `0000ffe9-…` (service ffe5).
- Start: write `aa8100f4`, then `aa8200a7` (write-without-response).
- Notifications concatenate frames: `aa <type> <len> <payload> <chk>`, little-endian:
  - `0x04` (12 B): V, I, P as uint32 ×1e-4 (V, A, W)
  - `0x07` (4 B): V mV, I mA as uint16 (lower resolution duplicate)
  - `0x06` (6 B): D+ mV, D− mV as uint16, then 2 unknown bytes
  - `0x05` (7 B): load resistance uint32 ×1e-4 Ω, then 3 unknown bytes
    (one is possibly temperature, unconfirmed)
  - `0x08` (17 B): accumulators and a seconds counter (scaling not confirmed)
- Checksum byte not validated (algorithm unknown); framing by length is reliable.
