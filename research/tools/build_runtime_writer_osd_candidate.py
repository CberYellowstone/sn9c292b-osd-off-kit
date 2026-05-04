from __future__ import annotations

from pathlib import Path
import hashlib


BASE = Path("out/current_device_dump_0x20000.bin")
OUT = Path("out/permanent_osd_candidates/current_base_osd_off_runtime_writer_0d2c_set_to_clear.src")
GUI_OUT = Path(
    "sonix_flasher2/sonix flasher collection/flash_public/"
    "SonixAllRomFile_osd_off_runtime_writer_0d2c_set_to_clear.src"
)
REPORT = Path("out/permanent_osd_candidates/runtime_writer_candidate_report.md")


PATCHES = [
    # Runtime bit0 ON path:
    #   0C66B: 90 0D 2C E0 44 01 F0
    #                  ^^^^^
    # Change ORL A,#0x01 into ANL A,#0xFE.
    (0x0C66F, bytes.fromhex("44 01"), bytes.fromhex("54 FE"), "0x0D2C bit0 set path -> clear path"),
    # Runtime bit1 ON path:
    #   0C6A7: 90 0D 2C E0 44 02 F0
    #                  ^^^^^
    # Change ORL A,#0x02 into ANL A,#0xFD.
    (0x0C6AB, bytes.fromhex("44 02"), bytes.fromhex("54 FD"), "0x0D2C bit1 set path -> clear path"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    data = bytearray(BASE.read_bytes())
    original = bytes(data)

    report_lines = [
        "# Runtime Writer OSD-Off Candidate",
        "",
        "This candidate does not modify the rejected boot initializer at `0x0D74E`.",
        "It changes two runtime `0x0D2C` ON paths into their matching OFF/clear logic.",
        "",
        f"- Base: `{BASE}`",
        f"- Base SHA256: `{sha256(original)}`",
        "",
        "## Patches",
        "",
        "| Offset | Before | After | Purpose |",
        "|---:|---|---|---|",
    ]

    for off, before, after, purpose in PATCHES:
        found = bytes(data[off : off + len(before)])
        if found != before:
            raise SystemExit(
                f"unexpected bytes at 0x{off:05X}: "
                f"expected {before.hex(' ').upper()}, got {found.hex(' ').upper()}"
            )
        data[off : off + len(after)] = after
        report_lines.append(
            f"| `0x{off:05X}` | `{before.hex(' ').upper()}` | "
            f"`{after.hex(' ').upper()}` | {purpose} |"
        )

    patched = bytes(data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    GUI_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(patched)
    GUI_OUT.write_bytes(patched)

    diffs = [(i, original[i], patched[i]) for i in range(len(original)) if original[i] != patched[i]]
    report_lines.extend(
        [
            "",
            "## Binary Diff",
            "",
            "```text",
            *[f"{off:05X}: {old:02X} -> {new:02X}" for off, old, new in diffs],
            "```",
            "",
            "## Output",
            "",
            f"- Candidate: `{OUT}`",
            f"- GUI copy: `{GUI_OUT}`",
            f"- Candidate SHA256: `{sha256(patched)}`",
            "",
            "## Risk Notes",
            "",
            "- This is still an executable-code ROM patch and must be treated as risky.",
            "- It avoids the failed early initializer patch at `0x0D74E`.",
            "- It targets runtime re-enable paths at `0x0C66F` and `0x0C6AB`.",
            "- Recovery path is known: force no-SPI by shorting SPI flash pin 1 to pin 4 during power-up, then flash stock ROM through the GUI.",
            "",
        ]
    )
    REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"wrote {GUI_OUT}")
    print(f"wrote {REPORT}")
    print(f"sha256 {sha256(patched)}")


if __name__ == "__main__":
    main()
