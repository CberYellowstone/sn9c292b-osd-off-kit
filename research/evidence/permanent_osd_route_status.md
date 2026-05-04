# SN9C292B Permanent OSD-Off Route Status

## Current State

- Runtime OSD disable is proven but volatile.
- Current device flash was dumped twice and verified byte-identical.
- Base dump: `out/current_device_dump_0x20000.bin`
- Base SHA256: `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`
- Historical persistent-config hypothesis at `0x1001E..0x10021` is rejected:
  changing `0x1001E/0x1001F` caused inverted video and did not disable OSD.
- Historical direct `0x0D2C` boot-initializer hypothesis is rejected:
  changing `0x0D74E: 0x13 -> 0x10` caused failed USB enumeration.
- Current active candidate is the runtime-writer patch documented in
  `2026-05-02 Runtime Writer Candidate` below.
- Used firmware area appears to end at `0x12D00`; the rest is `0xFF`.
- Because the tail is blank, the old last-word footer checksum workflow is not applicable to this dump as-is.

## Generated Candidate Images

- `cfg_1001e_1001f_enable_pair.bin`
  - Rejected historical candidate.
  - Two-byte change: `0x1001E..0x1001F: 01 01 -> 00 00`.
  - Hardware result: inverted video, OSD still enabled.

- `cfg_1001e_line_only.bin`
  - Rejected/deprioritized historical control candidate.
  - One-byte change only: `0x1001E: 01 -> 00`.
  - Same address family as the failed video/sensor candidate.

- `cfg_1001e_10021_all4_legacy_plan_d.bin`
  - Rejected historical reference candidate.
  - Four-byte legacy Plan D shape: `0x1001E..0x10021: 01 01 01 01 -> 00 00 00 00`.
  - Prior project notes reported bad video/audio behavior for this shape.

- `current_base_osd_off_runtime_writer_0d2c_set_to_clear.src`
  - Rejected hardware-tested candidate.
  - Four-byte executable-code diff at two runtime writer instructions:
    `0x0C66F/0x0C670` and `0x0C6AB/0x0C6AC`.
  - GUI copy:
    `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_osd_off_runtime_writer_0d2c_set_to_clear.src`
  - Hardware result: device no longer appears as DirectShow/UVC camera and
    Windows PnP has no present `VID_0C45` device.

## Tooling Added

- `tools/build_permanent_osd_candidates.py`
  - Offline candidate generator.
  - Produces candidate firmware, diff files, JSON metadata, similarity report, and MOVX scan.

- `tools/windows_xu_osd_probe.cpp`
  - Existing Windows KS/XU tool now also supports `--alt-sf-read`.
  - This probes the alternate `0x23/0x24` SPI-read protocol mentioned by `sonix_burn.exe.h`.
  - No flash-write code has been added.

## Alt SPI Read Probe

Re-tested with the camera confirmed free and the probe running outside the sandbox:

```powershell
D:\Code\SN9C292B\tools\windows_xu_osd_probe.exe
D:\Code\SN9C292B\tools\windows_xu_osd_probe.exe --sf-read 0x0 0x10 out\retry_sf_probe16.bin
D:\Code\SN9C292B\tools\windows_xu_osd_probe.exe --alt-sf-read 0x0 0x10 out\alt_sf_probe16.bin
```

Result:

- Default XU probe succeeds outside the sandbox.
- Current post-replug OSD state is `Line=1, Block=1`.
- Runtime XU control still works after replug:
  `--set 0 0` changes the live state to `Line=0, Block=0`.
- The established `--sf-read` path succeeds and reads the expected flash header:
  `53 4E 39 43 32 39 32 00 EB 52 23 B2 EF 3E 23 B2`.
- The alternate `0x23/0x24` SPI-read path reaches the camera but fails on both
  DEV_SPECIFIC nodes:
  - node 1: `0x80070490`
  - node 2: `0x80070492`
- Therefore the alternate read protocol from `sonix_burn.exe.h` is not proven
  usable through this Windows KS/XU path on the current device.
- Earlier in-sandbox `0x80070005` failures were execution-environment related,
  not proof that the camera was occupied.
