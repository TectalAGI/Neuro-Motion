import type {
  JointProfile,
  MotionState,
  PresentationStep,
  ShoulderPoseSample
} from "../types/presentation";

interface AnnotationOverlayProps {
  joint: JointProfile;
  motionState: MotionState;
  activeStep: PresentationStep;
  poseSample: ShoulderPoseSample;
}

export function AnnotationOverlay({
  joint,
  motionState,
  activeStep,
  poseSample
}: AnnotationOverlayProps) {
  const cardClassName = motionState.isBeyondNormal
    ? "annotation-overlay__status is-warning"
    : "annotation-overlay__status";

  return (
    <div className="annotation-overlay">
      <div className="annotation-overlay__hero">
        <p className="eyebrow">Live scene readout</p>
        <h3>{activeStep.title}</h3>
        <p>{activeStep.body}</p>
      </div>

      <div className="annotation-overlay__chips">
        <span>{joint.label}</span>
        <span>Reference max {joint.referenceMaxDeg}°</span>
        <span>Model max {joint.modelMaxDeg}°</span>
      </div>

      <div className={cardClassName}>
        <div>
          <p>Status</p>
          <strong>
            {motionState.isBeyondNormal
              ? `Beyond normal by ${Math.round(motionState.overageDeg)}°`
              : "Within reference window"}
          </strong>
        </div>
        <div className="annotation-overlay__mini-metrics">
          <span>
            Elevation
            <strong>{Math.round(motionState.currentElevationDeg)}°</strong>
          </span>
          <span>
            Pitch / yaw / roll
            <strong>
              {Math.round(poseSample.joints.shoulderPitchDeg)}° / {Math.round(poseSample.joints.shoulderYawDeg)}° /{" "}
              {Math.round(poseSample.joints.shoulderRollDeg)}°
            </strong>
          </span>
        </div>
      </div>
    </div>
  );
}
