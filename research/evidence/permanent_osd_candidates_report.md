# Permanent OSD-Off Candidate Report

This report is offline only. No device flash write was performed.

## Base Image

- Path: `out\current_device_dump_0x20000.bin`
- Size: 131072 bytes / 0x20000
- SHA256: `4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c`
- Header: `53 4E 39 43 32 39 32 00 EB 52 23 B2 EF 3E 23 B2`
- Config bytes 0x1001E..0x10021: `01 01 01 01`
- Trailing 0xFF starts at: 0x12D00
- SUM16 LE full image: 0xD3F3
- SUM16 LE used area 0..0x12D00: 0x3D73

## Candidates

### cfg_1001e_1001f_enable_pair

- Rank: preferred-first-test
- Risk: moderate; still limited to the config/descriptor-like region
- Rationale: Latest post-replug runtime proof reports both OSD enable line and block as active, so disable the matching two config bytes from the C1 tooling model.
- Output: `out\permanent_osd_candidates\cfg_1001e_1001f_enable_pair.bin`
- SHA256: `e981c40b5dc2d712966f75d6c6a6615f9bfb2671df60aea9ba8aa2c13ed49157`
- Ops:
  - 0x1001E: 0x01 -> 0x00 (line enable)
  - 0x1001F: 0x01 -> 0x00 (block enable)

### cfg_1001e_line_only

- Rank: minimal-change-control
- Risk: lowest byte-change count, but likely incomplete if block OSD is active
- Rationale: Smallest persistent default change. Kept as a narrow control candidate, but the latest post-replug proof showed block OSD enabled too.
- Output: `out\permanent_osd_candidates\cfg_1001e_line_only.bin`
- SHA256: `d99cd6c77981173f0e0267097fa87f668796f0ab4c421ebda95e19d4e35c9ef2`
- Ops:
  - 0x1001E: 0x01 -> 0x00 (candidate default for OSD line enable)

### cfg_1001e_10021_all4_legacy_plan_d

- Rank: reference-only
- Risk: high; not recommended as the first device test
- Rationale: Legacy Plan D shape: disable enable and autoscale bytes. Kept only as a comparison because prior notes reported bad video/audio.
- Output: `out\permanent_osd_candidates\cfg_1001e_10021_all4_legacy_plan_d.bin`
- SHA256: `1eaae873f45b89e68fe48d32a372830ee24a564449e457a06dffaee3adf3044f`
- Ops:
  - 0x1001E: 0x01 -> 0x00 (line enable)
  - 0x1001F: 0x01 -> 0x00 (block enable)
  - 0x10020: 0x01 -> 0x00 (line autoscale)
  - 0x10021: 0x01 -> 0x00 (block autoscale)

## MOVX Write Scan

Watched XDATA ranges: 0x0B70..0x0B8F, 0x0E20..0x0E3F, 0x1000..0x121F.

