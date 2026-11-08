// ── Zenith Dynamic Motion Engine (Google Antigravity Aesthetic) ──

function startApp() {
  document.documentElement.classList.add('js-ready');
  initAntigravityParticles();
  initNavbarScroll();
  initScrollReveal();
  initPlaygroundSimulator();
  initVoiceSwitcher();
  initFaqAccordion();
  init3DTilt();
  initButtonRipples();
  initHeroEqualizer();
  initSmoothScroll();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startApp);
} else {
  startApp();
}

// 1. Antigravity Physics Floating Micro-Particles Simulation
function initAntigravityParticles() {
  const canvas = document.getElementById('antigravityCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width, height;

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize, { passive: true });

  // Google Antigravity Particle Colors
  const colors = [
    '#4285f4', // Google Blue
    '#34a853', // Google Green
    '#fbbc05', // Google Yellow
    '#ea4335', // Google Red
    '#1a73e8', // Deep Google Blue
    '#00b4d8'  // Cyan
  ];

  const particleCount = 75;
  const particles = [];

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 2.2 + 1.6, // 1.6px to 3.8px
      color: colors[Math.floor(Math.random() * colors.length)],
      opacity: Math.random() * 0.45 + 0.35,
      speedY: -(Math.random() * 0.5 + 0.22), // Floating upward against gravity
      swayFreq: Math.random() * 0.02 + 0.008,
      swayAmp: Math.random() * 0.7 + 0.3,
      swayPhase: Math.random() * Math.PI * 2,
      vx: 0,
      vy: 0
    });
  }

  let mouseX = -9999;
  let mouseY = -9999;
  let mouseActive = false;

  window.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    mouseActive = true;
  }, { passive: true });

  window.addEventListener('mouseleave', () => {
    mouseActive = false;
  });

  let time = 0;

  function animate() {
    time += 1;
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];

      // Anti-gravity upward lift with gentle horizontal sway
      p.y += p.speedY + p.vy;
      p.x += Math.sin(time * p.swayFreq + p.swayPhase) * p.swayAmp + p.vx;

      // Natural damping on external velocity
      p.vx *= 0.94;
      p.vy *= 0.94;

      // Cursor deflection forcefield (interactive anti-gravity deflection)
      if (mouseActive) {
        const dx = p.x - mouseX;
        const dy = p.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const maxDist = 120;

        if (dist < maxDist && dist > 0.1) {
          const force = (1 - dist / maxDist) * 1.5;
          p.vx += (dx / dist) * force;
          p.vy += (dy / dist) * force;
        }
      }

      // Screen boundary wrap-around
      if (p.y < -15) {
        p.y = height + 15;
        p.x = Math.random() * width;
        p.vx = 0;
        p.vy = 0;
      } else if (p.y > height + 20) {
        p.y = -10;
      }

      if (p.x < -20) p.x = width + 10;
      else if (p.x > width + 20) p.x = -10;

      // Draw particle
      ctx.save();
      ctx.globalAlpha = p.opacity;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    requestAnimationFrame(animate);
  }

  animate();
}

