# 运行时关闭 OSD

运行时关闭不会修改 SPI Flash，也不会永久生效。断电、重插或设备重新初始化后，
OSD 通常会恢复。

## Windows

工具：

```text
runtime/windows/windows_xu_osd_probe.exe
runtime/windows/windows_xu_osd_probe.cpp
```

查询当前 OSD 状态：

```powershell
runtime\windows\windows_xu_osd_probe.exe
```

关闭 OSD：

```powershell
runtime\windows\windows_xu_osd_probe.exe --set 0 0
```

恢复 OSD：

```powershell
runtime\windows\windows_xu_osd_probe.exe --set 1 1
```

实现方式：

- 使用 Windows 原生 `usbvideo.sys`
- 通过 DirectShow 找到 `USB Camera`
- 通过 `IKsTopologyInfo` / `IKsControl` 访问 UVC Extension Unit
- 不需要 Zadig、WinUSB、libusb、PyUSB

已验证映射：

```text
XU_SONIX_USR_ID       = 0x04
XU_SONIX_USR_OSD_CTRL = 0x04
OSD subcommand        = 9A 04
payload size          = 11
```

验证记录见：

```text
runtime/windows/evidence/windows_runtime_osd_control_verification.md
```

## Linux

工具：

```text
runtime/linux/SONiX_UVC_TestAP
runtime/linux/source/
```

二进制来源：从已部署 NAS 的 `/opt/sn9c292b/SONiX_UVC_TestAP` 取回。

SHA256：

```text
8cb95d791fd18e12bd55e5a5db8788eafafa1d5f8230d5a80d225bd967c0db06
```

查询/初始化目标设备：

```bash
sudo runtime/linux/SONiX_UVC_TestAP -a /dev/videoX
```

关闭 OSD：

```bash
sudo runtime/linux/SONiX_UVC_TestAP --xuset-oe 0,0 /dev/videoX
```

恢复 OSD：

```bash
sudo runtime/linux/SONiX_UVC_TestAP --xuset-oe 1,1 /dev/videoX
```

`/dev/videoX` 需要替换为实际视频节点。可以用 `v4l2-ctl --list-devices`
或 `udevadm info -q property -n /dev/videoX` 判断。

## 编译 Linux 工具

源码保留在：

```text
burners/c1_sonix_test_ap/C1_SONIX_Test_AP-master/
runtime/linux/source/
```

常见依赖：

```bash
sudo apt install build-essential libv4l-dev
```

编译：

```bash
cd burners/c1_sonix_test_ap/C1_SONIX_Test_AP-master
make
```

