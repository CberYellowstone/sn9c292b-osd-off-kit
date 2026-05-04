from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROM_PATH = Path("out/current_device_dump_0x20000.bin")
ON_XDATA = Path("out/runtime_xdata/post_recovery_on_0d00_0eff.bin")
OFF_XDATA = Path("out/runtime_xdata/post_recovery_off_0d00_0eff.bin")
OUT_PATH = Path("out/permanent_osd_candidates/runtime_osd_writer_scan.md")

TARGETS = {
    0x0D2C: "runtime OSD gate byte; ROM-init patch here bricked enumeration",
    0x0E32: "runtime OSD state changes after XU set",
    0x0E37: "runtime OSD state changes after XU set",
    0x0E38: "runtime OSD state changes after XU set",
    0x0E6A: "runtime OSD state changes after XU set",
    0x0E24: "legacy OSD candidate, did not change in current runtime diff",
    0x0E27: "legacy OSD candidate, did not change in current runtime diff",
}


@dataclass
class Insn:
    ea: int
    size: int
    text: str
    dptr_imm: int | None = None
    call_target: int | None = None
    writes_dptr: bool = False
    reads_dptr: bool = False
    imm_a: int | None = None
    clears_a: bool = False


def rel_target(ea: int, size: int, off: int) -> int:
    if off >= 0x80:
        off -= 0x100
    return (ea + size + off) & 0xFFFF


def decode_one(buf: bytes, ea: int) -> Insn:
    op = buf[ea]
    b1 = buf[ea + 1] if ea + 1 < len(buf) else 0
    b2 = buf[ea + 2] if ea + 2 < len(buf) else 0

    if op == 0x00:
        return Insn(ea, 1, "NOP")
    if op == 0x02:
        t = (b1 << 8) | b2
        return Insn(ea, 3, f"LJMP 0x{t:04X}")
    if op == 0x12:
        t = (b1 << 8) | b2
        return Insn(ea, 3, f"LCALL 0x{t:04X}", call_target=t)
    if op == 0x22:
        return Insn(ea, 1, "RET")
    if op == 0x32:
        return Insn(ea, 1, "RETI")
    if op == 0x40:
        return Insn(ea, 2, f"JC 0x{rel_target(ea, 2, b1):04X}")
    if op == 0x44:
        return Insn(ea, 2, f"ORL A,#0x{b1:02X}")
    if op == 0x50:
        return Insn(ea, 2, f"JNC 0x{rel_target(ea, 2, b1):04X}")
    if op == 0x54:
        return Insn(ea, 2, f"ANL A,#0x{b1:02X}")
    if op == 0x60:
        return Insn(ea, 2, f"JZ 0x{rel_target(ea, 2, b1):04X}")
    if op == 0x64:
        return Insn(ea, 2, f"XRL A,#0x{b1:02X}")
    if op == 0x70:
        return Insn(ea, 2, f"JNZ 0x{rel_target(ea, 2, b1):04X}")
    if op == 0x74:
        return Insn(ea, 2, f"MOV A,#0x{b1:02X}", imm_a=b1)
    if op == 0x75:
        return Insn(ea, 3, f"MOV 0x{b1:02X},#0x{b2:02X}")
    if 0x78 <= op <= 0x7F:
        return Insn(ea, 2, f"MOV R{op - 0x78},#0x{b1:02X}")
    if op == 0x80:
        return Insn(ea, 2, f"SJMP 0x{rel_target(ea, 2, b1):04X}")
    if op == 0x90:
        t = (b1 << 8) | b2
        return Insn(ea, 3, f"MOV DPTR,#0x{t:04X}", dptr_imm=t)
    if op == 0x94:
        return Insn(ea, 2, f"SUBB A,#0x{b1:02X}")
    if op == 0xA3:
        return Insn(ea, 1, "INC DPTR")
    if op == 0xB4:
        return Insn(ea, 3, f"CJNE A,#0x{b1:02X},0x{rel_target(ea, 3, b2):04X}")
    if 0xB8 <= op <= 0xBF:
        return Insn(ea, 3, f"CJNE R{op - 0xB8},#0x{b1:02X},0x{rel_target(ea, 3, b2):04X}")
    if op == 0xC0:
        return Insn(ea, 2, f"PUSH 0x{b1:02X}")
    if op == 0xC3:
        return Insn(ea, 1, "CLR C")
    if op == 0xD0:
        return Insn(ea, 2, f"POP 0x{b1:02X}")
    if op == 0xD3:
        return Insn(ea, 1, "SETB C")
    if 0xD8 <= op <= 0xDF:
        return Insn(ea, 2, f"DJNZ R{op - 0xD8},0x{rel_target(ea, 2, b1):04X}")
    if op == 0xE0:
        return Insn(ea, 1, "MOVX A,@DPTR", reads_dptr=True)
    if op == 0xE4:
        return Insn(ea, 1, "CLR A", clears_a=True, imm_a=0)
    if op == 0xE6:
        return Insn(ea, 1, "MOV A,@R0")
    if 0xE8 <= op <= 0xEF:
        return Insn(ea, 1, f"MOV A,R{op - 0xE8}")
    if op == 0xF0:
        return Insn(ea, 1, "MOVX @DPTR,A", writes_dptr=True)
    if op == 0xF6:
        return Insn(ea, 1, "MOV @R0,A")
    if 0xF8 <= op <= 0xFF:
        return Insn(ea, 1, f"MOV R{op - 0xF8},A")
    return Insn(ea, 1, f"DB 0x{op:02X}")


