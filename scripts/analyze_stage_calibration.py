import argparse
import re
from pathlib import Path

import cv2
import numpy as np


ANGLE_RE = re.compile(r"_(\d{3})\.tif$", re.IGNORECASE)


def load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Failed to load image: {path}")

    h, w = img.shape
    cy, cx = h // 2, w // 2
    half = min(min(h, w) // 2, 450)
    img = img[cy - half:cy + half, cx - half:cx + half]
    img = cv2.GaussianBlur(img, (0, 0), 1.2).astype(np.float32)
    return img


def estimate_rotation(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    center = (a.shape[1] / 2, a.shape[0] / 2)
    max_radius = min(center)
    a_lp = cv2.warpPolar(a, (720, 360), center, max_radius, cv2.WARP_POLAR_LOG)
    b_lp = cv2.warpPolar(b, (720, 360), center, max_radius, cv2.WARP_POLAR_LOG)
    shift, response = cv2.phaseCorrelate(a_lp, b_lp)
    rot_deg = -shift[1] * 360.0 / a_lp.shape[0]
    while rot_deg <= -180:
        rot_deg += 360
    while rot_deg > 180:
        rot_deg -= 360
    return rot_deg, response


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate effective stage rotation from calibration images.")
    parser.add_argument("folder", help="Folder containing TIFF images with _AAA angle suffixes.")
    args = parser.parse_args()

    folder = Path(args.folder)
    files = sorted(folder.glob("*.tif"))
    entries = []
    for path in files:
        match = ANGLE_RE.search(path.name)
        if match:
            entries.append((int(match.group(1)), path))

    if len(entries) < 2:
        raise SystemExit("Need at least two angle-tagged TIFF files.")

    images = {angle: load_image(path) for angle, path in entries}
    ref_angle = entries[0][0]
    xs = []
    ys = []
    weights = []

    print("Relative-to-reference estimates")
    for angle, _ in entries[1:]:
        rot, response = estimate_rotation(images[ref_angle], images[angle])
        actual = abs(rot)
        xs.append(angle - ref_angle)
        ys.append(actual)
        weights.append(max(response, 0.0))
        print(f"{ref_angle:03d}->{angle:03d}: commanded={angle - ref_angle:6.2f}, estimated={actual:7.2f}, response={response:.4f}")

    X = np.vstack([np.array(xs), np.ones(len(xs))]).T
    y = np.array(ys)
    slope, intercept = np.polyfit(xs, ys, 1)

    w = np.array(weights)
    if np.allclose(w.sum(), 0.0):
        weighted_slope, weighted_intercept = slope, intercept
    else:
        W = np.diag(w)
        beta = np.linalg.inv(X.T @ W @ X) @ (X.T @ W @ y)
        weighted_slope, weighted_intercept = beta

    print()
    print(f"Unweighted actual_stage ~= {slope:.6f} * commanded + {intercept:.6f}")
    print(f"Weighted   actual_stage ~= {weighted_slope:.6f} * commanded + {weighted_intercept:.6f}")
    if weighted_slope != 0:
        print(f"Recommended stage_to_servo_ratio ~= {1.0 / weighted_slope:.6f}")


if __name__ == "__main__":
    main()
