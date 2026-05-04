from pathlib import Path

import cv2


def main() -> int:
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    for index in range(8):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, 30)
        ok, frame = cap.read()
        if ok and frame is not None:
            path = out_dir / f"camera_probe_index_{index}.jpg"
            cv2.imwrite(str(path), frame)
            print(
                f"index={index} ok "
                f"shape={frame.shape} "
                f"fps={cap.get(cv2.CAP_PROP_FPS):.2f} "
                f"saved={path}"
            )
        else:
            print(f"index={index} no-frame")
        cap.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