def disasm_window(buf: bytes, start: int, end: int) -> list[Insn]:
    out: list[Insn] = []
    ea = max(0, start)
    end = min(len(buf), end)
    while ea < end:
        insn = decode_one(buf, ea)
        out.append(insn)
        ea += max(1, insn.size)
    return out


def hexdump(buf: bytes, start: int, length: int) -> str:
    part = buf[max(0, start) : min(len(buf), start + length)]
    return " ".join(f"{b:02X}" for b in part)


def xdata_diff_lines() -> list[str]:
    if not ON_XDATA.exists() or not OFF_XDATA.exists():
        return ["- ON/OFF post-recovery XDATA dumps not found."]
    on = ON_XDATA.read_bytes()
    off = OFF_XDATA.read_bytes()
    lines = ["| XDATA | ON | OFF | Note |", "|---:|---:|---:|---|"]
    for addr, note in TARGETS.items():
        if 0x0D00 <= addr < 0x0F00:
            idx = addr - 0x0D00
            lines.append(f"| `0x{addr:04X}` | `0x{on[idx]:02X}` | `0x{off[idx]:02X}` | {note} |")
    return lines


def find_dptr_hits(buf: bytes, addr: int) -> list[int]:
    pat = bytes([0x90, addr >> 8, addr & 0xFF])
    hits: list[int] = []
    pos = 0
    while True:
        pos = buf.find(pat, pos)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
    return hits


def summarize_hit(buf: bytes, hit: int, target: int) -> list[str]:
    start = max(0, hit - 24)
    end = min(len(buf), hit + 56)
    insns = disasm_window(buf, start, end)
    lines: list[str] = []
    last_a: str | None = None
    dptr = None
    interesting: list[str] = []
    for insn in insns:
        marker = "=> " if insn.ea == hit else "   "
        if insn.dptr_imm is not None:
            dptr = insn.dptr_imm
        if insn.imm_a is not None:
            last_a = f"0x{insn.imm_a:02X}"
        elif insn.text.startswith("MOV A,R") or insn.reads_dptr:
            last_a = "dynamic"
        if insn.writes_dptr:
            desc = f"writes DPTR 0x{dptr:04X} with A={last_a or 'unknown'}" if dptr is not None else "writes unknown DPTR"
            interesting.append(f"`0x{insn.ea:05X}` {desc}")
        lines.append(f"{marker}0x{insn.ea:05X}: {insn.text}")

    risk = "low"
    if target == 0x0D2C:
        risk = "high: direct ROM initializer already caused no-enumeration when patched"
    elif target in (0x0E24, 0x0E27):
        risk = "medium: legacy path, not supported by current runtime diff"
    else:
        risk = "medium: runtime-correlated, but patch point must be proven late/post-USB"

    return [
        f"### Hit `0x{hit:05X}` for DPTR `0x{target:04X}`",
        "",
        f"- Raw bytes: `{hexdump(buf, hit - 8, 40)}`",
        f"- Interesting writes: {', '.join(interesting) if interesting else 'none in window'}",
        f"- Current risk: {risk}",
        "",
        "```asm",
        *lines,
        "```",
        "",
    ]


def main() -> None:
    buf = ROM_PATH.read_bytes()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Runtime OSD Writer Scan",
        "",
        "This report is generated from the current recovered stock ROM.",
        "",
        f"- ROM: `{ROM_PATH}`",
        f"- ROM size: `{len(buf)}` bytes",
        f"- ON XDATA: `{ON_XDATA}`",
        f"- OFF XDATA: `{OFF_XDATA}`",
        "",
        "## Post-Recovery Runtime Diff",
        "",
        *xdata_diff_lines(),
        "",
        "## DPTR Hit Summary",
        "",
        "| XDATA | Hits | Addresses |",
        "|---:|---:|---|",
    ]
    all_hits: dict[int, list[int]] = {}
    for addr in TARGETS:
        hits = find_dptr_hits(buf, addr)
        all_hits[addr] = hits
        hit_text = ", ".join(f"`0x{h:05X}`" for h in hits) or "-"
        lines.append(f"| `0x{addr:04X}` | {len(hits)} | {hit_text} |")

    lines.extend(["", "## Detailed Windows", ""])
    for addr, hits in all_hits.items():
        lines.extend([f"## Target `0x{addr:04X}`", "", TARGETS[addr], ""])
        for hit in hits:
            lines.extend(summarize_hit(buf, hit, addr))

    lines.extend(
        [
            "## Working Interpretation",
            "",
            "- Do not patch the direct `0x0D2C` initializer again; hardware result rejected it.",
            "- Current runtime diff does not support `0x0E24..0x0E27` as the live enable bytes on this recovered device.",
            "- Safer candidates should target a late/post-USB OSD handler path or a branch that answers OSD GET/SET as disabled without perturbing early USB boot.",
            "",
        ]
    )
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
