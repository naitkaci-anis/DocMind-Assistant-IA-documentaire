/**
 * stars.js — Galaxy background v3
 * Fond galaxie : étoiles scintillantes + faisceau violet + nébuleuses + étoiles filantes
 */
(function () {
    const canvas = document.getElementById('stars-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let stars    = [];
    let shooters = [];
    let nebulas  = [];

    /* ── Resize ───────────────────────────────────────── */
    function resize() {
        canvas.width  = window.innerWidth;
        canvas.height = window.innerHeight;
        initStars();
        initNebulas();
    }

    /* ── Init stars ───────────────────────────────────── */
    function initStars() {
        const W = canvas.width, H = canvas.height;
        const count = Math.min(Math.floor((W * H) / 3200), 380);
        stars = Array.from({ length: count }, () => ({
            x     : Math.random() * W,
            y     : Math.random() * H,
            r     : Math.random() * 1.5 + 0.2,
            phase : Math.random() * Math.PI * 2,
            speed : Math.random() * 0.007 + 0.002,
            bright: Math.random() * 0.55 + 0.35,
        }));
    }

    /* ── Init nebulas ─────────────────────────────────── */
    function initNebulas() {
        const W = canvas.width, H = canvas.height;
        nebulas = [
            { x: W * .72, y: H * .18, r: W * .28, c: [120, 40, 220], a: .07 },
            { x: W * .2,  y: H * .78, r: W * .22, c: [40, 100, 200], a: .055 },
            { x: W * .5,  y: H * .5,  r: W * .35, c: [90, 20, 160],  a: .04 },
        ];
    }

    /* ── Shooting star ────────────────────────────────── */
    function spawnShooter() {
        const W = canvas.width;
        shooters.push({
            x    : Math.random() * W * 1.2 - W * .1,
            y    : Math.random() * 80,
            vx   : -(Math.random() * 4 + 3),
            vy   : Math.random() * 3 + 2,
            life : 0,
            maxL : Math.random() * 60 + 50,
            tail : [],
        });
    }

    /* ── Draw background ──────────────────────────────── */
    function drawBackground() {
        const W = canvas.width, H = canvas.height;
        const g = ctx.createRadialGradient(W / 2, -H * .06, 0, W / 2, H / 2, H * 1.1);
        g.addColorStop(0,   '#1a0040');
        g.addColorStop(.18, '#0e0028');
        g.addColorStop(.5,  '#07001c');
        g.addColorStop(1,   '#03000a');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);
    }

    /* ── Draw nebulas ─────────────────────────────────── */
    function drawNebulas(t) {
        nebulas.forEach((n, i) => {
            const pulse = 1 + .08 * Math.sin(t * .0004 + i * 1.8);
            const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * pulse);
            g.addColorStop(0,   `rgba(${n.c[0]},${n.c[1]},${n.c[2]},${n.a})`);
            g.addColorStop(.5,  `rgba(${n.c[0]},${n.c[1]},${n.c[2]},${n.a * .4})`);
            g.addColorStop(1,   'transparent');
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.r * pulse, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    /* ── Draw central beam ────────────────────────────── */
    function drawBeam(t) {
        const W = canvas.width, H = canvas.height;
        const p = .72 + .28 * Math.sin(t * .0007);
        const b = ctx.createRadialGradient(W / 2, 0, 0, W / 2, H * .38, W * .42 * p);
        b.addColorStop(0,   `rgba(140, 55, 240, ${.24 * p})`);
        b.addColorStop(.4,  `rgba(100, 35, 200, ${.09 * p})`);
        b.addColorStop(1,   'transparent');
        ctx.fillStyle = b;
        ctx.fillRect(0, 0, W, H);
    }

    /* ── Draw stars ───────────────────────────────────── */
    function drawStars(t) {
        stars.forEach(s => {
            const op = s.bright * (.35 + .65 * (.5 + .5 * Math.sin(t * s.speed + s.phase)));
            if (s.r > 1.1 && op > .65) {
                const h = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 4.5);
                h.addColorStop(0,   `rgba(210,185,255,${op * .38})`);
                h.addColorStop(1,   'transparent');
                ctx.beginPath();
                ctx.arc(s.x, s.y, s.r * 4.5, 0, Math.PI * 2);
                ctx.fillStyle = h;
                ctx.fill();
            }
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(235,215,255,${op})`;
            ctx.fill();
        });
    }

    /* ── Draw shooting stars ──────────────────────────── */
    function drawShooters() {
        shooters = shooters.filter(s => s.life < s.maxL);
        shooters.forEach(s => {
            s.tail.push({ x: s.x, y: s.y });
            if (s.tail.length > 18) s.tail.shift();
            s.x += s.vx; s.y += s.vy; s.life++;

            if (s.tail.length < 2) return;
            ctx.beginPath();
            ctx.moveTo(s.tail[0].x, s.tail[0].y);
            s.tail.forEach(p => ctx.lineTo(p.x, p.y));
            const g = ctx.createLinearGradient(s.tail[0].x, s.tail[0].y, s.x, s.y);
            g.addColorStop(0,   'rgba(200,170,255,0)');
            g.addColorStop(1,   `rgba(230,210,255,${.7 * (1 - s.life / s.maxL)})`);
            ctx.strokeStyle = g;
            ctx.lineWidth   = 1.2;
            ctx.stroke();
        });
    }

    /* ── Main loop ────────────────────────────────────── */
    let lastShooter = 0;
    function loop(t) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawBackground();
        drawNebulas(t);
        drawBeam(t);
        drawStars(t);
        drawShooters();

        if (t - lastShooter > 4500 + Math.random() * 5000) {
            spawnShooter();
            lastShooter = t;
        }
        requestAnimationFrame(loop);
    }

    /* Exposé pour le toggle de thème — la visibilité réelle est gérée via CSS
     * ([data-theme="light"] #stars-canvas { opacity: .05 }).
     * Cette fonction permet une future personnalisation côté canvas. */
    window.setStarsTheme = function (mode) {
        canvas.style.opacity = mode === 'light' ? '0.05' : '';
    };

    window.addEventListener('resize', resize);
    resize();
    requestAnimationFrame(loop);
})();
