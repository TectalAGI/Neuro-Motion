from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button, Slider


ARM_LENGTH = 2.25
SCENE_RADIUS = 3.2
POSE_LIMITS = {"phi": (0.0, 180.0), "theta": (-150.0, 150.0)}
DEFAULT_CSV_PATH = Path(__file__).with_name("data") / "JayceArmData1.csv"
CPP_BACKEND_SOURCE = Path(__file__).with_name("main.cpp")
CPP_BACKEND_BINARY = Path(__file__).with_name("snap_backend.exe" if os.name == "nt" else "snap_backend")

# Apple iPhone 17 Pro Max dimensions from Apple technical specifications:
# height 163.4 mm, width 78.0 mm, thickness 8.75 mm.
IPHONE_17_PRO_MAX_HEIGHT_MM = 163.4
IPHONE_17_PRO_MAX_WIDTH_MM = 78.0
UPPER_ARM_REFERENCE_MM = 320.0
SENSOR_LENGTH_RATIO = min(0.72, IPHONE_17_PRO_MAX_HEIGHT_MM / UPPER_ARM_REFERENCE_MM)
SENSOR_OFFSET_RATIO = SENSOR_LENGTH_RATIO * 0.5
SENSOR_MARKER_SIZE = 140

LIF_DECAY = 0.5
LIF_THRESHOLD = 20.0
LIF_RESET = 0.0
SNAP_OOB_LOOKBACK_SECONDS = 1.0

@dataclass
class PoseState:
    phi_deg: float = 90.0
    theta_deg: float = 0.0
    # Research-informed defaults:
    # - arm-at-side neutral starts at 0 degrees of elevation
    # - normal shoulder elevation is commonly referenced to 180 degrees
    # - the scapular plane is typically described around 30-45 degrees anterior
    #   to the frontal plane, so we keep a +/-45 degree azimuth envelope
    #   around the playback baseline for theta.
    phi_min_deg: float = 15.0
    phi_max_deg: float = 165.0
    theta_min_deg: float = -45.0
    theta_max_deg: float = 45.0


@dataclass
class SensorFrame:
    time: float
    ax: float
    ay: float
    az: float
    abs_accel: float


@dataclass
class MotionFrame:
    time: float
    phi_deg: float
    theta_deg: float
    abs_accel: float
    voltage: float
    snap: bool
    cumulative_snaps: int


@dataclass
class BackendSnapFrame:
    time: float
    abs_accel: float
    voltage: float
    snap: bool
    cumulative_snaps: int


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def wrap_angle(angle_deg: float) -> float:
    return ((angle_deg + 180.0) % 360.0) - 180.0


def blend_angle(previous_deg: float, target_deg: float, alpha: float) -> float:
    delta = wrap_angle(target_deg - previous_deg)
    return wrap_angle(previous_deg + alpha * delta)


def compute_upper_direction(phi_deg: float, theta_deg: float) -> np.ndarray:
    phi = np.radians(phi_deg)
    theta = np.radians(theta_deg)
    direction = np.array(
        [
            np.sin(theta) * np.sin(phi),
            -np.cos(phi),
            np.cos(theta) * np.sin(phi),
        ],
        dtype=float,
    )
    return direction / np.linalg.norm(direction)


def compute_arm_points(phi_deg: float, theta_deg: float) -> tuple[np.ndarray, np.ndarray]:
    shoulder = np.array([0.0, 0.0, 0.0], dtype=float)
    elbow = shoulder + compute_upper_direction(phi_deg, theta_deg) * ARM_LENGTH
    return shoulder, elbow


def build_safe_envelope(state: PoseState, resolution: int = 24) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    phi_values = np.radians(np.linspace(state.phi_min_deg, state.phi_max_deg, resolution))
    theta_values = np.radians(np.linspace(state.theta_min_deg, state.theta_max_deg, resolution))
    theta_grid, phi_grid = np.meshgrid(theta_values, phi_values)

    x = np.sin(theta_grid) * np.sin(phi_grid) * ARM_LENGTH
    y = -np.cos(phi_grid) * ARM_LENGTH
    z = np.cos(theta_grid) * np.sin(phi_grid) * ARM_LENGTH
    return x, y, z