// 2. Navbar Scroll Transition
function initNavbarScroll() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  const onScroll = () => {
    if (window.scrollY > 20) {
      navbar.classList.add('navbar-scrolled');
    } else {
      navbar.classList.remove('navbar-scrolled');
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// 3. Multi-Directional Scroll Reveal Engine
function initScrollReveal() {
  const revealElements = document.querySelectorAll('[data-reveal]');
  if (!revealElements.length) return;

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in-view');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.08,
      rootMargin: '0px 0px -30px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
  } else {
    const checkViewport = () => {
      const bottom = window.innerHeight * 0.94;
      revealElements.forEach(el => {
        if (el.getBoundingClientRect().top <= bottom) {
          el.classList.add('is-in-view');
        }
      });
    };
    checkViewport();
    window.addEventListener('scroll', checkViewport, { passive: true });
  }

  // Double check elements on load
  setTimeout(() => {
    const bottom = window.innerHeight * 0.96;
    revealElements.forEach(el => {
      if (el.getBoundingClientRect().top <= bottom) {
        el.classList.add('is-in-view');
      }
    });
  }, 80);
}

// 4. Interactive Command Playground Simulator (Antigravity Style)
function initPlaygroundSimulator() {
  const chips = document.querySelectorAll('.playground-chip');
  const modeLabel = document.getElementById('hudModeLabel');
  const latencyVal = document.getElementById('hudLatencyVal');
  const voiceText = document.getElementById('hudVoiceText');
  const targetLabel = document.getElementById('hudTargetLabel');
  const telemetry = document.getElementById('hudScanTelemetry');
  const actionLogs = document.getElementById('hudActionLogs');

  if (!chips.length || !voiceText) return;

  const scenarios = {
    code: {
      mode: 'Agent Protocol: Autonomous Code Inspection & Patching',
      latency: '182ms',
      voice: '"Zenith, take a look at the open script in VS Code. It freezes when processing requests. Find the bottleneck and patch it."',
      target: 'Target: VS Code • Line 42 (asyncio.gather without timeout)',
      telemetry: 'Buffer: 1920x1080 @ 60fps • Detection: 38ms • Confidence: 99.4%',
      logs: [
        { time: '00:00.042', text: 'Acquired desktop screen buffer via zero-copy GDI mirror.', type: 'success' },
        { time: '00:00.098', text: 'Gemini 3.8 Live localized asyncio deadlocks in process loop.', type: 'info' },
        { time: '00:00.182', text: 'Synthesized voice response & applied inline code fix safely.', type: 'accent' }
      ]
    },
    doc: {
      mode: 'Agent Protocol: Document OCR & Financial Synthesis',
      latency: '214ms',
      voice: '"Zenith, analyze the open PDF. Extract Q3 net margin growth and read out the key risk factors."',
      target: 'Target: Acrobat Reader • Page 14 (Table 3.2 Operating Metrics)',
      telemetry: 'Buffer: 2560x1440 HiDPI • OCR Speed: 52ms • Tokens: 1,840 parsed',
      logs: [
        { time: '00:00.048', text: 'Scanned document raster with high-fidelity bounding boxes.', type: 'success' },
        { time: '00:00.126', text: 'Extracted +24.8% YoY net margin and identified tariff headwinds.', type: 'info' },
        { time: '00:00.214', text: 'Delivered conversational executive audio summary in Aoede timbre.', type: 'accent' }
      ]
    },
    music: {
      mode: 'Agent Protocol: Background Media Session Orchestration',
      latency: '168ms',
      voice: '"Zenith, put on something chill for coding on YouTube Music in the background."',
      target: 'Target: Headless Media Session • Stream Service: YouTube Web',
      telemetry: 'Session: Background Chromium PID 14820 • Zero UI Interruption',
      logs: [
        { time: '00:00.035', text: 'Parsed operator intent: Ambient Lo-Fi Instrumental.', type: 'success' },
        { time: '00:00.088', text: 'Resolved top-ranked streaming audio track without API key prompt.', type: 'info' },
        { time: '00:00.168', text: 'Began background WebRTC audio playback with smooth crossfade.', type: 'accent' }
      ]
    },
    ui: {
      mode: 'Agent Protocol: Windows UIAutomation Input Driver',
      latency: '194ms',
      voice: '"Zenith, click the blue Deploy button in the Chrome window and wait for the confirmation modal."',
      target: 'Target: Google Chrome • UIA Button[Name="Deploy Production"] [x: 1240, y: 380]',
      telemetry: 'UIA Tree Depth: 14 elements • Element Locating: 22ms • Native Injection',
      logs: [
        { time: '00:00.038', text: 'Queried Windows UIAutomation COM tree for active window.', type: 'success' },
        { time: '00:00.110', text: 'Verified element clickability & positioned cursor with human curve.', type: 'info' },
        { time: '00:00.194', text: 'Dispatched native WM_LBUTTONDOWN; modal confirmed.', type: 'accent' }
      ]
    }
  };

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const cmdKey = chip.getAttribute('data-cmd');
      const data = scenarios[cmdKey];
      if (!data) return;

      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      modeLabel.textContent = data.mode;
      latencyVal.textContent = data.latency;
      voiceText.textContent = data.voice;
      targetLabel.textContent = data.target;
      telemetry.textContent = data.telemetry;

      // Animate logs
      actionLogs.innerHTML = '';
      data.logs.forEach((log, index) => {
        setTimeout(() => {
          const entry = document.createElement('div');
          entry.className = `action-log-entry ${log.type}`;
          entry.innerHTML = `<span class="log-time">${log.time}</span><span class="log-text">${log.text}</span>`;
          actionLogs.appendChild(entry);
        }, index * 90);
      });
    });
  });
}

// 5. Voice Personas Switcher
function initVoiceSwitcher() {
  const cards = document.querySelectorAll('.voice-card');
  if (!cards.length) return;

  cards.forEach(card => {
    card.addEventListener('click', () => {
      cards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
    });
  });
}

// 6. FAQ Accordion Interaction
function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach(item => {
    const questionBtn = item.querySelector('.faq-question');
    if (!questionBtn) return;

    questionBtn.addEventListener('click', () => {
      const isOpen = item.classList.contains('is-open');

      faqItems.forEach(other => {
        if (other !== item) other.classList.remove('is-open');
      });

      if (isOpen) {
        item.classList.remove('is-open');
      } else {
        item.classList.add('is-open');
      }
    });
  });
}

