import argparse
import json
import math
import subprocess
import threading
import time
from pathlib import Path

import cv2
import numpy as np


class FfmpegDshowCapture:
    def __init__(
        self,
        ffmpeg_path: str,
        dshow_name: str,
        width: int,
        height: int,
        fps: int,
        input_codec: str,
    ):
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.frame_size = self.width * self.height * 3
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._latest: np.ndarray | None = None
        self._stderr_tail: list[str] = []

        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtbufsize",
            "256M",
            "-f",
            "dshow",
            "-video_size",
            f"{self.width}x{self.height}",
            "-framerate",
            str(self.fps),
        ]
        if input_codec:
            cmd += ["-vcodec", input_codec]
        cmd += [
            "-i",
            f"video={dshow_name}",
            "-an",
            "-sn",
            "-dn",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "pipe:1",
        ]

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            bufsize=0,
            creationflags=creationflags,
        )
        self._reader_thread = threading.Thread(target=self._reader, name="ffmpeg-frame-reader", daemon=True)
        self._stderr_thread = threading.Thread(target=self._stderr_reader, name="ffmpeg-stderr-reader", daemon=True)
        self._reader_thread.start()
        self._stderr_thread.start()

        if not self._ready.wait(timeout=8):
            detail = "\n".join(self._stderr_tail[-12:])
            self.release()
            raise RuntimeError(f"ffmpeg did not return a frame from {dshow_name!r}\n{detail}")

    def _read_exact(self, size: int) -> bytes:
        assert self.proc.stdout is not None
        chunks = []
        remaining = size
        while remaining and not self._stopped.is_set():
            chunk = self.proc.stdout.read(remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _reader(self) -> None:
        while not self._stopped.is_set():
            raw = self._read_exact(self.frame_size)
            if len(raw) != self.frame_size:
                break
            frame = np.frombuffer(raw, dtype=np.uint8).reshape((self.height, self.width, 3)).copy()
            with self._lock:
                self._latest = frame
            self._ready.set()
        self._stopped.set()

    def _stderr_reader(self) -> None:
        assert self.proc.stderr is not None
        for line in iter(self.proc.stderr.readline, b""):
            text = line.decode("utf-8", errors="replace").rstrip()
            if not text:
                continue
            self._stderr_tail.append(text)
            del self._stderr_tail[:-40]
            if self._stopped.is_set():
                break

    def read(self):
        if not self._ready.wait(timeout=2):
            return False, None
        with self._lock:
            if self._latest is None:
                return False, None
            return True, self._latest.copy()

    def get(self, prop_id: int) -> float:
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.width)
        if prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.height)
        if prop_id == cv2.CAP_PROP_FPS:
            return float(self.fps)
        return 0.0

    def release(self) -> None:
        self._stopped.set()
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)


def get_screen_size() -> tuple[int, int]:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return int(width), int(height)
    except Exception:
        return 1920, 1080