def angles_are_safe(phi_deg: float, theta_deg: float, state: PoseState) -> bool:
    return (
        state.phi_min_deg <= phi_deg <= state.phi_max_deg
        and state.theta_min_deg <= theta_deg <= state.theta_max_deg
    )


def motion_frame_is_safe(frame: MotionFrame, state: PoseState) -> bool:
    return angles_are_safe(float(frame.phi_deg), float(frame.theta_deg), state)


def pose_is_safe(state: PoseState) -> bool:
    return angles_are_safe(state.phi_deg, state.theta_deg, state)


def format_status(state: PoseState) -> str:
    phi_over = 0.0
    theta_over = 0.0

    if state.phi_deg < state.phi_min_deg:
        phi_over = state.phi_min_deg - state.phi_deg
    elif state.phi_deg > state.phi_max_deg:
        phi_over = state.phi_deg - state.phi_max_deg

    if state.theta_deg < state.theta_min_deg:
        theta_over = state.theta_min_deg - state.theta_deg
    elif state.theta_deg > state.theta_max_deg:
        theta_over = state.theta_deg - state.theta_max_deg

    if phi_over == 0 and theta_over == 0:
        return "Within safe range"

    messages: list[str] = []
    if phi_over:
        messages.append(f"Phi {phi_over:.0f}° outside")
    if theta_over:
        messages.append(f"Theta {theta_over:.0f}° outside")
    return "Outside safe range: " + " | ".join(messages)


def summarize_snap_relationships(
    frames: list[MotionFrame],
    state: PoseState,
    lookback_seconds: float = SNAP_OOB_LOOKBACK_SECONDS,
) -> tuple[int, int]:
    out_of_bounds_related = 0
    not_out_of_bounds_related = 0
    last_outside_time: float | None = None

    for frame in frames:
        if not motion_frame_is_safe(frame, state):
            last_outside_time = frame.time

        if not frame.snap:
            continue

        if last_outside_time is not None and frame.time - last_outside_time <= lookback_seconds:
            out_of_bounds_related += 1
        else:
            not_out_of_bounds_related += 1

    return out_of_bounds_related, not_out_of_bounds_related


def classify_snap_relationships(
    frames: list[MotionFrame],
    state: PoseState,
    lookback_seconds: float = SNAP_OOB_LOOKBACK_SECONDS,
) -> list[bool]:
    classifications: list[bool] = []
    last_outside_time: float | None = None

    for frame in frames:
        if not motion_frame_is_safe(frame, state):
            last_outside_time = frame.time

        is_oob_related = bool(
            frame.snap
            and last_outside_time is not None
            and frame.time - last_outside_time <= lookback_seconds
        )
        classifications.append(is_oob_related)

    return classifications


def parse_phyphox_csv(filepath: Path) -> list[SensorFrame]:
    frames: list[SensorFrame] = []
    with filepath.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            frames.append(
                SensorFrame(
                    time=float(row['Time (s)']),
                    ax=float(row['Acceleration x (m/s^2)']),
                    ay=float(row['Acceleration y (m/s^2)']),
                    az=float(row['Acceleration z (m/s^2)']),
                    abs_accel=float(row['Absolute acceleration (m/s^2)']),
                )
            )
    return frames