// 7. 3D Card Tilt with Dynamic Specular Glare
function init3DTilt() {
  const tiltCards = document.querySelectorAll('.interactive-tilt');

  tiltCards.forEach(card => {
    let bounds;

    const onMouseEnter = () => {
      bounds = card.getBoundingClientRect();
    };

    const onMouseMove = (e) => {
      if (card.hasAttribute('data-reveal') && !card.classList.contains('is-in-view')) {
        return;
      }

      if (!bounds) bounds = card.getBoundingClientRect();
      const mouseX = e.clientX - bounds.left;
      const mouseY = e.clientY - bounds.top;

      const percentX = (mouseX / bounds.width) * 100;
      const percentY = (mouseY / bounds.height) * 100;

      const tiltX = ((mouseY / bounds.height) - 0.5) * -10;
      const tiltY = ((mouseX / bounds.width) - 0.5) * 10;

      card.style.setProperty('--glare-x', `${percentX}%`);
      card.style.setProperty('--glare-y', `${percentY}%`);
      card.style.transform = `perspective(1000px) rotateX(${tiltX.toFixed(2)}deg) rotateY(${tiltY.toFixed(2)}deg) translateZ(6px) scale3d(1.012, 1.012, 1.012)`;
    };

    const onMouseLeave = () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0) scale3d(1, 1, 1)';
    };

    card.addEventListener('mouseenter', onMouseEnter);
    card.addEventListener('mousemove', onMouseMove);
    card.addEventListener('mouseleave', onMouseLeave);
  });
}

// 8. Button Click Ripple Micro-interaction
function initButtonRipples() {
  const buttons = document.querySelectorAll('.btn');

  buttons.forEach(btn => {
    btn.addEventListener('click', function (e) {
      const rect = this.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'btn-ripple';

      const diameter = Math.max(rect.width, rect.height);
      const radius = diameter / 2;

      ripple.style.width = ripple.style.height = `${diameter}px`;
      ripple.style.left = `${e.clientX - rect.left - radius}px`;
      ripple.style.top = `${e.clientY - rect.top - radius}px`;

      const existingRipple = this.querySelector('.btn-ripple');
      if (existingRipple) existingRipple.remove();

      this.appendChild(ripple);

      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  });
}

// 9. Interactive Acoustic Equalizer Visualizer (Reacts to Cursor Speed & Proximity)
function initHeroEqualizer() {
  const canvas = document.getElementById('heroEqualizer');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const container = canvas.parentElement;

  function resizeCanvas() {
    canvas.width = container.clientWidth * window.devicePixelRatio;
    canvas.height = container.clientHeight * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }

  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  const numBars = 54;
  const barWidth = 4;
  const barGap = 6;
  const bars = Array.from({ length: numBars }, (_, i) => ({
    targetHeight: 12,
    currentHeight: 12,
    speed: 0.1 + Math.random() * 0.08,
    phase: i * 0.18
  }));

  let tick = 0;
  let mouseInteraction = 0;
  let cursorXRatio = 0.5;

  container.addEventListener('mousemove', (e) => {
    const rect = container.getBoundingClientRect();
    cursorXRatio = (e.clientX - rect.left) / rect.width;
    mouseInteraction = Math.min(mouseInteraction + 0.15, 1.5);
  });

  container.addEventListener('mouseleave', () => {
    mouseInteraction = 0;
  });

  function render() {
    tick += 0.045 + (mouseInteraction * 0.025);
    mouseInteraction *= 0.96;

    const w = canvas.width / window.devicePixelRatio;
    const h = canvas.height / window.devicePixelRatio;

    ctx.clearRect(0, 0, w, h);

    const totalWidth = numBars * (barWidth + barGap) - barGap;
    const startX = (w - totalWidth) / 2;

    for (let i = 0; i < numBars; i++) {
      const bar = bars[i];
      const iRatio = i / numBars;
      
      const distToCursor = Math.abs(iRatio - cursorXRatio);
      const cursorBoost = Math.max(0, 1 - distToCursor * 3.5) * mouseInteraction * 45;

      const wave1 = Math.sin(tick * 1.2 + bar.phase) * 0.5 + 0.5;
      const wave2 = Math.cos(tick * 0.85 - bar.phase * 0.7) * 0.5 + 0.5;
      const wave3 = Math.sin(tick * 2.1 + i * 0.4) * 0.25;

      bar.targetHeight = 10 + (wave1 * 0.55 + wave2 * 0.35 + wave3 * 0.1) * (h * 0.72) + cursorBoost;
      bar.currentHeight += (bar.targetHeight - bar.currentHeight) * bar.speed;

      const x = startX + i * (barWidth + barGap);
      const y = (h - bar.currentHeight) / 2;

      const grad = ctx.createLinearGradient(0, y, 0, y + bar.currentHeight);
      if (mouseInteraction > 0.4) {
        grad.addColorStop(0, '#1a73e8');
        grad.addColorStop(0.5, '#4285f4');
        grad.addColorStop(1, '#34a853');
      } else {
        grad.addColorStop(0, '#4285f4');
        grad.addColorStop(0.5, '#34a853');
        grad.addColorStop(1, '#1e8e3e');
      }

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, Math.max(bar.currentHeight, 4), 2);
      ctx.fill();
    }

    requestAnimationFrame(render);
  }

  render();
}

// 10. Smooth Scroll (Including Back to Top)
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#' || targetId === '#top') {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }
      
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
}
