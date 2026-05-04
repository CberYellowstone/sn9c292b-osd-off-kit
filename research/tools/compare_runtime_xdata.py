from pathlib import Path


def diff_pair(base: Path, on_name: str, off_name: str) -> dict[int, tuple[int, int]]:
    on = (base / on_name).read_bytes()
    off = (base / off_name).read_bytes()
    if len(on) != len(off):
        raise ValueError(f"size mismatch: {on_name}={len(on)} {off_name}={len(off)}")
    return {i: (a, b) for i, (a, b) in enumerate(zip(on, off)) if a != b}


def main() -> None:
    base = Path("out/runtime_xdata")
    pairs = [
        ("pair1", "xdata_0000_17ff_on.bin", "xdata_0000_17ff_off.bin"),
        ("pair2", "xdata_0000_17ff_on2.bin", "xdata_0000_17ff_off2.bin"),
    ]

    diffs: list[dict[int, tuple[int, int]]] = []
    for label, on_name, off_name in pairs:
        diff = diff_pair(base, on_name, off_name)
        diffs.append(diff)
        print(f"{label}: {len(diff)} changed bytes")
        for addr, (on, off) in list(diff.items())[:80]:
            print(f"  0x{addr:04X}: {on:02X}->{off:02X}")

    common = sorted(set(diffs[0]) & set(diffs[1]))
    print(f"\ncommon changed addresses: {len(common)}")
    for addr in common:
        a1, b1 = diffs[0][addr]
        a2, b2 = diffs[1][addr]
        stable = "stable" if (a1, b1) == (a2, b2) else "dynamic"
        print(f"  0x{addr:04X}: p1 {a1:02X}->{b1:02X}, p2 {a2:02X}->{b2:02X} [{stable}]")


if __name__ == "__main__":
    main()
