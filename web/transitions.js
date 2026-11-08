// ── ZENITH SMOOTH INTERACTION ENGINE ──

document.addEventListener('DOMContentLoaded', () => {
  initNavbarScroll();
  fetchLatestRelease();
  initHeroTypewriter();
  init3DTiltCards();
  initScrollReveals();
  initMagneticButtons();
  initWordmarkHighlight();
});

// ── 0.5. Navbar Scroll Listener (Stripe / Apple Style Blur-on-Scroll) ──
function initNavbarScroll() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;
  const onScroll = () => {
    if (window.scrollY > 20) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ── 0. Fetch Latest GitHub Release Tag & Web Installer Download URL ──
async function fetchLatestRelease() {
  const versionEl = document.getElementById('latest-version-tag');
  const downloadBtns = document.querySelectorAll('.btn-primary, .btn-nav');
  const directFallback = 'https://github.com/Adbhut1234/Zenith/releases/latest/download/Zenith-Windows-Installer.exe';

  function applyDownloadUrl(url) {
    downloadBtns.forEach((btn) => {
      btn.setAttribute('href', url);
    });
  }

  try {
    // Query GitHub's official latest release endpoint
    const res = await fetch('https://api.github.com/repos/Adbhut1234/Zenith/releases/latest');
    if (res.ok) {
      const release = await res.json();
      if (release) {
        if (release.tag_name && versionEl) {
          versionEl.textContent = release.tag_name;
        }
        if (Array.isArray(release.assets)) {
          const installer = release.assets.find(
            (a) => a.name && a.name.toLowerCase().includes('installer') && a.name.endsWith('.exe')
          ) || release.assets.find(
            (a) => a.name && a.name.endsWith('.exe') && !a.name.endsWith('.blockmap')
          );
          if (installer && installer.browser_download_url) {
            applyDownloadUrl(installer.browser_download_url);
            return;
          }
        }
        applyDownloadUrl(directFallback);
        return;
      }
    }

    // Fallback: fetch all releases and sort by published date descending
    const listRes = await fetch('https://api.github.com/repos/Adbhut1234/Zenith/releases');
    if (listRes.ok) {
      const releases = await listRes.json();
      if (Array.isArray(releases) && releases.length > 0) {
        releases.sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
        const rel = releases[0];
        if (rel.tag_name && versionEl) {
          versionEl.textContent = rel.tag_name;
        }
        if (Array.isArray(rel.assets)) {
          const installer = rel.assets.find(
            (a) => a.name && a.name.toLowerCase().includes('installer') && a.name.endsWith('.exe')
          );
          if (installer && installer.browser_download_url) {
            applyDownloadUrl(installer.browser_download_url);
            return;
          }
        }
      }
    }
    applyDownloadUrl(directFallback);
  } catch (err) {
    applyDownloadUrl(directFallback);
  }
}

// ── 1. 3D Tilt & Dynamic Specular Light on Every Card ──
function init3DTiltCards() {
  const cards = document.querySelectorAll('.tilt-card, .voice-stat');

  cards.forEach((card) => {
    let rect = null;
    let targetX = 0;
    let targetY = 0;
    let targetLift = 0;
    let targetScale = 1;
    let currentX = 0;
    let currentY = 0;
    let currentLift = 0;
    let currentScale = 1;
    let isHovered = false;
    let rafId = null;

    const isNav = card.classList.contains('nav-link') || card.classList.contains('nav-brand') || card.classList.contains('btn-nav');
    const isButton = card.classList.contains('btn-primary') || card.classList.contains('btn-ghost');
    const perspectiveVal = isNav ? 600 : (isButton ? 700 : 1100);

    card.addEventListener('animationend', () => {
      card.style.animation = 'none';
    });

    card.addEventListener('mouseenter', () => {
      isHovered = true;
      card.style.animation = 'none';
      rect = card.getBoundingClientRect();
      if (!rafId) rafId = requestAnimationFrame(animateTilt);
    });

    card.addEventListener('mousemove', (e) => {
      if (!rect) rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      // Card-size aware tilt amplitude:
      // Buttons (.btn-primary, .btn-ghost) get rich 3D card tilt ±12.5°, 13px lift, and specular spotlight
      // Nav links and buttons get ultra-nimble ±11.0° tilt, 8px lift, and 1.04x scale
      // Smaller cards (.cap-card, .voice-stat) get rich tactile ±10.5° tilt, 14px 3D lift, and subtle scale
      // Compact pill badges (.hero-announcement) get dynamic ±14.0° tilt, 12px lift, and 1.03 scale
      // Large layout cards (.compare-card, .stage-3d-box) get stable ±3.5° tilt and 6px lift
      const isLargeCard = rect.width > 750;
      const isPill = (rect.width < 340 && !isNav) || isButton;
      const maxTilt = isButton ? 12.5 : (isNav ? 11.0 : (isLargeCard ? 3.5 : (isPill ? 14.0 : 10.5)));
      const maxLift = isButton ? 13.0 : (isNav ? 8.0 : (isLargeCard ? 6.0 : (isPill ? 12.0 : 14.0)));
      const maxScale = isButton ? 1.026 : (isNav ? 1.04 : (isLargeCard ? 1.004 : (isPill ? 1.03 : 1.018)));

      targetX = ((y - centerY) / centerY) * -maxTilt;
      targetY = ((x - centerX) / centerX) * maxTilt;
      targetLift = maxLift;
      targetScale = maxScale;

      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    });

    card.addEventListener('mouseleave', () => {
      isHovered = false;
      targetX = 0;
      targetY = 0;
      targetLift = 0;
      targetScale = 1;
      rect = null;
    });

    function animateTilt() {
      // Smooth linear interpolation (lerp)
      currentX += (targetX - currentX) * 0.14;
      currentY += (targetY - currentY) * 0.14;
      currentLift += (targetLift - currentLift) * 0.14;
      currentScale += (targetScale - currentScale) * 0.14;

      card.style.transform = `perspective(${perspectiveVal}px) rotateX(${currentX.toFixed(2)}deg) rotateY(${currentY.toFixed(2)}deg) translateZ(${currentLift.toFixed(1)}px) scale(${currentScale.toFixed(3)})`;

      if (!isHovered && Math.abs(currentX) < 0.04 && Math.abs(currentY) < 0.04 && Math.abs(currentLift) < 0.05 && Math.abs(currentScale - 1) < 0.001) {
        card.style.transform = `perspective(${perspectiveVal}px) rotateX(0deg) rotateY(0deg) translateZ(0px) scale(1)`;
        rafId = null;
        return;
      }

      rafId = requestAnimationFrame(animateTilt);
    }
  });
}

// ── 3. Scroll Reveal System (Staggered 3D Cascade) ──
function initScrollReveals() {
  const revealElements = document.querySelectorAll('.reveal-item');
  if (!revealElements.length) return;

  revealElements.forEach((el, idx) => {
    const delay = (idx % 4) * 0.12;
    el.style.transitionDelay = `${delay}s`;
    const rect = el.getBoundingClientRect();
    if (rect.top > window.innerHeight) {
      el.classList.add('reveal-pending');
    }
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.remove('reveal-pending');
          entry.target.classList.add('revealed');
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  revealElements.forEach((el) => observer.observe(el));
}

// ── 4. Magnetic Buttons (Subtle cursor attraction for non-3D-tilt buttons) ──
function initMagneticButtons() {
  const buttons = document.querySelectorAll('.btn-killswitch');

  buttons.forEach((btn) => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      btn.style.transform = `translate(${x * 0.18}px, ${y * 0.18}px)`;
    });

    btn.addEventListener('mouseleave', () => {
      btn.style.transform = 'translate(0px, 0px)';
    });
  });
}

