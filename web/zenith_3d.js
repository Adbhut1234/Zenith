// ── Zenith OS 3D Neural Core & Interactive Canvas ──
// Powered by Three.js

(function () {
  const container = document.getElementById('canvas3d-container');
  if (!container) return;

  // Scene setup
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  );
  camera.position.z = 6;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  // Group to hold all 3D components for mouse rotation
  const coreGroup = new THREE.Group();
  scene.add(coreGroup);

  // 1. Central Icosahedron Wireframe (System 2 Cognitive Mind Stone)
  const innerGeo = new THREE.IcosahedronGeometry(1.25, 2);
  const innerMat = new THREE.MeshPhongMaterial({
    color: 0x1a73e8,
    wireframe: true,
    transparent: true,
    opacity: 0.55,
    shininess: 90,
  });
  const innerMesh = new THREE.Mesh(innerGeo, innerMat);
  coreGroup.add(innerMesh);

  // 2. Inner Glowing Solid Nucleus
  const nucleusGeo = new THREE.IcosahedronGeometry(0.85, 1);
  const nucleusMat = new THREE.MeshStandardMaterial({
    color: 0x4285f4,
    emissive: 0x174ea6,
    emissiveIntensity: 0.6,
    roughness: 0.2,
    metalness: 0.8,
  });
  const nucleusMesh = new THREE.Mesh(nucleusGeo, nucleusMat);
  coreGroup.add(nucleusMesh);

  // 3. Floating Orbital Particle Swarm (Sovereign Neural Matrix)
  const particleCount = 750;
  const particleGeo = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const originalPositions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  const colorPalette = [
    new THREE.Color(0x4285f4), // Google Blue
    new THREE.Color(0x34a853), // Green
    new THREE.Color(0xfbbc05), // Amber
    new THREE.Color(0xea4335), // Red
    new THREE.Color(0x8ab4f8), // Cyan-Blue
  ];

  for (let i = 0; i < particleCount; i++) {
    const radius = 1.6 + Math.random() * 0.9;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(Math.random() * 2 - 1);

    const x = radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.sin(phi) * Math.sin(theta);
    const z = radius * Math.cos(phi);

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    originalPositions[i * 3] = x;
    originalPositions[i * 3 + 1] = y;
    originalPositions[i * 3 + 2] = z;

    const chosenColor = colorPalette[Math.floor(Math.random() * colorPalette.length)];
    colors[i * 3] = chosenColor.r;
    colors[i * 3 + 1] = chosenColor.g;
    colors[i * 3 + 2] = chosenColor.b;
  }

  particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const particleMat = new THREE.PointsMaterial({
    size: 0.045,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.NormalBlending,
  });

  const particleSystem = new THREE.Points(particleGeo, particleMat);
  coreGroup.add(particleSystem);

  // 4. Orbital Gimbal Rings (Vision & LiveKit WebRTC Streams)
  function createOrbitalRing(radius, tubeRadius, color, rotX, rotY) {
    const ringGeo = new THREE.TorusGeometry(radius, tubeRadius, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.35,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = rotX;
    ring.rotation.y = rotY;
    return ring;
  }

  const ring1 = createOrbitalRing(2.1, 0.012, 0x1a73e8, Math.PI / 4, 0);
  const ring2 = createOrbitalRing(2.3, 0.01, 0x34a853, -Math.PI / 3, Math.PI / 6);
  const ring3 = createOrbitalRing(2.5, 0.008, 0x5f6368, Math.PI / 2, Math.PI / 4);

  coreGroup.add(ring1);
  coreGroup.add(ring2);
  coreGroup.add(ring3);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambientLight);

  const pointLight1 = new THREE.PointLight(0x4285f4, 1.8, 50);
  pointLight1.position.set(5, 5, 5);
  scene.add(pointLight1);

  const pointLight2 = new THREE.PointLight(0x34a853, 1.2, 50);
  pointLight2.position.set(-5, -3, 3);
  scene.add(pointLight2);

  // Mouse Interaction with Smooth Interpolation (Lerp)
  let targetRotationX = 0;
  let targetRotationY = 0;
  let mouseX = 0;
  let mouseY = 0;

  window.addEventListener('mousemove', (e) => {
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    targetRotationY = (x / rect.width) * 1.5;
    targetRotationX = (y / rect.height) * 1.5;
  });

  // Mode Swapping (System 2, Voice, Vision, Memory)
  let currentPulseSpeed = 1.0;
  let audioReactivity = 0;

  window.setZenithMode = function (mode) {
    document.querySelectorAll('.mode-tab').forEach((t) => t.classList.remove('active'));
    const btn = document.querySelector(`[data-mode="${mode}"]`);
    if (btn) btn.classList.add('active');

    const descEl = document.getElementById('mode-description');

    if (mode === 'reasoning') {
      innerMat.color.setHex(0x1a73e8);
      nucleusMat.emissive.setHex(0x174ea6);
      currentPulseSpeed = 0.8;
      audioReactivity = 0.2;
      if (descEl) descEl.textContent = 'System 2 Subconscious Matrix: Pre-computes failure modes and counterfactuals.';
    } else if (mode === 'voice') {
      innerMat.color.setHex(0x34a853);
      nucleusMat.emissive.setHex(0x0d652d);
      currentPulseSpeed = 2.4;
      audioReactivity = 0.6;
      if (descEl) descEl.textContent = 'Gemini Multimodal Live: Full-duplex WebRTC audio streaming under 240ms.';
    } else if (mode === 'vision') {
      innerMat.color.setHex(0xfbbc05);
      nucleusMat.emissive.setHex(0xb06000);
      currentPulseSpeed = 1.4;
      audioReactivity = 0.4;
      if (descEl) descEl.textContent = 'Screen Vision OCR & UIAutomation: Zero-copy native Windows control.';
    } else if (mode === 'memory') {
      innerMat.color.setHex(0x9334e6);
      nucleusMat.emissive.setHex(0x5b21b6);
      currentPulseSpeed = 1.0;
      audioReactivity = 0.3;
      if (descEl) descEl.textContent = 'Neuroplastic Memory Matrix: Self-healing SQLite procedural playbooks.';
    }
  };

  // Animation Loop
  let clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);

    const elapsedTime = clock.getElapsedTime();

    // Base constant spin
    coreGroup.rotation.y += 0.004;
    coreGroup.rotation.x += 0.002;

    // Smooth mouse follow
    coreGroup.rotation.y += (targetRotationY - coreGroup.rotation.y) * 0.05;
    coreGroup.rotation.x += (targetRotationX - coreGroup.rotation.x) * 0.05;

    // Individual component counter-rotations
    innerMesh.rotation.y += 0.008 * currentPulseSpeed;
    nucleusMesh.rotation.x -= 0.006 * currentPulseSpeed;
    ring1.rotation.z += 0.005;
    ring2.rotation.z -= 0.007;
    ring3.rotation.x += 0.004;

    // Breathing / Pulse animation on inner core
    const pulse = 1 + Math.sin(elapsedTime * 2.5 * currentPulseSpeed) * (0.05 + audioReactivity * 0.08);
    nucleusMesh.scale.set(pulse, pulse, pulse);
    innerMesh.scale.set(pulse * 1.03, pulse * 1.03, pulse * 1.03);

    // Dynamic wave ripples on particles
    const pos = particleGeo.attributes.position.array;
    for (let i = 0; i < particleCount; i++) {
      const idx = i * 3;
      const ox = originalPositions[idx];
      const oy = originalPositions[idx + 1];
      const oz = originalPositions[idx + 2];

      const wave = Math.sin(elapsedTime * 3 + ox * 2 + oy * 2) * (0.04 + audioReactivity * 0.06);
      pos[idx] = ox * (1 + wave);
      pos[idx + 1] = oy * (1 + wave);
      pos[idx + 2] = oz * (1 + wave);
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

// ── 3D Card Tilt Interaction (Mouse specular highlight) ──
document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.card-3d');
  cards.forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -8;
      const rotateY = ((x - centerX) / centerX) * 8;

      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
    });
  });
});
