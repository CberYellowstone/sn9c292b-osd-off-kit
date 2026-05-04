# 摄像头畸变修正工具链

这一目录只包含当前可用的成品代码、工具代码和去敏后的模型参数。
没有包含样张、截图、录屏、标定照片或带现实场景的资源文件。

## 目录

```text
webgl/              浏览器 WebGL2 实时畸变修正成品
calibration/        去敏后的当前相机模型参数
calibration-tools/  OpenCV 标定和摄像头采集工具
live-tools/         OpenCV MJPEG 实时修正服务
```

## 当前实际使用模型

- 模型：`fisheye_kannala_brandt_4`
- 分辨率：`1920x1080`
- 预设 1：`balance=1.0`, `zoom=1.02`
- 预设 2：`balance=1.0`, `zoom=1.62`

模型参数文件：

```text
calibration/fine_calibration_models_sanitized.json
```

该 JSON 已删除原始图片路径、角点记录、样张和视频信息，只保留模型参数、
误差摘要和当前使用的预设。

## WebGL 实时预览

从仓库根目录启动静态服务器：

```powershell
python -m http.server 8093 --bind 127.0.0.1 --directory distortion-correction/webgl
```

打开：

```text
http://127.0.0.1:8093/
```

可用输入：

- 本机浏览器 `getUserMedia()` 摄像头
- go2rtc WebRTC 远端流

默认远端地址是 `http://127.0.0.1:1984`。如果 go2rtc 在 NAS 上，手动改成
你的 NAS 地址即可。

## OpenCV MJPEG 实时服务

依赖：

```bash
pip install opencv-python numpy
```

运行：

```powershell
python distortion-correction/live-tools/fisheye_live_mjpeg_server.py ^
  --calibration distortion-correction/calibration/fine_calibration_models_sanitized.json ^
  --balance 1.0 ^
  --zoom 1.02
```

浏览器访问：

```text
http://127.0.0.1:8094/
```

## 重新标定

工具：

```text
calibration-tools/camera_calibration_collect.py
calibration-tools/camera_calibration_from_video.py
calibration-tools/camera_calibration_from_images.py
```

这些脚本会生成图片、报告和模型文件。公开分享时只保留必要模型参数，不要把
采集到的照片、截图、视频或标定样张提交进仓库。

