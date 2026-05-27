# Neuro-Motion
A biologically inspired, neuromorphic control model designed to predict and reduce joint instability in people with hypermobility (hsd) using low-latency. Scalable to real hardware.

## Desktop app

The active shoulder ROM prototype is a desktop-only workspace in `mujoco_arm_demo/desktop_shoulder_workspace.py`. It uses Python, NumPy, and Matplotlib.

### Run the desktop app

```bash
python3 -m venv .venv
.venv/bin/pip install -r mujoco_arm_demo/desktop_requirements.txt
.venv/bin/python mujoco_arm_demo/desktop_shoulder_workspace.py
```

The desktop app includes:

- a native 3D shoulder workspace window
- `phi` and `theta` controls
- editable safe-range parameters
- bundled playback of `mujoco_arm_demo/data/JayceArmData1.csv`
- safe / outside-safe range feedback without using `npm` or a web browser

The bundled playback source came from Phyphox running on an iPhone 17 Pro Max mounted on the lateral shoulder, with the top of the phone toward the shoulder and the bottom toward the elbow.

On Windows, you can also double-click `run_desktop_app.bat` from the repository root after Python is installed.

## MuJoCo viewer

If you want the native MuJoCo viewer instead of the desktop controller, run:

```bash
python3 -m venv .venv
.venv/bin/pip install -r mujoco_arm_demo/requirements.txt
.venv/bin/mjpython mujoco_arm_demo/run_arm.py
```

On macOS, `run_arm.py` must be launched with `mjpython` so MuJoCo can open the passive viewer on the main thread.
