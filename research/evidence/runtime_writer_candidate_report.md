# Runtime Writer OSD-Off Candidate

This candidate does not modify the rejected boot initializer at `0x0D74E`.
It changes two runtime `0x0D2C` ON paths into their matching OFF/clear logic.

- Base: `out\current_device_dump_0x20000.bin`
- Base SHA256: `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`

## Patches

| Offset | Before | After | Purpose |
|---:|---|---|---|
| `0x0C66F` | `44 01` | `54 FE` | 0x0D2C bit0 set path -> clear path |
| `0x0C6AB` | `44 02` | `54 FD` | 0x0D2C bit1 set path -> clear path |

## Binary Diff

```text
0C66F: 44 -> 54
0C670: 01 -> FE
0C6AB: 44 -> 54
0C6AC: 02 -> FD
```

## Output

- Candidate: `out\permanent_osd_candidates\current_base_osd_off_runtime_writer_0d2c_set_to_clear.src`
- GUI copy: `sonix_flasher2\sonix flasher collection\flash_public\SonixAllRomFile_osd_off_runtime_writer_0d2c_set_to_clear.src`
- Candidate SHA256: `7e7bb49a9da5425327bc0bd23aba7ad2ec07f32ce159c93a192919ebcbbce155`

## Risk Notes

- This is still an executable-code ROM patch and must be treated as risky.
- It avoids the failed early initializer patch at `0x0D74E`.
- It targets runtime re-enable paths at `0x0C66F` and `0x0C6AB`.
- Recovery path is known: force no-SPI by shorting SPI flash pin 1 to pin 4 during power-up, then flash stock ROM through the GUI.
