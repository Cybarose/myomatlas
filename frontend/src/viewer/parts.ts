import { useGLTF } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";
import { myomaOrder } from "./palette";

export interface MyomaPart {
  id: string;
  geometry: THREE.BufferGeometry;
  centroid: THREE.Vector3;
}

export interface CaseParts {
  wall: THREE.BufferGeometry[];
  cavity: THREE.BufferGeometry[];
  myomas: MyomaPart[];
  center: THREE.Vector3;
  size: THREE.Vector3;
}

// Pull the named nodes out of the GLB and bake world transforms into geometry so
// wall, cavity and every myoma share one coordinate frame. useGLTF caches by url, so
// the detail card's mini view reuses the scene the main viewer already loaded.
export function useCaseParts(url: string): CaseParts {
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