- `sonix_flasher2\snx_flash.exe read` also failed with `Device open failed`.
- No flash write has been attempted.

## Write-Back Position

- The public C1 source only exposes `XU_SF_Read`.
- The local `snx_flash.exe` source only implements `dump|read`.
- `sonix_burn.exe.h` defines possible write selectors `0x25/0x26`, but no working source implementation is present.
- The official GUI burner may be the safer write path if it accepts the generated `.bin`.
- Direct device flash write is still a high-risk step and should not be run without explicit confirmation and a recovery plan.

## Next Gate

1. Treat the existing `--sf-read` protocol as the only proven live path.
2. Do not build a direct `0x25/0x26` write path from `sonix_burn.exe.h` alone;
   the paired `0x23/0x24` read path already failed on this device.
3. Prefer an official burner/bootloader workflow for the first persistent test,
   using `cfg_1001e_1001f_enable_pair.bin` as the best match for the latest
   observed `Line=1, Block=1` state.
4. Any flash write remains a dangerous operation and needs explicit confirmation
   plus a rollback/recovery plan.

## 2026-05-02 Device Write Attempt

The true write route found in the official decompiled burner is not `0x25/0x26`.
It is the same SONiX system XU selector `0x03` used by the proven read path:

- Read command: `0x88` for bank 0, `0x98` for bank 1.
- Write command: `0x08` for bank 0, `0x18` for bank 1.
- Flash write granularity: 8 bytes.
- Payload: `addr_low addr_high command data0..data7`.

`tools/windows_xu_osd_probe.cpp` was extended with:

- `--sf-patch-from-candidate <expected.bin> <candidate.bin>`
- `--i-accept-brick-risk`
- `--unlock-write-protect`

The tool refuses broad writes. For the current preferred candidate it computed
one single write block:

- Block address: `0x10018`
- Current block: `00 00 7F 17 00 08 01 01`
- Target block: `00 00 7F 17 00 08 00 00`
- Actual byte diffs:
  - `0x1001E: 01 -> 00`
  - `0x1001F: 01 -> 00`

Three live write attempts were made against the currently connected camera:

1. Direct selector `0x03` write without write-protect unlock.
   - Result: command completed, but verify read remained
     `00 00 7F 17 00 08 01 01`.
   - Conclusion: the page-program command is not enough by itself.

2. Selector `0x03` write after a first reconstruction of the official default
   write-protect branch.
   - Chip ID at ASIC `0x101F`: `0x92`.
   - Write-protect parameter source: flash `0x8034 = 0x23`.
   - Result: target block still did not stick.
   - Relock probe returned `0x8007001F`, but the camera remained accessible.

3. Selector `0x03` write after adding the official selector `0x05` status
   preamble.
   - Status preamble returned `base=0x7F00`, ID bytes `00 00 00 00`,
     status byte2 `0x17`.
   - Result: target block still did not stick.
   - Final block read confirmed unchanged:
     `00 00 7F 17 00 08 01 01`.

Post-attempt health checks:

- Camera still enumerates as `USB Camera`.
- OSD runtime XU still works.
- Flash read still works on DEV_SPECIFIC node 1.
- Target flash block is unchanged.
- Runtime OSD was set back to `Line=0, Block=0` as a temporary, volatile state.

## 2026-05-02 GUI ROM Extraction

The `flash_public\sonix_burn.exe` GUI was used manually through its ROM extract
function and produced:

- `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile.src`

Verification:

- Size: `131072` bytes (`0x20000`)
- SHA256: `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`
- Header: `53 4E 39 43 32 39 32 00` (`SN9C292\0`)
- It is byte-identical to `out\current_device_dump_0x20000.bin`.

Implication:

- The `flash_public\sonix_burn.exe` GUI can correctly read the current SN9C292
  device ROM.
- This is stronger evidence than the earlier DLL probe path, because it proves
  the GUI application itself can reach the attached camera through its own
  driver/XU stack.
- It does not by itself prove that GUI write-back will accept and program a
  patched image, but it makes the GUI route the best next software path.

GUI source-file handling:

- The burn path loads its source image into `dword_C43238`.
- The source file is selected by the GUI file-open flow for `*.SRC`, `*.BIN`,
  or `*.HEX`, and must be exactly `0x20000` bytes for this device.
