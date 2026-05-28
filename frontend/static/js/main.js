/**
 * Klyro — shared UI utilities & marketing interactions
 */
(function () {
  "use strict";

  var API_BASE = "";
  var TOKEN_KEY = "klyro_token";
  var LEGACY_TOKEN_KEY = "chatsite_token";

  function getAuthToken() {
    var t = localStorage.getItem(TOKEN_KEY);
    if (t) return t;
    var legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
    if (legacy) {
      localStorage.setItem(TOKEN_KEY, legacy);
      localStorage.removeItem(LEGACY_TOKEN_KEY);
      return legacy;
    }
    return null;
  }

  window.CS = window.CS || {};

  window.CS.apiBase = function () {
    return API_BASE;
  };

  window.CS.apiFetch = function (path, options) {
    options = options || {};
    var headers = options.headers || {};
    var token = getAuthToken();
    if (token && !headers.Authorization) {
      headers.Authorization = "Bearer " + token;
    }
    if (!headers["Content-Type"] && options.body && typeof options.body === "string") {
      headers["Content-Type"] = "application/json";
    }
    return fetch(API_BASE + path, Object.assign({}, options, { headers: headers }));
  };

  window.CS.toast = function (message, type) {
    type = type || "info";
    var root = document.getElementById("toast-root");
    if (!root) return;
    var el = document.createElement("div");
    el.className =
      "kly-toast-item cs-toast-item rounded-xl border px-4 py-3 text-sm shadow-lg " +
      (type === "error"
        ? "border-red-500/40 bg-red-950/90 text-red-100"
        : type === "success"
          ? "border-emerald-500/40 bg-emerald-950/90 text-emerald-100"
          : "border-slate-600 bg-slate-900/95 text-slate-100");
    el.textContent = message;
    root.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transform = "translateY(8px)";
      el.style.transition = "all 0.3s ease";
      setTimeout(function () {
        el.remove();
      }, 300);
    }, 4000);
  };

  window.CS.initTiltCards = function () {
    document.querySelectorAll("[data-tilt]").forEach(function (card) {
      card.addEventListener("mousemove", function (e) {
        var r = card.getBoundingClientRect();
        var x = e.clientX - r.left;
        var y = e.clientY - r.top;
        var midX = r.width / 2;
        var midY = r.height / 2;
        var rx = ((y - midY) / midY) * -6;
        var ry = ((x - midX) / midX) * 6;
        card.style.transform =
          "perspective(900px) rotateX(" + rx + "deg) rotateY(" + ry + "deg) scale3d(1.02,1.02,1.02)";
      });
      card.addEventListener("mouseleave", function () {
        card.style.transform = "";
      });
    });
  };

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  window.CS.initHeroLiveChat = function () {
    var root = document.getElementById("hero-chat-messages");
    if (!root) return;

    var reduced =
      typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    var avatarAgent =
      '<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 text-xs font-bold text-white">K</div>';
    var bubbleAgent =
      "max-w-[88%] rounded-2xl rounded-bl-md border px-3.5 py-2.5 text-sm leading-relaxed shadow-sm";
    var bubbleAgentStyle = "border-color:rgba(148,163,184,0.12);background:rgba(10,22,40,0.9);color:#cbd5e1";
    var bubbleUser = "max-w-[88%] rounded-2xl rounded-br-md px-3.5 py-2.5 text-sm leading-relaxed text-white shadow-md";
    var bubbleUserStyle = "background:linear-gradient(135deg,#06b6d4,#8b5cf6)";

    function scrollToBottom() {
      root.scrollTop = root.scrollHeight;
    }

    function addAgent(text) {
      var row = document.createElement("div");
      row.className = "flex justify-start kly-hero-msg";
      row.innerHTML =
        '<div class="flex max-w-[95%] items-end gap-2">' +
        avatarAgent +
        '<div class="' +
        bubbleAgent +
        '" style="' +
        bubbleAgentStyle +
        '">' +
        escapeHtml(text) +
        "</div></div>";
      root.appendChild(row);
      scrollToBottom();
    }

    function addUser(text) {
      var row = document.createElement("div");
      row.className = "flex justify-end kly-hero-msg";
      row.innerHTML = '<div class="' + bubbleUser + '" style="' + bubbleUserStyle + '">' + escapeHtml(text) + "</div>";
      root.appendChild(row);
      scrollToBottom();
    }

    var typingId = "hero-typing-indicator";

    function showTyping() {
      removeTyping();
      var row = document.createElement("div");
      row.id = typingId;
      row.className = "flex justify-start kly-hero-msg";
      row.innerHTML =
        '<div class="flex items-end gap-2">' +
        avatarAgent +
        '<div class="flex gap-1 rounded-2xl rounded-bl-md border px-4 py-3 shadow-sm" style="border-color:rgba(148,163,184,0.12);background:rgba(10,22,40,0.9)">' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-400/60" style="animation-delay:0ms"></span>' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-400/60" style="animation-delay:120ms"></span>' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-400/60" style="animation-delay:240ms"></span>' +
        "</div></div>";
      root.appendChild(row);
      scrollToBottom();
    }

    function removeTyping() {
      var t = document.getElementById(typingId);
      if (t) t.remove();
    }

    function runSequence(done) {
      root.innerHTML = "";
      addAgent("Hi — I'm trained on this site. Ask about pricing, setup, or how we compare.");
      if (reduced) {
        addUser("How fast can we go live?");
        addAgent("Most teams ship in under 10 minutes: add your URL, train, then paste one script.");
        setTimeout(done, 2800);
        return;
      }
      setTimeout(function () {
        addUser("Can it match our brand?");
      }, 900);
      setTimeout(function () {
        showTyping();
      }, 1900);
      setTimeout(function () {
        removeTyping();
        addAgent("Yes — tone, colors, and lead capture feel native. You control what the model sees.");
      }, 3000);
      setTimeout(function () {
        addUser("How fast to go live?");
      }, 4500);
      setTimeout(function () {
        showTyping();
      }, 5400);
      setTimeout(function () {
        removeTyping();
        addAgent("Usually under 10 minutes: crawl your pages, embed, then drop in the widget snippet.");
      }, 6600);
      setTimeout(done, 10500);
    }

    function loop() {
      runSequence(function () {
        setTimeout(function () {
          loop();
        }, 2200);
      });
    }

    setTimeout(loop, 500);
  };

  /* ────────────────────────────────────────────────────
     FAQ Accordion
  ──────────────────────────────────────────────────── */
  window.CS.initFaqAccordion = function () {
    document.querySelectorAll(".kly-faq-item").forEach(function (item) {
      var btn = item.querySelector(".kly-faq-btn");
      var answer = item.querySelector(".kly-faq-answer");
      if (!btn || !answer) return;
      btn.addEventListener("click", function () {
        var isOpen = answer.classList.contains("kly-faq-open");
        // close all
        document.querySelectorAll(".kly-faq-answer").forEach(function (a) {
          a.classList.remove("kly-faq-open");
          var parent = a.closest(".kly-faq-item");
          if (parent) parent.classList.remove("kly-faq-open-parent");
        });
        // open clicked one (if it was closed)
        if (!isOpen) {
          answer.classList.add("kly-faq-open");
          item.classList.add("kly-faq-open-parent");
          // scroll into view if partially hidden
          setTimeout(function () {
            var rect = item.getBoundingClientRect();
            if (rect.bottom > window.innerHeight) {
              item.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
          }, 440);
        }
      });
    });
  };

  /* ────────────────────────────────────────────────────
     Scroll Reveal  (IntersectionObserver)
  ──────────────────────────────────────────────────── */
  window.CS.initScrollReveal = function () {
    var els = document.querySelectorAll(".kly-reveal");
    if (!els.length) return;
    if (!("IntersectionObserver" in window)) {
      // fallback: show all immediately
      els.forEach(function (el) { el.classList.add("kly-visible"); });
      return;
    }
    var obs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("kly-visible");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -48px 0px" }
    );
    els.forEach(function (el) { obs.observe(el); });
  };

  /* ────────────────────────────────────────────────────
     Counter animation  (count-up on scroll-into-view)
  ──────────────────────────────────────────────────── */
  window.CS.initCounters = function () {
    var els = document.querySelectorAll("[data-counter]");
    if (!els.length) return;
    if (!("IntersectionObserver" in window)) return;
    var obs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          var el = e.target;
          var target = parseInt(el.getAttribute("data-counter"), 10);
          var duration = 1600;
          var startTime = null;
          function tick(now) {
            if (!startTime) startTime = now;
            var elapsed = now - startTime;
            var progress = Math.min(elapsed / duration, 1);
            // ease-out-cubic
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(eased * target);
            if (progress < 1) requestAnimationFrame(tick);
          }
          requestAnimationFrame(tick);
          obs.unobserve(el);
        });
      },
      { threshold: 0.5 }
    );
    els.forEach(function (el) { obs.observe(el); });
  };

  /* ──────────────────────────────────────────────────────
     Scroll-flip feature cards  (3D perspective rise on scroll)
  ──────────────────────────────────────────────────────── */
  window.CS.initFlipCards = function () {
    var cards = document.querySelectorAll(".kly-flip-card");
    if (!cards.length) return;

    var obs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("kly-card-visible");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -48px 0px" }
    );

    cards.forEach(function (card) { obs.observe(card); });
  };

  window.CS.initHeroGsap = function () {
    if (!window.gsap) return;
    var tl = gsap.timeline({ delay: 0.1 });
    tl.from('#kly-hero-badge', { opacity: 0, y: 20, duration: 0.6, ease: 'power3.out' })
      .from('#kly-hero-h1 .kly-h1-line', {
        opacity: 0, y: 40, stagger: 0.12, duration: 0.8, ease: 'power3.out'
      }, '-=0.3')
      .from('#kly-hero-sub', { opacity: 0, y: 20, duration: 0.6, ease: 'power3.out' }, '-=0.4')
      .from('#kly-hero-ctas', { opacity: 0, y: 16, duration: 0.5, ease: 'power3.out' }, '-=0.3')
      .from('#kly-hero-proof', { opacity: 0, y: 12, duration: 0.4, ease: 'power3.out' }, '-=0.2')
      .from('#kly-hero-widget', { opacity: 0, x: 40, duration: 0.9, ease: 'power3.out' }, '-=0.7');
  };

  window.CS.initGsapScroll = function () {
    if (!window.gsap || !window.ScrollTrigger) return;
    gsap.registerPlugin(ScrollTrigger);

    gsap.utils.toArray('.kly-bento').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 85%', once: true },
        opacity: 0, y: 40, scale: 0.97,
        duration: 0.7, delay: i * 0.06, ease: 'power3.out'
      });
    });

    gsap.utils.toArray('.kly-pricing-card').forEach(function (el, i) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', once: true },
        opacity: 0, y: 50, duration: 0.75, delay: i * 0.1, ease: 'power3.out'
      });
    });

    gsap.utils.toArray('.kly-section-head').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', once: true },
        opacity: 0, y: 30, duration: 0.7, ease: 'power3.out'
      });
    });
  };

  window.CS.initMagnetic = function () {
    document.querySelectorAll('.kly-magnetic').forEach(function (btn) {
      btn.addEventListener('mousemove', function (e) {
        var rect = btn.getBoundingClientRect();
        var cx = rect.left + rect.width / 2;
        var cy = rect.top + rect.height / 2;
        var dx = (e.clientX - cx) * 0.35;
        var dy = (e.clientY - cy) * 0.35;
        btn.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
      });
      btn.addEventListener('mouseleave', function () {
        btn.style.transform = '';
      });
    });
  };

  window.CS.initGsapCounters = function () {
    if (!window.gsap || !window.ScrollTrigger) return;
    document.querySelectorAll('.kly-gsap-counter').forEach(function (el) {
      var target = parseFloat(el.dataset.target || el.textContent);
      var prefix = el.dataset.prefix || '';
      var suffix = el.dataset.suffix || '';
      ScrollTrigger.create({
        trigger: el, start: 'top 85%', once: true,
        onEnter: function () {
          gsap.from({ n: 0 }, {
            n: target, duration: 2, ease: 'power2.out',
            onUpdate: function () {
              el.textContent = prefix + Math.round(this.targets()[0].n).toLocaleString() + suffix;
            }
          });
        }
      });
    });
  };
})();
