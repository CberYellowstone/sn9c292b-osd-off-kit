#!/usr/bin/env python3
"""
Fix footer SUM16 checksum for SONiX SN9C292B 128 KiB firmware images.

Behavior:
- Computes 16-bit little-endian word-sum over all but the last two bytes.
- Writes a 16-bit footer so that total SUM16 over full image equals 0x0000.

Usage:
  python tools/fix_footer_crc.py <firmware.bin> [--write]

If --write is provided, writes <firmware.bin>.fixed.bin with corrected footer.
Always prints before/after details.
"""
import argparse
from pathlib import Path


def sum16_words_le(data: bytes) -> int:
    total = 0
    length = len(data)
    # Exclude last 2 bytes (footer)
    for i in range(0, length - 2, 2):
        lo = data[i]
        hi = data[i + 1] if i + 1 < length - 2 else 0
        total = (total + ((hi << 8) | lo)) & 0xFFFF
    return total


def compute_footer(body_sum: int) -> int:
    return (-body_sum) & 0xFFFF


def write_fixed(path: Path, out_path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 2:
        raise ValueError("Firmware too small to contain footer")
    body_sum = sum16_words_le(raw)
    footer = compute_footer(body_sum)
    fixed = bytearray(raw)
    fixed[-2] = footer & 0xFF
    fixed[-1] = (footer >> 8) & 0xFF
    total = (body_sum + footer) & 0xFFFF
    out_path.write_bytes(fixed)
    return {
        'size': len(raw),
        'body_sum': f"0x{body_sum:04X}",
        'footer_written': f"0x{footer:04X}",
        'total': f"0x{total:04X}",
        'ok': total == 0,
        'output': str(out_path)
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('firmware', type=Path)
    p.add_argument('--write', action='store_true', help='Write <firmware>.fixed.bin')
    args = p.parse_args()

    path: Path = args.firmware
    if not path.exists():
        print(f"❌ Not found: {path}")
        return 1

    raw = path.read_bytes()
    if len(raw) < 2:
        print("❌ Firmware too small")
        return 1

    body_sum = sum16_words_le(raw)
    footer_needed = compute_footer(body_sum)
    current_footer = raw[-2] | (raw[-1] << 8)
    total_now = (body_sum + current_footer) & 0xFFFF
    print(f"Size: {len(raw)} bytes")
    print(f"Body SUM16: 0x{body_sum:04X}")
    print(f"Current footer: 0x{current_footer:04X}")
    print(f"Total now: 0x{total_now:04X} ({'OK' if total_now == 0 else 'BAD'})")
    print(f"Footer required for OK: 0x{footer_needed:04X}")

    if not args.write:
        return 0

    out_path = path.with_suffix(path.suffix + '.fixed.bin')
    info = write_fixed(path, out_path)
    print(f"\nWrote: {info['output']}")
    print(f"Body SUM16: {info['body_sum']}")
    print(f"Footer written: {info['footer_written']}")
    print(f"Total: {info['total']} ({'OK' if info['ok'] else 'BAD'})")
    return 0 if info['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())