- The ROM extract path writes `SonixAllRomFile.src`, but it does not by itself
  prove that this file has been loaded as the burn source.

Prepared GUI burn inputs:

- Original GUI extraction backup:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_original_gui_extract_20260502.src`
  - SHA256: `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`
- Patched OSD-off image for GUI load:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_osd_off_1001e_1001f.src`
  - SHA256: `e981c40b5dc2d712966f75d6c6a6615f9bfb2671df60aea9ba8aa2c13ed49157`
  - Only two bytes differ from the extracted ROM:
    - `0x1001E: 01 -> 00`
    - `0x1001F: 01 -> 00`

Current boundary:

- The candidate image and minimal write block are ready.
- The live selector `0x03` write command can be sent.
- The current implementation has not successfully put the serial flash into a
  programmable state.
- Further progress requires either:
  - finding the exact SN9C292/flash-model branch in the official burner state
    machine, or
  - using the correct SONiX SN9C292 burner/bootloader workflow, or
  - hardware-level SPI programming against the flash chip.

## 2026-05-02 GUI Burn Result: 0x1001E/0x1001F Candidate Rejected

The patched GUI image was burned through `flash_public\sonix_burn.exe`.

Observed result after reconnect:

- OSD was still enabled.
- The image became color-inverted.
- The device still enumerated and remained readable.
- The device path changed from the earlier `VID_0C45&PID_6366` family to
  `VID_0C45&PID_6362&MI_00`.

Read-back verification:

- `out\after_gui_flash_inverted_0x20000.bin`
  - SHA256: `e981c40b5dc2d712966f75d6c6a6615f9bfb2671df60aea9ba8aa2c13ed49157`
- This matches the patched GUI input:
  `SonixAllRomFile_osd_off_1001e_1001f.src`
- It differs from the original dump only at:
  - `0x1001E: 01 -> 00`
  - `0x1001F: 01 -> 00`

Conclusion:

- The GUI burn route is confirmed to write the full ROM image successfully.
- The `0x1001E/0x1001F` candidate is rejected as an OSD-default switch.
- Those bytes appear to affect video/sensor configuration instead; changing
  them causes an inverted image while leaving runtime OSD defaults enabled.
- Do not reuse this candidate for the remaining cameras.

Immediate recovery path:

- Burn back the original GUI extract:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_original_gui_extract_20260502.src`
- Expected recovery:
  - inverted image should return to normal,
  - OSD will likely remain enabled,
  - USB PID may return to the original `0C45:6366` behavior.

Next investigation direction:

- Treat the `0x10000` area as video/sensor configuration, not the OSD switch.
- Resume from the confirmed runtime OSD control path:
  - runtime OFF changes ASIC state around `0x0E32`, `0x0E37`, `0x0E38`,
  - persistent disable must likely be found by tracing how the firmware seeds
    that runtime state during boot.

## 2026-05-02 sonixsdk Review

The additional `jhdkrwmc/sonixsdk` repository was cloned and inspected.

Useful findings:

- `SonixUVCSDK2.12\SnCamDll.h` exports normal camera APIs plus:
  - `CameraReadDSP(BYTE CamNum, LONG laddress, OUT LONG* lData)`
  - `CameraWriteDSP(BYTE CamNum, LONG laddress, IN LONG* lData)`
- `SnCamDll.dll` exports 27 functions and has no OSD, ROM, flash, or persistent
  setting API.
- The DLL contains the SONiX system XU GUID and its `CameraReadDSP` /
  `CameraWriteDSP` implementation maps to the same kind of ASIC register
  access already exposed by `tools\windows_xu_osd_probe.exe`.
- It does not contain the SONiX user OSD XU GUID or the `9A 04` OSD command.
- `SNFilterDriver\Win10RS3\History.txt` says:
  `Fix burn AP burning type from usb changed to xu when reset`.

Conclusion:

- `sonixsdk` is useful corroboration for the system-XU/ASIC path.
- It does not provide a new permanent OSD-off API.
- The permanent route still needs a current-ROM patch.

## 2026-05-02 Runtime OSD State Isolation

`tools\windows_xu_osd_probe.cpp` was extended with:

- `--asic-write <addr> <value>`
- `--asic-read-bin <addr> <len> <out.bin>`

These operate on runtime ASIC/XDATA state only; they do not write ROM.

Two ON/OFF binary dumps of `0x0000..0x17FF` were collected under:

- `out\runtime_xdata\xdata_0000_17ff_on.bin`
- `out\runtime_xdata\xdata_0000_17ff_off.bin`
- `out\runtime_xdata\xdata_0000_17ff_on2.bin`
- `out\runtime_xdata\xdata_0000_17ff_off2.bin`

Repeated stable ON -> OFF transitions included:

- `0x0C3A: 0x13 -> 0x10`
- `0x0D2C: 0x13 -> 0x10`
- `0x1530: 0x25 -> 0x24`
- `0x1580: 0x11 -> 0x10`

Runtime isolation result:

- `0x0C3A: 0x13 -> 0x10` alone does **not** change OSD GET.
- `0x0D2C: 0x13 -> 0x10` alone changes OSD GET from:
  - `Line=1, Block=1`
  - to `Line=0, Block=0`

This makes `0x0D2C` the strongest current runtime-backed OSD state byte.

## 2026-05-02 Current-ROM One-Byte Candidate

Current ROM has one direct initializer for the runtime-proven byte:

```asm
0x0D74A: 90 0D 2C    MOV  DPTR,#0x0D2C
0x0D74D: 74 13       MOV  A,#0x13
0x0D74F: F0          MOVX @DPTR,A
```

Generated candidate:

- `out\permanent_osd_candidates\current_base_osd_off_0d2c_13_to_10.src`
- GUI copy:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_osd_off_0d2c_13_to_10.src`
- Candidate SHA256:
  `7be33af3a5389c057579695073b6300680183dd10dc54e8cd4c53f81d3026f84`

