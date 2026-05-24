import shoulderMotionJson from "./mujocoShoulderMotion.json";
import type {
  JointProfile,
  MuJoCoShoulderDataset,
  PresentationStep,
  SceneTheme
} from "../types/presentation";

export const sceneTheme: SceneTheme = {
  background: "#edf2e7",
  panel: "rgba(255, 252, 246, 0.82)",
  panelEdge: "rgba(48, 75, 64, 0.12)",
  text: "#16211d",
  muted: "#536356",
  normal: "#1c8276",
  hsd: "#ca8d28",
  danger: "#c24d33",
  bone: "#f2eddc",
  glow: "#daf0e7"
};

export const shoulderDataset = shoulderMotionJson as unknown as MuJoCoShoulderDataset;

export const shoulderProfile: JointProfile = {
  id: "shoulder",
  label: "Upper-arm shoulder ROM",
  axis: {
    pitch: "x"
  },
  referenceMaxDeg: shoulderDataset.referenceMaxElevationDeg,
  modelMaxDeg: shoulderDataset.modelMaxElevationDeg,
  sourceLabel: "MuJoCo shoulder scaffold from arm.xml",
  note: shoulderDataset.notes
};

const named = shoulderDataset.namedSampleIndices;

export const presentationSteps: PresentationStep[] = [
  {
    id: "baseline",
    title: "Neutral MuJoCo pose",
    body: "Start from the MuJoCo shoulder neutral and establish the upper arm’s resting vector before moving through the spatial envelope.",
    sampleIndex: named.baseline,
    cameraPose: {
      position: [5.5, 2.7, 6.7],
      target: [0.05, 0.68, 0],
      fov: 32
    },
    highlightTargets: ["joint"],
    showWarning: false
  },
  {
    id: "forward-reach",
    title: "Forward reach sample",
    body: "Drive the browser arm from a MuJoCo-derived pitch-only pose so the viewer can see the sagittal lift in true 3D space.",
    sampleIndex: named.forward_reach,
    cameraPose: {
      position: [4.7, 2.1, 5.7],
      target: [0.0, 0.75, 0],
      fov: 29
    },
    highlightTargets: ["joint", "normal-range"],
    showWarning: false
  },
  {
    id: "reference-ceiling",
    title: "Reference ceiling",
    body: "Move to the MuJoCo sample that reaches the 90-degree reference band, giving us a clear baseline for upper-arm elevation in this scaffold.",
    sampleIndex: named.reference_ceiling,
    cameraPose: {
      position: [4.1, 1.75, 4.7],
      target: [0.0, 0.82, 0],
      fov: 26
    },
    highlightTargets: ["joint", "normal-range"],
    showWarning: false
  },
  {
    id: "model-limit",
    title: "3D model envelope limit",
    body: "Jump to the highest-elevation MuJoCo sample from the current shoulder scaffold and flag it as beyond the 90-degree reference band.",
    sampleIndex: named.model_limit,
    cameraPose: {
      position: [3.85, 1.5, 4.2],
      target: [0.15, 0.86, 0],
      fov: 24
    },
    highlightTargets: ["joint", "warning", "hsd-range"],
    showWarning: true
  }
];