- off=0x00265 dptr=0x1155 imm=none bytes=`90 11 55 E0 54 CF 12 AC 5F F0 12 BB D0 90 0B DA E0 64 84 60 03 12 AC F0`
- off=0x0027D dptr=0x100E imm=none bytes=`90 10 0E E0 54 F7 F0 90 08 66 E0 FF A3 E0 90 0A 9A CF F0 A3 EF F0 90 08`
- off=0x00323 dptr=0x100E imm=none bytes=`90 10 0E E0 44 08 F0 90 0C 10 12 14 D9 00 00 00 00 12 AD 5F E4 90 0F 54`
- off=0x00367 dptr=0x1101 imm=none bytes=`90 11 01 E0 54 EF 12 AC D3 F0 90 0B DA E0 B4 84 09 12 AD 7E 12 AC 5F F0`
- off=0x003B9 dptr=0x1003 imm=none bytes=`90 10 03 E0 20 E0 03 44 01 F0 12 AC 8F 90 0C 10 12 AC 45 02 A4 7B 12 AD`
- off=0x003ED dptr=0x1003 imm=none bytes=`90 10 03 E0 20 E0 03 44 01 F0 12 AC 8F 24 D0 FF EE 34 07 FE E4 3D FD E4`
- off=0x00445 dptr=0x100E imm=none bytes=`90 10 0E E0 44 08 F0 12 AD 5F 90 0C 10 12 14 D9 00 00 00 00 80 1D 12 AD`
- off=0x0049F dptr=0x100E imm=imm@0x004AF=0x01 bytes=`90 10 0E E0 44 08 F0 7F 01 12 C9 6F 90 0B DB 74 01 F0 22 90 0F 53 EF F0`
- off=0x00541 dptr=0x113E imm=imm@0x00545=0xFF, imm@0x00556=0x84 bytes=`90 11 3E 74 FF F0 02 A5 A2 90 0F 53 E0 64 07 70 33 90 0B DA 74 84 F0 E4`
- off=0x00661 dptr=0x1101 imm=none bytes=`90 11 01 E0 44 80 F0 12 AC F0 E4 FF 12 CA 37 90 14 08 E0 54 FE 12 AC D3`
- off=0x00697 dptr=0x1101 imm=imm@0x006A2=0x15 bytes=`90 11 01 E0 44 80 F0 90 0B DA 74 15 F0 90 10 03 E0 20 E0 03 44 01 F0 12`
- off=0x006A4 dptr=0x1003 imm=none bytes=`90 10 03 E0 20 E0 03 44 01 F0 12 AC 23 02 A7 77 12 AD 58 60 1C 12 AD 92`
- off=0x006C8 dptr=0x1003 imm=none bytes=`90 10 03 E0 20 E0 03 44 01 F0 12 AC 23 02 A7 77 12 AD 58 60 35 90 0C 0A`
- off=0x006E9 dptr=0x1003 imm=none bytes=`90 10 03 E0 20 E0 03 44 01 F0 12 AC 23 80 1A 90 11 01 E0 54 7F 12 AC D3`
- off=0x006F8 dptr=0x1101 imm=none bytes=`90 11 01 E0 54 7F 12 AC D3 12 AC 58 F0 90 0C 0C 12 14 D9 00 00 00 00 12`
- off=0x0079D dptr=0x111C imm=none bytes=`90 11 1C E0 75 F0 10 A4 D3 94 80 E5 F0 94 02 40 03 02 A8 C3 90 11 55 E0`
- off=0x007BD dptr=0x1101 imm=imm@0x007CB=0xC3 bytes=`90 11 01 E0 20 E0 03 02 A8 C3 12 B3 84 74 C3 F0 A3 74 F7 12 B4 06 74 0B`
- off=0x007DB dptr=0x0B75 imm=none bytes=`90 0B 75 A3 E0 90 11 B4 F0 90 0B 77 12 B4 0D 90 0B 79 12 B3 DD 90 0B 7B`
- off=0x007E0 dptr=0x11B4 imm=none bytes=`90 11 B4 F0 90 0B 77 12 B4 0D 90 0B 79 12 B3 DD 90 0B 7B A3 E0 90 11 BB`
- off=0x007F5 dptr=0x11BB imm=none bytes=`90 11 BB 12 B3 E2 90 0B 7D 12 B3 CE 90 0B 7D A3 E0 90 11 BE F0 90 0B 7F`
- off=0x007FB dptr=0x0B7D imm=none bytes=`90 0B 7D 12 B3 CE 90 0B 7D A3 E0 90 11 BE F0 90 0B 7F 12 B3 A9 90 0B 7F`
- off=0x00801 dptr=0x0B7D imm=none bytes=`90 0B 7D A3 E0 90 11 BE F0 90 0B 7F 12 B3 A9 90 0B 7F A3 E0 90 11 BF F0`
- off=0x00806 dptr=0x11BE imm=none bytes=`90 11 BE F0 90 0B 7F 12 B3 A9 90 0B 7F A3 E0 90 11 BF F0 90 0B 81 12 B3`
- off=0x0080A dptr=0x0B7F imm=none bytes=`90 0B 7F 12 B3 A9 90 0B 7F A3 E0 90 11 BF F0 90 0B 81 12 B3 BC 90 0B 81`
- off=0x00810 dptr=0x0B7F imm=none bytes=`90 0B 7F A3 E0 90 11 BF F0 90 0B 81 12 B3 BC 90 0B 81 A3 E0 90 11 C0 F0`
- off=0x00815 dptr=0x11BF imm=none bytes=`90 11 BF F0 90 0B 81 12 B3 BC 90 0B 81 A3 E0 90 11 C0 F0 90 0B 83 A3 E0`
- off=0x00819 dptr=0x0B81 imm=none bytes=`90 0B 81 12 B3 BC 90 0B 81 A3 E0 90 11 C0 F0 90 0B 83 A3 E0 90 11 CB F0`
- off=0x0081F dptr=0x0B81 imm=none bytes=`90 0B 81 A3 E0 90 11 C0 F0 90 0B 83 A3 E0 90 11 CB F0 90 0B 85 A3 E0 90`
- off=0x00824 dptr=0x11C0 imm=none bytes=`90 11 C0 F0 90 0B 83 A3 E0 90 11 CB F0 90 0B 85 A3 E0 90 11 CC F0 90 0B`
- off=0x00828 dptr=0x0B83 imm=none bytes=`90 0B 83 A3 E0 90 11 CB F0 90 0B 85 A3 E0 90 11 CC F0 90 0B 87 A3 E0 90`
- off=0x0082D dptr=0x11CB imm=none bytes=`90 11 CB F0 90 0B 85 A3 E0 90 11 CC F0 90 0B 87 A3 E0 90 11 CD F0 90 0B`
- off=0x00831 dptr=0x0B85 imm=none bytes=`90 0B 85 A3 E0 90 11 CC F0 90 0B 87 A3 E0 90 11 CD F0 90 0B 89 A3 E0 90`
- off=0x00836 dptr=0x11CC imm=none bytes=`90 11 CC F0 90 0B 87 A3 E0 90 11 CD F0 90 0B 89 A3 E0 90 11 D5 F0 90 0B`
- off=0x0083A dptr=0x0B87 imm=none bytes=`90 0B 87 A3 E0 90 11 CD F0 90 0B 89 A3 E0 90 11 D5 F0 90 0B 8B 12 B4 1B`
- off=0x0083F dptr=0x11CD imm=none bytes=`90 11 CD F0 90 0B 89 A3 E0 90 11 D5 F0 90 0B 8B 12 B4 1B 90 0B 8D A3 E0`
- off=0x00843 dptr=0x0B89 imm=none bytes=`90 0B 89 A3 E0 90 11 D5 F0 90 0B 8B 12 B4 1B 90 0B 8D A3 E0 90 11 D6 F0`
- off=0x00848 dptr=0x11D5 imm=none bytes=`90 11 D5 F0 90 0B 8B 12 B4 1B 90 0B 8D A3 E0 90 11 D6 F0 90 0B 8F 12 B3`
- off=0x0084C dptr=0x0B8B imm=none bytes=`90 0B 8B 12 B4 1B 90 0B 8D A3 E0 90 11 D6 F0 90 0B 8F 12 B3 EB 90 0B 91`
- off=0x00852 dptr=0x0B8D imm=none bytes=`90 0B 8D A3 E0 90 11 D6 F0 90 0B 8F 12 B3 EB 90 0B 91 A3 E0 90 11 D3 F0`
- off=0x00857 dptr=0x11D6 imm=none bytes=`90 11 D6 F0 90 0B 8F 12 B3 EB 90 0B 91 A3 E0 90 11 D3 F0 90 0B 93 A3 E0`
- off=0x0085B dptr=0x0B8F imm=none bytes=`90 0B 8F 12 B3 EB 90 0B 91 A3 E0 90 11 D3 F0 90 0B 93 A3 E0 90 11 D4 F0`
- off=0x00866 dptr=0x11D3 imm=none bytes=`90 11 D3 F0 90 0B 93 A3 E0 90 11 D4 F0 90 0B 95 A3 E0 90 11 06 F0 90 0B`
- off=0x0086F dptr=0x11D4 imm=none bytes=`90 11 D4 F0 90 0B 95 A3 E0 90 11 06 F0 90 0B 97 A3 E0 90 11 07 F0 90 0B`
- off=0x00878 dptr=0x1106 imm=none bytes=`90 11 06 F0 90 0B 97 A3 E0 90 11 07 F0 90 0B 99 A3 E0 90 11 08 F0 90 0B`
- off=0x00881 dptr=0x1107 imm=none bytes=`90 11 07 F0 90 0B 99 A3 E0 90 11 08 F0 90 0B 9B A3 E0 90 11 09 F0 90 0B`
- off=0x0088A dptr=0x1108 imm=none bytes=`90 11 08 F0 90 0B 9B A3 E0 90 11 09 F0 90 0B 9D A3 E0 90 11 0A 12 B3 F0`
- off=0x00893 dptr=0x1109 imm=none bytes=`90 11 09 F0 90 0B 9D A3 E0 90 11 0A 12 B3 F0 90 0B 9F A3 E0 90 11 AC F0`
- off=0x0089C dptr=0x110A imm=none bytes=`90 11 0A 12 B3 F0 90 0B 9F A3 E0 90 11 AC F0 90 0B A1 A3 E0 90 11 AD F0`
- off=0x008A7 dptr=0x11AC imm=none bytes=`90 11 AC F0 90 0B A1 A3 E0 90 11 AD F0 90 0B A3 A3 E0 90 11 AE F0 90 0B`
- off=0x008B0 dptr=0x11AD imm=none bytes=`90 11 AD F0 90 0B A3 A3 E0 90 11 AE F0 90 0B A5 02 A9 C6 12 B3 84 74 C5`
- off=0x008B9 dptr=0x11AE imm=imm@0x008C7=0xC5 bytes=`90 11 AE F0 90 0B A5 02 A9 C6 12 B3 84 74 C5 F0 A3 74 05 12 B4 06 74 0B`
- off=0x008DC dptr=0x11B4 imm=none bytes=`90 11 B4 F0 90 0B A9 12 B4 0D 90 0B AB 12 B3 DD 90 0B AD A3 E0 54 7F FF`
- off=0x008F4 dptr=0x11BB imm=none bytes=`90 11 BB E0 54 80 4F F0 90 0B AF 12 B3 CE 90 0B AF A3 E0 90 11 BE F0 90`
- off=0x00907 dptr=0x11BE imm=none bytes=`90 11 BE F0 90 0B B1 12 B3 A9 90 0B B1 A3 E0 90 11 BF F0 90 0B B3 12 B3`
- off=0x00916 dptr=0x11BF imm=none bytes=`90 11 BF F0 90 0B B3 12 B3 BC 90 0B B3 A3 E0 90 11 C0 F0 90 0B B5 A3 E0`
- off=0x00925 dptr=0x11C0 imm=none bytes=`90 11 C0 F0 90 0B B5 A3 E0 90 11 CB F0 90 0B B7 A3 E0 90 11 CC F0 90 0B`
- off=0x0092E dptr=0x11CB imm=none bytes=`90 11 CB F0 90 0B B7 A3 E0 90 11 CC F0 90 0B B9 A3 E0 90 11 CD F0 90 0B`
- off=0x00937 dptr=0x11CC imm=none bytes=`90 11 CC F0 90 0B B9 A3 E0 90 11 CD F0 90 0B BB A3 E0 90 11 D5 F0 90 0B`
- off=0x00940 dptr=0x11CD imm=none bytes=`90 11 CD F0 90 0B BB A3 E0 90 11 D5 F0 90 0B BD 12 B4 1B 90 0B BF A3 E0`
- off=0x00949 dptr=0x11D5 imm=none bytes=`90 11 D5 F0 90 0B BD 12 B4 1B 90 0B BF A3 E0 90 11 D6 F0 90 0B C1 12 B3`
- off=0x00958 dptr=0x11D6 imm=none bytes=`90 11 D6 F0 90 0B C1 12 B3 EB 90 0B C3 A3 E0 90 11 D3 F0 90 0B C5 A3 E0`
- off=0x00967 dptr=0x11D3 imm=none bytes=`90 11 D3 F0 90 0B C5 A3 E0 90 11 D4 F0 90 0B C7 A3 E0 90 11 0F F0 90 0B`
- off=0x00970 dptr=0x11D4 imm=none bytes=`90 11 D4 F0 90 0B C7 A3 E0 90 11 0F F0 90 0B C9 A3 E0 90 11 10 F0 90 0B`
- off=0x00979 dptr=0x110F imm=none bytes=`90 11 0F F0 90 0B C9 A3 E0 90 11 10 F0 90 0B CB A3 E0 90 11 11 F0 90 0B`
- off=0x00982 dptr=0x1110 imm=none bytes=`90 11 10 F0 90 0B CB A3 E0 90 11 11 F0 90 0B CD A3 E0 90 11 12 F0 90 0B`
- off=0x0098B dptr=0x1111 imm=none bytes=`90 11 11 F0 90 0B CD A3 E0 90 11 12 F0 90 0B CF A3 E0 54 07 FF 90 11 13`
- off=0x00994 dptr=0x1112 imm=none bytes=`90 11 12 F0 90 0B CF A3 E0 54 07 FF 90 11 13 E0 54 F8 4F F0 90 0B D1 A3`
- off=0x009A0 dptr=0x1113 imm=none bytes=`90 11 13 E0 54 F8 4F F0 90 0B D1 A3 E0 90 11 AC F0 90 0B D3 A3 E0 90 11`
- off=0x009AD dptr=0x11AC imm=none bytes=`90 11 AC F0 90 0B D3 A3 E0 90 11 AD F0 90 0B D5 A3 E0 90 11 AE F0 90 0B`
- off=0x009B6 dptr=0x11AD imm=none bytes=`90 11 AD F0 90 0B D5 A3 E0 90 11 AE F0 90 0B D7 A3 E0 90 11 AF F0 90 11`
- off=0x009BF dptr=0x11AE imm=none bytes=`90 11 AE F0 90 0B D7 A3 E0 90 11 AF F0 90 11 3E E0 44 08 F0 90 12 0E E0`
- off=0x009C8 dptr=0x11AF imm=none bytes=`90 11 AF F0 90 11 3E E0 44 08 F0 90 12 0E E0 44 01 F0 E0 44 10 F0 E0 44`
- off=0x009CC dptr=0x113E imm=none bytes=`90 11 3E E0 44 08 F0 90 12 0E E0 44 01 F0 E0 44 10 F0 E0 44 04 F0 22 A3`
- off=0x009D3 dptr=0x120E imm=none bytes=`90 12 0E E0 44 01 F0 E0 44 10 F0 E0 44 04 F0 22 A3 F0 7B 1B 7D 05 12 AD`
- off=0x00A07 dptr=0x1124 imm=none bytes=`90 11 24 F0 90 08 68 E0 FA A3 E0 FB CE EA CE 78 03 CE C3 13 CE 13 D8 F9`
- off=0x00A1F dptr=0x1125 imm=none bytes=`90 11 25 F0 ED CE EC CE 78 03 CE C3 13 CE 13 D8 F9 54 01 C4 33 33 54 C0`
- off=0x00A38 dptr=0x1151 imm=none bytes=`90 11 51 E0 54 BF 4F F0 EB CE EA CE 78 02 CE C3 13 CE 13 D8 F9 54 01 C4`
- off=0x00A56 dptr=0x1151 imm=none bytes=`90 11 51 E0 54 7F 4F F0 12 BC 49 CD EF CD 90 08 66 12 AD B0 2D 90 11 52`
- off=0x00A6B dptr=0x1152 imm=none bytes=`90 11 52 F0 12 BC 57 CD EF CD 90 08 68 E0 FE A3 E0 78 03 CE C3 13 CE 13`
- off=0x00A86 dptr=0x1153 imm=none bytes=`90 11 53 F0 90 08 6A E0 FE A3 E0 90 11 21 F0 90 11 23 12 AD A6 90 08 6C`
- ... 428 more rows omitted in markdown

