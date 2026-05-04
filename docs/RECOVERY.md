# 救砖和回滚

## 首选回滚

如果摄像头仍能被 GUI 烧录器识别，直接烧回：

```text
firmware/original/SonixAllRomFile_original_gui_extract_20260502.src
```

## no-SPI/recovery 模式

如果错误固件导致设备无法正常枚举，已验证的恢复方式是：

1. 上电瞬间让外部 SPI Flash 临时不可读。
2. 实测可通过短接 SPI Flash Pin 1 和 Pin 4 达成。
3. 设备会进入 SONiX no-SPI/recovery 类模式。
4. 此时使用 GUI 烧录器烧回原始 ROM。

历史实测现象：

- recovery/无 SPI 诱导后可能出现 `VID_0C45&PID_6362`
- 正常工作固件为 `VID_0C45&PID_6366`

## 不建议的路线

已经实测过“清空/不接 ROM 后让设备自然工作”的假设，结论是不可用。
no-SPI 模式只适合作为恢复/烧录入口，不适合作为最终工作模式。

## 风险

短接 Flash 属于硬件风险操作，可能造成设备或主机 USB 口损坏。只有在已经接受
报废风险，并且知道对应 Flash 引脚定义时再做。

