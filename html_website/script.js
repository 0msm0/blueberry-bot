/**
 * Blueberry Bot Landing Page - Interactive Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initCounterAnimation();
    initScrollAnimations();
    initSmoothScroll();
    initNavbarScroll();
});

/**
 * Create floating particles in the background
 */
function initParticles() {
    const particlesContainer = document.getElementById('particles');
    const particleCount = 30;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';

        // Random position
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';

        // Random size
        const size = Math.random() * 6 + 2;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';

        // Random animation delay and duration
        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = (Math.random() * 20 + 10) + 's';

        // Random color variation
        const colors = ['#6366f1', '#8b5cf6', '#06b6d4', '#818cf8'];
        particle.style.background = colors[Math.floor(Math.random() * colors.length)];

        particlesContainer.appendChild(particle);
    }
}

/**
 * Animate counter numbers when they come into view
 */
function initCounterAnimation() {
    const counters = document.querySelectorAll('.stat-number');
    let animated = false;

    const animateCounters = () => {
        if (animated) return;

        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-target'));
            const duration = 2000; // 2 seconds
            const increment = target / (duration / 16); // 60fps
            let current = 0;

            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    counter.textContent = Math.ceil(current);
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target;
                    // Add + sign for some numbers
                    if (target === 100) {
                        counter.textContent = target + '%';
                    } else if (target > 10) {
                        counter.textContent = target + '+';
                    }
                }
            };

            updateCounter();
        });

        animated = true;
    };

    // Use Intersection Observer to trigger animation when stats are visible
    const statsSection = document.querySelector('.hero-stats');
    if (statsSection) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounters();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        observer.observe(statsSection);
    }
}

/**
 * Animate elements when they scroll into view
 */
function initScrollAnimations() {
    // Add animate-on-scroll class to elements
    const animateElements = document.querySelectorAll(
        '.feature-card, .step, .transform-before, .transform-after, .main-quote'
    );

    animateElements.forEach(el => {
        el.classList.add('animate-on-scroll');
    });

    // Create intersection observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');

                // Add staggered delay for feature cards
                if (entry.target.classList.contains('feature-card')) {
                    const cards = document.querySelectorAll('.feature-card');
                    cards.forEach((card, index) => {
                        card.style.transitionDelay = (index * 0.1) + 's';
                    });
                }
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    animateElements.forEach(el => observer.observe(el));
}

/**
 * Smooth scroll for anchor links
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Navbar background change on scroll
 */
function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        // Add/remove solid background based on scroll position
        if (currentScroll > 100) {
            navbar.style.background = 'rgba(15, 23, 42, 0.95)';
        } else {
            navbar.style.background = 'rgba(15, 23, 42, 0.8)';
        }

        lastScroll = currentScroll;
    });
}

/**
 * Add hover effect to feature cards
 */
document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('mouseenter', function(e) {
        // Create ripple effect
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            background: radial-gradient(circle at ${e.offsetX}px ${e.offsetY}px,
                rgba(99, 102, 241, 0.1) 0%, transparent 50%);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;

        this.style.position = 'relative';
        this.appendChild(ripple);

        requestAnimationFrame(() => {
            ripple.style.opacity = '1';
        });
    });

    card.addEventListener('mouseleave', function() {
        const ripple = this.querySelector('div[style*="radial-gradient"]');
        if (ripple) {
            ripple.style.opacity = '0';
            setTimeout(() => ripple.remove(), 300);
        }
    });
});

/**
 * Parallax effect for hero section
 */
window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const hero = document.querySelector('.hero-visual');

    if (hero && scrolled < window.innerHeight) {
        hero.style.transform = `translateY(${scrolled * 0.1}px)`;
    }
});

/**
 * Add typing effect to chat messages (replay on click)
 */
const phoneScreen = document.querySelector('.phone-screen');
if (phoneScreen) {
    phoneScreen.addEventListener('click', () => {
        const messages = phoneScreen.querySelectorAll('.chat-message');
        const typing = phoneScreen.querySelector('.typing-indicator');

        // Reset animations
        messages.forEach((msg, i) => {
            msg.style.animation = 'none';
            msg.offsetHeight; // Trigger reflow
            msg.style.animation = `messageIn 0.5s ease ${0.5 + i}s backwards`;
        });

        if (typing) {
            typing.style.animation = 'none';
            typing.offsetHeight;
            typing.style.animation = 'messageIn 0.5s ease 3.5s backwards';
        }
    });
}

// Console easter egg
console.log('%c🫐 Blueberry Bot', 'font-size: 24px; font-weight: bold; color: #6366f1;');
console.log('%cTake control of your daily life!', 'font-size: 14px; color: #8b5cf6;');
console.log('%cVisit us on Telegram: https://t.me/YourBlueberryBot', 'font-size: 12px; color: #64748b;');
