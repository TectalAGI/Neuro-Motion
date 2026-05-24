# Neuro-Motion
A biologically inspired, neuromorphic control model designed to predict and reduce joint instability in people with hypermobility (hsd) using low-latency. Scalable to real hardware.

## Shoulder ROM presentation demo

A browser-based 3D presentation prototype lives in `demo/`. It focuses on:

- upper-arm shoulder ROM rather than elbow ROM
- a premium browser presentation surface built with React, Vite, and React Three Fiber
- direct pose data exported from the MuJoCo scaffold in `mujoco_arm_demo/arm.xml`
- a reference-band warning when the MuJoCo-derived upper-arm elevation exceeds the current scaffold baseline

## Setup

These steps assume you are starting from the repository root.

### 1. Create the Python environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r mujoco_arm_demo/requirements.txt
```

### 2. Export MuJoCo shoulder data

```bash
.venv/bin/python mujoco_arm_demo/export_shoulder_motion.py
```

### 3. Start the 3D web app

```bash
cd demo
npm install
npm run dev
```

Then open [http://localhost:4173](http://localhost:4173) in a browser.

## MuJoCo viewer

If you want the native MuJoCo viewer instead of the web app, run:

```bash
.venv/bin/mjpython mujoco_arm_demo/run_arm.py
```

On macOS, `run_arm.py` must be launched with `mjpython` so MuJoCo can open the passive viewer on the main thread.

### Notes on the defaults

The current prototype is driven by exported MuJoCo shoulder samples rather than a clinical flexion table. In its current form, the scaffold tops out at roughly 110 degrees of upper-arm elevation, so it should be treated as a shoulder-space prototype rather than a full 180-degree clinical shoulder-flexion model.
