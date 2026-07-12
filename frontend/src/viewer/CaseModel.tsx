import { Html, useGLTF } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { ModelMeta, Projected } from "../types";
import { myomaColor, myomaOrder } from "./palette";

interface MyomaPart {
  id: string;
  geometry: THREE.BufferGeometry;
  centroid: THREE.Vector3;
}

interface Props {
  url: string;
  selected: string | null;
  onSelect: (id: string | null) => void;
  onReady: (meta: ModelMeta) => void;
  onProject: (points: Projected[]) => void;
}

// A dimmed myoma is muted toward the stage grey rather than made transparent: the
// frosted wall only refracts opaque geometry, so a transparent myoma would vanish.
const MUTED = new THREE.Color("#2f343c");

// Pull the named nodes out of the GLB and bake world transforms into geometry so
// wall, cavity and every myoma share one coordinate frame.
function useCaseParts(url: string) {
  const { scene } = useGLTF(url);

  return useMemo(() => {
    const wall: THREE.BufferGeometry[] = [];
    const cavity: THREE.BufferGeometry[] = [];
    const myomas: MyomaPart[] = [];

    scene.updateMatrixWorld(true);
    scene.traverse((object) => {
      const mesh = object as THREE.Mesh;
      if (!mesh.isMesh || !mesh.geometry) return;

      const geometry = mesh.geometry.clone();
      geometry.applyMatrix4(mesh.matrixWorld);
      geometry.computeVertexNormals();
      geometry.computeBoundingBox();

      const name = mesh.name.toLowerCase();
      if (name.includes("myoma")) {
        const centroid = new THREE.Vector3();
        geometry.boundingBox?.getCenter(centroid);
        myomas.push({ id: mesh.name, geometry, centroid });
      } else if (name.includes("cavity")) cavity.push(geometry);
      else if (name.includes("wall")) wall.push(geometry);
    });

    myomas.sort((a, b) => myomaOrder(a.id) - myomaOrder(b.id));

    const box = new THREE.Box3();
    for (const g of [...wall, ...cavity, ...myomas.map((m) => m.geometry)]) {
      if (g.boundingBox) box.union(g.boundingBox);
    }
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    return { wall, cavity, myomas, center, size };
  }, [scene]);
}

// A true-to-scale reference bar sitting under the model, in millimeters.
function ScaleBar({ y, length }: { y: number; length: number }) {
  return (
    <group position={[0, y, 0]}>
      <mesh>
        <boxGeometry args={[length, 1.2, 1.2]} />
        <meshBasicMaterial color="#6d7481" toneMapped={false} />
      </mesh>
      {[-length / 2, length / 2].map((x) => (
        <mesh key={x} position={[x, 3, 0]}>
          <boxGeometry args={[1.2, 7, 1.2]} />
          <meshBasicMaterial color="#6d7481" toneMapped={false} />
        </mesh>
      ))}
      <Html center position={[0, -6, 0]} style={{ pointerEvents: "none" }}>
        <span className="figure whitespace-nowrap text-[10px] tracking-[0.1em] text-fg3">
          {length} mm
        </span>
      </Html>
    </group>
  );
}