def make_board(screen_w: int, screen_h: int, cols: int, rows: int, margin_ratio: float) -> tuple[np.ndarray, int]:
    squares_x = cols + 1
    squares_y = rows + 1
    usable_w = int(screen_w * (1.0 - margin_ratio))
    usable_h = int(screen_h * (1.0 - margin_ratio))
    square = max(16, min(usable_w // squares_x, usable_h // squares_y))
    board_w = square * squares_x
    board_h = square * squares_y

    img = np.full((screen_h, screen_w, 3), 255, np.uint8)
    x0 = (screen_w - board_w) // 2
    y0 = (screen_h - board_h) // 2

    for y in range(squares_y):
        for x in range(squares_x):
            if (x + y) % 2 == 0:
                color = (0, 0, 0)
            else:
                color = (255, 255, 255)
            cv2.rectangle(
                img,
                (x0 + x * square, y0 + y * square),
                (x0 + (x + 1) * square, y0 + (y + 1) * square),
                color,
                thickness=-1,
            )
    return img, square


def open_camera(
    index: int,
    dshow_name: str | None,
    ffmpeg_dshow_name: str | None,
    ffmpeg_path: str,
    ffmpeg_input_codec: str,
    width: int,
    height: int,
    fps: int,
):
    if ffmpeg_dshow_name:
        return FfmpegDshowCapture(ffmpeg_path, ffmpeg_dshow_name, width, height, fps, ffmpeg_input_codec)

    if dshow_name:
        source = f"video={dshow_name}"
    else:
        source = index

    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    if not cap.isOpened():
        raise RuntimeError(f"camera {source!r} could not be opened")
    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        raise RuntimeError(f"camera {source!r} opened but did not return frames")
    return cap


def detect_corners(frame: np.ndarray, cols: int, rows: int):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    pattern_size = (cols, rows)
    flags = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCornersSB(gray, pattern_size, flags=flags)
    if found:
        return True, corners

    legacy_flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(gray, pattern_size, legacy_flags)
    if found:
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            50,
            0.001,
        )
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    return found, corners


def calibrate(valid_records: list[dict], cols: int, rows: int, square_size: float, image_size: tuple[int, int], out_dir: Path):
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= square_size

    objpoints = []
    imgpoints = []
    for item in valid_records:
        objpoints.append(objp.copy())
        corners = np.asarray(item["corners"], dtype=np.float32).reshape(-1, 1, 2)
        imgpoints.append(corners)

    flags = 0
    rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints,
        imgpoints,
        image_size,
        None,
        None,
        flags=flags,
    )

    per_view_errors = []
    for i, (obj, img) in enumerate(zip(objpoints, imgpoints)):
        projected, _ = cv2.projectPoints(obj, rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
        err = cv2.norm(img, projected, cv2.NORM_L2) / len(projected)
        per_view_errors.append(float(err))

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image_size": {"width": image_size[0], "height": image_size[1]},
        "pattern": {"inner_corners_cols": cols, "inner_corners_rows": rows, "square_size_units": square_size},
        "valid_frames": len(valid_records),
        "rms_reprojection_error": float(rms),
        "mean_per_view_error": float(np.mean(per_view_errors)) if per_view_errors else None,
        "max_per_view_error": float(np.max(per_view_errors)) if per_view_errors else None,
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.ravel().tolist(),
        "per_view_errors": per_view_errors,
        "frames": [{"file": item["file"], "annotated": item["annotated"]} for item in valid_records],
        "notes": [
            "OpenCV distortion model is not identical to FFmpeg lenscorrection.",
            "Use OpenCV undistort/remap for physically calibrated correction.",
            "FFmpeg lenscorrection can be tuned from k1/k2 as a visual approximation.",
        ],
    }

    (out_dir / "calibration_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    sample_path = out_dir / valid_records[-1]["file"]
    sample = cv2.imread(str(sample_path))
    if sample is not None:
        undistorted = cv2.undistort(sample, camera_matrix, dist_coeffs)
        cv2.imwrite(str(out_dir / "undistorted_sample.jpg"), undistorted)

    report_lines = [
        "# SN9C292B Camera Calibration Result",
        "",
        f"- valid frames: {len(valid_records)}",
        f"- image size: {image_size[0]}x{image_size[1]}",
        f"- RMS reprojection error: {rms:.6f}",
        f"- mean per-view error: {result['mean_per_view_error']:.6f}",
        f"- max per-view error: {result['max_per_view_error']:.6f}",
        "",
        "## Camera Matrix",
        "",
        "```json",
        json.dumps(camera_matrix.tolist(), indent=2),
        "```",
        "",
        "## Distortion Coefficients",
        "",
        "OpenCV order is usually `[k1, k2, p1, p2, k3]`:",
        "",
        "```json",
        json.dumps(dist_coeffs.ravel().tolist(), indent=2),
        "```",
        "",
        "## Notes",
        "",
        "- This is an OpenCV calibration result.",
        "- FFmpeg `lenscorrection` uses a simpler model and should be tuned visually from this result.",
    ]
    (out_dir / "calibration_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description="Display a chessboard and capture calibration frames.")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--dshow-name", default=None)
    parser.add_argument("--ffmpeg-dshow-name", default=None)
    parser.add_argument("--ffmpeg-path", default="ffmpeg")
    parser.add_argument("--ffmpeg-input-codec", default="mjpeg")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--cols", type=int, default=9, help="inner corners columns")
    parser.add_argument("--rows", type=int, default=6, help="inner corners rows")
    parser.add_argument("--square-size", type=float, default=1.0)
    parser.add_argument("--min-valid", type=int, default=12)
    parser.add_argument("--out", default="out/camera_calibration")
    parser.add_argument("--margin", type=float, default=0.10)
    args = parser.parse_args()

    session = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) / session
    captures_dir = out_dir / "captures"
    annotated_dir = out_dir / "annotated"
    rejected_dir = out_dir / "rejected"
    for path in (captures_dir, annotated_dir, rejected_dir):
        path.mkdir(parents=True, exist_ok=True)

    screen_w, screen_h = get_screen_size()
    board, board_square_px = make_board(screen_w, screen_h, args.cols, args.rows, args.margin)
    cv2.imwrite(str(out_dir / "displayed_chessboard.png"), board)

    if args.ffmpeg_dshow_name:
        print(f"Using FFmpeg DirectShow camera name: {args.ffmpeg_dshow_name}")
        print(f"FFmpeg input codec: {args.ffmpeg_input_codec or '(auto)'}")
    elif args.dshow_name:
        print(f"Using DirectShow camera name: {args.dshow_name}")
    else:
        print(f"Using camera index: {args.camera}")
    print(f"Capture request: {args.width}x{args.height}@{args.fps} MJPEG")
    print(f"Screen board: {screen_w}x{screen_h}, square={board_square_px}px")
    print(f"Output directory: {out_dir}")
    print("")
    print("Controls:")
    print("  SPACE / c : capture current camera frame")
    print("  q / ESC   : finish and calibrate")
    print("")
    print("Move/tilt the camera between captures. Aim for 15-25 accepted frames.")

    cap = open_camera(
        args.camera,
        args.dshow_name,
        args.ffmpeg_dshow_name,
        args.ffmpeg_path,
        args.ffmpeg_input_codec,
        args.width,
        args.height,
        args.fps,
    )
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Actual capture: {actual_w}x{actual_h}@{actual_fps:.2f}")

    cv2.namedWindow("Calibration Chessboard", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Calibration Chessboard", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    valid_records = []
    total_captures = 0

    try:
        while True:
            cv2.imshow("Calibration Chessboard", board)
            key = cv2.waitKey(30) & 0xFF
            if key in (ord("q"), 27):
                break
            if key not in (ord(" "), ord("c")):
                continue

            # Let auto exposure settle after the user moves the camera.
            frame = None
            for _ in range(5):
                ok, frame = cap.read()
                if not ok:
                    frame = None
                time.sleep(0.03)
            if frame is None:
                print("capture failed: no frame")
                continue

            total_captures += 1
            found, corners = detect_corners(frame, args.cols, args.rows)
            if found:
                file_name = f"captures/frame_{len(valid_records) + 1:03d}.jpg"
                annotated_name = f"annotated/frame_{len(valid_records) + 1:03d}_corners.jpg"
                cv2.imwrite(str(out_dir / file_name), frame)
                annotated = frame.copy()
                cv2.drawChessboardCorners(annotated, (args.cols, args.rows), corners, found)
                cv2.imwrite(str(out_dir / annotated_name), annotated)
                valid_records.append(
                    {
                        "file": file_name,
                        "annotated": annotated_name,
                        "corners": corners.reshape(-1, 2).tolist(),
                    }
                )
                print(f"accepted {len(valid_records):02d}: {file_name}")
            else:
                rejected_name = f"rejected/rejected_{total_captures:03d}.jpg"
                cv2.imwrite(str(out_dir / rejected_name), frame)
                print(f"rejected: {rejected_name}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if len(valid_records) < args.min_valid:
        print(f"Not enough valid frames: {len(valid_records)} < {args.min_valid}")
        print(f"Saved partial session: {out_dir}")
        return 2

    result = calibrate(
        valid_records,
        args.cols,
        args.rows,
        args.square_size,
        (actual_w, actual_h),
        out_dir,
    )
    print("")
    print("Calibration complete.")
    print(f"RMS reprojection error: {result['rms_reprojection_error']:.6f}")
    print(f"Result JSON: {out_dir / 'calibration_result.json'}")
    print(f"Report: {out_dir / 'calibration_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
