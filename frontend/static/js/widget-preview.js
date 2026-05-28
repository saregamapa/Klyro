/**
 * Klyro — in-dashboard preview using public widget API
 */
(function () {
  "use strict";

  function escapeHtml(t) {
    var d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }

  function previewSessionId(chatbotId) {
    var key = "klyro_preview_session_" + chatbotId;
    var sid = sessionStorage.getItem(key);
    if (!sid) {
      sid =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : "preview-" + Date.now();
      sessionStorage.setItem(key, sid);
    }
    return sid;
  }

  window.CSWidgetPreview = {
    init: function (chatbotId) {
      var form = document.getElementById("preview-form");
      var input = document.getElementById("preview-input");
      var messages = document.getElementById("preview-messages");
      if (!form || !input || !messages) return;

      var sessionId = previewSessionId(chatbotId);
      var leadKey = "klyro_preview_lead_" + chatbotId;

      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        var text = input.value.trim();
        if (!text) return;
        input.value = "";
        input.disabled = true;

        var userDiv = document.createElement("div");
        userDiv.className = "flex justify-end";
        userDiv.innerHTML =
          '<div class="max-w-[90%] rounded-2xl rounded-br-sm bg-emerald-600 px-3 py-2 text-slate-50">' +
          escapeHtml(text) +
          "</div>";
        messages.appendChild(userDiv);
        messages.scrollTop = messages.scrollHeight;

        var loading = document.createElement("div");
        loading.className = "flex justify-start text-slate-500 text-xs";
        loading.textContent = "Thinking…";
        messages.appendChild(loading);
        messages.scrollTop = messages.scrollHeight;

        try {
          var res = await fetch("/api/v1/widget/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chatbot_id: chatbotId,
              message: text,
              session_id: sessionId,
            }),
            signal: AbortSignal.timeout ? AbortSignal.timeout(10000) : undefined,
          });
          var data = await res.json().catch(function () {
            return {};
          });
          loading.remove();
          var botDiv = document.createElement("div");
          botDiv.className = "flex justify-start";
          var reply;
          if (res.ok && data.reply != null) reply = data.reply;
          else if (typeof data.detail === "string") reply = data.detail;
          else if (Array.isArray(data.detail))
            reply =
              data.detail
                .map(function (x) {
                  return x.msg || "";
                })
                .join(" ") || "Request failed";
          else reply = "Request failed";
          botDiv.innerHTML =
            '<div class="max-w-[90%] rounded-2xl rounded-bl-sm border border-slate-600 bg-slate-800/80 px-3 py-2 text-slate-100">' +
            escapeHtml(reply) +
            "</div>";
          messages.appendChild(botDiv);

          if (
            res.ok &&
            data.show_lead_form &&
            !sessionStorage.getItem(leadKey)
          ) {
            var leadWrap = document.createElement("div");
            leadWrap.className =
              "mt-2 max-w-[95%] rounded-xl border border-emerald-500/35 bg-emerald-950/50 p-3 text-xs text-slate-300";
            var prompt = escapeHtml(
              data.lead_prompt ||
                "Want someone to follow up? Add your name and email."
            );
            leadWrap.innerHTML =
              '<p class="mb-2 text-slate-200">' +
              prompt +
              '</p><input type="text" class="preview-lead-name mb-1 w-full rounded-lg border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-white" placeholder="Name" />' +
              '<input type="email" class="preview-lead-email mb-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-2 py-1.5 text-sm text-white" placeholder="Email" />' +
              '<button type="button" class="preview-lead-send rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500">Send</button>';
            messages.appendChild(leadWrap);
            var sendBtn = leadWrap.querySelector(".preview-lead-send");
            sendBtn.addEventListener("click", async function () {
              var nm = (leadWrap.querySelector(".preview-lead-name") || {}).value;
              nm = (nm || "").trim();
              var em = (leadWrap.querySelector(".preview-lead-email") || {}).value;
              em = (em || "").trim();
              if (!nm || !em) {
                if (window.CS && window.CS.toast) window.CS.toast("Name and email required", "error");
                return;
              }
              sendBtn.disabled = true;
              try {
                var lr = await fetch("/api/v1/widget/leads", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    chatbot_id: chatbotId,
                    name: nm,
                    email: em,
                  }),
                });
                var ld = await lr.json().catch(function () {
                  return {};
                });
                if (!lr.ok)
                  throw new Error(
                    typeof ld.detail === "string" ? ld.detail : "Could not save lead"
                  );
                sessionStorage.setItem(leadKey, "1");
                leadWrap.innerHTML =
                  '<p class="text-emerald-300">Thanks — your details were saved.</p>';
                if (window.CS && window.CS.toast) window.CS.toast("Lead captured", "success");
              } catch (err) {
                if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
                sendBtn.disabled = false;
              }
            });
          }
        } catch (err) {
          loading.remove();
          var errMsg = err.name === "AbortError" ? "Request timed out. Please try again." : (err.message || "Network error. Please try again.");
          if (window.CS && window.CS.toast) window.CS.toast(errMsg, "error");
        }
        input.disabled = false;
        input.focus();
        messages.scrollTop = messages.scrollHeight;
      });
    },
  };
})();
