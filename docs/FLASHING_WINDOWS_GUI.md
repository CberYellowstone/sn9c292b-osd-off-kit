# Windows GUI 烧录步骤

推荐使用这套 GUI 烧录器：

```text
burners/sonix_burn_flash_public/sonix_burn.exe
burners/sonix_burn_flash_public/BurnerApLib.dll
```

## 烧写前检查

确认这两个固件都存在：

```text
firmware/original/SonixAllRomFile_original_gui_extract_20260502.src
firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src
```

原始固件 SHA256：

```text
4f1fd4a76d03d0118d414933ab8d31fe6537bc23e82deb75b8abba773169777c
```

成功关闭 OSD 的固件 SHA256：

```text
be1645fbe8a2d09a64aa84bcaf933405087581cebab6a4388f1399839e161a2e
```

## 推荐流程

1. 只连接一颗目标摄像头。
2. 关闭所有正在占用摄像头的软件。
3. 打开：

   ```text
   burners/sonix_burn_flash_public/sonix_burn.exe
   ```

4. 先用 GUI 的提取 ROM 功能读取一次当前 ROM。
5. 保存并比对大小，应为 `131072` 字节。
6. 选择并烧写：

   ```text
   firmware/osd_off_success/SonixAllRomFile_osd_off_edit_BitmapFonts.src
   ```

7. 烧写完成后重新插拔摄像头。
8. 打开摄像头画面，确认图像正常且 OSD 不显示。

## 回滚

如果效果不符合预期，烧回：

```text
firmware/original/SonixAllRomFile_original_gui_extract_20260502.src
```

如果设备已经无法正常枚举，参考 `docs/RECOVERY.md`。

## 不要烧这些文件

以下文件保留为研究记录，已经实测失败或存在明确风险：

```text
firmware/rejected_experimental/SonixAllRomFile_osd_off_1001e_1001f.src
firmware/rejected_experimental/SonixAllRomFile_osd_off_0d2c_13_to_10.src
firmware/rejected_experimental/SonixAllRomFile_osd_off_runtime_writer_0d2c_set_to_clear.src
```

