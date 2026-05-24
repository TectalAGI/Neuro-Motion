# Neuro-Motion
A biologically inspired, neuromorphic control model designed to predict and reduce joint instability in people with hypermobility (hsd) using low-latency. Scalable to real hardware.

## Shoulder ROM presentation demo

A browser-based 3D presentation prototype now lives in [demo](/Users/nyancho/Documents/Projects/Neuro-Motion/demo). It focuses on:

- upper-arm shoulder ROM rather than elbow ROM
- a premium browser presentation surface built with React, Vite, and React Three Fiber
- direct pose data exported from the MuJoCo scaffold in [mujoco_arm_demo/arm.xml](/Users/nyancho/Documents/Projects/Neuro-Motion/mujoco_arm_demo/arm.xml)
- a reference-band warning when the MuJoCo-derived upper-arm elevation exceeds the current scaffold baseline

### Run it locally

From the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r /Users/nyancho/Documents/Projects/Neuro-Motion/mujoco_arm_demo/requirements.txt
.venv/bin/python /Users/nyancho/Documents/Projects/Neuro-Motion/mujoco_arm_demo/export_shoulder_motion.py

cd /Users/nyancho/Documents/Projects/Neuro-Motion/demo
npm install
npm run dev
```

Then open [http://localhost:4173](http://localhost:4173).

### Notes on the defaults

The current prototype is driven by exported MuJoCo shoulder samples rather than a clinical flexion table. In its current form, the scaffold tops out at roughly 110 degrees of upper-arm elevation, so it should be treated as a shoulder-space prototype rather than a full 180-degree clinical shoulder-flexion model.
