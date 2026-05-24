import type { JointProfile, MotionState, SceneTheme } from "../types/presentation";

interface FallbackPanelProps {
  joint: JointProfile;
  motionState: MotionState;
  theme: SceneTheme;
}

function polar(cx: number, cy: number, radius: number, degrees: number) {
  const radians = (degrees * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy - radius * Math.sin(radians)
  };
}

function arcPath(cx: number, cy: number, radius: number, endDegrees: number) {
  const start = polar(cx, cy, radius, 180);
  const end = polar(cx, cy, radius, 180 - endDegrees);
  const largeArc = endDegrees > 180 ? "1" : "0";

  return `M ${start.x.toFixed(2)} ${start.y.toFixed(2)} A ${radius} ${radius} 0 ${largeArc} 0 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`;
}

export function FallbackPanel({
  joint,
  motionState,
  theme
}: FallbackPanelProps) {
  const visualMax = joint.modelMaxDeg;
  const normalSweep = (joint.referenceMaxDeg / visualMax) * 180;
  const hsdSweep = (joint.modelMaxDeg / visualMax) * 180;
  const currentSweep = (motionState.currentElevationDeg / visualMax) * 180;
  const statusClassName = motionState.isBeyondNormal ? "fallback-card is-warning" : "fallback-card";

  return (
    <div className={statusClassName}>
      <div className="fallback-card__copy">
        <p className="eyebrow">2D fallback</p>
        <h3>Shoulder workspace</h3>
        <p>WebGL is unavailable on this device, so the pose is shown as a simple elevation gauge.</p>
      </div>

      <svg viewBox="0 0 320 220" className="fallback-card__gauge" role="img" aria-label="2D ROM fallback gauge">
        <path d={arcPath(160, 180, 108, 180)} className="fallback-arc fallback-arc--base" />
        <path d={arcPath(160, 180, 108, normalSweep)} className="fallback-arc fallback-arc--normal" />
        <path d={arcPath(160, 180, 122, hsdSweep)} className="fallback-arc fallback-arc--hsd" />
        <line
          x1="160"
          y1="180"
          x2={polar(160, 180, 96, 180 - currentSweep).x}
          y2={polar(160, 180, 96, 180 - currentSweep).y}
          stroke={motionState.isBeyondNormal ? theme.danger : theme.text}
          strokeWidth="7"
          strokeLinecap="round"
        />
        <circle cx="160" cy="180" r="10" fill={theme.text} />
        <text x="160" y="208" textAnchor="middle" className="fallback-card__label">
          {joint.label}
        </text>
      </svg>

      <div className="fallback-card__metrics">
        <div>
          <span>Phi</span>
          <strong>{Math.round(motionState.currentElevationDeg)}°</strong>
        </div>
        <div>
          <span>Reference max</span>
          <strong>{joint.referenceMaxDeg}°</strong>
        </div>
        <div>
          <span>Over reference</span>
          <strong>{Math.round(motionState.overageDeg)}°</strong>
        </div>
      </div>
    </div>
  );
}
