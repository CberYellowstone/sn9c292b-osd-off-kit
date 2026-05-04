# 固件说明

## 已验证成功版本

```text
firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src
```

该版本基于原始 GUI 提取 ROM 修改。用户实测烧写后摄像头可正常启动，画面正常，
OSD 不再显示。

当前文件信息：

- 大小：`131072` 字节
- SHA256：`be1645fbe8a2d09a64aa84bcaf933405087581cebab6a4388f1399839e161a2e`
- 修改方式：修改 Bitmap 字体数据，使 OSD 渲染出来的字符不可见
- 未使用旧 footer/checksum 重算脚本

## 原始固件

```text
firmware/original/SonixAllRomFile_original_gui_extract_20260502.src
```

该文件来自 `sonix_burn.exe` GUI 的提取 ROM 功能，并与运行时读出的
`current_device_dump_0x20000.bin` 一致。

原始固件 SHA256：

```text
4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c
```

## 为什么这次不重算 checksum

本次成功路线没有重算 checksum/footer。

前期实测表明，GUI 烧写器可以写入未重算 checksum 的 ROM；其中
`SonixAllRomFile_osd_off_1001e_1001f.src` 虽然导致画面反色且 OSD 未关闭，
但设备仍能枚举并显示画面。这说明当前设备的烧写/启动路径没有强制依赖
旧脚本假设的 checksum 规则。

仓库中保留的 checksum 脚本互相假设并不完全一致：

- `research/checksum/fix_footer_sn9fresh.py`：按整文件最后 2 字节 footer
- `research/checksum/fix_footer_crc_project_vibe.py`：也按最后 2 字节 footer
- `research/checksum/patch_osd_off_ida_legacy.py`：按 `0x1FFE..0x1FFF`

当前原始 128KB ROM 本身也不满足这些脚本的统一校验假设。因此这些脚本只作为
研究资料保留，不建议普通用户对成功固件再做 footer 修改。

## 已拒绝候选

```text
firmware/rejected_experimental/SonixAllRomFile_osd_off_1001e_1001f.src
```

结果：能启动，但画面反色，OSD 仍存在。

```text
firmware/rejected_experimental/SonixAllRomFile_osd_off_0d2c_13_to_10.src
```

结果：设备无法正常枚举。

```text
firmware/rejected_experimental/SonixAllRomFile_osd_off_runtime_writer_0d2c_set_to_clear.src
```

结果：设备无法正常枚举。

详细研究记录见：

```text
research/evidence/permanent_osd_route_status.md
```

