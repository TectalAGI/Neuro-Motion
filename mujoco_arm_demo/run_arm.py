from __future__ import annotations

import argparse
import platform
import sys
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np


MODEL_PATH = Path(__file__).with_name("arm.xml")

# Control order matches the actuator order in arm.xml.
REST_CTRL = np.array([0.0, 0.0, 0.0, 0.8, 0.0, 0.0], dtype=float)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open a small MuJoCo demo of a human arm."
    )
    parser.add_argument(
        "--mode",
        choices=("animate", "rest"),
        default="animate",
        help="Animate the arm or hold a relaxed resting pose.",
    )
    return parser.parse_args()


def make_model() -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    # Reset to the keyframed home pose before the viewer starts.
    mujoco.mj_resetDataKeyframe(model, data, 0)
    data.ctrl[:] = REST_CTRL
    mujoco.mj_forward(model, data)
    return model, data


def ensure_supported_launcher() -> None:
    if platform.system() == "Darwin" and Path(sys.executable).name != "mjpython":
        raise SystemExit(
            "On macOS, run this script with `mjpython mujoco_arm_demo/run_arm.py` "
            "so MuJoCo can open the passive viewer on the main thread."
        )


def animated_ctrl(sim_time: float) -> np.ndarray:
    """Generate a smooth looping motion inside the actuator limits."""
    return np.array(
        [
            0.35 * np.sin(0.8 * sim_time),
            0.45 * np.sin(0.5 * sim_time + 0.6),
            0.25 * np.sin(1.1 * sim_time + 0.3),
            1.0 + 0.55 * np.sin(0.9 * sim_time - 0.2),
            0.25 * np.sin(1.4 * sim_time),
            0.18 * np.sin(1.7 * sim_time + 0.4),
        ],
        dtype=float,
    )


def main() -> None:
    args = parse_args()
    ensure_supported_launcher()
    model, data = make_model()

    print(f"Loaded model from {MODEL_PATH}")
    print("Actuators:", ", ".join(model.actuator(i).name for i in range(model.nu)))
    print("Mode:", args.mode)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        with viewer.lock():
            viewer.cam.azimuth = 140
            viewer.cam.elevation = -22
            viewer.cam.distance = 1.45
            viewer.cam.lookat[:] = (0.0, 0.0, 0.08)

        start_wall = time.perf_counter()
        while viewer.is_running():
            if args.mode == "animate":
                data.ctrl[:] = animated_ctrl(data.time)
            else:
                data.ctrl[:] = REST_CTRL

            mujoco.mj_step(model, data)
            viewer.sync()

            elapsed = time.perf_counter() - start_wall
            sleep_for = data.time - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)


if __name__ == "__main__":
    main()
