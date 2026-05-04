import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

from camera_calibration_collect import FfmpegDshowCapture


class CorrectedFrameSource:
    def __init__(
        self,
        calibration_path: Path,
        device_name: str,
        width: int,
        height: int,
        fps: int,
        input_codec: str,
        balance: float,
        jpeg_quality: int,
        output_width: int | None,
        output_height: int | None,
        max_output_fps: float,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.jpeg_quality = jpeg_quality
        self.output_size = None
        if output_width and output_height:
            self.output_size = (int(output_width), int(output_height))
        self.max_output_fps = float(max_output_fps)
        self.latest_jpeg: bytes | None = None
        self.latest_error: str | None = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        data = json.loads(calibration_path.read_text(encoding="utf-8"))
        model = next(item for item in data["models"] if item.get("name") == "fisheye_kannala_brandt_4")
        camera_matrix = np.asarray(model["camera_matrix"], dtype=np.float64)
        dist_coeffs = np.asarray(model["dist_coeffs"], dtype=np.float64).reshape(-1, 1)

        image_size = (width, height)
        new_camera_matrix = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
            camera_matrix,
            dist_coeffs,
            image_size,
            np.eye(3),
            balance=balance,
        )
        self.map1, self.map2 = cv2.fisheye.initUndistortRectifyMap(
            camera_matrix,
            dist_coeffs,
            np.eye(3),
            new_camera_matrix,
            image_size,
            cv2.CV_16SC2,
        )
        self.new_camera_matrix = new_camera_matrix
        self.capture = FfmpegDshowCapture("ffmpeg", device_name, width, height, fps, input_codec)
        self.thread = threading.Thread(target=self._run, name="corrected-frame-source", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        frame_delay = 1.0 / max(1.0, self.max_output_fps or self.fps)
        while not self.stop_event.is_set():
            ok, frame = self.capture.read()
            if not ok or frame is None:
                with self.lock:
                    self.latest_error = "camera frame read failed"
                time.sleep(0.1)
                continue

            corrected = cv2.remap(frame, self.map1, self.map2, interpolation=cv2.INTER_LINEAR)
            if self.output_size is not None:
                corrected = cv2.resize(corrected, self.output_size, interpolation=cv2.INTER_AREA)
            ok, encoded = cv2.imencode(
                ".jpg",
                corrected,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(self.jpeg_quality)],
            )
            if ok:
                with self.lock:
                    self.latest_jpeg = encoded.tobytes()
                    self.latest_error = None
            time.sleep(frame_delay)

    def snapshot(self) -> tuple[bytes | None, str | None]:
        with self.lock:
            return self.latest_jpeg, self.latest_error

    def close(self) -> None:
        self.stop_event.set()
        self.capture.release()


def make_handler(source: CorrectedFrameSource):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SN9C292B-Fisheye-MJPEG/1.0"

        def log_message(self, fmt, *args):
            sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), fmt % args))

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._index()
            elif self.path == "/snapshot.jpg":
                self._snapshot()
            elif self.path == "/stream.mjpg":
                self._stream()
            else:
                self.send_error(404, "not found")

        def _index(self):
            body = b"""<!doctype html>
<html><head><meta charset="utf-8"><title>SN9C292B Fisheye Live</title>
<style>html,body{margin:0;background:#111;color:#ddd;font-family:system-ui,sans-serif}img{width:100vw;height:auto;display:block}</style>
</head><body><img src="/stream.mjpg" alt="stream"></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _snapshot(self):
            jpeg, err = source.snapshot()
            if jpeg is None:
                self.send_error(503, err or "no frame yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(jpeg)))
            self.end_headers()
            self.wfile.write(jpeg)

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            last_frame = None
            while True:
                jpeg, err = source.snapshot()
                if jpeg is None:
                    if err:
                        time.sleep(0.1)
                    continue
                if jpeg == last_frame:
                    time.sleep(0.01)
                    continue
                last_frame = jpeg
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    break

    return Handler


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description="Serve live fisheye-corrected USB Camera frames over MJPEG.")
    parser.add_argument(
        "--calibration",
        default="distortion-correction/calibration/fine_calibration_models_sanitized.json",
    )
    parser.add_argument("--device", default="USB Camera")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--input-codec", default="mjpeg")
    parser.add_argument("--balance", type=float, default=1.0)
    parser.add_argument("--jpeg-quality", type=int, default=82)
    parser.add_argument("--output-width", type=int, default=0)
    parser.add_argument("--output-height", type=int, default=0)
    parser.add_argument("--max-output-fps", type=float, default=15.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8092)
    args = parser.parse_args()

    source = CorrectedFrameSource(
        Path(args.calibration),
        args.device,
        args.width,
        args.height,
        args.fps,
        args.input_codec,
        args.balance,
        args.jpeg_quality,
        args.output_width or None,
        args.output_height or None,
        args.max_output_fps,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(source))
    print(f"Serving fisheye balance={args.balance} on http://{args.host}:{args.port}/")
    print("Endpoints: /stream.mjpg /snapshot.jpg")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
