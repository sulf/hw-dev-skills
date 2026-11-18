---
name: pr-hw-validation
description: Validate a firmware pull request on real hardware by running the same checks on the base build and the PR build, then comparing. Use when reviewing or testing a firmware PR and the user wants on-device evidence, or asks to "validate on hardware", "bench test this PR", "test before/after", or "compare against main on the device".
---

# PR hardware validation (before/after)

Host tests and CI builds show that a firmware change compiles and that its logic holds
in isolation. Only the device shows what the change does to the radio, the timers and
the peripherals. This skill runs one set of checks against the base build and the PR
build on the same hardware, then compares the two.

## 1. Work out what hardware the PR needs

Read the diff and name the boards and peripherals it touches: the target board or
boards, any companion chip, and anything the change depends on, such as an access
point, Ethernet, a second node or a power meter. Write the list down in plain words,
for example "one Wi-Fi basestation on a 2.4 GHz AP whose power can be cut".

Then decide what a before/after run can show for this PR:

- **Reproducible**: the bug or behaviour can be triggered on demand. Plan a trigger,
  the signal that shows it, and a pass criterion for each build.
- **Not reproducible on demand**, for example a rare stall: a before/after run only
  shows the change causes no regression. Say so up front, and plan smoke checks
  (boot, connect, normal operation for N minutes, logs free of new errors).

## 2. Look for the hardware, read-only

List what is attached without opening any port:

```bash
ls -l /dev/serial/by-id/ 2>/dev/null     # USB serial adapters and native USB consoles
lsusb                                    # Espressif 303a, SEGGER J-Link 1366, CP210x 10c4, CH34x 1a86, FTDI 0403
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Check for any bench notes the user keeps, such as a probe inventory or a memory file
with serial numbers, IPs and flash recipes, and match devices to them.

Opening a serial port can reset the board, because DTR/RTS drive EN and BOOT on many
dev boards. Listing `/dev` and `lsusb` never touches the device. Don't open a port at
this step.

## 3. Ask the user, every time

Always ask before you touch hardware, even when a matching board is attached. One
question per PR, with these options:

- **Use the detected hardware**: name each device and what you will do to it,
  including flashing, rebooting, power-cycling and how long it takes.
- **I'll connect it**: the user provides the hardware. Wait, then repeat step 2.
- **Skip hardware validation**: carry on without it, and record in the review that
  the PR was not checked on a device.

State in the question what each build needs, for example "flashes base then PR
firmware to the board on /dev/ttyUSB0, about 10 minutes, restores its current
firmware afterwards". Treat "skip" as a normal answer and don't argue with it.

Never flash, reboot or open a console on a device that is in service, such as one
installed at a site or used by someone else, without the user naming it explicitly.

## 4. Prepare

1. Record the device's current state: firmware version, build or commit, and the
   console's status output. That state is what you restore at the end.
2. If the flash layout allows it, back up the app partition, or keep the exact image
   that was running.
3. Build both images from clean worktrees: base at the merge-base, and the PR head.
   Record both SHAs and the SHA-256 of each image.
4. Flash the app partition only, so NVS or config (identity, credentials, pairing)
   survives. If the PR changes the bootloader, partition table or flash layout, stop
   and ask. Those changes can break the restore path or brick the board, and need
   their own explicit go-ahead.

## 5. Run

For each build, base first and then the PR:

1. Flash, verify the readback or checksum, and confirm the version string on boot.
2. Run the same trigger or smoke steps, with the same timings and the same
   environment. Capture the console log to a file per build.
3. Record each pass criterion as met or not met, with the log line that shows it.

Don't mix trigger methods between builds. If the environment changes mid-run, for
example the AP reboots or someone handles the board, note it and rerun that build.

If an `fnb58` meter is attached and the PR could change power draw, log current for
the same window on both builds.

## 6. Restore and report

Flash the original image back, confirm the original version on boot, and check that
identity and config survived.

Report a short table:

| Check | Base `<sha>` | PR `<sha>` |
|---|---|---|
| Boots, version string | … | … |
| Trigger / smoke step | … | … |

Then add what the run proves and what it doesn't, the log files' paths, and whether
the restore succeeded. If anything couldn't be restored, say so first.

When posting the result to the PR, only post if the user asked, and follow their
comment conventions. A hardware result is evidence for the review. It doesn't replace
reading the code.