// ── 5. Terminal-Grade Hero Typewriter Animation ──
function initHeroTypewriter() {
  const line1El = document.getElementById('type-line-1');
  const line2El = document.getElementById('type-line-2');
  const cursorEl = document.getElementById('type-cursor');
  const line1Wrap = document.querySelector('.type-line-1');
  const line2Wrap = document.querySelector('.type-line-2');

  if (!line1El || !line2El || !cursorEl) return;

  const text1 = 'An AI assistant that actually';
  const text2 = 'lives on your PC.';

  line1El.textContent = '';
  line2El.textContent = '';

  if (line1Wrap) line1Wrap.appendChild(cursorEl);

  let idx1 = 0;
  let idx2 = 0;

  function typeLine1() {
    if (idx1 < text1.length) {
      line1El.textContent += text1.charAt(idx1);
      idx1++;
      setTimeout(typeLine1, 28 + Math.random() * 12);
    } else {
      setTimeout(() => {
        if (line2Wrap) line2Wrap.appendChild(cursorEl);
        setTimeout(typeLine2, 100);
      }, 140);
    }
  }

  function typeLine2() {
    if (idx2 < text2.length) {
      line2El.textContent += text2.charAt(idx2);
      idx2++;
      setTimeout(typeLine2, 34 + Math.random() * 14);
    }
  }

  // Allow preloader to clear before typing starts
  setTimeout(typeLine1, 400);
}

