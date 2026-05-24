import { ContactShadows, OrbitControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { useEffect } from "react";
import { Vector3 } from "three";
import type { SceneTheme } from "../types/presentation";
import { JointModel, type ShoulderWorkspacePose } from "./JointModel";

interface PresentationSceneProps {
  pose: ShoulderWorkspacePose;
  theme: SceneTheme;
}

function CameraSetup() {
  const { camera } = useThree();

  useEffect(() => {
    camera.position.set(4.8, 2.2, 5.4);
    camera.lookAt(new Vector3(0, 0.95, 0));
    camera.updateProjectionMatrix();
  }, [camera]);

  return null;
}

export function PresentationScene({ pose, theme }: PresentationSceneProps) {
  return (
    <>
      <color attach="background" args={[theme.background]} />
      <fog attach="fog" args={[theme.background, 10, 18]} />
      <ambientLight intensity={1.4} />
      <hemisphereLight intensity={0.88} groundColor="#d7ddd2" color="#fffdf8" />
      <directionalLight
        position={[6.5, 7.5, 5.5]}
        intensity={2.5}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-5, 3.5, -4]} intensity={0.55} color="#d7f1f0" />

      <JointModel pose={pose} theme={theme} />

      <ContactShadows
        position={[0, -0.18, 0]}
        opacity={0.24}
        scale={9.8}
        blur={2}
        far={6}
        color="#78807b"
      />
      <CameraSetup />
      <OrbitControls
        enablePan={false}
        target={[0, 0.95, 0]}
        minDistance={3.2}
        maxDistance={9}
        minPolarAngle={0.5}
        maxPolarAngle={2.25}
      />
    </>
  );
}
