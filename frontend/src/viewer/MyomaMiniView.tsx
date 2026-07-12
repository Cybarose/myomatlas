import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import * as THREE from "three";
import { useCaseParts } from "./parts";

interface Props {
  url: string;
  myomaId: string;
  color: string;
}

const STAGE = "#15171d";
const FOV = 35;

// Clearance around the fitted lesion, as a multiple of its bounding radius.
const FIT_MARGIN = 1.18;

function fitDistance(radius: number): number {
  // Distance at which a sphere of this radius fits the vertical field of view. The mini
  // view is wider than it is tall, so the vertical axis is the binding one.
  const half = (FOV / 2) * (Math.PI / 180);
  return (radius / Math.sin(half)) * FIT_MARGIN;
}

function MiniModel({ part, color }: { part: THREE.BufferGeometry; color: string }) {
  return (
    <mesh geometry={part}>
      <meshPhysicalMaterial
        color={color}
        roughness={0.42}
        metalness={0}
        clearcoat={0.35}
        clearcoatRoughness={0.45}
        envMapIntensity={0.7}
        emissive={new THREE.Color(color)}
        emissiveIntensity={0.16}
      />
    </mesh>
  );
}

// The GLB is already in the drei cache, so this resolves without a fetch. Reading the
// geometry out here rather than inside the Canvas means the camera can be built with the
// right distance and clip planes up front, instead of being corrected one frame later.
function MiniScene({ url, myomaId, color }: Props) {
  const { myomas } = useCaseParts(url);
  const part = myomas.find((myoma) => myoma.id === myomaId);
  if (!part) return null;

  const geometry = part.geometry;
  if (!geometry.boundingSphere) geometry.computeBoundingSphere();
  const sphere = geometry.boundingSphere;

  // The group is centered on the bounding box, which is not exactly the bounding sphere
  // center, so carry that offset into the radius. This bounds the lesion in every
  // orientation, so the autorotate can never swing a lobe past the edge of the frame.
  const offset = sphere ? sphere.center.distanceTo(part.centroid) : 0;
  const radius = Math.max((sphere?.radius ?? 4) + offset, 2);

  const distance = fitDistance(radius);
  const position: [number, number, number] = [
    distance * 0.58,
    distance * 0.4,
    distance * 0.71,
  ];

  return (
    <Canvas
      key={myomaId}
      dpr={[1, 2]}
      gl={{ antialias: true }}
      camera={{
        fov: FOV,
        position,
        near: Math.max(0.01, distance - radius * 2),
        far: distance + radius * 6,
      }}
    >
      <color attach="background" args={[STAGE]} />
      <ambientLight intensity={0.55} color="#f2f3f5" />
      <hemisphereLight args={["#dfe3e8", "#2a2d33", 0.7]} />
      <directionalLight position={[60, 80, 60]} intensity={1.5} />
      <directionalLight position={[-60, 20, -40]} intensity={0.6} color="#e4e8ee" />

      <group position={[-part.centroid.x, -part.centroid.y, -part.centroid.z]}>
        <MiniModel part={geometry} color={color} />
      </group>

      <OrbitControls
        enablePan={false}
        enableZoom={false}
        enableDamping
        dampingFactor={0.08}
        rotateSpeed={0.6}
        autoRotate
        autoRotateSpeed={0.9}
      />
    </Canvas>
  );
}

// Small orbitable view of one myoma, drawn from the GLB the main viewer already loaded.
// The frame is painted the same colour as the stage rather than given the usual inset
// border: the canvas can miss the box by a subpixel, and a tinted border underneath it
// showed through as a stray edge on one side.
export default function MyomaMiniView({ url, myomaId, color }: Props) {
  return (
    <div
      className="relative h-[132px] overflow-hidden rounded-md"
      style={{ backgroundColor: STAGE }}
    >
      <Suspense fallback={null}>
        <MiniScene url={url} myomaId={myomaId} color={color} />
      </Suspense>
    </div>
  );
}
