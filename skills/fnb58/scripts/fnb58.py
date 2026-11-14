#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["bleak"]
# ///
"""Read a FNIRSI FNB58 USB power meter over Bluetooth LE.

  fnb58.py scan                       list nearby FNB58s
  fnb58.py log [-d SECS] [-o CSV] [--live] [--address MAC]
      -d 0 (default 30) / Ctrl-C stops; prints a summary at the end.
"""
import argparse, asyncio, csv, signal, statistics as st, struct, sys, time
from bleak import BleakClient, BleakScanner

NOTIFY = "0000ffe4-0000-1000-8000-00805f9b34fb"
WRITE = "0000ffe9-0000-1000-8000-00805f9b34fb"
INIT = [bytes.fromhex("aa8100f4"), bytes.fromhex("aa8200a7")]
is_fnb = lambda d, a: (a.local_name or d.name or "").startswith(("FNB58", "FNB48", "FNB"))


class Decoder:
    """Frames: aa <type> <len> <payload[len]> <chk>. Little-endian."""
    def __init__(self, t0, live):
        self.buf, self.rows, self.t0, self.live = bytearray(), [], t0, live
        self.dp = self.dm = self.ohm = None

    def feed(self, data):
        self.buf += data
        while len(self.buf) >= 3:
            if self.buf[0] != 0xAA:
                del self.buf[0]; continue
            n = self.buf[2]
            if len(self.buf) < 4 + n:
                return
            typ, p = self.buf[1], bytes(self.buf[3:3 + n])
            del self.buf[:4 + n]
            if typ == 0x04 and n >= 12:      # V, I, P  (x1e-4)
                v, i, w = (x / 1e4 for x in struct.unpack_from("<III", p))
                row = (round(time.time() - self.t0, 3), v, i, w, self.dp, self.dm, self.ohm)
                self.rows.append(row)
                if self.live:
                    print(f"{row[0]:8.2f}s  {v:7.4f} V  {i*1000:8.2f} mA  {w:7.4f} W", flush=True)
            elif typ == 0x06 and n >= 4:     # D+, D- (mV)
                a, b = struct.unpack_from("<HH", p); self.dp, self.dm = a / 1e3, b / 1e3
            elif typ == 0x05 and n >= 4:     # load resistance (x1e-4 ohm)
                self.ohm = struct.unpack_from("<I", p)[0] / 1e4


async def find(address, timeout=15):
    if address:
        d = await BleakScanner.find_device_by_address(address, timeout=timeout)
    else:
        d = await BleakScanner.find_device_by_filter(is_fnb, timeout=timeout)
    if not d:
        sys.exit("No FNB58 found over BLE. Is it on with Bluetooth enabled, and not connected to the phone app?")
    return d


async def scan(_):
    found = await BleakScanner.discover(timeout=8, return_adv=True)
    hits = [(d, a) for d, a in found.values() if is_fnb(d, a)]
    for d, a in hits:
        print(f"{d.address}  {a.local_name}  rssi {a.rssi}")
    if not hits:
        print("none found")


async def log(args):
    dev = await find(args.address)
    print(f"connecting to {dev.name} ({dev.address})", file=sys.stderr)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, stop.set)
    loop.add_signal_handler(signal.SIGTERM, stop.set)
    async with BleakClient(dev, timeout=20, disconnected_callback=lambda _: stop.set()) as c:
        dec = Decoder(time.time(), args.live)
        await c.start_notify(NOTIFY, lambda _, d: dec.feed(d))
        for cmd in INIT:
            await c.write_gatt_char(WRITE, cmd, response=False)
            await asyncio.sleep(0.3)
        try:
            await asyncio.wait_for(stop.wait(), args.duration or None)
        except asyncio.TimeoutError:
            pass
    rows = dec.rows
    if not rows:
        sys.exit("connected but received no data")
    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "volts", "amps", "watts", "dplus_v", "dminus_v", "load_ohm"])
            w.writerows(rows)
    T = max(rows[-1][0] - rows[0][0], 1e-9)
    print(f"\n{dev.name}: {len(rows)} samples over {T:.1f}s ({len(rows)/T:.1f} Hz)"
          + (f" -> {args.out}" if args.out else ""))
    for name, idx, unit in (("Voltage", 1, "V"), ("Current", 2, "A"), ("Power", 3, "W")):
        x = [r[idx] for r in rows]
        print(f"  {name:8s} mean {st.mean(x):.4f} {unit}  min {min(x):.4f}  max {max(x):.4f}  sd {st.pstdev(x):.4f}")
    # trapezoidal integration
    e = q = 0.0
    for a, b in zip(rows, rows[1:]):
        dt = b[0] - a[0]; e += (a[3] + b[3]) / 2 * dt; q += (a[2] + b[2]) / 2 * dt
    print(f"  Energy   {e/3.6:.3f} mWh   Charge {q/3.6:.3f} mAh")
    last = rows[-1]
    if last[4] is not None:
        print(f"  D+ {last[4]:.3f} V  D- {last[5]:.3f} V  Load {last[6]} ohm")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan")
    lg = sub.add_parser("log")
    lg.add_argument("-d", "--duration", type=float, default=30, help="seconds; 0 = until Ctrl-C")
    lg.add_argument("-o", "--out", help="CSV output path")
    lg.add_argument("--live", action="store_true", help="print each sample")
    lg.add_argument("--address", help="BLE MAC (default: first FNB* found)")
    args = ap.parse_args()
    asyncio.run({"scan": scan, "log": log}[args.cmd](args))


if __name__ == "__main__":
    main()
