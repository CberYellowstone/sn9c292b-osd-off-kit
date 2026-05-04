# Linux/NAS 热插拔自动关闭 OSD

本目录提供一套已部署过的 systemd + udev 示例：

```text
runtime/nas-systemd/osd-off.sh
runtime/nas-systemd/sn9c292b-osd-off.service
runtime/nas-systemd/90-sn9c292b-osd-off.rules
```

目标：摄像头插入 Linux/NAS 后，自动执行一次运行时 OSD off。

## 安装

```bash
sudo install -d /opt/sn9c292b
sudo install -m 0755 runtime/linux/SONiX_UVC_TestAP /opt/sn9c292b/SONiX_UVC_TestAP
sudo install -m 0755 runtime/nas-systemd/osd-off.sh /opt/sn9c292b/osd-off.sh
sudo install -m 0644 runtime/nas-systemd/sn9c292b-osd-off.service /etc/systemd/system/sn9c292b-osd-off.service
sudo install -m 0644 runtime/nas-systemd/90-sn9c292b-osd-off.rules /etc/udev/rules.d/90-sn9c292b-osd-off.rules
sudo systemctl daemon-reload
sudo udevadm control --reload-rules
```

重新插拔摄像头后查看日志：

```bash
cat /tmp/sn9c292b_osd_off.log
```

## 鲁棒性

`osd-off.sh` 会扫描所有 `/dev/video*`，并通过 udev 属性筛选：

```text
ID_VENDOR_ID=0c45
ID_MODEL_ID=6366
```

因此：

- 插在不同 USB 口通常可以工作
- 多个 `/dev/video*` 节点时会逐个尝试
- 多个同 VID/PID 摄像头同时插入时，脚本会尝试所有匹配节点

如果你的设备 PID 不是 `6366`，需要修改：

```text
runtime/nas-systemd/osd-off.sh
runtime/nas-systemd/90-sn9c292b-osd-off.rules
```

## go2rtc 示例

本仓库同时保留了当时的 go2rtc 示例：

```text
runtime/nas-systemd/go2rtc.example.yaml
runtime/nas-systemd/go2rtc.example.service
runtime/nas-systemd/go2rtc_linux_amd64
```

这部分用于推流，不是关闭 OSD 的必要条件。

