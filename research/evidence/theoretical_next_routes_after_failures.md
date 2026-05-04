# SN9C292B OSD Permanent-Off Theoretical Routes After Failures

Date: 2026-05-02

## Scope

This is a no-device-write, no-new-firmware-candidate analysis.

The current connected camera is not reliably recoverable by the user right now,
so the next step should be theoretical triage only. The goal is to reduce the
next burn attempt to a patch family that is meaningfully different from the
two hardware-rejected OSD-enable-state patches.

## Hard Evidence So Far

### Runtime OSD Disable Works, But Is Volatile

On stock firmware, the Windows XU probe proved:

- OSD GET after replug: `Line=1`, `Block=1`
- Runtime `--set 0 0` changes it to `Line=0`, `Block=0`
- Replug restores OSD, so the setting is RAM-only unless another persistence
  mechanism is found.

### Flash Write/GUI Burn Path Works

The GUI burner extracted a ROM image identical to the live dump:

- Size: `0x20000`
- SHA256:
  `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`

The GUI burner also successfully wrote a patched image, proven by read-back.
So the failure mode is not "cannot flash"; the failure mode is "wrong patch
target".

### Three Branches Are Rejected

1. `0x1001E/0x1001F`

   Result: OSD remained enabled, image became inverted.

   Interpretation: this byte pair belongs to video/sensor/config data, not the
   persistent OSD enable default.

2. Direct boot initializer `0x0D74E: 0x13 -> 0x10`

   Result: no normal USB enumeration.

   Interpretation: live `XDATA[0x0D2C] = 0x10` clears OSD, but baking that value
   into boot initialization breaks early firmware state.

3. Runtime writer handler patch at `0x0C66F/0x0C6AB`

   Result: no normal USB enumeration.

   Interpretation: the `0x0C63F..0x0C6B5` handler and the
   `0x0D2C/0x0C3A/0x1530/0x1580` state group are coupled to critical USB/video
   state. This family should not be patched again without much stronger proof.

### Old 0x0B7x Theory Does Not Apply Directly To This Dump

The old EDESIX reference firmware has classic patterns:

- `90 0B 75 74 01 F0`
- `90 0B 76 74 01 F0`
- `90 0B 77 74 01 F0`

The current live dump has none of these exact enable-write patterns.

The current dump does contain references to `0x0B75`, `0x0B77`, and `0x0BA5`,
but the observed windows are config/data-transfer code, not obvious OSD enable
stores. This matches the failed `0x1001E/0x1001F` result: nearby data can affect
video setup instead of OSD.

## Current Static Comparison Notes

The current live dump is not byte-identical to the old EDESIX OV2710 target:

- Current vs old EDESIX OV2710: `55,733` bytes differ.
- Current vs NO-OSD OV9712: `104,447` bytes differ.
- Current has `90 0D 2C` at seven locations; old EDESIX does not.
- Current has `OV2710` once at `0x2012`.
- Current has no ASCII `OSD`, `Date`, `Time`, or `USB Camera` strings.

Implication:

- The old project-vibe reports are useful as historical warning and comparison
  material, but offsets from those reports cannot be treated as direct patch
  addresses for the current dump.
- The NO-OSD firmware is not a burnable donor. Its value is only comparative:
  finding classes of data/code that are absent or neutralized in no-OSD builds.

## Ranked Next Routes

### Route 1: Host-Side Auto Runtime Disable

Status: safest practical workaround.

Idea:

- Keep stock firmware.
- On every device arrival, run the proven runtime command equivalent to:
  `windows_xu_osd_probe.exe --set 0 0`.

Why it is valuable:

- Zero flash risk.
- It already works when the camera enumerates.
- It can be automated with Windows Task Scheduler, a background service, or a
  Linux udev/systemd rule.

Limit:

- Not true device-side permanence.
- OSD may appear briefly between USB enumeration and the auto-disable command.

This route should remain the fallback baseline even if firmware work continues.

### Route 2: Runtime-Only Persistence Hunt

Status: next safest real research path after recovery.

Idea:

- Before burning anything else, exhaust all Sonix XU controls that may save OSD
  parameters or user settings into flash.
- Test not only OSD enable, but also size, auto-scale, color, start position,
  multi-size, and string.

Why it is promising:

- Existing Sonix TestAP output proves the camera exposes multiple OSD controls:
  enable, size, autoscale, color, start position, multi-size, and string.
- Some Sonix devices may have a separate save/config pathway, even if direct
  `Set_Enable(0,0)` is volatile.