Verified binary diff against the restored original dump:

```text
0000D74E: 13 10
```

Rationale:

- Runtime proof: writing `ASIC/XDATA[0x0D2C] = 0x10` disables both OSD GET
  bits immediately.
- ROM proof: current firmware explicitly initializes `0x0D2C` with `0x13`.
- Patch scope: one byte only, in current-device ROM, not an old project-vibe
  binary.

Risk:

- This is still an executable-code patch and must be burned only through a
  controlled GUI workflow with the original backup ready.
- It is much better supported than the rejected `0x1001E/0x1001F` candidate,
  but it is not yet hardware-verified after replug.

## 2026-05-02 Hardware Result: 0x0D2C Candidate Rejected

The candidate below was burned through the GUI:

- `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_osd_off_0d2c_13_to_10.src`
- SHA256:
  `7be33af3a5389c057579695073b6300680183dd10dc54e8cd4c53f81d3026f84`

Observed result after flashing:

- The device no longer appears as a normal DirectShow/UVC camera.
- A fresh Windows PnP check found no present `VID_0C45`, `PID_6362`, or
  `PID_6366` device.
- This is different from the earlier bad video/sensor candidate, where the
  camera still enumerated as `VID_0C45&PID_6366` with problem code 10.

Conclusion:

- `0x0D2C: 0x13 -> 0x10` is rejected as a permanent ROM patch.
- The runtime effect was misleading: writing `0x0D2C` live can clear the OSD
  state, but baking the same byte into ROM appears to break USB boot or early
  initialization.
- Do not burn this candidate again, and do not use it on the remaining cameras.

Recovery priority:

1. Restore the original ROM if the camera can be made to enumerate.
2. If `VID_0C45&PID_6362` appears, use the GUI burner recovery route to flash:
   `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_original_gui_extract_20260502.src`
3. If no `VID_0C45` device appears at all, use the hardware recovery route:
   make the external SPI flash unreadable at power-up or program the flash
   directly with a 3.3 V SPI programmer.

Known-good original backup:

