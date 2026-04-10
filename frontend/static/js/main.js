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
      '<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-xs font-bold text-slate-950">K</div>';
    var bubbleAgent =
      "max-w-[88%] rounded-2xl rounded-bl-md border border-slate-600/50 bg-slate-800/90 px-3.5 py-2.5 text-sm leading-relaxed text-slate-200 shadow-sm";
    var bubbleUser = "max-w-[88%] rounded-2xl rounded-br-md bg-gradient-to-br from-emerald-600 to-teal-600 px-3.5 py-2.5 text-sm leading-relaxed text-white shadow-md";

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
        '<div class="flex gap-1 rounded-2xl rounded-bl-md border border-slate-600/50 bg-slate-800/80 px-4 py-3">' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay:0ms"></span>' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay:120ms"></span>' +
        '<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style="animation-delay:240ms"></span>' +
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
})();
