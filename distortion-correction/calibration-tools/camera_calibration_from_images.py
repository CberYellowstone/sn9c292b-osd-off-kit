import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from camera_calibration_collect import detect_corners


def build_object_points(cols: int, rows: int, square_size: float) -> np.ndarray:
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= square_size
    return objp


def reprojection_errors_pinhole(objpoints, imgpoints, rvecs, tvecs, camera_matrix, dist_coeffs):
    errors = []
    for obj, img, rvec, tvec in zip(objpoints, imgpoints, rvecs, tvecs):
        projected, _ = cv2.projectPoints(obj, rvec, tvec, camera_matrix, dist_coeffs)
        err = cv2.norm(img, projected, cv2.NORM_L2) / len(projected)
        errors.append(float(err))
    return errors


def reprojection_errors_fisheye(objpoints, imgpoints, rvecs, tvecs, camera_matrix, dist_coeffs):
    errors = []
    for obj, img, rvec, tvec in zip(objpoints, imgpoints, rvecs, tvecs):
        projected, _ = cv2.fisheye.projectPoints(obj, rvec, tvec, camera_matrix, dist_coeffs)
        err = cv2.norm(img, projected, cv2.NORM_L2) / len(projected)
        errors.append(float(err))
    return errors


def fov_from_camera_matrix(camera_matrix: np.ndarray, image_size: tuple[int, int]) -> dict:
    width, height = image_size
    fx = float(camera_matrix[0, 0])
    fy = float(camera_matrix[1, 1])
    return {
        "horizontal_deg": math.degrees(2.0 * math.atan(width / (2.0 * fx))) if fx > 0 else None,
        "vertical_deg": math.degrees(2.0 * math.atan(height / (2.0 * fy))) if fy > 0 else None,
    }


def scan_images(image_dir: Path, cols: int, rows: int, out_dir: Path):
    files = sorted(
        p
        for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    )
    if not files:
        raise FileNotFoundError(f"no images found in {image_dir}")

    annotated_dir = out_dir / "annotated"
    rejected_dir = out_dir / "rejected"
    annotated_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    records = []
    image_size = None
    for idx, path in enumerate(files, start=1):
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"skip unreadable: {path}")
            continue
        height, width = frame.shape[:2]
        if image_size is None:
            image_size = (width, height)
        elif image_size != (width, height):
            raise ValueError(f"image size mismatch: {path} has {width}x{height}, expected {image_size}")

        found, corners = detect_corners(frame, cols, rows)
        if not found:
            rejected = rejected_dir / f"{idx:03d}_{path.stem}_rejected.jpg"
            cv2.imwrite(str(rejected), frame)
            print(f"rejected {idx:02d}: {path.name}")
            continue

        corners = np.asarray(corners, dtype=np.float32).reshape(-1, 1, 2)
        annotated = frame.copy()
        cv2.drawChessboardCorners(annotated, (cols, rows), corners, True)
        annotated_path = annotated_dir / f"{idx:03d}_{path.stem}_corners.jpg"
        cv2.imwrite(str(annotated_path), annotated)
        records.append(
            {
                "source": str(path),
                "annotated": str(annotated_path.relative_to(out_dir)),
                "corners": corners.reshape(-1, 2).tolist(),
            }
        )
        print(f"accepted {len(records):02d}: {path.name}")

    if image_size is None:
        raise RuntimeError("no readable images")
    return records, image_size, len(files)


def calibrate_pinhole(name: str, flags: int, objpoints, imgpoints, image_size):
    rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints,
        imgpoints,
        image_size,
        None,
        None,
        flags=flags,
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-8),
    )
    errors = reprojection_errors_pinhole(objpoints, imgpoints, rvecs, tvecs, camera_matrix, dist_coeffs)
    return {
        "name": name,
        "family": "pinhole",
        "flags": int(flags),
        "rms_reprojection_error": float(rms),
        "mean_per_view_error": float(np.mean(errors)),
        "max_per_view_error": float(np.max(errors)),
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.ravel().tolist(),
        "fov_degrees": fov_from_camera_matrix(camera_matrix, image_size),
        "per_view_errors": errors,
    }, camera_matrix, dist_coeffs


