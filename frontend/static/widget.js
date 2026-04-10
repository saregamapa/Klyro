/**
 * KlyroAI embeddable chat widget
 * Usage:
 *   <script src="http://localhost:8000/widget.js" data-bot-id="1"></script>
 * Optional: data-api-url="https://api.example.com" if API differs from script host
 */
(function () {
  "use strict";

  var SCRIPT = document.currentScript;
  if (!SCRIPT) {
    console.error("[KlyroAI] currentScript not available");
    return;
  }

  var BOT_ID = SCRIPT.getAttribute("data-bot-id");
  var API_ORIGIN =
    SCRIPT.getAttribute("data-api-url") || new URL(SCRIPT.src).origin;
  var ROOT_ID = "klyroai-widget-root";

  if (!BOT_ID || !/^\d+$/.test(String(BOT_ID).trim())) {
    console.error("[KlyroAI] Missing or invalid data-bot-id on script tag");
    return;
  }
  BOT_ID = parseInt(String(BOT_ID).trim(), 10);

  if (document.getElementById(ROOT_ID)) {
    console.warn("[KlyroAI] Widget already mounted");
    return;
  }

  function escapeHtml(text) {
    var d = document.createElement("div");
    d.textContent = text == null ? "" : String(text);
    return d.innerHTML;
  }

  var root = document.createElement("div");
  root.id = ROOT_ID;
  document.body.appendChild(root);

  var tw = document.createElement("script");
  tw.src = "https://cdn.tailwindcss.com";
  tw.onload = function () {
    if (window.tailwind) {
      window.tailwind.config = {
        important: "#" + ROOT_ID,
        corePlugins: { preflight: false },
      };
    }
    mount();
  };
  document.head.appendChild(tw);

  function formatApiError(data) {
    if (!data || data.detail == null) return "";
    var d = data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map(function (x) {
          return (x && x.msg) || JSON.stringify(x);
        })
        .join(" ");
    }
    return JSON.stringify(d);
  }

  function mount() {
    root.innerHTML =
      '<div class="pointer-events-none fixed bottom-5 right-5 z-[2147483647] flex flex-col items-end gap-3 font-sans text-slate-800">' +
      '  <div id="klyro-panel" class="pointer-events-auto hidden h-[min(32rem,calc(100vh-6rem))] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">' +
      '    <div class="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">' +
      '      <span class="text-sm font-semibold text-slate-800">Chat</span>' +
      '      <button type="button" id="klyro-close" class="rounded-lg p-1 text-slate-500 hover:bg-slate-200 hover:text-slate-700" aria-label="Close chat">&times;</button>' +
      "    </div>" +
      '    <div id="klyro-messages" class="flex flex-1 flex-col gap-3 overflow-y-auto p-4 text-sm"></div>' +
      '    <div id="klyro-lead" class="hidden flex-col gap-2 border-t border-emerald-100 bg-emerald-50/90 px-3 py-3 text-xs">' +
      '      <p id="klyro-lead-text" class="text-slate-700"></p>' +
      '      <input id="klyro-lead-name" type="text" autocomplete="name" placeholder="Your name" class="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-800 outline-none focus:border-emerald-500" />' +
      '      <input id="klyro-lead-email" type="email" autocomplete="email" placeholder="Email" class="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-800 outline-none focus:border-emerald-500" />' +
      '      <div class="flex flex-wrap gap-2">' +
      '        <button type="button" id="klyro-lead-submit" class="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500">Send</button>' +
      '        <button type="button" id="klyro-lead-dismiss" class="rounded-lg px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-100">Not now</button>' +
      "      </div>" +
      "    </div>" +
      '    <div id="klyro-error" class="hidden border-t border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700"></div>' +
      '    <form id="klyro-form" class="flex gap-2 border-t border-slate-100 p-3">' +
      '      <input id="klyro-input" type="text" autocomplete="off" placeholder="Type a message…" class="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500" />' +
      '      <button type="submit" id="klyro-send" class="shrink-0 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50">Send</button>' +
      "    </form>" +
      "  </div>" +
      '  <button type="button" id="klyro-fab" class="pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-600 text-2xl text-white shadow-lg transition hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:ring-offset-2" aria-label="Open chat">💬</button>' +
      "</div>";

    var panel = root.querySelector("#klyro-panel");
    var fab = root.querySelector("#klyro-fab");
    var closeBtn = root.querySelector("#klyro-close");
    var form = root.querySelector("#klyro-form");
    var input = root.querySelector("#klyro-input");
    var sendBtn = root.querySelector("#klyro-send");
    var messagesEl = root.querySelector("#klyro-messages");
    var errEl = root.querySelector("#klyro-error");
    var leadBox = root.querySelector("#klyro-lead");
    var leadText = root.querySelector("#klyro-lead-text");
    var leadName = root.querySelector("#klyro-lead-name");
    var leadEmail = root.querySelector("#klyro-lead-email");
    var leadSubmit = root.querySelector("#klyro-lead-submit");
    var leadDismiss = root.querySelector("#klyro-lead-dismiss");
    var leadStorageKey = "klyro_lead_sent_" + BOT_ID;

    function hideLeadBox() {
      if (!leadBox) return;
      leadBox.classList.add("hidden");
      leadBox.classList.remove("flex");
    }

    function maybeShowLeadForm(data) {
      if (!data || !data.show_lead_form || sessionStorage.getItem(leadStorageKey)) return;
      if (!leadBox || !leadText) return;
      leadText.textContent =
        data.lead_prompt ||
        "Want pricing or a callback? Leave your name and email and the team will reach out.";
      leadName.value = "";
      leadEmail.value = "";
      leadBox.classList.remove("hidden");
      leadBox.classList.add("flex");
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    if (leadDismiss) {
      leadDismiss.addEventListener("click", function () {
        hideLeadBox();
      });
    }

    if (leadSubmit) {
      leadSubmit.addEventListener("click", async function () {
        var nm = (leadName && leadName.value) ? leadName.value.trim() : "";
        var em = (leadEmail && leadEmail.value) ? leadEmail.value.trim() : "";
        if (!nm || !em) {
          showError("Please enter your name and email.");
          return;
        }
        showError("");
        leadSubmit.disabled = true;
        try {
          var lr = await fetch(API_ORIGIN + "/api/v1/widget/leads", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chatbot_id: BOT_ID,
              name: nm,
              email: em,
            }),
          });
          var ld = await lr.json().catch(function () {
            return {};
          });
          if (!lr.ok) throw new Error(formatApiError(ld) || "Could not send");
          sessionStorage.setItem(leadStorageKey, "1");
          hideLeadBox();
          appendBubble("Thanks — we received your details and will follow up soon.", "bot");
        } catch (err) {
          showError(err.message || "Send failed");
        } finally {
          leadSubmit.disabled = false;
        }
      });
    }

    function setOpen(open) {
      panel.classList.toggle("hidden", !open);
      panel.classList.toggle("flex", open);
      fab.setAttribute("aria-expanded", open ? "true" : "false");
    }

    fab.addEventListener("click", function () {
      setOpen(panel.classList.contains("hidden"));
      if (!panel.classList.contains("hidden")) input.focus();
    });
    closeBtn.addEventListener("click", function () {
      setOpen(false);
    });

    function appendBubble(text, who) {
      var wrap = document.createElement("div");
      wrap.className =
        who === "user"
          ? "ml-8 flex justify-end"
          : "mr-8 flex justify-start";
      var bubble = document.createElement("div");
      bubble.className =
        who === "user"
          ? "max-w-[95%] rounded-2xl rounded-br-md bg-emerald-600 px-3 py-2 text-white"
          : "max-w-[95%] rounded-2xl rounded-bl-md border border-slate-100 bg-slate-50 px-3 py-2 text-slate-800";
      bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br/>");
      wrap.appendChild(bubble);
      messagesEl.appendChild(wrap);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function showError(msg) {
      errEl.textContent = msg || "";
      errEl.classList.toggle("hidden", !msg);
    }

    appendBubble(
      "Hi! Ask me anything about this site — I answer from the knowledge we’ve indexed.",
      "bot"
    );

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      var text = (input.value || "").trim();
      if (!text) return;

      showError("");
      appendBubble(text, "user");
      input.value = "";
      sendBtn.disabled = true;
      input.disabled = true;

      try {
        var res = await fetch(API_ORIGIN + "/api/v1/widget/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chatbot_id: BOT_ID, message: text }),
        });
        var data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) {
          throw new Error(formatApiError(data) || res.statusText);
        }
        if (!data.reply && data.reply !== "") {
          throw new Error("Invalid response from server");
        }
        appendBubble(data.reply, "bot");
        maybeShowLeadForm(data);
      } catch (err) {
        showError(err.message || "Something went wrong");
        appendBubble(
          "Sorry, I couldn’t get a response. Please try again.",
          "bot"
        );
      } finally {
        sendBtn.disabled = false;
        input.disabled = false;
        input.focus();
      }
    });
  }
})();
