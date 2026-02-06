import './style.css'
import './cat-stats.css'


document.addEventListener('DOMContentLoaded', () => {
  // Custom Cursor
  const cursorDot = document.querySelector('[data-cursor-dot]');
  const cursorOutline = document.querySelector('[data-cursor-outline]');

  window.addEventListener('mousemove', function (e) {
    const posX = e.clientX;
    const posY = e.clientY;

    // Dot follows instantly
    cursorDot.style.left = `${posX}px`;
    cursorDot.style.top = `${posY}px`;

    // Outline follows with slight delay/animation (via keyframes logic or just transform)
    // Here using animate for smooth trailing effect
    cursorOutline.animate({
      left: `${posX}px`,
      top: `${posY}px`
    }, { duration: 500, fill: "forwards" });
  });

  // Video Playlist Logic
  const videoPlayer = document.querySelector('.hero-video');
  const videos = [
    '/Cinematic_BIM_Kitchen_Deconstruction_Animation.mp4',
    '/Architectural_Film_Generation_Request.mp4',
    '/Architectural_Video_Generation_Request.mp4'
  ];
  let currentVideoIndex = 0;

  if (videoPlayer) {
    videoPlayer.addEventListener('ended', () => {
      currentVideoIndex = (currentVideoIndex + 1) % videos.length;
      videoPlayer.src = videos[currentVideoIndex];
      videoPlayer.play();
    });
  }

  // Scroll Reveal Logic (Logo Cutout Effect)
  const revealSection = document.getElementById('video-reveal-section');
  const maskOverlay = document.querySelector('.mask-overlay');
  const solidLogoOverlay = document.querySelector('.solid-logo-overlay');

  if (revealSection && maskOverlay && solidLogoOverlay) {
    window.addEventListener('scroll', () => {
      const sectionTop = revealSection.offsetTop;
      const sectionHeight = revealSection.offsetHeight;
      const scrollY = window.scrollY;
      const windowHeight = window.innerHeight;

      // Calculate progress: 0 when wrapper hits top, 1 when scrolling past
      const start = sectionTop;
      const end = sectionTop + sectionHeight - windowHeight;

      let progress = (scrollY - start) / (end - start);
      progress = Math.max(0, Math.min(1, progress));

      // 1. Curtain Rises UP (Clip the bottom of the black mask)
      // At 0% progress: inset(0 0 0% 0) -> Full mask visible
      // At 100% progress: inset(0 0 100% 0) -> Mask completely cropped from bottom up
      const clipValue = progress * 100;
      maskOverlay.style.clipPath = `inset(0 0 ${clipValue}% 0)`;
      maskOverlay.style.webkitClipPath = `inset(0 0 ${clipValue}% 0)`;

      // Keep opacity 1 so we see the sharp edge
      maskOverlay.style.opacity = 1;

      // 2. Fade IN the White Logo (Wait until mask is mostly gone)
      let logoOpacity = (progress - 0.5) * 2.0;
      solidLogoOverlay.style.opacity = Math.max(0, Math.min(1, logoOpacity));
    });
  }

  // Intersection Observer for fade-in animations on scroll
  const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
  };

  const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target); // Only animate once
      }
    });
  }, observerOptions);

  const targets = document.querySelectorAll('.fade-on-scroll');
  targets.forEach(target => {
    observer.observe(target);
  });

  // ==========================================
  // TEXT REVEAL SCROLL ANIMATION
  // ==========================================
  const visionSection = document.getElementById('vision-scroll-section');
  const textContainer = document.getElementById('reveal-text');

  if (visionSection && textContainer) {
    // 1. Split text into words
    const text = textContainer.innerText;
    textContainer.innerHTML = ''; // Clear default text
    const words = text.split(' ');

    // Create spans
    words.forEach(word => {
      const span = document.createElement('span');
      span.textContent = word;
      span.classList.add('reveal-word');
      textContainer.appendChild(span);
    });

    const spans = document.querySelectorAll('.reveal-word');

    // Simplified Reveal using Intersection Observer for Robustness
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Animate words rapidly
          const spans = document.querySelectorAll('.reveal-word');
          spans.forEach((span, i) => {
            setTimeout(() => span.classList.add('active'), i * 50);
          });

          // Animate Signature
          const signature = document.getElementById('reveal-signature');
          if (signature) signature.classList.add('active');

          // Animate Stats
          const stats = document.getElementById('stats-counter');
          if (stats && !stats.classList.contains('animated')) {
            stats.classList.add('active');
            stats.classList.add('animated');

            const pCount = window.aoStats?.projects || 50;
            const sqmCount = window.aoStats?.sqm || 1500351;

            animateValue("stat-projects", 0, pCount, 2000, "+");
            animateValue("stat-countries", 0, 2, 1000, "");
            animateValue("stat-sqm", 0, sqmCount, 2500, "+");
          }

          // Unobserve after triggering
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 }); // Trigger when 30% visible

    if (visionSection) {
      revealObserver.observe(visionSection);
    }
  }

  // FORCE MENU COLLAPSE ON SCROLL
  // If user scrolls, we want the "curtain" to disappear even if mouse is hovering
  // or generally to give the feel that it reveals the video.
  const mainHeader = document.getElementById('main-header');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      mainHeader.classList.add('force-collapse');
    } else {
      mainHeader.classList.remove('force-collapse');
    }
  });
});