- GUI original extract:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_original_gui_extract_20260502.src`
- Current dump mirror:
  `out\current_device_dump_0x20000.bin`
- SHA256 for both:
  `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`

Existing local evidence for recovery mode:

- `project-vibe\logs\usbtree_recovery_mode_with_spi_flash_to_ground.txt`
  shows a working recovery-like enumeration as `VID_0C45&PID_6362`,
  product string `USB 2.0 Camera`, manufacturer `Sonix Technology Co., Ltd.`,
  and `Problem Code: 0`.
- `project-vibe\logs\usbtree_fw_osd_off flash .txt` shows a separate failed
  firmware state as `VID_0C45&PID_6366` with `CM_PROB_FAILED_START`.

Linux cross-check:

- The device was connected to `apps.ystone.top` and monitored through
  `dmesg -wT`, `udevadm monitor`, `lsusb`, and `/sys/bus/usb/devices`.
- Watch directory on the remote host:
  `/tmp/sn9c292b_usb_watch_20260502_143643`
- Current `lsusb` showed no `0c45:*` device.
- Kernel log repeatedly showed:
  - `new high-speed USB device ... using ehci-pci`
  - `device descriptor read/8, error -71`
  - `Cannot enable. Maybe the USB cable is bad?`
  - `unable to enumerate USB device`

Interpretation:

- This failure happens before the device can publish a VID/PID or USB
  descriptors.
- Linux confirms the Windows result: this is not a Windows driver issue.
- Software recovery over UVC/XU/GUI burner is not available unless the camera
  can first be made to enumerate as `VID_0C45&PID_6362` or `VID_0C45&PID_6366`.

## 2026-05-02 Recovery Success and No-ROM Hypothesis Rejected

Recovery result:

- The camera was recovered by temporarily shorting SPI flash pin 1 and pin 4
  during power-up.
- This made the SPI flash unreadable long enough for the device to enter the
  Sonix no-SPI/recovery path.
- The original ROM was then flashed back through the GUI burner.
- After recovery, the camera enumerates normally again as `VID_0C45&PID_6366`
  and works with the original firmware.
- OSD is still present, as expected, because the restored image is the original
  stock firmware.

Rejected branch:

- Hypothesis: clear or remove the external flash and rely on the chip's internal
  ROM/no-SPI firmware, expecting OSD to disappear while the camera remains
  usable.
- Hardware result: tested and rejected. No-ROM / empty-flash operation is not a
  usable final mode for this camera.
- Do not spend further attempts on "clear flash to remove OSD".

Current rule:

- Treat no-SPI mode as a recovery/burner entry only.
- A usable permanent OSD-off solution still requires a valid external ROM image
  with a correct firmware patch.

## 2026-05-02 Runtime Writer Candidate

Post-recovery state was revalidated on the restored stock firmware:

- Windows PnP: `VID_0C45&PID_6366\SN0001`, `CM_PROB_NONE`
- DirectShow camera: `USB Camera`
- Runtime OSD GET after stock restore: `Line=1, Block=1`
- Runtime `--set 0 0` still works and changes OSD GET to `Line=0, Block=0`

New post-recovery ON/OFF ASIC/XDATA diff:

```text
0x0D2C: ON=0x13 OFF=0x10
0x0E32: ON=0x02 OFF=0x29
0x0E37: ON=0x00 OFF=0x04
0x0E38: ON=0x02 OFF=0x01
0x0E6A: ON=0x4D OFF=0x35
```

Important correction:

- `0x0E24..0x0E27` did not change in the current recovered-device runtime
  ON/OFF diff.
- Old `0x0B7x`, `0x0E24` direct-clear, late-clear stub, whole-function hook,
  and no-ROM branches should not be reused as first-line candidates.

Current ROM writer scan output:

- `out\permanent_osd_candidates\runtime_osd_writer_scan.md`

Most relevant runtime OSD set-enable handler region:

```asm
0x0C63F: MOV R0,#0x80
...
0x0C648: MOV DPTR,#0x0D2C
0x0C64B: MOVX A,@DPTR
0x0C64C: ANL A,#0xFE
0x0C64E: MOVX @DPTR,A      ; existing bit0 clear path
...
0x0C66B: MOV DPTR,#0x0D2C
0x0C66E: MOVX A,@DPTR
0x0C66F: ORL A,#0x01
0x0C671: MOVX @DPTR,A      ; bit0 set path
...
0x0C684: MOV DPTR,#0x0D2C
0x0C687: MOVX A,@DPTR
0x0C688: ANL A,#0xFD
0x0C68A: MOVX @DPTR,A      ; existing bit1 clear path
...
0x0C6A7: MOV DPTR,#0x0D2C
0x0C6AA: MOVX A,@DPTR
0x0C6AB: ORL A,#0x02
0x0C6AD: MOVX @DPTR,A      ; bit1 set path
0x0C6AE: MOV DPTR,#0x0D2C
0x0C6B1: MOVX A,@DPTR
0x0C6B2: MOV DPTR,#0x0C3A
0x0C6B5: MOVX @DPTR,A      ; mirror 0x0D2C to 0x0C3A
```

Generated candidate:

- `out\permanent_osd_candidates\current_base_osd_off_runtime_writer_0d2c_set_to_clear.src`
- GUI copy:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_osd_off_runtime_writer_0d2c_set_to_clear.src`
- Candidate report:
  `out\permanent_osd_candidates\runtime_writer_candidate_report.md`
