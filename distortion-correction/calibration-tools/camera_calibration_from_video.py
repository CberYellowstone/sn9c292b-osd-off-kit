import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from camera_calibration_collect import calibrate, detect_corners


def candidate_vector(corners: np.ndarray, image_size: tuple[int, int]) -> np.ndarray:
    width, height = image_size
    pts = corners.reshape(-1, 2)
    center = pts.mean(axis=0)
    x, y, w, h = cv2.boundingRect(pts.astype(np.float32))
    area = (w * h) / float(width * height)

    row_len = int(round(math.sqrt(len(pts)))) if len(pts) else 1
    first = pts[0]
    last = pts[-1]
    diagonal_angle = math.atan2(float(last[1] - first[1]), float(last[0] - first[0])) / math.pi

    return np.array(
        [
            center[0] / width,
            center[1] / height,
            math.sqrt(max(area, 1e-9)),
            w / width,
            h / height,
            diagonal_angle,
            row_len / 10.0,
        ],
        dtype=np.float32,
    )


def diversity_distance(a: np.ndarray, b: np.ndarray) -> float:
    weights = np.array([1.4, 1.4, 1.0, 0.6, 0.6, 0.8, 0.1], dtype=np.float32)
    return float(np.linalg.norm((a - b) * weights))


def select_diverse(candidates: list[dict], max_valid: int, min_gap_frames: int) -> list[dict]:
    if len(candidates) <= max_valid:
        return candidates

    selected: list[dict] = []
    remaining = candidates.copy()

    # Start with a centered, large, clean view. It stabilizes calibration.
    center = np.array([0.5, 0.5], dtype=np.float32)
    first = min(
        remaining,
        key=lambda item: float(np.linalg.norm(item["vector"][:2] - center)) - float(item["vector"][2]),
    )
    selected.append(first)
    remaining.remove(first)

    while remaining and len(selected) < max_valid:
        def score(item: dict) -> float:
            if any(abs(item["frame_index"] - picked["frame_index"]) < min_gap_frames for picked in selected):
                return -1.0
            return min(diversity_distance(item["vector"], picked["vector"]) for picked in selected)

        best = max(remaining, key=score)
        best_score = score(best)
        if best_score < 0:
            break
        selected.append(best)
        remaining.remove(best)

    selected.sort(key=lambda item: item["frame_index"])
    return selected


def save_selected_frames(
    video_path: Path,
    selected: list[dict],
    cols: int,
    rows: int,
    out_dir: Path,
) -> list[dict]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")

    captures_dir = out_dir / "captures"
    annotated_dir = out_dir / "annotated"
    captures_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)

    records = []
    try:
        for idx, item in enumerate(selected, start=1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, item["frame_index"])
            ok, frame = cap.read()
            if not ok or frame is None:
                continue

            file_name = f"captures/frame_{idx:03d}_src_{item['frame_index']:06d}.jpg"
            annotated_name = f"annotated/frame_{idx:03d}_src_{item['frame_index']:06d}_corners.jpg"
            cv2.imwrite(str(out_dir / file_name), frame)

            annotated = frame.copy()
            corners = item["corners"].reshape(-1, 1, 2)
            cv2.drawChessboardCorners(annotated, (cols, rows), corners, True)
            cv2.imwrite(str(out_dir / annotated_name), annotated)

            records.append(
                {
                    "file": file_name,
                    "annotated": annotated_name,
                    "corners": item["corners"].reshape(-1, 2).tolist(),
                    "frame_index": int(item["frame_index"]),
                    "time_sec": float(item["time_sec"]),
                }
            )
    finally:
        cap.release()

    return records


def scan_video(video_path: Path, cols: int, rows: int, step: int) -> tuple[list[dict], tuple[int, int], float, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    image_size = (width, height)

    candidates = []
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            if frame_index % step != 0:
                frame_index += 1
                continue

            found, corners = detect_corners(frame, cols, rows)
            if found:
                corners = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
                candidates.append(
                    {
                        "frame_index": frame_index,
                        "time_sec": frame_index / fps,
                        "corners": corners,
                        "vector": candidate_vector(corners, image_size),
                    }
                )
            frame_index += 1
    finally:
        cap.release()

    return candidates, image_size, fps, frame_count


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description="Calibrate camera distortion from a recorded chessboard video.")
    parser.add_argument("video")
    parser.add_argument("--cols", type=int, default=9, help="inner corners columns")
    parser.add_argument("--rows", type=int, default=6, help="inner corners rows")
    parser.add_argument("--square-size", type=float, default=1.0)
    parser.add_argument("--step", type=int, default=5)
    parser.add_argument("--max-valid", type=int, default=30)
    parser.add_argument("--min-valid", type=int, default=12)
    parser.add_argument("--min-gap-sec", type=float, default=0.5)
    parser.add_argument("--out", default="out/camera_calibration_from_video")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    session = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) / session
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"video: {video_path}")
    print(f"output: {out_dir}")
    print(f"pattern: {args.cols}x{args.rows} inner corners")
    print(f"scan step: every {args.step} frames")

    candidates, image_size, fps, frame_count = scan_video(video_path, args.cols, args.rows, args.step)
    print(f"video size: {image_size[0]}x{image_size[1]} frames={frame_count} fps={fps:.3f}")
    print(f"detected candidates: {len(candidates)}")

    min_gap_frames = max(1, int(round(args.min_gap_sec * fps)))
    selected = select_diverse(candidates, args.max_valid, min_gap_frames)
    print(f"selected diverse frames: {len(selected)}")

    records = save_selected_frames(video_path, selected, args.cols, args.rows, out_dir)
    if len(records) < args.min_valid:
        summary = {
            "video": str(video_path),
            "image_size": {"width": image_size[0], "height": image_size[1]},
            "fps": fps,
            "frame_count": frame_count,
            "detected_candidates": len(candidates),
            "selected_frames": len(records),
            "min_valid": args.min_valid,
        }
        (out_dir / "failed_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"not enough selected frames: {len(records)} < {args.min_valid}")
        print(f"partial output: {out_dir}")
        return 2

    result = calibrate(records, args.cols, args.rows, args.square_size, image_size, out_dir)
    result["source_video"] = str(video_path)
    result["source_fps"] = fps
    result["source_frame_count"] = frame_count
    result["detected_candidates"] = len(candidates)
    result["selected_source_frames"] = [
        {"frame_index": item["frame_index"], "time_sec": item["time_sec"]} for item in records
    ]
    (out_dir / "calibration_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("")
    print("calibration complete")
    print(f"RMS reprojection error: {result['rms_reprojection_error']:.6f}")
    print(f"mean per-view error: {result['mean_per_view_error']:.6f}")
    print(f"result: {out_dir / 'calibration_result.json'}")
    print(f"report: {out_dir / 'calibration_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
