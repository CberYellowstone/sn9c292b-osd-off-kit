from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def word_sum(data: bytes, endian: str) -> int:
    total = 0
    for i in range(0, len(data), 2):
        chunk = data[i : i + 2]
        if len(chunk) < 2:
            chunk = chunk + b"\x00"
        total = (total + int.from_bytes(chunk, endian)) & 0xFFFF
    return total


def find_all(data: bytes, needle: bytes) -> list[int]:
    out: list[int] = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


def hexbytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def scan_movx_writes(data: bytes) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    watched = set(range(0x0B70, 0x0B80)) | set(range(0x0E20, 0x0E30))
    for i in range(0, len(data) - 12):
        if data[i] != 0x90:
            continue
        dptr = (data[i + 1] << 8) | data[i + 2]
        if dptr not in watched:
            continue
        window = data[i : i + 12]
        if 0xF0 not in window:
            continue
        rows.append(
            {
                "offset": i,
                "dptr": dptr,
                "window": hexbytes(window),
            }
        )
    return rows


def scan_known_sequences(data: bytes) -> list[dict[str, object]]:
    patterns = {
        "write_0b75_01": bytes.fromhex("90 0B 75 74 01 F0"),
        "write_0b76_01": bytes.fromhex("90 0B 76 74 01 F0"),
        "write_0b77_01": bytes.fromhex("90 0B 77 74 01 F0"),
        "write_0e24_01": bytes.fromhex("90 0E 24 74 01 F0"),
        "write_0e25_01": bytes.fromhex("90 0E 25 74 01 F0"),
        "write_0e26_01": bytes.fromhex("90 0E 26 74 01 F0"),
        "write_0e27_01": bytes.fromhex("90 0E 27 74 01 F0"),
        "xu_osd_tag_9a04": bytes.fromhex("9A 04"),
    }
    rows: list[dict[str, object]] = []
    for name, pat in patterns.items():
        for off in find_all(data, pat):
            rows.append(
                {
                    "name": name,
                    "offset": off,
                    "bytes": hexbytes(data[off : off + max(len(pat), 16)]),
                }
            )
    return rows


def dump_regions(data: bytes, regions: list[int], size: int = 64) -> list[dict[str, object]]:
    rows = []
    for off in regions:
        rows.append({"offset": off, "bytes": hexbytes(data[off : off + size])})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware")
    ap.add_argument("--json-out", default="out/current_dump_analysis.json")
    args = ap.parse_args()

    path = Path(args.firmware)
    data = path.read_bytes()

    known_regions = [0x04C0, 0x0AC0, 0x0AF0, 0x4520, 0xAD00, 0xBB70, 0x10000]
    report = {
        "path": str(path),
        "size": len(data),
        "sha256": sha256(data),
        "header_ascii": data[:8].decode("latin1", errors="replace"),
        "word_sum_le": word_sum(data, "little"),
        "word_sum_be": word_sum(data, "big"),
        "known_sequences": scan_known_sequences(data),
        "movx_writes": scan_movx_writes(data),
        "regions": dump_regions(data, known_regions),
    }

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"size={report['size']}")
    print(f"sha256={report['sha256']}")
    print(f"header={report['header_ascii']!r}")
    print(f"word_sum_le=0x{report['word_sum_le']:04X}")
    print(f"word_sum_be=0x{report['word_sum_be']:04X}")
    print(f"known_sequences={len(report['known_sequences'])}")
    for row in report["known_sequences"]:
        print(f"  {row['name']} @ 0x{row['offset']:05X}: {row['bytes']}")
    print(f"movx_writes={len(report['movx_writes'])}")
    for row in report["movx_writes"]:
        print(f"  @ 0x{row['offset']:05X} DPTR=0x{row['dptr']:04X}: {row['window']}")
    print(f"json={out_path}")


if __name__ == "__main__":
    main()