// Helper Function for Counting Animation
function animateValue(id, start, end, duration, prefix = "") {
  const obj = document.getElementById(id);
  if (!obj) return;

  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);

    const value = Math.floor(progress * (end - start) + start);
    // Format nicely with commas
    const formatted = value.toLocaleString();
    obj.innerHTML = prefix + formatted;

    if (progress < 1) {
      window.requestAnimationFrame(step);
    } else {
      // Ensure final value is exact
      const finalFormatted = end.toLocaleString();
      obj.innerHTML = prefix + finalFormatted;
    }
  };
  window.requestAnimationFrame(step);
}

// VIDEO CAROUSEL LOGIC
document.addEventListener('DOMContentLoaded', () => {
  const videos = document.querySelectorAll('.carousel-track .hero-video');
  let currentIndex = 0;

  if (videos.length > 0) {
    // Ensure first video plays
    videos[0].play();

    // Initial text set handled by HTML, but good to ensure sync if needed

    videos.forEach((video, index) => {
      video.addEventListener('ended', () => {
        // Determine next index loop
        const nextIndex = (index + 1) % videos.length;
        const nextVideo = videos[nextIndex];

        // Switch classes for fade effect
        videos[index].classList.remove('active');
        nextVideo.classList.add('active');

        // Play next video
        // Using load() ensures the video is reset and ready to play from the start
        nextVideo.load();
        const playPromise = nextVideo.play();

        if (playPromise !== undefined) {
          playPromise.catch(error => {
            console.error("Auto-play was prevented:", error);
            // Retry with load() to reset internal state completely
            nextVideo.load();
            nextVideo.play().catch(e => console.error("Retry failed:", e));
          });
        }

        // Update Title Text with Fade
        const mainTitle = document.querySelector('.main-title');
        if (mainTitle && nextVideo.dataset.text) {
          mainTitle.style.opacity = 0;
          setTimeout(() => {
            mainTitle.innerText = nextVideo.dataset.text;
            mainTitle.style.opacity = 1;
          }, 500); // Wait for fade out
        }
      });
    });
  }
});

// SPARKLE EFFECT
document.addEventListener('DOMContentLoaded', () => {
  const bg = document.getElementById('sparkle-bg');
  if (!bg) return;

  // Create random stars initially
  for (let i = 0; i < 30; i++) { // Initial population
    const x = Math.random() * window.innerWidth;
    const y = Math.random() * window.innerHeight;
    createSparkle(x, y, bg, false);
  }

  // Mouse Move
  window.addEventListener('mousemove', (e) => {
    if (Math.random() > 0.85) {
      const rect = bg.getBoundingClientRect();
      if (e.clientY >= rect.top && e.clientY <= rect.bottom) {
        createSparkle(e.clientX, e.clientY - rect.top, bg, true);
      }
    }
  });
});