- Candidate SHA256:
  `7e7bb49a9da5425327bc0bd23aba7ad2ec07f32ce159c93a192919ebcbbce155`

Binary diff:

```text
0x0C66F: 44 -> 54    ; ORL A,#0x01 -> ANL A,#0xFE
0x0C670: 01 -> FE
0x0C6AB: 44 -> 54    ; ORL A,#0x02 -> ANL A,#0xFD
0x0C6AC: 02 -> FD
```

Rationale:

- It avoids the rejected early initializer at `0x0D74E`.
- It modifies two runtime re-enable paths instead of boot-time required state.
- The replacement instructions mirror existing firmware clear paths:
  - existing `54 FE` clears bit0,
  - existing `54 FD` clears bit1.
- It should make this handler unable to turn `0x0D2C` bit0/bit1 back on.

Limitation:

- This handler appears to consume internal bytes `0x80` and `0x81`, matching
  the runtime OSD `Line` and `Block` set path.
- If boot-time default OSD does not execute this handler, this candidate may
  only prevent runtime re-enable and may not clear the first on-screen OSD after
  power-up.

Risk:

- Lower risk than the rejected `0x0D74E` early initializer patch.
- Still an executable-code ROM patch.
- Known recovery remains available through SPI flash pin 1 to pin 4 no-SPI
  entry and GUI stock-ROM restore.

Hardware result:

- The runtime-writer candidate was burned through the GUI.
- After flashing, the target camera no longer appears in DirectShow/UVC.
- Fresh Windows PnP/CIM checks found no present `VID_0C45`, `PID_6362`, or
  `PID_6366` device.
- This matches the previous no-enumeration failure class.

Conclusion:

- `current_base_osd_off_runtime_writer_0d2c_set_to_clear.src` is rejected.
- Although it avoided the direct `0x0D74E` boot initializer, the
  `0x0C63F..0x0C6B5` runtime writer region is still coupled to USB/video
  critical state and is not safe to patch this way.
- Do not reuse this candidate on the remaining cameras.

Immediate recovery:

- Use the already validated no-SPI recovery method:
  short SPI flash pin 1 to pin 4 only during power-up, enter recovery/burner
  mode, then flash the stock image back through the GUI.
- Stock image:
  `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_original_gui_extract_20260502.src`

## 2026-05-02 Pure-Theory Pause After Repeated No-Enumeration Failures

Current user constraint:

- The user does not currently have convenient shorting/programmer equipment for
  recovery.
- Therefore no further flash candidate should be created or burned until a
  recovery path is available again.

New theory report:

- `out\permanent_osd_candidates\theoretical_next_routes_after_failures.md`

Decision:

- Stop treating direct OSD enable state as the primary firmware patch target.
- Avoid further patches around `0x0D2C`, `0x0C3A`, `0x1530`, `0x1580`, and
  `0x0C63F..0x0C6B5`.
- The next credible firmware direction is to leave OSD state valid while making
  rendered output invisible:
  - blank glyph/font data,
  - blank/default string or character-buffer seed,
  - harmless color/attribute defaults,
  - off-screen/default-position defaults.
- Before firmware work resumes, prefer runtime-only research into Sonix OSD XU
  controls and any hidden "save/commit to flash" path.
