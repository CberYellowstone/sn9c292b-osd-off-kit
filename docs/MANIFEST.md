# 文件清单

## 烧录器

- `burners/sonix_burn_flash_public/sonix_burn.exe`
- `burners/sonix_burn_flash_public/BurnerApLib.dll`
- `burners/sonix_burn_flash_public/sonix_burn.exe.c`
- `burners/sonix_burn_flash_public/sonix_burn.exe.h`
- `burners/sonix_burn_flash_public/sonix_burn.exe.asm`
- `burners/amcrest_usb_xu_burnerap/USB_XU_BurnerAp_v1.1.3.0/`
- `burners/amcrest_usb_xu_burnerap/Amcrest.zip`
- `burners/c1_sonix_test_ap/C1_SONIX_Test_AP-master/`
- `burners/c1_sonix_test_ap/C1_SONIX_Test_AP-master.zip`
- `burners/snx_flash_dumper/snx_flash.exe`
- `burners/snx_flash_dumper/libusb-1.0.dll`

## 固件

- `firmware/original/SonixAllRomFile_original_gui_extract_20260502.src`
- `firmware/original/SonixAllRomFile_gui_extract_duplicate.src`
- `firmware/original/current_device_dump_0x20000.bin`
- `firmware/original/current_device_dump_0x20000_verify.bin`
- `firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src`
- `firmware/rejected_experimental/*.src`
- `firmware/readback_evidence/*.bin`

## 运行时关闭 OSD

- `runtime/windows/windows_xu_osd_probe.exe`
- `runtime/windows/windows_xu_osd_probe.cpp`
- `runtime/windows/evidence/windows_runtime_osd_control_verification.md`
- `runtime/linux/SONiX_UVC_TestAP`
- `runtime/linux/source/*.c`
- `runtime/linux/source/*.h`
- `runtime/nas-systemd/osd-off.sh`
- `runtime/nas-systemd/sn9c292b-osd-off.service`
- `runtime/nas-systemd/90-sn9c292b-osd-off.rules`

## 研究资料

- `research/evidence/*.md`
- `research/tools/*.py`
- `research/checksum/*.py`

## SONiX SDK 参考

- `third_party/sonixsdk/SnCamDll.h`
- `third_party/sonixsdk/SnCamDll.dll`
- `third_party/sonixsdk/Sonix UVC SDK 2.12.exe`
- `third_party/sonixsdk/Sonix Camera SDK.exe`

## 校验

完整 SHA256 文件在：

```text
SHA256SUMS.txt
```

Windows 校验脚本：

```powershell
scripts\verify_sha256.ps1
```
