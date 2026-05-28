/**
 * Klyro — Stripe checkout & billing UI
 */
(function () {
  "use strict";

  var TOKEN_KEY = "klyro_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function authHeaders() {
    var t = getToken();
    if (!t) return null;
    return { Authorization: "Bearer " + t, "Content-Type": "application/json" };
  }

  function requireAuth() {
    if (!getToken()) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
      return false;
    }
    return true;
  }

  async function startCheckout(plan) {
    var h = authHeaders();
    if (!h) return;
    try {
      var res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        headers: h,
        body: JSON.stringify({ plan: plan }),
      });
      var data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) throw new Error(data.detail || "Checkout failed");
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (err) {
      if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
    }
  }

  window.KlyroBilling = {
    initPricingPage: function () {
      document.querySelectorAll("[data-checkout-plan]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (!requireAuth()) return;
          var plan = btn.getAttribute("data-checkout-plan");
          if (plan) startCheckout(plan);
        });
      });
    },

    initAccountPage: function () {
      if (!requireAuth()) return;
      var loading = document.getElementById("billing-loading");
      var panel = document.getElementById("billing-panel");
      var h = authHeaders();

      Promise.all([
        fetch("/api/v1/billing/subscription", { headers: h }).then(function (r) {
          return r.json();
        }),
        fetch("/api/v1/billing/usage", { headers: h }).then(function (r) {
          return r.json();
        }),
      ])
        .then(function (results) {
          var sub = results[0];
          var usage = results[1];
          if (loading) loading.classList.add("hidden");
          if (panel) panel.classList.remove("hidden");
          var planEl = document.getElementById("billing-plan");
          var statusEl = document.getElementById("billing-status");
          var usageEl = document.getElementById("billing-usage");
          if (planEl) planEl.textContent = sub.plan || "free";
          if (statusEl) statusEl.textContent = "Status: " + (sub.status || "active");
          if (usageEl && usage.messages_limit != null) {
            var lim = usage.messages_limit < 0 ? "unlimited" : usage.messages_limit;
            var bots = usage.chatbots_limit < 0 ? "unlimited" : usage.chatbots_limit;
            usageEl.textContent =
              usage.messages_used +
              " / " +
              lim +
              " messages this month · " +
              usage.chatbots_used +
              " / " +
              bots +
              " chatbots";
          }
        })
        .catch(function () {
          if (loading) loading.textContent = "Could not load billing info.";
        });

      var portalBtn = document.getElementById("billing-portal-btn");
      if (portalBtn) {
        portalBtn.addEventListener("click", async function () {
          try {
            var res = await fetch("/api/v1/billing/portal", {
              method: "POST",
              headers: h,
            });
            var data = await res.json().catch(function () {
              return {};
            });
            if (!res.ok) throw new Error(data.detail || "Portal unavailable");
            if (data.portal_url) window.location.href = data.portal_url;
          } catch (err) {
            if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
          }
        });
      }
    },
  };
})();