What to test later, on a recovered enumerating device:

- Set line/block disabled, then search RAM/XDATA changes beyond `0x0D2C`.
- Try setting OSD string to blanks or nulls, then replug.
- Try moving start position off-screen, then replug.
- Try font and border colors, then replug.
- Search the Sonix SDK/DLL/burner for a "save parameter" or "commit to flash"
  control path.

Limit:

- Current Windows probe only implements enable and low-level reads/writes.
  More XU commands would need to be mapped or implemented.

### Route 3: Make OSD Invisible Instead Of Disabling The Engine

Status: best theoretical firmware direction.

Idea:

- Stop patching the OSD enable state.
- Let the firmware believe OSD is enabled, but make the rendered output blank,
  transparent, off-screen, or visually harmless.

Candidate sub-routes:

1. Blank glyph/font data

   Find the font/glyph bitmap table used for digits/date/time and replace only
   glyph bitmaps with blank glyphs.

   Benefit: likely pure data if correctly identified.

   Risk: hard to identify without strong static evidence.

2. Blank or space out OSD character buffer initialization

   Find the code/data that seeds the overlay character cells and make it write
   spaces or zero-length text.

   Benefit: targets visible content rather than boot/USB state.

   Risk: current ROM has no obvious ASCII strings, so content may be generated
   numerically.

3. Color/attribute invisibility

   Change default font/border color or attribute bytes so foreground and border
   become transparent or match background.

   Benefit: smaller and more local than disabling control bits.

   Risk: if color values map to video pipeline registers, wrong values could
   affect image color or format.

4. Off-screen/default-position route

   Change default start row/column or size so OSD draws outside visible area or
   at size zero.

   Benefit: preserves OSD engine and control state.

   Risk: bounds checks may clamp position; bad geometry may hit rendering bugs.

Research gate before any burn:

- Identify a candidate data table.
- Prove it is not in the sensor/video config block.
- Prove no USB descriptor or boot-state code bytes are changed.
- Prefer a candidate that modifies only a small data table and not executable
  branches.

### Route 4: Late Post-USB Clear Hook

Status: possible but currently high risk.

Idea:

- Add a delayed call after USB enumeration/video init that invokes the existing
  clear path equivalent to `Set_Enable(0,0)`.

Why it is tempting:

- It would preserve the early boot value that USB/video seems to require.
- It targets a moment closer to the known-working runtime disable behavior.

Why it is dangerous:

- It requires code-cave/hook work.
- The old late-clear/hook branches in the historical repo often led to Code 10
  or failed start states.
- The latest runtime-writer patch shows that even "runtime-looking" OSD code can
  still be critical during boot.

This should not be the next burn target unless a clear post-enumeration anchor is
found from logs, XU traces, or IDA call graph proof.

### Route 5: Cross-Firmware Transplant

Status: not recommended for burning.

Idea:

- Borrow code/data from `NONAME_SN9_NO_OSD_OV9712` or an AMCREST/no-OSD build.

Problem:

- Sensor differs.
- The current dump differs substantially from the old EDESIX and NO-OSD images.
- Previous hybrid/safe-data attempts in the historical repo were not a proven
  solution for the current camera.

Safe use:

- Use donor firmwares only to locate possible font, string, OSD attribute, or
  layout tables.
- Do not transplant code blocks or broad data regions.

### Route 6: Hardware Programmer First, Then Continue Firmware Burns

Status: engineering prerequisite for further risky attempts.

Idea:

- Get a 3.3 V SPI programmer or reliable SOIC8 clip setup.
- Read the flash externally and verify it matches the GUI stock backup.
- Only then resume burn testing.

Why it matters:

- Current patch families can produce no-enumeration states.
- Without shorting/programmer recovery, software recovery is impossible when the
  device never publishes VID/PID.

## Decision

Until hardware recovery is convenient again, do not create or flash another ROM
candidate.

The best theoretical next work is:

1. Expand runtime XU control knowledge offline from Sonix sources/binaries.
2. When the device is recovered, test all OSD runtime controls for replug
   persistence before touching firmware.
3. If firmware patching resumes, target invisible rendering data:
   font/glyph/string/color/position tables.
4. Avoid all patches that directly change:
   `0x0D2C`, `0x0C3A`, `0x1530`, `0x1580`, or the `0x0C63F..0x0C6B5`
   set-enable handler.

The strategic shift is:

```text
old idea: make OSD enable state false
new idea: keep OSD state valid, make OSD output invisible
```

This is the first route that is materially different from both no-enumeration
failures.
