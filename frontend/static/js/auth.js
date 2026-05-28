/**
 * Klyro — login & signup
 */
(function () {
  "use strict";

  function showErr(id, msg) {
    var p = document.getElementById(id);
    if (!p) return;
    if (msg) {
      p.textContent = msg;
      p.classList.remove("hidden");
    } else {
      p.textContent = "";
      p.classList.add("hidden");
    }
  }

  window.CSAuth = {
    initLogin: function () {
      var form = document.getElementById("login-form");
      if (!form) return;
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        var email = document.getElementById("email").value.trim();
        var password = document.getElementById("password").value;
        showErr("email-err", "");
        showErr("password-err", "");
        if (!email) {
          showErr("email-err", "Email is required");
          return;
        }
        if (!password) {
          showErr("password-err", "Password is required");
          return;
        }
        var btn = document.getElementById("login-submit");
        btn.disabled = true;
        try {
          var res = await fetch("/api/v1/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: password }),
          });
          var data = await res.json().catch(function () {
            return {};
          });
          if (!res.ok) {
            throw new Error(typeof data.detail === "string" ? data.detail : "Login failed");
          }
          localStorage.setItem("klyro_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("klyro_refresh_token", data.refresh_token);
          }
          localStorage.removeItem("chatsite_token");
          if (window.CS && window.CS.toast) window.CS.toast("Welcome back!", "success");
          window.location.href = "/dashboard";
        } catch (err) {
          if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
          else alert(err.message);
        } finally {
          btn.disabled = false;
        }
      });
    },

    initSignup: function () {
      var form = document.getElementById("signup-form");
      if (!form) return;
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        var email = document.getElementById("email").value.trim();
        var password = document.getElementById("password").value;
        showErr("email-err", "");
        showErr("password-err", "");
        if (!email) {
          showErr("email-err", "Email is required");
          return;
        }
        if (password.length < 8) {
          showErr("password-err", "Use at least 8 characters");
          return;
        }
        var btn = document.getElementById("signup-submit");
        btn.disabled = true;
        try {
          var res = await fetch("/api/v1/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: password }),
          });
          var data = await res.json().catch(function () {
            return {};
          });
          if (!res.ok) {
            throw new Error(typeof data.detail === "string" ? data.detail : "Signup failed");
          }
          var loginRes = await fetch("/api/v1/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: password }),
          });
          var loginData = await loginRes.json().catch(function () {
            return {};
          });
          if (!loginRes.ok) {
            throw new Error("Account created — please log in.");
          }
          localStorage.setItem("klyro_token", loginData.access_token);
          if (loginData.refresh_token) {
            localStorage.setItem("klyro_refresh_token", loginData.refresh_token);
          }
          localStorage.removeItem("chatsite_token");
          if (window.CS && window.CS.toast) window.CS.toast("Account created!", "success");
          window.location.href = "/dashboard";
        } catch (err) {
          if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
          else alert(err.message);
        } finally {
          btn.disabled = false;
        }
      });
    },
  };

  // Silent token refresh — runs on every page load
  (async function refreshOnLoad() {
    var tok = localStorage.getItem("klyro_token");
    var ref = localStorage.getItem("klyro_refresh_token");
    if (!tok || !ref) return;

    try {
      var parts = tok.split(".");
      if (parts.length !== 3) return;
      var payload = JSON.parse(atob(parts[1]));
      var expiresAt = payload.exp * 1000;
      var fiveMin = 5 * 60 * 1000;
      if (Date.now() < expiresAt - fiveMin) return;
    } catch (_) {
      return;
    }

    try {
      var res = await fetch("/api/v1/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: ref }),
      });
      if (!res.ok) {
        localStorage.removeItem("klyro_token");
        localStorage.removeItem("klyro_refresh_token");
        return;
      }
      var data = await res.json();
      localStorage.setItem("klyro_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("klyro_refresh_token", data.refresh_token);
    } catch (_) {}
  })();
})();