## Closest Same-Size Firmware Samples

-  57.484% full,  96.973% descriptor, run=52480: `project-vibe\RecycleBin\firmware_builds_bad\firmware_patched_disable_all_osd.bin`
-  57.484% full,  96.973% descriptor, run=52480: `sonix_flasher2\gpt5\firmwares nukes\firmware_patched_disable_all_osd.bin`
-  57.482% full,  96.973% descriptor, run=52480: `project-vibe\RecycleBin\firmware_builds_bad\firmware_patched_disable_line_osd.bin`
-  57.482% full,  96.973% descriptor, run=52480: `sonix_flasher2\gpt5\firmwares nukes\firmware_patched_disable_line_osd.bin`
-  57.481% full,  96.973% descriptor, run=52480: `project-vibe\firmware\old\target_with_noname_block.bin`
-  57.480% full,  96.973% descriptor, run=52480: `project-vibe\RecycleBin\firmware_builds_bad\firmware_patched_zone_2.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sn9fresh\artifacts\sonix_original.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sn9fresh\IDA Live fw files\firmware_backup.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sn9fresh\known good OSD ON\firmware_backup.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sn9fresh\known good OSD ON\firmware_backup_raw.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\firmware_backup - Copy (4).bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\25-08-10\firmware_backup.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\backup\firmware_backup - Copy (4).bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\25-08-10\bad\fw_osd_v0_min.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\25-08-10\bad\fw_osd_v1_nop.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\25-08-10\bad\fw_osd_v2_two.bin`
-  57.479% full,  96.973% descriptor, run=52480: `sonixcam\25-08-10\bad\fw_osd_v3_all4_noftr.bin`
-  57.479% full,  96.973% descriptor, run=52480: `project-vibe\codex_resarch\EDESIX_SN9_OSD_OV2710.bin`
-  57.479% full,  96.973% descriptor, run=52480: `project-vibe\firmware\EDESIX_SN9_OSD_OV2710_TARGET.bin`
-  57.479% full,  96.973% descriptor, run=52480: `project-vibe\codex_resarch\bins\EDESIX_SN9_OSD_OV2710.bin`

## Decision Notes

- The current dump has an all-0xFF tail, so the legacy last-word footer fixer is not applicable as-is.
- The safest first firmware experiment is the one-byte config candidate, not a code patch.
- The four-byte legacy Plan D candidate is generated for comparison only because prior reports showed broken video/audio behavior.
- Flash write remains a separate high-risk step and needs explicit confirmation plus a restore plan.
