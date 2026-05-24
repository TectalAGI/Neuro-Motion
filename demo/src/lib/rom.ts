import type { JointProfile, MotionState } from "../types/presentation";

export function clampElevation(value: number, max: number) {
  return Math.min(max, Math.max(0, value));
}

export function createMotionState(
  profile: JointProfile,
  currentElevationDeg: number,
  targetElevationDeg: number
): MotionState {
  const ceiling = profile.modelMaxDeg;
  const clampedCurrent = clampElevation(currentElevationDeg, ceiling);
  const overageDeg = Math.max(0, clampedCurrent - profile.referenceMaxDeg);

  return {
    currentElevationDeg: clampedCurrent,
    targetElevationDeg,
    normalizedProgress: ceiling <= 0 ? 0 : clampedCurrent / ceiling,
    isBeyondNormal: clampedCurrent > profile.referenceMaxDeg,
    overageDeg
  };
}

export function degreesToRadians(degrees: number) {
  return (degrees * Math.PI) / 180;
}
