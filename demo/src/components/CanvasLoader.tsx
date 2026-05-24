import { Html } from "@react-three/drei";

export function CanvasLoader() {
  return (
    <Html center>
      <div className="scene-loader">
        <div className="scene-loader__pulse" />
        <div>
          <p className="scene-loader__eyebrow">Preparing scene</p>
          <p className="scene-loader__title">Loading the shoulder presentation</p>
        </div>
      </div>
    </Html>
  );
}