export default function CaseModel({ url, selected, onSelect, onReady, onProject }: Props) {
  const { wall, cavity, myomas, center, size } = useCaseParts(url);
  const [hovered, setHovered] = useState<string | null>(null);

  const meshRefs = useRef<Record<string, THREE.Mesh>>({});
  const camera = useThree((state) => state.camera);
  const viewport = useThree((state) => state.size);
  const scratch = useMemo(() => new THREE.Vector3(), []);
  const lastKey = useRef("");

  useEffect(() => {
    onReady({
      myomaIds: myomas.map((m) => m.id),
      sizeMm: [size.x, size.y, size.z],
      hasWall: wall.length > 0,
      hasCavity: cavity.length > 0,
    });
  }, [myomas, size, wall.length, cavity.length, onReady]);

  useEffect(() => {
    document.body.style.cursor = hovered ? "pointer" : "auto";
    return () => {
      document.body.style.cursor = "auto";
    };
  }, [hovered]);

  // Project each myoma centroid to screen space so the overlay can anchor its card.
  // Uses matrixWorld, so any camera fitting applied above is accounted for. State is
  // pushed only when a projected pixel actually moves, so an idle scene is quiet.
  useFrame(() => {
    const points: Projected[] = [];
    for (const part of myomas) {
      const mesh = meshRefs.current[part.id];
      if (!mesh) continue;
      scratch.copy(part.centroid).applyMatrix4(mesh.matrixWorld).project(camera);
      points.push({
        id: part.id,
        x: (scratch.x * 0.5 + 0.5) * viewport.width,
        y: (scratch.y * -0.5 + 0.5) * viewport.height,
        visible: scratch.z < 1,
      });
    }
    const key = points.map((p) => `${p.id}:${p.x | 0}:${p.y | 0}:${p.visible ? 1 : 0}`).join("|");
    if (key !== lastKey.current) {
      lastKey.current = key;
      onProject(points);
    }
  });

  const floorY = -size.y / 2 - 10;

  return (
    <group position={[-center.x, -center.y, -center.z]}>
      {myomas.map((part, index) => {
        const isSelected = selected === part.id;
        const isHovered = hovered === part.id;
        const dimmed = selected !== null && !isSelected;
        const base = new THREE.Color(myomaColor(index));
        const shown = dimmed ? base.clone().lerp(MUTED, 0.62) : base;
        return (
          <mesh
            key={part.id}
            geometry={part.geometry}
            ref={(mesh) => {
              if (mesh) meshRefs.current[part.id] = mesh;
            }}
            onPointerOver={(event) => {
              event.stopPropagation();
              setHovered(part.id);
            }}
            onPointerOut={() => setHovered(null)}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(isSelected ? null : part.id);
            }}
          >
            {/* Held to a modest environment response, so a myoma reads as the colour on
                its card rather than picking up the cool studio. */}
            <meshPhysicalMaterial
              color={shown}
              roughness={dimmed ? 0.62 : 0.45}
              metalness={0}
              clearcoat={0.3}
              clearcoatRoughness={0.5}
              envMapIntensity={dimmed ? 0.4 : 0.85}
              emissive={base}
              emissiveIntensity={isSelected ? 0.22 : isHovered ? 0.09 : 0}
            />
          </mesh>
        );
      })}

      {/* Opaque so it stays visible through the frosted wall. */}
      {cavity.map((geometry, index) => (
        <mesh key={`cavity-${index}`} geometry={geometry}>
          <meshPhysicalMaterial
            color="#b9ae9c"
            roughness={0.85}
            metalness={0}
            clearcoat={0.08}
            envMapIntensity={0.35}
          />
        </mesh>
      ))}

      {/* Frosted glass organ. Front faces only: the shell is carved around every myoma,
          and its inner surfaces face away from the camera, so culling them keeps the
          glass clean and the opaque myomas read straight through it.

          Deliberately not a transmission material. Physical transmission samples a buffer
          that excludes the scene background, so the shell transmits black, and a real
          index of refraction smears the view through a jagged marching-cubes surface.
          A matte, low-opacity surface with a crisp clearcoat gives the frost and the edge
          highlights without either failure. */}
      {wall.map((geometry, index) => (
        <mesh key={`wall-${index}`} geometry={geometry}>
          <meshPhysicalMaterial
            color="#e9eaec"
            transparent
            opacity={0.4}
            roughness={0.44}
            metalness={0}
            clearcoat={1}
            clearcoatRoughness={0.16}
            specularIntensity={1}
            // A neutral milky core. On a dark stage a translucent shell only ever darkens
            // what is behind it, so the wall has to carry its own brightness to read as a
            // light shell rather than as stone. No tint, so it stays quiet.
            emissive={new THREE.Color("#9aa0a6")}
            emissiveIntensity={0.55}
            envMapIntensity={2}
            side={THREE.FrontSide}
            depthWrite={false}
          />
        </mesh>
      ))}

      <ScaleBar y={floorY} length={50} />
    </group>
  );
}
