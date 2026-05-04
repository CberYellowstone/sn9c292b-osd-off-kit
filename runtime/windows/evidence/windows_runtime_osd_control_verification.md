# Windows Runtime OSD Control Verification

## 结论

当前这台 `USB\VID_0C45&PID_6366\SN0001` 摄像头支持运行时 OSD 控制。

已在 Windows 原生 `usbvideo.sys` 驱动路径下验证成功，不需要 Zadig、WinUSB、libusb、PyUSB，也不需要刷固件。

## 设备状态

PowerShell PnP 只读枚举结果：

```text
Status Class  FriendlyName         InstanceId
------ -----  ------------         ----------
OK     USB    USB Composite Device USB\VID_0C45&PID_6366\SN0001
OK     MEDIA  USB 2.0 Camera       USB\VID_0C45&PID_6366&MI_03\6&183AF011&0&0003
OK     Camera USB Camera           USB\VID_0C45&PID_6366&MI_00\6&183AF011&0&0000
```

## 实现方式

新增探针：

```text
tools\windows_xu_osd_probe.cpp
tools\windows_xu_osd_probe.exe
```

它通过 DirectShow 枚举 `USB Camera`，再通过 `IKsTopologyInfo` / `IKsControl`
访问 `usbvideo.sys` 暴露的 UVC Extension Unit。

关键映射来自 `SONiX_UVC_TestAP`：

```text
XU_SONIX_USR_ID         = 0x04
XU_SONIX_USR_OSD_CTRL   = 0x04
OSD enable subcommand   = 9A 04
payload size            = 11
```

Windows KS 侧实际命中：

```text
DEV_SPECIFIC node 1 -> 0x80070492
DEV_SPECIFIC node 2 -> 成功
```

## 验证记录

初始只读 GET：

```text
Trying SONiX user OSD GET on DEV_SPECIFIC node 2...
raw get bytes (11): 01 01 00 00 00 00 00 00 00 00 00
Using SONiX user XU node: 2
OSD Enable Line = 1
OSD Enable Block = 1
```

临时关闭 OSD：

```powershell
tools\windows_xu_osd_probe.exe --set 0 0
```

关闭后立即回读：

```text
Setting OSD Enable Line=0, Block=0
raw get bytes (11): 00 00 00 00 00 00 00 00 00 00 00
After SET: OSD Enable Line = 0
After SET: OSD Enable Block = 0
```

独立再次 GET：

```text
raw get bytes (11): 00 00 00 00 00 00 00 00 00 00 00
OSD Enable Line = 0
OSD Enable Block = 0
```

## 视觉留证

关闭后用 ffmpeg 从 `USB Camera` 取了一帧：

```text
out\windows_osd_off_probe.jpg
```

当前图像较暗，但画面内未见日期/时间类 OSD 字符。

## 复现命令

查询当前 OSD 状态：

```powershell
tools\windows_xu_osd_probe.exe
```

临时关闭 OSD：

```powershell
tools\windows_xu_osd_probe.exe --set 0 0
```

临时恢复 OSD：

```powershell
tools\windows_xu_osd_probe.exe --set 1 1
```

## 风险边界

- 这是运行时控制，不写 SPI flash，不改固件，不改 Windows 驱动绑定。
- 断电、重插或重新初始化后，设备很可能恢复默认 OSD ON。
- 如果要永久去除 OSD，再考虑固件补丁；但已有历史补丁记录显示刷机路线风险明显更高。

## 参考

- Microsoft Learn: Device Requirements for USB Video Class Extension Units
  https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/device-requirements-for-usb-video-class-extension-units
- Microsoft Learn: Extension Unit Plug-In Architecture
  https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/extension-unit-plug-in-architecture
- Microsoft Learn: PROPSETID_VIDCAP_EXTENSION_UNIT
  https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/propsetid-vidcap-extension-unit
