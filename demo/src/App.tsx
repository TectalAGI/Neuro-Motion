import { lazy, Suspense, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { CanvasLoader } from "./components/CanvasLoader";
import { FallbackPanel } from "./components/FallbackPanel";
import { sceneTheme } from "./data/presentation";
import type { ShoulderWorkspacePose } from "./components/JointModel";

const LazyPresentationScene = lazy(async () => {
  const module = await import("./components/PresentationScene");
  return { default: module.PresentationScene };
});

function supportsWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      canvas.getContext("webgl") || canvas.getContext("experimental-webgl") || canvas.getContext("webgl2")
    );
  } catch {
    return false;
  }
}

const INITIAL_POSE: ShoulderWorkspacePose = {
  thetaDeg: 0,
  phiDeg: 90,
  axialRollDeg: 0
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export default function App() {
  const [pose, setPose] = useState<ShoulderWorkspacePose>(INITIAL_POSE);
  const [webglEnabled] = useState(() => supportsWebGL());

  const metrics = useMemo(
    () => ({
      thetaDeg: Math.round(pose.thetaDeg),
      phiDeg: Math.round(pose.phiDeg),
      axialRollDeg: Math.round(pose.axialRollDeg)
    }),
    [pose]
  );

  function updatePose<K extends keyof ShoulderWorkspacePose>(key: K, value: number) {
    setPose((current) => ({
      ...current,
      [key]: value
    }));
  }

  return (
    <div className="page-shell">
      <main className="workspace-shell">
        <aside className="panel workspace-controls">
          <div className="workspace-controls__header">
            <p className="eyebrow">Shoulder workspace</p>
            <h1>Upper arm</h1>
          </div>

          <div className="control-grid">
            <label className="field">
              <div className="field-row">
                <span>Phi</span>
                <strong>{metrics.phiDeg}°</strong>
              </div>
              <input
                type="range"
                min="0"
                max="180"
                step="1"
                value={pose.phiDeg}
                onInput={(event) => updatePose("phiDeg", clamp(Number(event.currentTarget.value), 0, 180))}
              />
            </label>

            <label className="field">
              <div className="field-row">
                <span>Theta</span>
                <strong>{metrics.thetaDeg}°</strong>
              </div>
              <input
                type="range"
                min="-150"
                max="150"
                step="1"
                value={pose.thetaDeg}
                onInput={(event) => updatePose("thetaDeg", clamp(Number(event.currentTarget.value), -150, 150))}
              />
            </label>

            <label className="field">
              <div className="field-row">
                <span>Axial roll</span>
                <strong>{metrics.axialRollDeg}°</strong>
              </div>
              <input
                type="range"
                min="-180"
                max="180"
                step="1"
                value={pose.axialRollDeg}
                onInput={(event) => updatePose("axialRollDeg", clamp(Number(event.currentTarget.value), -180, 180))}
              />
            </label>

          </div>

          <div className="metrics-panel metrics-panel--angles">
            <div>
              <span>Phi</span>
              <strong>{metrics.phiDeg}°</strong>
            </div>
            <div>
              <span>Theta</span>
              <strong>{metrics.thetaDeg}°</strong>
            </div>
            <div>
              <span>Roll</span>
              <strong>{metrics.axialRollDeg}°</strong>
            </div>
          </div>
        </aside>

        <section className="panel workspace-scene">
          <div className="workspace-scene__header">
            <p className="eyebrow">3D view</p>
            <span>Scroll to zoom. Drag to orbit.</span>
          </div>

          <div className="scene-stage scene-stage--clean">
            {webglEnabled ? (
              <div className="scene-canvas">
                <Canvas
                  shadows
                  dpr={[1, 1.75]}
                  style={{ width: "100%", height: "100%" }}
                  camera={{ position: [4.8, 2.2, 5.4], fov: 32 }}
                >
                  <Suspense fallback={<CanvasLoader />}>
                    <LazyPresentationScene pose={pose} theme={sceneTheme} />
                  </Suspense>
                </Canvas>
              </div>
            ) : (
              <FallbackPanel
                joint={{
                  id: "shoulder",
                  label: "Upper arm",
                  axis: { pitch: "x" },
                  referenceMaxDeg: 180,
                  modelMaxDeg: 180,
                  sourceLabel: "Browser controls",
                  note: ""
                }}
                motionState={{
                  currentElevationDeg: pose.phiDeg,
                  targetElevationDeg: pose.phiDeg,
                  normalizedProgress: pose.phiDeg / 180,
                  isBeyondNormal: false,
                  overageDeg: 0
                }}
                theme={sceneTheme}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