// ── 6. Footer Wordmark Dynamic Cursor Spotlight Highlight ──
function initWordmarkHighlight() {
  const wordmark = document.querySelector('.footer-wordmark');
  if (!wordmark) return;

  let rect = null;
  let targetX = 0;
  let targetY = 0;
  let currentX = 0;
  let currentY = 0;
  let lastX = 0;
  let lastY = 0;

  let targetIntensity = 0;
  let currentIntensity = 0;

  let targetRadius = 280;
  let currentRadius = 280;

  let targetRotX = 0;
  let targetRotY = 0;
  let currentRotX = 0;
  let currentRotY = 0;
  let targetLift = 0;
  let currentLift = 0;

  let isInside = false;
  let rafId = null;

  function updateRect() {
    rect = wordmark.getBoundingClientRect();
  }

  window.addEventListener('resize', updateRect, { passive: true });
  window.addEventListener('scroll', updateRect, { passive: true });

  wordmark.addEventListener('mouseenter', (e) => {
    isInside = true;
    targetIntensity = 1.0;
    updateRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    currentX = x;
    currentY = y;
    targetX = x;
    targetY = y;
    lastX = x;
    lastY = y;
    if (!rafId) rafId = requestAnimationFrame(animate);
  });

  wordmark.addEventListener('mousemove', (e) => {
    if (!rect) updateRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    targetX = x;
    targetY = y;
    targetIntensity = 1.0;

    // Velocity-reactive beam radius (dynamic spotlight expansion on movement)
    const dist = Math.hypot(x - lastX, y - lastY);
    targetRadius = Math.min(380, 260 + dist * 3.8);
    lastX = x;
    lastY = y;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    targetRotX = ((y - centerY) / centerY) * -6.5;
    targetRotY = ((x - centerX) / centerX) * 6.5;
    targetLift = 14;

    if (!rafId) rafId = requestAnimationFrame(animate);
  });

  wordmark.addEventListener('mouseleave', () => {
    isInside = false;
    targetIntensity = 0.0; // Silky smooth decay to 0!
    targetRadius = 260;
    targetRotX = 0;
    targetRotY = 0;
    targetLift = 0;
    if (!rafId) rafId = requestAnimationFrame(animate);
  });

  function animate(now) {
    // 1. Organic mouse position lerp
    currentX += (targetX - currentX) * 0.18;
    currentY += (targetY - currentY) * 0.18;

    // 2. Continuous silky smooth intensity fade (no snapping or instant disappear)
    currentIntensity += (targetIntensity - currentIntensity) * 0.08;

    // 3. Dynamic radius lerp + subtle breathing shimmer when hovering
    targetRadius += (270 - targetRadius) * 0.05; // gradually returns to baseline radius
    const shimmer = isInside ? Math.sin((now || performance.now()) * 0.0035) * 8 : 0;
    currentRadius += (targetRadius - currentRadius) * 0.12;

    // 4. 3D tilt & lift physics lerp
    currentRotX += (targetRotX - currentRotX) * 0.12;
    currentRotY += (targetRotY - currentRotY) * 0.12;
    currentLift += (targetLift - currentLift) * 0.12;

    const effectiveRadius = Math.max(120, currentRadius + shimmer);

    wordmark.style.setProperty('--mouse-x', `${currentX.toFixed(1)}px`);
    wordmark.style.setProperty('--mouse-y', `${currentY.toFixed(1)}px`);
    wordmark.style.setProperty('--spotlight-intensity', currentIntensity.toFixed(3));
    wordmark.style.setProperty('--spotlight-radius', `${effectiveRadius.toFixed(1)}px`);

    const scale = 1 + (currentLift / 14) * 0.025;
    wordmark.style.transform = `perspective(1000px) rotateX(${currentRotX.toFixed(2)}deg) rotateY(${currentRotY.toFixed(2)}deg) translateZ(${currentLift.toFixed(1)}px) scale(${scale.toFixed(3)})`;

    // Only shut off the animation loop when intensity is essentially 0 and physics is rested
    if (!isInside && currentIntensity < 0.005 && Math.abs(currentRotX) < 0.05 && Math.abs(currentRotY) < 0.05 && Math.abs(currentLift) < 0.05) {
      wordmark.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px) scale(1)';
      wordmark.style.setProperty('--spotlight-intensity', '0');
      currentIntensity = 0;
      rafId = null;
      return;
    }

    rafId = requestAnimationFrame(animate);
  }
}
