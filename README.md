# SN9C292B OSD Off Kit

这是一个面向 SN9C292B + OV2710 类 UVC 摄像头的 OSD 关闭资料包。

当前已验证的永久方案是：用 SONiX GUI 烧录器写入
`firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src`。
该版本通过清空/修改 Bitmap 字体数据让 OSD 不再显示，用户实测成功。

## 适用设备

已验证设备：

- USB VID/PID: `0C45:6366`
- 芯片/传感器组合：`SN9C292B + OV2710`
- Windows 设备名常见为：`USB Camera` / `USB 2.0 Camera`

相近 SONiX 设备可能可参考，但不要直接烧写本仓库固件，除非你确认 ROM
和硬件配置完全匹配。

## 最短路径

1. 备份当前 ROM。
2. 用 `burners/sonix_burn_flash_public/sonix_burn.exe` 打开 GUI 烧录器。
3. 烧写：

   ```text
   firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src
   ```

4. 重新插拔摄像头。
5. 确认画面正常，OSD 不再显示。

详细步骤见：

- `docs/FLASHING_WINDOWS_GUI.md`
- `docs/FIRMWARE_NOTES.md`
- `docs/RECOVERY.md`
- `docs/DISTORTION_CORRECTION.md`

## 运行时临时关闭

如果不想刷固件，可以使用 UVC Extension Unit 运行时关闭 OSD。
这个方式不写 Flash，风险低，但断电、重插后通常会恢复。

Windows:

```powershell
runtime\windows\windows_xu_osd_probe.exe --set 0 0
```

Linux:

```bash
sudo runtime/linux/SONiX_UVC_TestAP --xuset-oe 0,0 /dev/videoX
```

详细说明见：

- `docs/RUNTIME_OSD_OFF.md`
- `docs/LINUX_NAS_SYSTEMD.md`

## 目录结构

```text
burners/
  sonix_burn_flash_public/       Windows GUI 烧录器和反编译参考
  amcrest_usb_xu_burnerap/       另一套 USB XU Burner AP
  c1_sonix_test_ap/              SONiX UVC TestAP 源码和压缩包
  snx_flash_dumper/              早期 dump/read 工具

firmware/
  original/                      原始 ROM 和重复读取备份
  osd_off_success/               已实测成功关闭 OSD 的固件
  rejected_experimental/         已实测失败或有风险的候选，勿烧
  readback_evidence/             历史读回证据

runtime/
  windows/                       Windows XU 运行时 OSD 控制工具
  linux/                         Linux SONiX_UVC_TestAP 二进制和源码片段
  nas-systemd/                   NAS/Linux 热插拔自动关闭 OSD 示例

distortion-correction/           当前可用的畸变修正成品和工具代码

research/
  evidence/                      本次研究过程和失败路线记录
  tools/                         固件分析/候选生成脚本
  checksum/                      旧 checksum/footer 脚本，仅供研究

third_party/
  sonixsdk/                      SONiX SDK 参考文件
  sonix_windows_driver/          SONiX Windows driver 相关文件

docs/reference/                  SN9C292B 数据手册
```

## 关键文件 SHA256

```text
4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c  firmware/original/SonixAllRomFile_original_gui_extract_20260502.src
be1645fbe8a2d09a64aa84bcaf933405087581cebab6a4388f1399839e161a2e  firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src
aceff196aff746a671fdaaf6beec47675832030ab5cdbe6747cb99edbefe1bb6  runtime/windows/windows_xu_osd_probe.exe
8cb95d791fd18e12bd55e5a5db8788eafafa1d5f8230d5a80d225bd967c0db06  runtime/linux/SONiX_UVC_TestAP
8d273a58e9a69384af01c016afa92ea7551fb7cee0139913c6e159460397bbdc  burners/sonix_burn_flash_public/sonix_burn.exe
ca2872636895f731eab16bb31d7eb9dc06d49e44f47498b97362c46d5c705572  burners/sonix_burn_flash_public/BurnerApLib.dll
```

完整校验表见 `SHA256SUMS.txt`。

Windows 下可执行：

```powershell
scripts\verify_sha256.ps1
```

## 风险声明

刷写错误固件可能导致设备无法枚举。已验证的恢复方式是让外部 SPI Flash
在上电瞬间临时不可读，使设备进入 SONiX no-SPI/recovery 模式，再用 GUI
烧回原始 ROM。

本仓库包含第三方工具、SDK、固件和反编译资料。公开发布前，请自行确认这些
文件的再分发权限。相关说明见 `docs/LEGAL_NOTICE.md`。
