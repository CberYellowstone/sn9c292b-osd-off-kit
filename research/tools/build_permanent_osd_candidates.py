from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


FW_SIZE = 0x20000
DEFAULT_DUMP = Path("out/current_device_dump_0x20000.bin")
DEFAULT_OUT_DIR = Path("out/permanent_osd_candidates")

CONFIG_OFFSETS = [0x1001E, 0x1001F, 0x10020, 0x10021]
SIMILARITY_ROOTS = [
    Path("sn9fresh"),
    Path("sonixcam"),
    Path("project-vibe"),
    Path("sonix_flasher2"),
]


@dataclass(frozen=True)
class PatchOp:
    offset: int
    old: int
    new: int
    note: str


@dataclass(frozen=True)
class Candidate:
    name: str
    rank: str
    rationale: str
    risk: str
    ops: list[PatchOp]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hexbytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def word_sum_le(data: bytes, start: int = 0, end: int | None = None) -> int:
    total = 0
    end = len(data) if end is None else min(end, len(data))
    if end % 2:
        end -= 1
    for i in range(start, end, 2):
        total = (total + data[i] + (data[i + 1] << 8)) & 0xFFFF
    return total


def trailing_ff_start(data: bytes) -> int:
    last_used = -1
    for i in range(len(data) - 1, -1, -1):
        if data[i] != 0xFF:
            last_used = i
            break
    return last_used + 1


def write_diff(old: bytes, new: bytes, path: Path) -> None:
    lines = []
    for i, (a, b) in enumerate(zip(old, new)):
        if a != b:
            lines.append(f"0x{i:05X}: 0x{a:02X} -> 0x{b:02X}")
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def apply_candidate(base: bytes, candidate: Candidate) -> bytes:
    buf = bytearray(base)
    for op in candidate.ops:
        actual = buf[op.offset]
        if actual != op.old:
            raise ValueError(
                f"{candidate.name}: offset 0x{op.offset:05X} expected "
                f"0x{op.old:02X}, found 0x{actual:02X}"
            )
        buf[op.offset] = op.new
    return bytes(buf)


def build_candidates(base: bytes) -> list[Candidate]:
    for off in CONFIG_OFFSETS:
        if off >= len(base):
            raise ValueError(f"config offset outside image: 0x{off:05X}")

    return [
        Candidate(
            name="cfg_1001e_1001f_enable_pair",
            rank="preferred-first-test",
            rationale=(
                "Latest post-replug runtime proof reports both OSD enable line "
                "and block as active, so disable the matching two config bytes "
                "from the C1 tooling model."
            ),
            risk="moderate; still limited to the config/descriptor-like region",
            ops=[
                PatchOp(0x1001E, base[0x1001E], 0x00, "line enable"),
                PatchOp(0x1001F, base[0x1001F], 0x00, "block enable"),
            ],
        ),
        Candidate(
            name="cfg_1001e_line_only",
            rank="minimal-change-control",
            rationale=(
                "Smallest persistent default change. Kept as a narrow control "
                "candidate, but the latest post-replug proof showed block OSD "
                "enabled too."
            ),
            risk="lowest byte-change count, but likely incomplete if block OSD is active",
            ops=[
                PatchOp(
                    0x1001E,
                    base[0x1001E],
                    0x00,
                    "candidate default for OSD line enable",
                )
            ],
        ),
        Candidate(
            name="cfg_1001e_10021_all4_legacy_plan_d",
            rank="reference-only",
            rationale=(
                "Legacy Plan D shape: disable enable and autoscale bytes. Kept "
                "only as a comparison because prior notes reported bad video/audio."
            ),
            risk="high; not recommended as the first device test",
            ops=[
                PatchOp(0x1001E, base[0x1001E], 0x00, "line enable"),
                PatchOp(0x1001F, base[0x1001F], 0x00, "block enable"),
                PatchOp(0x10020, base[0x10020], 0x00, "line autoscale"),
                PatchOp(0x10021, base[0x10021], 0x00, "block autoscale"),
            ],
        ),
    ]