def calibrate_fisheye(objpoints, imgpoints, image_size):
    objpoints_f = [obj.reshape(-1, 1, 3).astype(np.float64) for obj in objpoints]
    imgpoints_f = [img.astype(np.float64) for img in imgpoints]
    camera_matrix = np.array(
        [[image_size[0], 0.0, image_size[0] / 2.0], [0.0, image_size[0], image_size[1] / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)
    flags = cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC | cv2.fisheye.CALIB_FIX_SKEW
    rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.fisheye.calibrate(
        objpoints_f,
        imgpoints_f,
        image_size,
        camera_matrix,
        dist_coeffs,
        None,
        None,
        flags=flags,
        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 1e-8),
    )
    errors = reprojection_errors_fisheye(objpoints_f, imgpoints_f, rvecs, tvecs, camera_matrix, dist_coeffs)
    return {
        "name": "fisheye_kannala_brandt_4",
        "family": "fisheye",
        "flags": int(flags),
        "rms_reprojection_error": float(rms),
        "mean_per_view_error": float(np.mean(errors)),
        "max_per_view_error": float(np.max(errors)),
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.ravel().tolist(),
        "fov_degrees": fov_from_camera_matrix(camera_matrix, image_size),
        "per_view_errors": errors,
    }, camera_matrix, dist_coeffs


def write_undistort_samples(
    image_path: Path,
    image_size: tuple[int, int],
    model_results: list[dict],
    model_mats: dict[str, tuple[np.ndarray, np.ndarray]],
    out_dir: Path,
):
    img = cv2.imread(str(image_path))
    if img is None:
        return
    sample_dir = out_dir / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(sample_dir / "sample_original.jpg"), img)

    thumbs = []
    font = cv2.FONT_HERSHEY_SIMPLEX
    for result in model_results:
        name = result["name"]
        camera_matrix, dist_coeffs = model_mats[name]
        if result["family"] == "fisheye":
            new_k = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
                camera_matrix, dist_coeffs, image_size, np.eye(3), balance=0.5
            )
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(
                camera_matrix, dist_coeffs, np.eye(3), new_k, image_size, cv2.CV_16SC2
            )
            und = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR)
            suffix = "balance05"
        else:
            new_k, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, image_size, 0.5, image_size)
            und = cv2.undistort(img, camera_matrix, dist_coeffs, None, new_k)
            suffix = "alpha05"
            result.setdefault("optimal_new_camera_matrix", {})["alpha_0_5"] = {
                "matrix": new_k.tolist(),
                "roi": [int(v) for v in roi],
            }
        out_path = sample_dir / f"sample_{name}_{suffix}.jpg"
        cv2.imwrite(str(out_path), und)
        small = cv2.resize(und, (480, 270))
        cv2.rectangle(small, (0, 0), (440, 34), (0, 0, 0), -1)
        cv2.putText(small, name[:32], (8, 24), font, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
        thumbs.append(small)

    original = cv2.resize(img, (480, 270))
    cv2.rectangle(original, (0, 0), (150, 34), (0, 0, 0), -1)
    cv2.putText(original, "original", (8, 24), font, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
    thumbs.insert(0, original)
    while len(thumbs) % 2:
        thumbs.append(np.zeros_like(original))
    rows = [np.hstack(thumbs[i : i + 2]) for i in range(0, len(thumbs), 2)]
    cv2.imwrite(str(sample_dir / "model_contact_sheet_alpha05.jpg"), np.vstack(rows))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description="Calibrate camera models from chessboard image files.")
    parser.add_argument("--images", default="out/fine")
    parser.add_argument("--cols", type=int, default=9, help="inner corners columns")
    parser.add_argument("--rows", type=int, default=6, help="inner corners rows")
    parser.add_argument("--square-size", type=float, default=1.0)
    parser.add_argument("--out", default="out/fine_calibration")
    parser.add_argument("--min-valid", type=int, default=12)
    args = parser.parse_args()

    image_dir = Path(args.images)
    session = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) / session
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"images: {image_dir}")
    print(f"output: {out_dir}")
    print(f"pattern: {args.cols}x{args.rows} inner corners")

    records, image_size, total_files = scan_images(image_dir, args.cols, args.rows, out_dir)
    print(f"image size: {image_size[0]}x{image_size[1]}")
    print(f"accepted images: {len(records)} / {total_files}")
    if len(records) < args.min_valid:
        print(f"not enough valid images: {len(records)} < {args.min_valid}")
        return 2

    base_obj = build_object_points(args.cols, args.rows, args.square_size)
    objpoints = [base_obj.copy() for _ in records]
    imgpoints = [np.asarray(record["corners"], dtype=np.float32).reshape(-1, 1, 2) for record in records]

    model_specs = [
        ("pinhole_radial_k1k2_no_tangent", cv2.CALIB_ZERO_TANGENT_DIST | cv2.CALIB_FIX_K3),
        ("pinhole_brown_5", 0),
        ("pinhole_rational_8", cv2.CALIB_RATIONAL_MODEL),
    ]

    results = []
    model_mats = {}
    for name, flags in model_specs:
        try:
            result, camera_matrix, dist_coeffs = calibrate_pinhole(name, flags, objpoints, imgpoints, image_size)
            results.append(result)
            model_mats[name] = (camera_matrix, dist_coeffs)
            print(f"{name}: rms={result['rms_reprojection_error']:.6f} mean={result['mean_per_view_error']:.6f}")
        except cv2.error as exc:
            results.append({"name": name, "family": "pinhole", "error": str(exc)})
            print(f"{name}: failed: {exc}")

    try:
        result, camera_matrix, dist_coeffs = calibrate_fisheye(objpoints, imgpoints, image_size)
        results.append(result)
        model_mats[result["name"]] = (camera_matrix, dist_coeffs)
        print(f"{result['name']}: rms={result['rms_reprojection_error']:.6f} mean={result['mean_per_view_error']:.6f}")
    except cv2.error as exc:
        results.append({"name": "fisheye_kannala_brandt_4", "family": "fisheye", "error": str(exc)})
        print(f"fisheye_kannala_brandt_4: failed: {exc}")

    ok_results = [item for item in results if "error" not in item]
    if not ok_results:
        raise RuntimeError("all calibration models failed")

    # Prefer a stable wide-angle model over a slightly lower-RMS overfit.
    sorted_by_rms = sorted(ok_results, key=lambda item: item["rms_reprojection_error"])
    brown = next((item for item in ok_results if item["name"] == "pinhole_brown_5"), None)
    rational = next((item for item in ok_results if item["name"] == "pinhole_rational_8"), None)
    fisheye = next((item for item in ok_results if item["name"] == "fisheye_kannala_brandt_4"), None)
    best = sorted_by_rms[0]
    rational_suspicious = False
    if rational is not None:
        radial = rational["dist_coeffs"][:8]
        rational_suspicious = max(abs(float(v)) for v in radial) > 10.0

    if fisheye is not None and best["rms_reprojection_error"] > 0:
        fisheye_delta = (fisheye["rms_reprojection_error"] - best["rms_reprojection_error"]) / best["rms_reprojection_error"]
    else:
        fisheye_delta = float("inf")

    if fisheye is not None and rational_suspicious and fisheye_delta < 0.03:
        recommended = fisheye
        recommendation_reason = (
            "The rational model has the lowest RMS, but its radial coefficients are very large and likely overfit. "
            "The fisheye model is within 3% RMS, uses a compact 4-coefficient wide-angle model, and gives more stable borders."
        )
    elif brown is not None and best["rms_reprojection_error"] > 0 and (
        (brown["rms_reprojection_error"] - best["rms_reprojection_error"]) / best["rms_reprojection_error"] < 0.03
    ):
        recommended = brown
        recommendation_reason = "The simpler Brown-Conrady model is within 3% RMS of the best model, so it is preferred."
    else:
        recommended = best
        recommendation_reason = "This model has the best measured RMS without a simpler model close enough to replace it."

    sample_source = Path(records[len(records) // 2]["source"])
    write_undistort_samples(sample_source, image_size, ok_results, model_mats, out_dir)

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": str(image_dir),
        "image_size": {"width": image_size[0], "height": image_size[1]},
        "pattern": {"inner_corners_cols": args.cols, "inner_corners_rows": args.rows, "square_size_units": args.square_size},
        "total_files": total_files,
        "valid_images": len(records),
        "records": records,
        "models": results,
        "recommended_model": recommended["name"],
        "recommendation_reason": recommendation_reason,
    }
    (out_dir / "fine_calibration_models.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report_lines = [
        "# Fine Camera Calibration Model Comparison",
        "",
        f"- source: `{image_dir}`",
        f"- valid images: {len(records)} / {total_files}",
        f"- image size: {image_size[0]}x{image_size[1]}",
        f"- recommended model: `{recommended['name']}`",
        f"- reason: {recommendation_reason}",
        "",
        "## Model Results",
        "",
    ]
    for item in results:
        if "error" in item:
            report_lines.append(f"- `{item['name']}`: failed")
            continue
        report_lines.append(
            f"- `{item['name']}`: RMS `{item['rms_reprojection_error']:.6f}`, "
            f"mean `{item['mean_per_view_error']:.6f}`, max `{item['max_per_view_error']:.6f}`, "
            f"HFOV `{item['fov_degrees']['horizontal_deg']:.2f}` deg"
        )
    report_lines += [
        "",
        "## Recommended Parameters",
        "",
        "```json",
        json.dumps(
            {
                "name": recommended["name"],
                "camera_matrix": recommended["camera_matrix"],
                "dist_coeffs": recommended["dist_coeffs"],
                "fov_degrees": recommended["fov_degrees"],
            },
            indent=2,
        ),
        "```",
        "",
        "## Notes",
        "",
        "- A screen-based target is less reliable than a printed flat board.",
        "- If the monitor is curved, calibration may absorb screen curvature into lens distortion coefficients.",
        "- For this camera class, fisheye should only win if it is both lower-error and visually less distorted near borders.",
    ]
    (out_dir / "fine_calibration_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"recommended: {recommended['name']}")
    print(f"result: {out_dir / 'fine_calibration_models.json'}")
    print(f"report: {out_dir / 'fine_calibration_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
