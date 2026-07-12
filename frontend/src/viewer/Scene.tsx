import {
  Bounds,
  ContactShadows,
  Environment,
  Lightformer,
  OrbitControls,
} from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, memo, useCallback, useState } from "react";
import ErrorBoundary from "../components/ErrorBoundary";
import type { ModelMeta, Projected } from "../types";
import CaseModel from "./CaseModel";

interface Props {
  url: string;
  sourceName: string;
  selected: string | null;
  onSelect: (id: string | null) => void;
  onReady: (meta: ModelMeta) => void;
  onProject: (points: Projected[]) => void;
}

const WORKSPACE = "#1b1d22";

// Soft, dimensional studio light built from lightformers, so nothing is fetched at
// runtime. Glass needs a bright, clean environment for its refraction and edges, with
// broad panels rather than hard points, plus one warm bounce so it never goes clinical.
function Studio() {
  return (
    <>
      <ambientLight intensity={0.38} color="#f2f3f5" />
      <hemisphereLight args={["#dfe3e8", "#2a2d33", 0.6]} />
      <directionalLight position={[70, 90, 60]} intensity={1.6} color="#ffffff" />
      <directionalLight position={[-80, 30, -55]} intensity={0.8} color="#e4e8ee" />
      <directionalLight position={[0, -50, -60]} intensity={0.4} color="#efe9e2" />
      <Environment resolution={256} frames={1}>
        <Lightformer
          form="rect"
          intensity={5}
          color="#ffffff"
          position={[8, 10, 8]}
          scale={[14, 14, 1]}
          target={[0, 0, 0]}
        />
        <Lightformer
          form="rect"
          intensity={2.2}
          color="#e8ebef"
          position={[-11, 4, -7]}
          scale={[12, 12, 1]}
          target={[0, 0, 0]}
        />
        <Lightformer
          form="rect"
          intensity={2.6}
          color="#f4f6f8"
          position={[0, 12, -10]}
          scale={[12, 6, 1]}
          target={[0, 0, 0]}
        />
        <Lightformer
          form="circle"
          intensity={1.3}
          color="#f6f1ea"
          position={[0, -10, 6]}
          scale={8}
          target={[0, 0, 0]}
        />
      </Environment>
    </>
  );
}

function caseLabel(sourceName: string): string {
  return sourceName.replace(/\.[^.]+$/, "");
}

function LoadFailed({ sourceName }: { sourceName: string }) {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="max-w-sm rounded-xl border border-line bg-surface px-6 py-5 text-center">
        <h3 className="text-[14px] font-semibold tracking-tight text-fg">
          Case model unavailable
        </h3>
        <p className="mt-2 text-[13px] leading-relaxed text-fg2">
          The 3D model for{" "}
          <span className="font-medium text-fg">{caseLabel(sourceName)}</span> could not be
          opened. Load a case from disk to continue.
        </p>
      </div>
    </div>
  );
}

function Scene({ url, sourceName, selected, onSelect, onReady, onProject }: Props) {
  const [floorY, setFloorY] = useState(-50);

  const handleReady = useCallback(
    (meta: ModelMeta) => {
      setFloorY(-meta.sizeMm[1] / 2 - 12);
      onReady(meta);
    },
    [onReady],
  );

  return (
    <ErrorBoundary key={url} fallback={<LoadFailed sourceName={sourceName} />}>
      <Canvas
        dpr={[1, 2]}
        gl={{ antialias: true }}
        camera={{ fov: 34, position: [130, 75, 165], near: 1, far: 3000 }}
        onPointerMissed={() => onSelect(null)}
      >
        <color attach="background" args={[WORKSPACE]} />
        <fog attach="fog" args={[WORKSPACE, 460, 1020]} />
        <Studio />

        <Suspense fallback={null}>
          <Bounds fit clip observe margin={1.35}>
            <CaseModel
              url={url}
              selected={selected}
              onSelect={onSelect}
              onReady={handleReady}
              onProject={onProject}
            />
          </Bounds>
        </Suspense>

        <ContactShadows
          position={[0, floorY, 0]}
          opacity={0.5}
          scale={340}
          blur={3.2}
          far={95}
          color="#0e1013"
        />

        <OrbitControls
          makeDefault
          enablePan={false}
          enableDamping
          dampingFactor={0.07}
          rotateSpeed={0.65}
          zoomSpeed={0.7}
          minDistance={45}
          maxDistance={700}
        />
      </Canvas>
    </ErrorBoundary>
  );
}

// Memoized so the per-frame projection updates in the overlay never re-render the canvas.
export default memo(Scene);