def compile_cpp_backend(source_path: Path = CPP_BACKEND_SOURCE, binary_path: Path = CPP_BACKEND_BINARY) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"C++ backend source not found: {source_path}")

    if binary_path.exists() and binary_path.stat().st_mtime >= source_path.stat().st_mtime:
        return binary_path

    compiler = next((name for name in ("c++", "g++", "clang++") if shutil.which(name)), None)
    if compiler is None:
        raise RuntimeError("No C++ compiler found. Install c++, g++, or clang++ to use the backend.")

    command = [compiler, "-std=c++17", "-O2", str(source_path), "-o", str(binary_path)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return binary_path


def load_cpp_snap_frames(csv_path: Path) -> list[BackendSnapFrame]:
    binary_path = compile_cpp_backend()
    result = subprocess.run(
        [str(binary_path), str(csv_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    rows: list[BackendSnapFrame] = []
    reader = csv.DictReader(result.stdout.splitlines())
    for row in reader:
        rows.append(
            BackendSnapFrame(
                time=float(row["time"]),
                abs_accel=float(row["abs_accel"]),
                voltage=float(row["voltage"]),
                snap=bool(int(row["snap"])),
                cumulative_snaps=int(row["cumulative_snaps"]),
            )
        )
    return rows


def derive_motion_frames(
    sensor_frames: list[SensorFrame],
    backend_frames: list[BackendSnapFrame] | None = None,
) -> list[MotionFrame]:
    if not sensor_frames:
        return []

    frames: list[MotionFrame] = []
    baseline_theta_raw: float | None = None
    smoothed_phi: float | None = None
    smoothed_theta: float | None = None
    voltage = 0.0

    backend_available = bool(backend_frames) and len(backend_frames) == len(sensor_frames)

    for index, sensor in enumerate(sensor_frames):
        accel_mag = max(sensor.abs_accel, 1e-6)
        gx = sensor.ax / accel_mag
        gy = sensor.ay / accel_mag
        gz = sensor.az / accel_mag

        # Because the phone is mounted with its top toward the shoulder and its bottom toward
        # the elbow, the phone's long axis approximates the humerus. We estimate elevation from
        # the alignment between gravity and the phone's Y axis.
        phi_raw = np.degrees(np.arccos(np.clip(-gy, -1.0, 1.0)))

        # Accelerometer-only data cannot uniquely recover yaw around gravity, so theta is treated
        # as a relative sweep from the first frame using the phone's X/Z projection.
        theta_raw = np.degrees(np.arctan2(gx, -gz if abs(gz) > 1e-6 else 1e-6))
        if baseline_theta_raw is None:
            baseline_theta_raw = theta_raw
        theta_relative = wrap_angle(theta_raw - baseline_theta_raw)

        if smoothed_phi is None:
            smoothed_phi = phi_raw
            smoothed_theta = theta_relative
        else:
            smoothed_phi = 0.84 * smoothed_phi + 0.16 * phi_raw
            smoothed_theta = blend_angle(smoothed_theta, theta_relative, 0.18)

        if backend_available:
            backend_frame = backend_frames[index]
            snap_voltage = backend_frame.voltage
            snap = backend_frame.snap
            cumulative_snaps = backend_frame.cumulative_snaps
        else:
            voltage = (voltage + sensor.abs_accel) * LIF_DECAY
            snap = voltage > LIF_THRESHOLD
            snap_voltage = voltage
            if snap:
                voltage = LIF_RESET
            cumulative_snaps = frames[-1].cumulative_snaps + int(snap) if frames else int(snap)

        frames.append(
            MotionFrame(
                time=sensor.time,
                phi_deg=clamp(smoothed_phi, *POSE_LIMITS["phi"]),
                theta_deg=clamp(smoothed_theta, *POSE_LIMITS["theta"]),
                abs_accel=sensor.abs_accel,
                voltage=snap_voltage,
                snap=snap,
                cumulative_snaps=cumulative_snaps,
            )
        )

    return frames


class ShoulderWorkspaceApp:
    def __init__(self, state: PoseState, playback_frames: list[MotionFrame], playback_source: Path | None) -> None:
        self.state = state
        self.playback_frames = playback_frames
        self.playback_source = playback_source
        self.playback_index = 0
        self.playback_active = False
        self.syncing_pose_sliders = False
        self.snap_oob_related_count = 0
        self.snap_not_oob_related_count = 0
        self.snap_oob_prefix_counts: list[int] = []
        self.snap_other_prefix_counts: list[int] = []

        if self.playback_frames:
            snap_oob_flags = classify_snap_relationships(self.playback_frames, self.state)
            oob_count = 0
            other_count = 0
            for frame, is_oob_related in zip(self.playback_frames, snap_oob_flags):
                if frame.snap:
                    if is_oob_related:
                        oob_count += 1
                    else:
                        other_count += 1
                self.snap_oob_prefix_counts.append(oob_count)
                self.snap_other_prefix_counts.append(other_count)

            self.snap_oob_related_count = oob_count
            self.snap_not_oob_related_count = other_count

        self.figure = plt.figure(figsize=(15.2, 8.8))
        self.figure.canvas.manager.set_window_title("Neuro-Motion Shoulder Workspace")
        self.figure.patch.set_facecolor("#edf2e7")

        self.scene_ax = self.figure.add_axes([0.05, 0.10, 0.56, 0.82], projection="3d")
        self.scene_ax.set_facecolor("#f8f7f2")
        self._style_scene_axes()

        self.panel_ax = self.figure.add_axes([0.66, 0.06, 0.31, 0.88])
        self.panel_ax.axis("off")
        self.panel_ax.set_facecolor("#fffaf2")
        self._build_panel_labels()

        self.slider_axes: dict[str, plt.Axes] = {}
        self.sliders: dict[str, Slider] = {}
        self._build_sliders()
        self._build_buttons()

        self.status_artist = self.panel_ax.text(
            0.02,
            0.89,
            "",
            fontsize=14,
            fontweight="bold",
            color="#16211d",
            transform=self.panel_ax.transAxes,
            va="top",
        )
        self.playback_artist = self.panel_ax.text(
            0.02,
            0.82,
            "",
            fontsize=10,
            color="#536356",
            transform=self.panel_ax.transAxes,
            va="top",
            linespacing=1.35,
        )
        self.metric_artist = self.panel_ax.text(
            0.02,
            0.68,
            "",
            fontsize=11,
            color="#536356",
            transform=self.panel_ax.transAxes,
            va="top",
            linespacing=1.35,
        )
        self.snap_indicator_label = self.panel_ax.text(
            0.76,
            0.975,
            "Snap",
            fontsize=11,
            color="#536356",
            transform=self.panel_ax.transAxes,
            va="center",
            ha="right",
        )
        self.snap_indicator = self.panel_ax.scatter(
            [0.82],
            [0.975],
            s=190,
            c=["#c85d3d"],
            edgecolors="#f8f7f2",
            linewidths=1.6,
            transform=self.panel_ax.transAxes,
            zorder=5,
        )

        self.timer = self.figure.canvas.new_timer(interval=33)
        self.timer.single_shot = True
        self.timer.add_callback(self._advance_playback)

        if self.playback_frames:
            self._apply_playback_frame(0)
        else:
            self.redraw()

    def _style_scene_axes(self) -> None:
        self.scene_ax.set_xlim(-SCENE_RADIUS, SCENE_RADIUS)
        self.scene_ax.set_ylim(-SCENE_RADIUS, SCENE_RADIUS)
        self.scene_ax.set_zlim(-SCENE_RADIUS, SCENE_RADIUS)
        self.scene_ax.set_box_aspect((1.25, 1.0, 1.0))
        self.scene_ax.view_init(elev=18, azim=-58)
        self.scene_ax.set_xticks([])
        self.scene_ax.set_yticks([])
        self.scene_ax.set_zticks([])
        self.scene_ax.grid(False)
        self.scene_ax.set_xlabel("")
        self.scene_ax.set_ylabel("")
        self.scene_ax.set_zlabel("")
        self.scene_ax.set_title("3D Demo", fontsize=18, pad=14, color="#16211d")

    def _build_panel_labels(self) -> None:
        self.panel_ax.text(
            0.02,
            0.98,
            "Shoulder Playback",
            fontsize=20,
            fontweight="bold",
            color="#16211d",
            transform=self.panel_ax.transAxes,
            va="top",
        )

    def _build_sliders(self) -> None:
        slider_specs = [
            ("phi_deg", "Phi", *POSE_LIMITS["phi"], self.state.phi_deg, 0.31),
            ("theta_deg", "Theta", *POSE_LIMITS["theta"], self.state.theta_deg, 0.23),
        ]

        for key, label, minimum, maximum, value, y in slider_specs:
            slider_ax = self.figure.add_axes([0.72, y, 0.23, 0.034], facecolor="#f5f0e5")
            self.slider_axes[key] = slider_ax
            slider = Slider(slider_ax, label, minimum, maximum, valinit=value, valstep=1)
            slider.label.set_color("#16211d")
            slider.valtext.set_color("#16211d")
            slider.on_changed(lambda raw, slider_key=key: self._on_slider(slider_key, raw))
            self.sliders[key] = slider

    def _build_buttons(self) -> None:
        self.play_button_ax = self.figure.add_axes([0.70, 0.49, 0.085, 0.05])
        self.replay_button_ax = self.figure.add_axes([0.81, 0.49, 0.09, 0.05])
        self.reset_button_ax = self.figure.add_axes([0.92, 0.49, 0.075, 0.05])

        self.play_button = Button(self.play_button_ax, "Play")
        self.replay_button = Button(self.replay_button_ax, "Replay")
        self.reset_button = Button(self.reset_button_ax, "Reset")

        self.play_button.on_clicked(self._toggle_playback)
        self.replay_button.on_clicked(self._replay)
        self.reset_button.on_clicked(self._reset)

    def _on_slider(self, key: str, raw_value: float) -> None:
        value = float(raw_value)
        setattr(self.state, key, value)

        if self.syncing_pose_sliders:
            return

        if key in {"phi_deg", "theta_deg"} and self.playback_active:
            self._stop_playback()

        self.redraw()

    def _toggle_playback(self, _event: object) -> None:
        if not self.playback_frames:
            return
        if self.playback_active:
            self._stop_playback()
            return
        self.playback_active = True
        self.play_button.label.set_text("Pause")
        self._schedule_next_frame()

    def _stop_playback(self) -> None:
        self.playback_active = False
        self.timer.stop()
        self.play_button.label.set_text("Play")
        self.figure.canvas.draw_idle()

    def _replay(self, _event: object) -> None:
        if not self.playback_frames:
            return
        self.playback_index = 0
        self._apply_playback_frame(0)
        self.playback_active = True
        self.play_button.label.set_text("Pause")
        self._schedule_next_frame()

    def _reset(self, _event: object) -> None:
        self._stop_playback()
        self.state.phi_min_deg = 15.0
        self.state.phi_max_deg = 165.0
        self.state.theta_min_deg = -45.0
        self.state.theta_max_deg = 45.0
        self.playback_index = 0
        if self.playback_frames:
            self._apply_playback_frame(0)
        else:
            self.state.phi_deg = 90.0
            self.state.theta_deg = 0.0
            self._sync_all_sliders()
            self.redraw()

    def _schedule_next_frame(self) -> None:
        if not self.playback_active or self.playback_index >= len(self.playback_frames) - 1:
            self._stop_playback()
            return
        current_frame = self.playback_frames[self.playback_index]
        next_frame = self.playback_frames[self.playback_index + 1]
        interval_ms = max(15, int((next_frame.time - current_frame.time) * 1000))
        self.timer.interval = interval_ms
        self.timer.start()

    def _advance_playback(self) -> None:
        if not self.playback_active:
            return
        next_index = self.playback_index + 1
        if next_index >= len(self.playback_frames):
            self._stop_playback()
            return
        self._apply_playback_frame(next_index)
        self._schedule_next_frame()

    def _apply_playback_frame(self, index: int) -> None:
        frame = self.playback_frames[index]
        self.playback_index = index
        self.state.phi_deg = frame.phi_deg
        self.state.theta_deg = frame.theta_deg
        self._sync_pose_sliders()
        self.redraw()

    def _sync_pose_sliders(self) -> None:
        self.syncing_pose_sliders = True
        self.sliders["phi_deg"].set_val(self.state.phi_deg)
        self.sliders["theta_deg"].set_val(self.state.theta_deg)
        self.syncing_pose_sliders = False

    def _sync_all_sliders(self) -> None:
        self.syncing_pose_sliders = True
        self.sliders["phi_deg"].set_val(self.state.phi_deg)
        self.sliders["theta_deg"].set_val(self.state.theta_deg)
        self.syncing_pose_sliders = False

    def redraw(self) -> None:
        self.scene_ax.cla()
        self._style_scene_axes()
        self._draw_floor()
        self._draw_safe_envelope()
        self._draw_arm()
        self._draw_scene_overlay()
        self._update_panel_text()
        self.figure.canvas.draw_idle()

    def _draw_floor(self) -> None:
        floor_angles = np.linspace(0, 2 * np.pi, 120)
        floor_x = np.cos(floor_angles) * 2.8
        floor_y = np.sin(floor_angles) * 2.8
        floor_z = np.full_like(floor_x, -2.0)
        self.scene_ax.plot_trisurf(floor_x, floor_y, floor_z, color="#eef1ea", alpha=0.55, linewidth=0)

    def _draw_safe_envelope(self) -> None:
        x, y, z = build_safe_envelope(self.state)
        self.scene_ax.plot_surface(
            x,
            z,
            y,
            color="#1c8276",
            alpha=0.14,
            linewidth=0,
            antialiased=True,
            shade=False,
        )
        self.scene_ax.plot_wireframe(
            x,
            z,
            y,
            rstride=4,
            cstride=4,
            color="#1c8276",
            linewidth=0.6,
            alpha=0.30,
        )

    def _draw_arm(self) -> None:
        shoulder, elbow = compute_arm_points(self.state.phi_deg, self.state.theta_deg)
        safe = pose_is_safe(self.state)
        current_frame = self.playback_frames[self.playback_index] if self.playback_frames else None
        arm_color = "#c85d3d" if current_frame and current_frame.snap else ("#1c8276" if safe else "#c85d3d")
        sensor_color = "#205f8d" if current_frame and not current_frame.snap else "#aa4a2b"

        x_points = [shoulder[0], elbow[0]]
        y_points = [shoulder[2], elbow[2]]
        z_points = [shoulder[1], elbow[1]]

        self.scene_ax.plot(
            x_points,
            y_points,
            z_points,
            color=arm_color,
            linewidth=14,
            solid_capstyle="round",
        )
        self.scene_ax.scatter(
            [shoulder[0], elbow[0]],
            [shoulder[2], elbow[2]],
            [shoulder[1], elbow[1]],
            s=[420, 280],
            c=[arm_color, arm_color],
            alpha=0.94,
            edgecolors="#f8f7f2",
            linewidths=1.8,
        )

        direction = elbow - shoulder
        sensor_end = shoulder + direction * SENSOR_LENGTH_RATIO
        sensor_center = shoulder + direction * SENSOR_OFFSET_RATIO
        self.scene_ax.plot(
            [shoulder[0], sensor_end[0]],
            [shoulder[2], sensor_end[2]],
            [shoulder[1], sensor_end[1]],
            color=sensor_color,
            linewidth=7,
            alpha=0.92,
            solid_capstyle="round",
        )
        self.scene_ax.scatter(
            [sensor_center[0]],
            [sensor_center[2]],
            [sensor_center[1]],
            s=SENSOR_MARKER_SIZE,
            c=[sensor_color],
            alpha=0.9,
            edgecolors="#f8f7f2",
            linewidths=1.4,
        )

    def _draw_scene_overlay(self) -> None:
        if not self.playback_frames:
            return

        current = self.playback_frames[self.playback_index]
        current_oob_count = self.snap_oob_prefix_counts[self.playback_index]
        current_other_count = self.snap_other_prefix_counts[self.playback_index]
        snap_state = "SNAP" if current.snap else "Monitoring"
        overlay_text = "\n".join(
            [
                f"Snaps {current.cumulative_snaps}",
                f"OOB {current_oob_count} | Other {current_other_count}",
                snap_state,
            ]
        )
        self.scene_ax.text2D(
            0.03,
            0.94,
            overlay_text,
            transform=self.scene_ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            color="#16211d",
            bbox={
                "boxstyle": "round,pad=0.45",
                "facecolor": "#fffaf2",
                "edgecolor": "#d6ddd0",
                "alpha": 0.92,
            },
        )

    def _update_panel_text(self) -> None:
        safe = pose_is_safe(self.state)
        self.status_artist.set_text(format_status(self.state))
        self.status_artist.set_color("#16211d" if safe else "#c85d3d")

        if self.playback_frames:
            current = self.playback_frames[self.playback_index]
            total_time = self.playback_frames[-1].time
            mode = "Playing" if self.playback_active else "Paused"
            self.playback_artist.set_text(
                "\n".join(
                    [
                        f"{mode}  |  t {current.time:.2f}s / {total_time:.2f}s",
                        f"|a| {current.abs_accel:.2f} m/s²",
                        "Snap detected" if current.snap else "No snap at current frame",
                    ]
                )
            )
            self.snap_indicator.set_facecolor("#205f8d" if current.snap else "#c85d3d")
        else:
            self.playback_artist.set_text("No playback file loaded")
            self.snap_indicator.set_facecolor("#c85d3d")

        self.metric_artist.set_text(
            "\n".join(
                [
                    f"Phi {self.state.phi_deg:.0f}°  |  Theta {self.state.theta_deg:.0f}°",
                    f"Phi safe {self.state.phi_min_deg:.0f}° to {self.state.phi_max_deg:.0f}°",
                    f"Theta safe {self.state.theta_min_deg:.0f}° to {self.state.theta_max_deg:.0f}°",
                ]
            )
        )

    def save_preview(self, output_path: Path) -> None:
        self.redraw()
        self.figure.savefig(output_path, dpi=160, bbox_inches="tight")

    def run(self) -> None:
        plt.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desktop shoulder ROM workspace with Phyphox playback.")
    parser.add_argument(
        "--save-preview",
        type=Path,
        help="Render a preview image to disk instead of opening the desktop window.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to a Phyphox acceleration CSV file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv.resolve() if args.csv else None
    playback_frames: list[MotionFrame] = []

    if csv_path and csv_path.exists():
        sensor_frames = parse_phyphox_csv(csv_path)
        backend_frames: list[BackendSnapFrame] | None = None
        try:
            backend_frames = load_cpp_snap_frames(csv_path)
            if len(backend_frames) != len(sensor_frames):
                print(
                    f"C++ backend frame count mismatch ({len(backend_frames)} vs {len(sensor_frames)}). "
                    "Falling back to Python snap detection."
                )
                backend_frames = None
        except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
            print(f"C++ backend unavailable, using Python snap detection: {error}")

        playback_frames = derive_motion_frames(sensor_frames, backend_frames)

    initial_state = PoseState()
    if playback_frames:
        initial_state.phi_deg = playback_frames[0].phi_deg
        initial_state.theta_deg = playback_frames[0].theta_deg

    app = ShoulderWorkspaceApp(initial_state, playback_frames, csv_path if playback_frames else None)

    if args.save_preview:
        args.save_preview.parent.mkdir(parents=True, exist_ok=True)
        app.save_preview(args.save_preview)
        print(f"Saved desktop playback preview to {args.save_preview}")
        return

    app.run()


if __name__ == "__main__":
    main()
