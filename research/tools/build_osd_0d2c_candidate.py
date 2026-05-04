import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "out" / "current_device_dump_0x20000.bin"
OUT_DIR = ROOT / "out" / "permanent_osd_candidates"
FLASH_PUBLIC = (
    ROOT
    / "sonix_flasher2"
    / "sonix flasher collection"
    / "flash_public"
)

PATCH_OFFSET = 0x0D74E
EXPECTED = 0x13
PATCHED = 0x10


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    data = bytearray(BASE.read_bytes())
    if len(data) != 0x20000:
        raise SystemExit(f"unexpected base size: 0x{len(data):X}")
    if data[PATCH_OFFSET] != EXPECTED:
        raise SystemExit(
            f"unexpected byte at 0x{PATCH_OFFSET:05X}: "
            f"0x{data[PATCH_OFFSET]:02X}, expected 0x{EXPECTED:02X}"
        )

    base_sha = sha256(data)
    data[PATCH_OFFSET] = PATCHED
    candidate_sha = sha256(data)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate = OUT_DIR / "current_base_osd_off_0d2c_13_to_10.src"
    candidate.write_bytes(data)

    flash_public_candidate = FLASH_PUBLIC / "SonixAllRomFile_osd_off_0d2c_13_to_10.src"
    shutil.copyfile(candidate, flash_public_candidate)

    meta = {
        "base": str(BASE.relative_to(ROOT)),
        "base_sha256": base_sha,
        "candidate": str(candidate.relative_to(ROOT)),
        "flash_public_candidate": str(flash_public_candidate.relative_to(ROOT)),
        "candidate_sha256": candidate_sha,
        "patches": [
            {
                "offset": f"0x{PATCH_OFFSET:05X}",
                "from": f"0x{EXPECTED:02X}",
                "to": f"0x{PATCHED:02X}",
                "reason": "Runtime-proven OSD state byte 0x0D2C OFF value; ROM init writes 0x13.",
                "context": "90 0D 2C 74 13 F0 -> 90 0D 2C 74 10 F0",
            }
        ],
    }
    meta_path = OUT_DIR / "current_base_osd_off_0d2c_13_to_10.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
