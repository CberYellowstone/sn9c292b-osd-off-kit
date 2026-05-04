# 畸变修正说明

当前仓库已加入实际在用的摄像头畸变修正工具链：

```text
distortion-correction/
```

内容包括：

- WebGL2 浏览器实时修正页面
- 单独的 GLSL fragment shader
- go2rtc WebRTC 接入代码
- OpenCV 标定脚本
- OpenCV MJPEG 实时修正服务
- 去敏后的当前 `fisheye_kannala_brandt_4` 模型参数

刻意排除：

- 标定照片
- 样张
- 截图
- 录屏和 AVI
- 带现实画面的模型对比图

详细使用方式见：

```text
distortion-correction/README.md
```

