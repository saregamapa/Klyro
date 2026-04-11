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
      "cs-toast-item rounded-xl border px-4 py-3 text-sm shadow-lg " +
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
      '<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-xs font-bold text-white">K</div>';
    var bubbleAgent =
      "max-w-[88%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-3.5 py-2.5 text-sm leading-relaxed text-slate-700 shadow-sm";
    var bubbleUser = "max-w-[88%] rounded-2xl rounded-br-md bg-gradient-to-br from-indigo-500 to-violet-600 px-3.5 py-2.5 text-sm leading-relaxed text-white shadow-md";

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
        '">' +
        escapeHtml(text) +
        "</div></div>";
      root.appendChild(row);
      scrollToBottom();
    }

    function addUser(text) {
      var row = document.createElement("div");
      row.className = "flex justify-end kly-hero-msg";
      row.innerHTML = '<div class="' + bubbleUser + '">' + escapeHtml(text) + "</div>";
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
        '<div class="flex gap-1 rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300" style="animation-delay:0ms"></span>' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300" style="animation-delay:120ms"></span>' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300" style="animation-delay:240ms"></span>' +
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
})();