function createSparkle(x, y, container, animated) {
  const sparkle = document.createElement('div');
  const size = Math.random() * 3 + 1;
  sparkle.style.position = 'absolute';
  sparkle.style.left = x + 'px';
  sparkle.style.top = y + 'px';
  sparkle.style.width = size + 'px';
  sparkle.style.height = size + 'px';
  sparkle.style.background = 'white';
  sparkle.style.borderRadius = '50%';
  sparkle.style.pointerEvents = 'none';
  sparkle.style.opacity = Math.random();
  sparkle.style.boxShadow = `0 0 ${size * 2}px white`;

  if (animated) {
    sparkle.style.transition = 'opacity 1s ease-out, transform 1s ease-out';
    setTimeout(() => {
      sparkle.style.opacity = '0';
      sparkle.style.transform = `translate(${Math.random() * 20 - 10}px, ${Math.random() * 20 - 10}px)`;
    }, 50);
    setTimeout(() => sparkle.remove(), 1000);
  } else {
    // Static twinkling
    sparkle.style.animation = `twinkle ${Math.random() * 3 + 2}s infinite alternate`;
  }

  container.appendChild(sparkle);
}

// Global CSS for twinkle needs to be injected or present
const style = document.createElement('style');
style.innerHTML = `
  @keyframes twinkle {
    0% { opacity: 0.2; transform: scale(1); }
    100% { opacity: 1; transform: scale(1.2); }
  }
`;
document.head.appendChild(style);

// Category Stats Logic
document.addEventListener('DOMContentLoaded', () => {
  fetchStats();
});

async function fetchStats() {
  console.log("Fetching stats from backend...");
  try {
    const response = await fetch('/api/projects/stats', {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      console.error('Failed to fetch stats:', response.statusText);
      return;
    }

    const data = await response.json();
    console.log("Stats received:", data);

    const categories = data.categories;

    // Update Global Stats
    if (data.global) {
      window.aoStats = {
        projects: data.global.total_projects,
        sqm: data.global.total_sqm
      };

      // Immediate DOM update for global counters if they are already visible or animated
      const pEl = document.getElementById('stat-projects');
      const sEl = document.getElementById('stat-sqm');

      // Check if parent container has 'animated' class (from main logic) or just force update
      // We'll verify if window.aoStats was set in time.
      if (pEl) {
        // If it's already "50" or "+50", update it. 
        // If animation running, window.aoStats will be picked up? No, animation logic runs once.
        // We should force update the text content just in case.
        if (pEl.innerHTML.includes("+")) {
          // Only update if it looks like it finished or is static
          pEl.innerHTML = "+" + data.global.total_projects.toLocaleString();
          sEl.innerHTML = "+" + data.global.total_sqm.toLocaleString();
        }
      }
    }

    // Animate Category Stats
    const catSection = document.getElementById('project-categories');

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCategoryStats(categories);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });

    if (catSection) {
      observer.observe(catSection);
    }

  } catch (error) {
    console.error('Error fetching stats:', error);
  }
}

function animateCategoryStats(categories) {
  if (!categories) return;

  for (const [key, stats] of Object.entries(categories)) {
    // key is residential, commercial, etc.
    const sqmElements = document.querySelectorAll(`.cat-stat-sqm[data-cat="${key}"]`);
    const countElements = document.querySelectorAll(`.cat-stat-count[data-cat="${key}"]`);

    sqmElements.forEach(el => {
      animateValueInternal(el, 0, stats.sqm, 2000, "");
    });

    countElements.forEach(el => {
      animateValueInternal(el, 0, stats.count, 1500, "");
    });
  }
}

function animateValueInternal(obj, start, end, duration, prefix = "") {
  if (!obj) return;
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    const value = Math.floor(progress * (end - start) + start);
    obj.innerHTML = prefix + value.toLocaleString();
    if (progress < 1) {
      window.requestAnimationFrame(step);
    } else {
      obj.innerHTML = prefix + end.toLocaleString();
    }
  };
  window.requestAnimationFrame(step);
}

