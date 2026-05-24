import { useMemo } from "react";
import { Matrix4, Quaternion, Vector3 } from "three";
import type { SceneTheme } from "../types/presentation";

export interface ShoulderWorkspacePose {
  thetaDeg: number;
  phiDeg: number;
  axialRollDeg: number;
}

interface JointModelProps {
  pose: ShoulderWorkspacePose;
  theme: SceneTheme;
}

const Y_AXIS = new Vector3(0, 1, 0);

function degreesToRadians(degrees: number) {
  return (degrees * Math.PI) / 180;
}

function makeSegmentTransform(start: Vector3, end: Vector3) {
  const direction = end.clone().sub(start);
  const length = direction.length();
  const midpoint = start.clone().addScaledVector(direction, 0.5);
  const quaternion = new Quaternion().setFromUnitVectors(Y_AXIS, direction.clone().normalize());
  const matrix = new Matrix4().compose(midpoint, quaternion, new Vector3(1, length, 1));

  return { matrix, direction: direction.normalize() };
}

export function JointModel({ pose, theme }: JointModelProps) {
  const model = useMemo(() => {
    const shoulder = new Vector3(0, 1.18, 0);
    const upperArmLength = 2.25;

    const phi = degreesToRadians(pose.phiDeg);
    const theta = degreesToRadians(pose.thetaDeg);
    const axialRoll = degreesToRadians(pose.axialRollDeg);

    const upperDirection = new Vector3(
      Math.sin(theta) * Math.sin(phi),
      -Math.cos(phi),
      Math.cos(theta) * Math.sin(phi)
    ).normalize();

    const elbow = shoulder.clone().addScaledVector(upperDirection, upperArmLength);
    const upperArm = makeSegmentTransform(shoulder, elbow);
    const humeralHeadOrientation = new Quaternion()
      .setFromUnitVectors(Y_AXIS, upperArm.direction)
      .multiply(new Quaternion().setFromAxisAngle(upperArm.direction, axialRoll));

    return {
      shoulder,
      elbow,
      upperArm,
      humeralHeadOrientation
    };
  }, [pose]);

  return (
    <group>
      <mesh position={[0, -0.24, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[5.8, 96]} />
        <meshStandardMaterial color="#dfe8de" transparent opacity={0.76} />
      </mesh>

      <group position={[-0.95, 1.08, -0.16]}>
        <mesh castShadow>
          <capsuleGeometry args={[0.3, 1.45, 8, 22]} />
          <meshStandardMaterial color={theme.bone} metalness={0.12} roughness={0.54} />
        </mesh>
        <mesh position={[0.82, -0.92, 0.08]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <capsuleGeometry args={[0.26, 0.95, 8, 20]} />
          <meshStandardMaterial color={theme.bone} metalness={0.1} roughness={0.56} />
        </mesh>
      </group>

      <mesh position={model.shoulder} castShadow>
        <sphereGeometry args={[0.34, 32, 32]} />
        <meshStandardMaterial
          color={theme.bone}
          emissive={theme.glow}
          emissiveIntensity={0.28}
          metalness={0.12}
          roughness={0.42}
        />
      </mesh>

      <mesh matrix={model.upperArm.matrix} matrixAutoUpdate={false} castShadow>
        <capsuleGeometry args={[0.23, 1, 10, 24]} />
        <meshStandardMaterial color={theme.bone} metalness={0.14} roughness={0.46} />
      </mesh>

      <mesh position={model.elbow} quaternion={model.humeralHeadOrientation} castShadow>
        <capsuleGeometry args={[0.12, 0.32, 8, 18]} />
        <meshStandardMaterial color={theme.bone} metalness={0.1} roughness={0.5} />
      </mesh>
    </group>
  );
}