def scan_movx_writes(data: bytes) -> list[dict[str, object]]:
    watched = (
        set(range(0x0B70, 0x0B90))
        | set(range(0x0E20, 0x0E40))
        | set(range(0x1000, 0x1220))
    )
    rows: list[dict[str, object]] = []
    for off in range(0, len(data) - 24):
        if data[off] != 0x90:
            continue
        dptr = (data[off + 1] << 8) | data[off + 2]
        if dptr not in watched:
            continue
        window = data[off : off + 24]
        movx_positions = [idx for idx, b in enumerate(window) if b == 0xF0]
        if not movx_positions:
            continue
        imm_writes = []
        for idx in movx_positions:
            if idx >= 2 and window[idx - 2] == 0x74:
                imm_writes.append(
                    {
                        "movx_offset": off + idx,
                        "immediate_offset": off + idx - 1,
                        "value": window[idx - 1],
                    }
                )
        rows.append(
            {
                "offset": off,
                "dptr": dptr,
                "movx_offsets": [off + idx for idx in movx_positions],
                "immediate_writes": imm_writes,
                "window": hexbytes(window),
            }
        )
    return rows


def longest_equal_run(a: bytes, b: bytes) -> int:
    best = 0
    cur = 0
    for x, y in zip(a, b):
        if x == y:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def similarity_rows(base: bytes, out_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    out_resolved = out_dir.resolve()
    for root in SIMILARITY_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.bin"):
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if out_resolved in resolved.parents:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if len(data) != len(base):
                continue
            equal = sum(1 for x, y in zip(base, data) if x == y)
            code_equal = sum(1 for x, y in zip(base[:0x10000], data[:0x10000]) if x == y)
            desc_equal = sum(
                1
                for x, y in zip(base[0x10000:0x10400], data[0x10000:0x10400])
                if x == y
            )
            rows.append(
                {
                    "path": str(path),
                    "sha256": sha256_hex(data),
                    "equal_bytes": equal,
                    "equal_pct": round(equal / len(base) * 100, 3),
                    "code_equal_pct": round(code_equal / 0x10000 * 100, 3),
                    "descriptor_equal_pct": round(desc_equal / 0x400 * 100, 3),
                    "longest_equal_run": longest_equal_run(base, data),
                    "config_1001e_10021": hexbytes(data[0x1001E:0x10022]),
                }
            )
    rows.sort(
        key=lambda row: (
            row["equal_bytes"],
            row["descriptor_equal_pct"],
            row["longest_equal_run"],
        ),
        reverse=True,
    )
    return rows


def make_report(
    base_path: Path,
    base: bytes,
    out_dir: Path,
    candidates_meta: list[dict[str, object]],
    movx_rows: list[dict[str, object]],
    similar: list[dict[str, object]],
) -> str:
    tff = trailing_ff_start(base)
    lines = [
        "# Permanent OSD-Off Candidate Report",
        "",
        "This report is offline only. No device flash write was performed.",
        "",
        "## Base Image",
        "",
        f"- Path: `{base_path}`",
        f"- Size: {len(base)} bytes / 0x{len(base):X}",
        f"- SHA256: `{sha256_hex(base)}`",
        f"- Header: `{hexbytes(base[:16])}`",
        f"- Config bytes 0x1001E..0x10021: `{hexbytes(base[0x1001E:0x10022])}`",
        f"- Trailing 0xFF starts at: 0x{tff:05X}",
        f"- SUM16 LE full image: 0x{word_sum_le(base):04X}",
        f"- SUM16 LE used area 0..0x{tff:05X}: 0x{word_sum_le(base, 0, tff):04X}",
        "",
        "## Candidates",
        "",
    ]
    for meta in candidates_meta:
        lines.extend(
            [
                f"### {meta['name']}",
                "",
                f"- Rank: {meta['rank']}",
                f"- Risk: {meta['risk']}",
                f"- Rationale: {meta['rationale']}",
                f"- Output: `{meta['bin']}`",
                f"- SHA256: `{meta['sha256']}`",
                "- Ops:",
            ]
        )
        for op in meta["ops"]:
            lines.append(
                f"  - 0x{op['offset']:05X}: 0x{op['old']:02X} -> "
                f"0x{op['new']:02X} ({op['note']})"
            )
        lines.append("")

    lines.extend(
        [
            "## MOVX Write Scan",
            "",
            "Watched XDATA ranges: 0x0B70..0x0B8F, 0x0E20..0x0E3F, 0x1000..0x121F.",
            "",
        ]
    )
    for row in movx_rows[:80]:
        immediates = row["immediate_writes"]
        imm_text = "none"
        if immediates:
            imm_text = ", ".join(
                f"imm@0x{i['immediate_offset']:05X}=0x{i['value']:02X}"
                for i in immediates
            )
        lines.append(
            f"- off=0x{row['offset']:05X} dptr=0x{row['dptr']:04X} "
            f"imm={imm_text} bytes=`{row['window']}`"
        )
    if len(movx_rows) > 80:
        lines.append(f"- ... {len(movx_rows) - 80} more rows omitted in markdown")
    lines.append("")

    lines.extend(["## Closest Same-Size Firmware Samples", ""])
    if not similar:
        lines.append("- No same-size repository firmware samples found.")
    for row in similar[:20]:
        lines.append(
            f"- {row['equal_pct']:>7.3f}% full, "
            f"{row['descriptor_equal_pct']:>7.3f}% descriptor, "
            f"run={row['longest_equal_run']}: `{row['path']}`"
        )
    lines.append("")

    lines.extend(
        [
            "## Decision Notes",
            "",
            "- The current dump has an all-0xFF tail, so the legacy last-word footer fixer is not applicable as-is.",
            "- The safest first firmware experiment is the one-byte config candidate, not a code patch.",
            "- The four-byte legacy Plan D candidate is generated for comparison only because prior reports showed broken video/audio behavior.",
            "- Flash write remains a separate high-risk step and needs explicit confirmation plus a restore plan.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    base_path = args.dump
    out_dir = args.out_dir
    base = base_path.read_bytes()
    if len(base) != FW_SIZE:
        raise ValueError(f"unexpected firmware size {len(base)}; expected {FW_SIZE}")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diffs").mkdir(parents=True, exist_ok=True)

    candidates_meta: list[dict[str, object]] = []
    for candidate in build_candidates(base):
        patched = apply_candidate(base, candidate)
        bin_path = out_dir / f"{candidate.name}.bin"
        diff_path = out_dir / "diffs" / f"{candidate.name}.diff.txt"
        json_path = out_dir / f"{candidate.name}.json"
        bin_path.write_bytes(patched)
        write_diff(base, patched, diff_path)
        meta = {
            "name": candidate.name,
            "rank": candidate.rank,
            "rationale": candidate.rationale,
            "risk": candidate.risk,
            "base": str(base_path),
            "base_sha256": sha256_hex(base),
            "bin": str(bin_path),
            "diff": str(diff_path),
            "sha256": sha256_hex(patched),
            "ops": [
                {
                    "offset": op.offset,
                    "old": op.old,
                    "new": op.new,
                    "note": op.note,
                }
                for op in candidate.ops
            ],
        }
        json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        candidates_meta.append(meta)

    movx_rows = scan_movx_writes(base)
    similar = similarity_rows(base, out_dir)

    analysis_json = {
        "base": str(base_path),
        "base_sha256": sha256_hex(base),
        "size": len(base),
        "config_1001e_10021": list(base[0x1001E:0x10022]),
        "trailing_ff_start": trailing_ff_start(base),
        "word_sum_le_full": word_sum_le(base),
        "word_sum_le_used": word_sum_le(base, 0, trailing_ff_start(base)),
        "candidates": candidates_meta,
        "movx_writes": movx_rows,
        "similar_firmware": similar,
    }
    (out_dir / "analysis.json").write_text(
        json.dumps(analysis_json, indent=2), encoding="utf-8"
    )
    report = make_report(base_path, base, out_dir, candidates_meta, movx_rows, similar)
    (out_dir / "permanent_osd_candidates_report.md").write_text(
        report, encoding="utf-8"
    )

    print(f"base_sha256={sha256_hex(base)}")
    print(f"config_1001e_10021={hexbytes(base[0x1001E:0x10022])}")
    print(f"candidates={len(candidates_meta)}")
    for meta in candidates_meta:
        print(f"  {meta['name']}: {meta['bin']}")
    print(f"movx_writes={len(movx_rows)}")
    print(f"similar_same_size={len(similar)}")
    print(f"report={out_dir / 'permanent_osd_candidates_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
