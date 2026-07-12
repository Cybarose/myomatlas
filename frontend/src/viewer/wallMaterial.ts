import * as THREE from "three";

// Soft tissue rose. Muted and desaturated on purpose: the wall is a backdrop and the
// coloured myomas have to stay the focus and stay legible through it.
// The stage tone maps with ACES, which desaturates anything it drives bright toward
// white. A pale pink under this studio simply renders as grey, so the albedo is a deeper,
// saturated rose that lands in the saturated part of the curve and reads as soft tissue.
const TISSUE = "#eda198";
const TISSUE_CORE = "#8e544e";

// Undulations per millimetre. The case is roughly 100 mm across, so this gives a few
// broad swells rather than visible grain.
const NOISE_FREQUENCY = 0.07;

// Normal perturbation and roughness variation. Both stay small: this is surface
// character, not a displacement, and the silhouette must not change.
const BUMP_STRENGTH = 0.42;
const ROUGHNESS_VARIATION = 0.18;

// Value noise over world position. The marching cubes mesh carries no UVs, so the
// variation is sampled in object space instead of from a texture.
const NOISE_GLSL = `
varying vec3 vTissuePos;

float tissueHash(vec3 p) {
  p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419));
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float tissueNoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(
      mix(tissueHash(i + vec3(0.0, 0.0, 0.0)), tissueHash(i + vec3(1.0, 0.0, 0.0)), f.x),
      mix(tissueHash(i + vec3(0.0, 1.0, 0.0)), tissueHash(i + vec3(1.0, 1.0, 0.0)), f.x),
      f.y),
    mix(
      mix(tissueHash(i + vec3(0.0, 0.0, 1.0)), tissueHash(i + vec3(1.0, 0.0, 1.0)), f.x),
      mix(tissueHash(i + vec3(0.0, 1.0, 1.0)), tissueHash(i + vec3(1.0, 1.0, 1.0)), f.x),
      f.y),
    f.z);
}

float tissueFbm(vec3 p) {
  return 0.60 * tissueNoise(p) + 0.28 * tissueNoise(p * 2.4) + 0.12 * tissueNoise(p * 5.1);
}
`;

// Semi-transparent so the myomas read straight through it. Deliberately not a
// transmission material: transmission samples a buffer without the scene background, so
// the shell would transmit black on this dark stage.
export function createWallMaterial(): THREE.MeshPhysicalMaterial {
  const material = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(TISSUE),
    transparent: true,
    opacity: 0.55,
    // Matte and diffuse. The studio is neutral white, so every specular term the wall
    // takes is white, and a glossy shell washes the rose straight back out to grey. The
    // hue has to come from the diffuse and emissive terms, which are tinted.
    roughness: 0.7,
    metalness: 0,
    clearcoat: 0.15,
    clearcoatRoughness: 0.5,
    specularIntensity: 0.25,
    sheen: 0.35,
    sheenRoughness: 0.75,
    sheenColor: new THREE.Color("#e8a79e"),
    // On a dark stage a translucent shell only darkens what is behind it, so the wall
    // carries its own warmth to read as tissue rather than as stone.
    emissive: new THREE.Color(TISSUE_CORE),
    emissiveIntensity: 0.38,
    envMapIntensity: 0.25,
    side: THREE.FrontSide,
    depthWrite: false,
  });

  material.onBeforeCompile = (shader) => {
    shader.uniforms.uNoiseFrequency = { value: NOISE_FREQUENCY };
    shader.uniforms.uBumpStrength = { value: BUMP_STRENGTH };
    shader.uniforms.uRoughnessVariation = { value: ROUGHNESS_VARIATION };

    // Sample in world space. The noise gradient is then a world-space direction, which the
    // view matrix alone can rotate into view space, and normalMatrix is not declared in
    // three's fragment stage.
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\nvarying vec3 vTissuePos;`)
      .replace(
        "#include <project_vertex>",
        `vTissuePos = (modelMatrix * vec4(transformed, 1.0)).xyz;\n#include <project_vertex>`,
      );

    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
uniform float uNoiseFrequency;
uniform float uBumpStrength;
uniform float uRoughnessVariation;
${NOISE_GLSL}`,
      )
      // Gentle roughness drift, so the sheen breaks up instead of reading as flat plastic.
      .replace(
        "#include <roughnessmap_fragment>",
        `#include <roughnessmap_fragment>
{
  float rn = tissueFbm(vTissuePos * uNoiseFrequency * 1.7);
  roughnessFactor = clamp(roughnessFactor + (rn - 0.5) * uRoughnessVariation * 2.0, 0.08, 1.0);
}`,
      )
      // Perturb the shading normal only. The geometry, and so the silhouette, is untouched,
      // which keeps the smoothed anatomy free of stair-step edges.
      .replace(
        "#include <normal_fragment_maps>",
        `#include <normal_fragment_maps>
{
  vec3 p = vTissuePos * uNoiseFrequency;
  float e = 0.65;
  float n0 = tissueFbm(p);
  vec3 grad = vec3(
    tissueFbm(p + vec3(e, 0.0, 0.0)) - n0,
    tissueFbm(p + vec3(0.0, e, 0.0)) - n0,
    tissueFbm(p + vec3(0.0, 0.0, e)) - n0);
  vec3 bumped = normal - normalize(mat3(viewMatrix) * grad) * uBumpStrength;
  normal = normalize(bumped);
}`,
      );
  };

  // Without this the perturbed program can be served from the cache of a plain physical
  // material compiled with the same defines.
  material.customProgramCacheKey = () => "myomatlas-wall-tissue";

  return material;
}
