export type JointId = "shoulder";

export type HighlightTarget = "joint" | "normal-range" | "hsd-range" | "warning";

export interface JointAxis {
  pitch: "x" | "y" | "z";
}

export interface JointProfile {
  id: JointId;
  label: string;
  axis: JointAxis;
  referenceMaxDeg: number;
  modelMaxDeg: number;
  sourceLabel: string;
  sourceUrl?: string;
  note: string;
}

export interface MotionState {
  currentElevationDeg: number;
  targetElevationDeg: number;
  normalizedProgress: number;
  isBeyondNormal: boolean;
  overageDeg: number;
}

export interface MotionPreset {
  jointId: JointId;
  startDeg: number;
  endDeg: number;
  durationMs: number;
  easing: string;
}

export interface CameraPose {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
}

export interface PresentationStep {
  id: string;
  title: string;
  body: string;
  sampleIndex: number;
  cameraPose: CameraPose;
  highlightTargets: HighlightTarget[];
  showWarning: boolean;
}

export interface SceneTheme {
  background: string;
  panel: string;
  panelEdge: string;
  text: string;
  muted: string;
  normal: string;
  hsd: string;
  danger: string;
  bone: string;
  glow: string;
}

export interface ShoulderPoseSample {
  index: number;
  joints: {
    shoulderPitchDeg: number;
    shoulderYawDeg: number;
    shoulderRollDeg: number;
    elbowFlexDeg: number;
    wristPitchDeg: number;
    wristYawDeg: number;
  };
  arm: {
    elevationDeg: number;
    direction: [number, number, number];
  };
  points: {
    shoulder: [number, number, number];
    elbow: [number, number, number];
    hand: [number, number, number];
  };
}

export interface MuJoCoShoulderDataset {
  modelName: string;
  sourceXml: string;
  referenceMaxElevationDeg: number;
  modelMaxElevationDeg: number;
  notes: string;
  namedSampleIndices: Record<string, number>;
  samples: ShoulderPoseSample[];
}
