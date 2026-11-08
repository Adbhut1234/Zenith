// ── ZENITH 3D COGNITIVE CORE (Apple & Linear Quality) ──
// References: linear.app, apple.com/airpods-pro, lusion.co

(function () {
  const container = document.getElementById('zenith-3d-viewport');
  if (!container) return;

  // Scene setup
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  );
  camera.position.z = 5.2;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const coreGroup = new THREE.Group();
  scene.add(coreGroup);

  // ── Custom GLSL Shaders: Deep Iridescent Purple-to-Indigo Core with Cyan Rim ──
  const coreVertexShader = `
    uniform float uTime;
    uniform float uPulse;
    uniform float uDisplacement;
    varying vec3 vNormal;
    varying vec3 vPosition;
    varying float vNoise;

    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

    float snoise(vec3 v) {
      const vec2 C = vec2(1.0/6.0, 1.0/3.0);
      const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy));
      vec3 x0 = v - i + dot(i, C.xxx);
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min(g.xyz, l.zxy);
      vec3 i2 = max(g.xyz, l.zxy);
      vec3 x1 = x0 - i1 + C.xxx;
      vec3 x2 = x0 - i2 + C.yyy;
      vec3 x3 = x0 - D.yyy;
      i = mod289(i);
      vec4 p = permute(permute(permute(
                i.z + vec4(0.0, i1.z, i2.z, 1.0))
              + i.y + vec4(0.0, i1.y, i2.y, 1.0))
              + i.x + vec4(0.0, i1.x, i2.x, 1.0));
      float n_ = 0.142857142857;
      vec3  ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_);
      vec4 x = x_ *ns.x + ns.yyyy;
      vec4 y = y_ *ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4(x.xy, y.xy);
      vec4 b1 = vec4(x.zw, y.zw);
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
      vec3 p0 = vec3(a0.xy, h.x);
      vec3 p1 = vec3(a0.zw, h.y);
      vec3 p2 = vec3(a1.xy, h.z);
      vec3 p3 = vec3(a1.zw, h.w);
      vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
      p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vPosition = position;
      float noise = snoise(position * 1.5 + vec3(uTime * 0.7));
      vNoise = noise;
      vec3 newPos = position + normal * (noise * uDisplacement + uPulse * 0.15);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
    }
  `;

  const coreFragmentShader = `
    uniform float uTime;
    uniform vec3 uColorA; // #0f2923
    uniform vec3 uColorB; // #64d2b1
    uniform vec3 uRimColor; // #6eb5ff
    uniform float uAlertState; // 0.0 normal, 1.0 #ff6b6b
    varying vec3 vNormal;
    varying vec3 vPosition;
    varying float vNoise;

    void main() {
      vec3 viewDir = normalize(-vPosition);
      // Sharp grazing rim
      float fresnel = pow(1.0 - max(dot(viewDir, vNormal), 0.0), 2.8);

      // Obsidian-teal to Zenith signature mint core
      vec3 baseColor = mix(uColorA, uColorB, vPosition.y * 0.5 + 0.5);
      
      // Soft Blue grazing edge
      vec3 color = mix(baseColor, uRimColor, fresnel * 0.95);

      // Inner luminance veins (mint-energy)
      color += vec3(0.03, 0.12, 0.09);

      // Alert override (#ff6b6b from Zenith app tokens)
      vec3 alertColor = vec3(1.0, 0.42, 0.42);
      color = mix(color, alertColor, uAlertState);

      gl_FragColor = vec4(color + vec3(vNoise * 0.08), 0.95);
    }
  `;

  // 1. Central Icosahedral Mind Core
  const coreGeo = new THREE.IcosahedronGeometry(1.22, 4);
  const coreUniforms = {
    uTime: { value: 0 },
    uPulse: { value: 0 },
    uDisplacement: { value: 0.18 },
    uColorA: { value: new THREE.Color(0x0f2923) }, // Obsidian-Teal
    uColorB: { value: new THREE.Color(0x64d2b1) }, // Zenith Signature Mint
    uRimColor: { value: new THREE.Color(0x6eb5ff) }, // Zenith Soft Blue
    uAlertState: { value: 0.0 },
  };

  const coreMat = new THREE.ShaderMaterial({
    vertexShader: coreVertexShader,
    fragmentShader: coreFragmentShader,
    uniforms: coreUniforms,
    transparent: true,
  });

  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  coreGroup.add(coreMesh);

  // 2. Wireframe faceted outer shell
  const wireGeo = new THREE.IcosahedronGeometry(1.28, 2);
  const wireMat = new THREE.MeshBasicMaterial({
    color: 0x64d2b1,
    wireframe: true,
    transparent: true,
    opacity: 0.45,
  });
  const wireMesh = new THREE.Mesh(wireGeo, wireMat);
  coreGroup.add(wireMesh);

  // 3. Orbital Gimbal Rings (Zenith Mint, Soft Blue, Soft Purple)
  function createOrbitalRing(radius, tube, color, rx, ry, rz) {
    const geo = new THREE.TorusGeometry(radius, tube, 16, 120);
    const mat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.65 });
    const ring = new THREE.Mesh(geo, mat);
    ring.rotation.set(rx, ry, rz);
    return ring;
  }

  const ring1 = createOrbitalRing(1.85, 0.012, 0x64d2b1, Math.PI / 3, 0.2, 0); // Mint
  const ring2 = createOrbitalRing(2.15, 0.01, 0x6eb5ff, -Math.PI / 4, 0.5, 0);  // Soft Blue
  const ring3 = createOrbitalRing(2.42, 0.008, 0xa78bfa, Math.PI / 2, 0, 0.4); // Soft Purple

  coreGroup.add(ring1);
  coreGroup.add(ring2);
  coreGroup.add(ring3);

  // 4. 3,000 Particle Field (Sovereign Neural Swarm)
  const isMobile = window.innerWidth < 768;
  const particleCount = isMobile ? 600 : 3000;
  const particleGeo = new THREE.BufferGeometry();
  const particlePositions = new Float32Array(particleCount * 3);
  const originalPos = new Float32Array(particleCount * 3);
  const particleColors = new Float32Array(particleCount * 3);

  // Matches Zenith native app accent tokens: mint, soft blue, soft purple, amber, white
  const pPalette = [
    new THREE.Color(0x64d2b1),
    new THREE.Color(0x6eb5ff),
    new THREE.Color(0xa78bfa),
    new THREE.Color(0xffb84d),
    new THREE.Color(0x48b898),
    new THREE.Color(0xffffff),
  ];

  for (let i = 0; i < particleCount; i++) {
    const r = 1.6 + Math.random() * 2.0;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(Math.random() * 2 - 1);

    const x = r * Math.sin(phi) * Math.cos(theta);
    const y = r * Math.sin(phi) * Math.sin(theta);
    const z = r * Math.cos(phi);

    particlePositions[i * 3] = x;
    particlePositions[i * 3 + 1] = y;
    particlePositions[i * 3 + 2] = z;

    originalPos[i * 3] = x;
    originalPos[i * 3 + 1] = y;
    originalPos[i * 3 + 2] = z;

    const c = pPalette[Math.floor(Math.random() * pPalette.length)];
    particleColors[i * 3] = c.r;
    particleColors[i * 3 + 1] = c.g;
    particleColors[i * 3 + 2] = c.b;
  }

  particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
  particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

  const particleMat = new THREE.PointsMaterial({
    size: isMobile ? 0.04 : 0.032,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
  });

  const particleSystem = new THREE.Points(particleGeo, particleMat);
  coreGroup.add(particleSystem);

  // ── Mouse Tilting ──
  let targetRotX = 0;
  let targetRotY = 0;

  window.addEventListener('mousemove', (e) => {
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    targetRotY = (x / (rect.width / 2)) * 0.26;
    targetRotX = (y / (rect.height / 2)) * 0.26;
  });

  // ── Core State Switcher ──
  let currentState = 'idle';
  window.setCoreState = function (state) {
    currentState = state;
    document.querySelectorAll('.btn-core-tab').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`[data-state="${state}"]`);
    if (btn) btn.classList.add('active');

    const statusPill = document.getElementById('core-hud-state');

    if (state === 'idle') {
      coreUniforms.uAlertState.value = 0.0;
      coreUniforms.uDisplacement.value = 0.18;
      wireMat.color.setHex(0x64d2b1);
      wireMat.opacity = 0.45;
      ring1.scale.set(1, 1, 1);
      ring2.scale.set(1, 1, 1);
      if (statusPill) statusPill.textContent = 'Idle (Ready)';
    } else if (state === 'listening') {
      coreUniforms.uAlertState.value = 0.0;
      coreUniforms.uDisplacement.value = 0.28;
      wireMat.color.setHex(0x64d2b1);
      wireMat.opacity = 0.7;
      ring1.scale.set(1.25, 1.25, 1.25);
      ring2.scale.set(1.2, 1.2, 1.2);
      if (statusPill) statusPill.textContent = 'Listening (WebRTC)';
    } else if (state === 'thinking') {
      coreUniforms.uAlertState.value = 0.0;
      coreUniforms.uDisplacement.value = 0.38;
      wireMat.color.setHex(0x6eb5ff);
      wireMat.opacity = 0.95;
      wireMesh.rotation.y += 0.5;
      if (statusPill) statusPill.textContent = 'Deliberating';
    } else if (state === 'alert') {
      coreUniforms.uAlertState.value = 1.0;
      coreUniforms.uDisplacement.value = 0.06;
      wireMat.color.setHex(0xff6b6b);
      if (statusPill) statusPill.textContent = 'Alert Mode';
    }
  };

  // ── Render Loop ──
  const clock = new THREE.Clock();
  let audioLevel = 0.0;

  function animate() {
    requestAnimationFrame(animate);

    const time = clock.getElapsedTime();
    coreUniforms.uTime.value = time;

    // Organic breathing pulse
    audioLevel = Math.sin(time * 2.8) * 0.12 + 0.15;
    if (currentState === 'listening') audioLevel += 0.22;
    if (currentState === 'thinking') audioLevel = Math.sin(time * 8.0) * 0.28 + 0.32;

    coreUniforms.uPulse.value = audioLevel;

    // Mouse tilt
    coreGroup.rotation.y += (targetRotY - coreGroup.rotation.y) * 0.06;
    coreGroup.rotation.x += (targetRotX - coreGroup.rotation.x) * 0.06;

    // Rotation
    const isAlert = currentState === 'alert';
    const rotSpeed = currentState === 'thinking' ? 0.025 : (isAlert ? 0.0 : 0.005);
    coreMesh.rotation.y += rotSpeed;
    wireMesh.rotation.y -= rotSpeed * 1.5;

    if (!isAlert) {
      ring1.rotation.z += 0.007;
      ring2.rotation.z -= 0.009;
      ring3.rotation.x += 0.005;
    }

    // Particle wave
    const pos = particleGeo.attributes.position.array;
    for (let i = 0; i < particleCount; i++) {
      const idx = i * 3;
      const ox = originalPos[idx];
      const oy = originalPos[idx + 1];
      const oz = originalPos[idx + 2];

      const wave = Math.sin(time * 3.2 + ox * 2.5) * (0.05 + audioLevel * 0.12);
      pos[idx] = ox * (1.0 + wave);
      pos[idx + 1] = oy * (1.0 + wave);
      pos[idx + 2] = oz * (1.0 + wave);
    }
    particleGeo.attributes.position.needsUpdate = true;

    renderer.render(scene, camera);
  }

  animate();

  // Resize handler
  window.addEventListener('resize', () => {
    if (!container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });
})();
