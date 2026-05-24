from __future__ import annotations

import json
import math
from pathlib import Path

import mujoco
import numpy as np


MODEL_PATH = Path(__file__).with_name("arm.xml")
OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "demo"
    / "src"
    / "data"
    / "mujocoShoulderMotion.json"
)

ANCHOR_POSES = [
    ("baseline", np.array([0.0, 0.0, 0.0, 0.8, 0.0, 0.0], dtype=float)),
    ("forward_reach", np.array([0.8, 0.0, 0.0, 0.95, 0.0, 0.0], dtype=float)),
    ("reference_ceiling", np.array([1.57, 0.0, 0.0, 1.0, 0.0, 0.0], dtype=float)),
    ("model_limit", np.array([0.0, -1.92, -1.396, 1.0, 0.0, 0.0], dtype=float)),
]
SEGMENT_SAMPLES = 36
REFERENCE_MAX_ELEVATION_DEG = 90.0


def degrees(value: float) -> float:
    return round(math.degrees(value), 3)


def measure_pose(
    model: mujoco.MjModel,
    upper_body_id: int,
    forearm_body_id: int,
    hand_body_id: int,
    qpos: np.ndarray,
    index: int,
) -> dict[str, object]:
    data = mujoco.MjData(model)
    data.qpos[:] = qpos
    mujoco.mj_forward(model, data)

    rotation = np.array(data.xmat[upper_body_id]).reshape(3, 3)
    arm_direction = rotation @ np.array([0.0, 0.0, -1.0], dtype=float)
    arm_direction /= np.linalg.norm(arm_direction)

    elevation = math.degrees(
        math.acos(np.clip(arm_direction @ np.array([0.0, 0.0, -1.0]), -1.0, 1.0))
    )

    return {
        "index": index,
        "joints": {
            "shoulderPitchDeg": degrees(qpos[0]),
            "shoulderYawDeg": degrees(qpos[1]),
            "shoulderRollDeg": degrees(qpos[2]),
            "elbowFlexDeg": degrees(qpos[3]),
            "wristPitchDeg": degrees(qpos[4]),
            "wristYawDeg": degrees(qpos[5]),
        },
        "arm": {
            "elevationDeg": round(elevation, 3),
            "direction": [round(value, 6) for value in arm_direction.tolist()],
        },
        "points": {
            "shoulder": [round(value, 6) for value in data.xpos[upper_body_id].tolist()],
            "elbow": [round(value, 6) for value in data.xpos[forearm_body_id].tolist()],
            "hand": [round(value, 6) for value in data.xpos[hand_body_id].tolist()],
        },
    }


def estimate_model_max_elevation(model: mujoco.MjModel, upper_body_id: int) -> float:
    best = 0.0

    for pitch in np.linspace(model.jnt_range[0][0], model.jnt_range[0][1], 21):
        for yaw in np.linspace(model.jnt_range[1][0], model.jnt_range[1][1], 21):
            for roll in np.linspace(model.jnt_range[2][0], model.jnt_range[2][1], 21):
                data = mujoco.MjData(model)
                data.qpos[:] = [pitch, yaw, roll, 0.8, 0.0, 0.0]
                mujoco.mj_forward(model, data)

                rotation = np.array(data.xmat[upper_body_id]).reshape(3, 3)
                arm_direction = rotation @ np.array([0.0, 0.0, -1.0], dtype=float)
                arm_direction /= np.linalg.norm(arm_direction)
                elevation = math.degrees(
                    math.acos(
                        np.clip(arm_direction @ np.array([0.0, 0.0, -1.0]), -1.0, 1.0)
                    )
                )
                best = max(best, elevation)

    return round(best, 3)


def build_dataset() -> dict[str, object]:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    upper_body_id = model.body("upper_arm").id
    forearm_body_id = model.body("forearm").id
    hand_body_id = model.body("hand").id

    samples: list[dict[str, object]] = []
    named_indices: dict[str, int] = {}

    for anchor_index, (name, anchor) in enumerate(ANCHOR_POSES):
        if anchor_index == 0:
            named_indices[name] = len(samples)
            samples.append(
                measure_pose(
                    model,
                    upper_body_id,
                    forearm_body_id,
                    hand_body_id,
                    anchor,
                    len(samples),
                )
            )
            continue

        previous = ANCHOR_POSES[anchor_index - 1][1]
        interpolation = np.linspace(0.0, 1.0, SEGMENT_SAMPLES + 1)[1:]

        for step_index, mix in enumerate(interpolation, start=1):
            qpos = (1.0 - mix) * previous + mix * anchor
            sample = measure_pose(
                model,
                upper_body_id,
                forearm_body_id,
                hand_body_id,
                qpos,
                len(samples),
            )
            samples.append(sample)
            if step_index == len(interpolation):
                named_indices[name] = sample["index"]  # type: ignore[index]

    return {
        "modelName": "human_arm_demo",
        "sourceXml": str(MODEL_PATH.relative_to(Path(__file__).resolve().parents[1])),
        "referenceMaxElevationDeg": REFERENCE_MAX_ELEVATION_DEG,
        "modelMaxElevationDeg": estimate_model_max_elevation(model, upper_body_id),
        "notes": (
            "This MuJoCo scaffold directly drives the browser pose data. In its current form, "
            "the upper-arm envelope tops out at roughly 110 degrees of elevation, so it should "
            "be treated as a spatial shoulder prototype rather than a full clinical 180-degree flexion model."
        ),
        "namedSampleIndices": named_indices,
        "samples": samples,
    }


def main() -> None:
    dataset = build_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2))
    print(f"Wrote MuJoCo shoulder motion dataset to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
