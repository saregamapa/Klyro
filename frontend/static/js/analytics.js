/**
 * Klyro — analytics dashboard
 */
(function () {
  "use strict";

  var TOKEN_KEY = "klyro_token";
  var LEGACY_TOKEN_KEY = "chatsite_token";

  function getToken() {
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

  function authHeaders() {
    var t = getToken();
    if (!t) return null;
    return { Authorization: "Bearer " + t, "Content-Type": "application/json" };
  }

  function requireAuth() {
    if (!getToken()) {
      window.location.href = "/login";
      return false;
    }
    return true;
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function formatDate(isoString) {
    try {
      var date = new Date(isoString);
      return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return isoString;
    }
  }

  window.CSAnalytics = {
    init: function () {
      if (!requireAuth()) return;

      var select = document.getElementById("chatbot-select");
      var logout = document.getElementById("logout-btn");
      var loM = document.getElementById("logout-btn-mobile");

      function doLogout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(LEGACY_TOKEN_KEY);
        window.location.href = "/";
      }

      if (logout) logout.addEventListener("click", doLogout);
      if (loM) loM.addEventListener("click", doLogout);

      if (select) {
        select.addEventListener("change", function (e) {
          var id = parseInt(e.target.value, 10);
          if (id && Number.isFinite(id)) {
            loadAnalytics(id);
          } else {
            showEmpty();
          }
        });
      }

      loadChatbots();
    },
  };

  function loadChatbots() {
    var h = authHeaders();
    if (!h) return;

    var loading = document.getElementById("analytics-loading");
    var empty = document.getElementById("analytics-empty");
    var select = document.getElementById("chatbot-select");

    fetch("/api/v1/chatbots", { headers: h })
      .then(function (res) {
        return res.json().then(function (d) {
          return { ok: res.ok, data: d };
        });
      })
      .then(function (r) {
        if (!r.ok) throw new Error("Failed to load chatbots");
        var list = r.data || [];

        if (loading) loading.classList.add("hidden");

        if (!list.length) {
          showEmpty();
          return;
        }

        if (empty) empty.classList.add("hidden");
        if (select) {
          select.innerHTML = '<option value="">Choose a chatbot…</option>';
          list.forEach(function (bot) {
            var option = document.createElement("option");
            option.value = String(bot.id);
            option.textContent = bot.name;
            select.appendChild(option);
          });
        }
      })
      .catch(function (err) {
        if (loading) loading.classList.add("hidden");
        showEmpty();
      });
  }

  function showEmpty() {
    var empty = document.getElementById("analytics-empty");
    var content = document.getElementById("analytics-content");
    if (content) content.classList.add("hidden");
    if (empty) empty.classList.remove("hidden");
  }

  function loadAnalytics(chatbotId) {
    var h = authHeaders();
    if (!h) return;

    var loading = document.getElementById("analytics-loading");
    var content = document.getElementById("analytics-content");
    var empty = document.getElementById("analytics-empty");

    if (loading) loading.classList.remove("hidden");
    if (content) content.classList.add("hidden");
    if (empty) empty.classList.add("hidden");

    function safeFetch(url) {
      return fetch(url, { headers: h })
        .then(function (r) {
          if (!r.ok) return { ok: false, data: null };
          return r.json().then(function (d) { return { ok: true, data: d }; });
        })
        .catch(function () { return { ok: false, data: null }; });
    }

    Promise.all([
      safeFetch("/api/v1/analytics/" + chatbotId),
      safeFetch("/api/v1/chatbots/" + chatbotId + "/conversations?limit=10"),
      safeFetch("/api/v1/chatbots/" + chatbotId + "/leads"),
    ])
      .then(function (results) {
        if (loading) loading.classList.add("hidden");

        var analyticsR = results[0];
        var conversationsR = results[1];
        var leadsR = results[2];

        // Stat cards
        var totalConv = 0;
        var totalLeads = 0;
        var avgMsg = 0;

        if (analyticsR.ok && analyticsR.data) {
          totalConv = analyticsR.data.total_chats || 0;
          avgMsg = Math.round((analyticsR.data.avg_messages_per_day || 0) * 10) / 10;
        }

        if (leadsR.ok && leadsR.data) {
          var leadsItems = Array.isArray(leadsR.data) ? leadsR.data : (leadsR.data.items || []);
          totalLeads = typeof leadsR.data.total === "number" ? leadsR.data.total : leadsItems.length;
        }

        var statConv = document.getElementById("stat-conversations");
        var statLeads = document.getElementById("stat-leads");
        var statAvg = document.getElementById("stat-avg");

        if (statConv) statConv.textContent = String(totalConv);
        if (statLeads) statLeads.textContent = String(totalLeads);
        if (statAvg) statAvg.textContent = String(avgMsg);

        // Top questions
        var topWrap = document.getElementById("top-questions-wrap");
        var topList = document.getElementById("top-questions-list");

        if (analyticsR.ok && analyticsR.data && analyticsR.data.top_questions && analyticsR.data.top_questions.length) {
          if (topWrap) topWrap.classList.remove("hidden");
          if (topList) {
            topList.innerHTML = "";
            analyticsR.data.top_questions.forEach(function (q, idx) {
              var li = document.createElement("li");
              li.className = "flex justify-between items-start p-3 rounded-lg bg-slate-800/30 hover:bg-slate-800/50 transition";
              li.innerHTML =
                '<span class="flex-1 text-slate-300">' + escapeHtml(q.question) + '</span>' +
                '<span class="ml-3 text-right text-emerald-400 font-medium">' + q.count + '×</span>';
              topList.appendChild(li);
            });
          }
        } else {
          if (topWrap) topWrap.classList.add("hidden");
        }

        // Conversations table
        var convBody = document.getElementById("conversations-body");
        var convEmpty = document.getElementById("conversations-empty");

        if (convBody) {
          convBody.innerHTML = "";

          var convItems = conversationsR.ok && conversationsR.data
            ? (Array.isArray(conversationsR.data) ? conversationsR.data : (conversationsR.data.items || []))
            : [];
          if (convItems.length) {
            if (convEmpty) convEmpty.classList.add("hidden");
            convItems.forEach(function (conv) {
              var tr = document.createElement("tr");
              tr.className = "border-t border-slate-700/40";
              var created = conv.created_at ? formatDate(conv.created_at) : "—";
              var msgCount = (conv.messages && Array.isArray(conv.messages)) ? conv.messages.length : 0;
              var visitor = conv.visitor_id ? "Visitor #" + conv.visitor_id.slice(0, 8) : "—";
              tr.innerHTML =
                '<td class="py-2.5 pr-4 align-top text-sm">' + escapeHtml(created) + '</td>' +
                '<td class="py-2.5 pr-4 align-top text-sm">' + msgCount + '</td>' +
                '<td class="py-2.5 align-top text-sm text-slate-500">' + escapeHtml(visitor) + '</td>';
              convBody.appendChild(tr);
            });
          } else {
            if (convEmpty) convEmpty.classList.remove("hidden");
          }
        }

        if (content) content.classList.remove("hidden");
      })
      .catch(function (err) {
        if (loading) loading.classList.add("hidden");
        if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
        showEmpty();
      });
  }
})();
