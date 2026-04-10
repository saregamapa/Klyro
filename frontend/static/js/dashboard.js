/**
 * Klyro — dashboard, create flow, detail
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

  function bearerOnlyHeaders() {
    var t = getToken();
    if (!t) return null;
    return { Authorization: "Bearer " + t };
  }

  function requireAuth() {
    if (!getToken()) {
      window.location.href = "/login";
      return false;
    }
    return true;
  }

  window.CSDashboard = {
    init: function () {
      if (!requireAuth()) return;
      var grid = document.getElementById("dashboard-grid");
      if (grid && !grid.dataset.deleteDelegate) {
        grid.dataset.deleteDelegate = "1";
        grid.addEventListener("click", function (ev) {
          var btn = ev.target.closest(".chatbot-delete-btn");
          if (!btn) return;
          ev.preventDefault();
          ev.stopPropagation();
          var bid = btn.getAttribute("data-chatbot-id");
          if (!bid) return;
          if (!window.confirm("Delete this chatbot? This cannot be undone.")) return;
          var h = authHeaders();
          if (!h) return;
          btn.disabled = true;
          fetch("/api/v1/chatbots/" + bid, { method: "DELETE", headers: h })
            .then(function (res) {
              if (!res.ok) {
                return res.json().then(function (d) {
                  throw new Error(d.detail || "Delete failed");
                });
              }
              if (window.CS && window.CS.toast) window.CS.toast("Chatbot deleted", "success");
              loadChatbots();
            })
            .catch(function (err) {
              if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
              btn.disabled = false;
            });
        });
      }
      var logout = document.getElementById("logout-btn");
      function doLogout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(LEGACY_TOKEN_KEY);
        window.location.href = "/";
      }
      if (logout) logout.addEventListener("click", doLogout);
      var loM = document.getElementById("logout-btn-mobile");
      if (loM) loM.addEventListener("click", doLogout);
      loadChatbots();
    },

    initCreate: function () {
      if (!requireAuth()) return;
      var form = document.getElementById("create-form");
      if (!form) return;

      var uploadInput = document.getElementById("upload-docs");
      var dropzone = document.getElementById("upload-dropzone");
      var fileListEl = document.getElementById("upload-file-list");

      function renderFileList() {
        if (!fileListEl || !uploadInput) return;
        fileListEl.innerHTML = "";
        var files = uploadInput.files;
        if (!files || !files.length) return;
        for (var i = 0; i < files.length; i++) {
          var li = document.createElement("li");
          li.textContent = files[i].name + " (" + Math.ceil(files[i].size / 1024) + " KB)";
          fileListEl.appendChild(li);
        }
      }

      if (uploadInput && fileListEl) {
        uploadInput.addEventListener("change", renderFileList);
      }

      if (dropzone && uploadInput) {
        dropzone.addEventListener("click", function () {
          uploadInput.click();
        });
        dropzone.addEventListener("dragover", function (e) {
          e.preventDefault();
          e.stopPropagation();
          dropzone.classList.add("border-emerald-500/50", "bg-emerald-500/5");
        });
        dropzone.addEventListener("dragleave", function (e) {
          e.preventDefault();
          dropzone.classList.remove("border-emerald-500/50", "bg-emerald-500/5");
        });
        dropzone.addEventListener("drop", function (e) {
          e.preventDefault();
          e.stopPropagation();
          dropzone.classList.remove("border-emerald-500/50", "bg-emerald-500/5");
          var dt = e.dataTransfer;
          if (!dt || !dt.files || !dt.files.length) return;
          var merged = new DataTransfer();
          var seen = {};
          function addFile(f) {
            var k = f.name + "-" + f.size;
            if (seen[k]) return;
            seen[k] = true;
            merged.items.add(f);
          }
          var existing = uploadInput.files;
          for (var i = 0; i < existing.length; i++) addFile(existing[i]);
          for (var j = 0; j < dt.files.length; j++) addFile(dt.files[j]);
          uploadInput.files = merged.files;
          renderFileList();
        });
      }

      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        var name = document.getElementById("name").value.trim();
        var websiteUrl = document.getElementById("website_url").value.trim();
        var files = uploadInput && uploadInput.files ? uploadInput.files : null;
        var hasFiles = files && files.length > 0;

        if (!name) {
          if (window.CS && window.CS.toast) window.CS.toast("Name is required", "error");
          return;
        }
        var h = authHeaders();
        var bh = bearerOnlyHeaders();
        if (!h || !bh) return;

        var btn = document.getElementById("train-btn");
        var progress = document.getElementById("train-progress");
        var statusEl = document.getElementById("train-status");
        var bar = document.getElementById("train-bar");

        btn.disabled = true;
        form.classList.add("opacity-50", "pointer-events-none");
        progress.classList.remove("hidden");
        function setBar(pct, msg) {
          if (bar) bar.style.width = pct + "%";
          if (statusEl && msg) statusEl.textContent = msg;
        }

        try {
          setBar(15, "Creating chatbot…");
          var body = { name: name, website_url: websiteUrl || null };
          var res = await fetch("/api/v1/chatbots", {
            method: "POST",
            headers: h,
            body: JSON.stringify(body),
          });
          var data = await res.json().catch(function () {
            return {};
          });
          if (!res.ok) throw new Error(data.detail || "Create failed");
          var id = parseInt(data.id, 10);
          if (!Number.isFinite(id) || id < 1) throw new Error("Invalid response from server");

          if (websiteUrl) {
            setBar(35, "Crawling your website…");
            var ingestRes = await fetch("/api/v1/chatbots/" + id + "/ingest", {
              method: "POST",
              headers: h,
              body: "{}",
            });
            if (!ingestRes.ok) {
              var ingErr = await ingestRes.json().catch(function () {
                return {};
              });
              throw new Error(ingErr.detail || "Ingest failed — check the website URL");
            }
            setBar(55, "Website content saved.");
          }

          if (hasFiles) {
            setBar(websiteUrl ? 60 : 35, "Reading documents…");
            var fd = new FormData();
            for (var fi = 0; fi < files.length; fi++) {
              fd.append("files", files[fi]);
            }
            var ingestFilesRes = await fetch("/api/v1/chatbots/" + id + "/ingest-files", {
              method: "POST",
              headers: bh,
              body: fd,
            });
            var ingestFileData = await ingestFilesRes.json().catch(function () {
              return {};
            });
            if (!ingestFilesRes.ok) {
              var d = ingestFileData.detail;
              var detailMsg =
                typeof d === "string"
                  ? d
                  : Array.isArray(d)
                    ? d
                        .map(function (x) {
                          return x.msg || x;
                        })
                        .join("; ")
                    : "Document upload failed — check file types and sizes";
              throw new Error(detailMsg);
            }
            if (
              ingestFileData.warnings &&
              ingestFileData.warnings.length &&
              window.CS &&
              window.CS.toast
            ) {
              var w0 = ingestFileData.warnings[0];
              var more = ingestFileData.warnings.length > 1 ? " (+" + (ingestFileData.warnings.length - 1) + ")" : "";
              window.CS.toast(w0 + more, "info");
            }
            setBar(websiteUrl ? 75 : 55, "Documents saved.");
          }

          if (websiteUrl || hasFiles) {
            setBar(85, "Creating embeddings…");
            var embedRes = await fetch("/api/v1/chatbots/" + id + "/embed", {
              method: "POST",
              headers: h,
            });
            if (!embedRes.ok) {
              var emErr = await embedRes.json().catch(function () {
                return {};
              });
              throw new Error(emErr.detail || "Embed failed — check OpenAI key");
            }
            setBar(100, "Done!");
            if (window.CS && window.CS.toast) window.CS.toast("Chatbot trained successfully", "success");
          } else {
            setBar(100, "Saved!");
            if (window.CS && window.CS.toast)
              window.CS.toast(
                "Chatbot saved. No website or documents were added, so it has no knowledge base yet.",
                "success"
              );
          }

          setTimeout(function () {
            window.location.href = "/chatbot/" + id;
          }, 600);
        } catch (err) {
          if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
          btn.disabled = false;
          form.classList.remove("opacity-50", "pointer-events-none");
          progress.classList.add("hidden");
        }
      });
    },

    initDetail: function () {
      if (!requireAuth()) return;
      var id = window.__CHATBOT_ID__;
      if (!id) return;

      var loading = document.getElementById("detail-loading");
      var content = document.getElementById("detail-content");
      var h = authHeaders();
      if (!h) return;

      fetch("/api/v1/chatbots/" + id, { headers: h })
        .then(function (r) {
          return r.json().then(function (d) {
            return { ok: r.ok, d: d };
          });
        })
        .then(function (_ref) {
          if (!_ref.ok) throw new Error(_ref.d.detail || "Not found");
          return _ref.d;
        })
        .then(function (bot) {
          if (loading) loading.classList.add("hidden");
          if (content) content.classList.remove("hidden");
          document.getElementById("detail-name").textContent = bot.name;
          document.getElementById("detail-url").textContent = bot.website_url || "No website URL set";

          var origin = window.location.origin;
          var snippet =
            '<script src="' +
            origin +
            '/widget.js" data-bot-id="' +
            id +
            '"><\/script>';
          document.getElementById("install-snippet").textContent = snippet;

          document.getElementById("copy-snippet").onclick = function () {
            navigator.clipboard.writeText(snippet).then(function () {
              if (window.CS && window.CS.toast) window.CS.toast("Copied to clipboard", "success");
            });
          };

          var delBtn = document.getElementById("delete-chatbot-btn");
          if (delBtn) {
            delBtn.onclick = function () {
              if (!window.confirm("Delete this chatbot permanently? This cannot be undone.")) return;
              delBtn.disabled = true;
              fetch("/api/v1/chatbots/" + id, { method: "DELETE", headers: h })
                .then(function (res) {
                  if (!res.ok) {
                    return res.json().then(function (d) {
                      throw new Error(d.detail || "Delete failed");
                    });
                  }
                  if (window.CS && window.CS.toast) window.CS.toast("Chatbot deleted", "success");
                  window.location.href = "/dashboard";
                })
                .catch(function (err) {
                  if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
                  delBtn.disabled = false;
                });
            };
          }

          return fetch("/api/v1/chatbots/" + id + "/conversations", { headers: h });
        })
        .then(function (r) {
          return r.json().then(function (d) {
            return { ok: r.ok, d: d };
          });
        })
        .then(function (_ref2) {
          if (_ref2.ok && Array.isArray(_ref2.d)) {
            var el = document.getElementById("stat-conv");
            if (el) el.textContent = String(_ref2.d.length);
          }
          return Promise.all([
            fetch("/api/v1/analytics/" + id, { headers: h }).then(function (r) {
              return r.json().then(function (d) {
                return { ok: r.ok, d: d };
              });
            }),
            fetch("/api/v1/chatbots/" + id + "/leads", { headers: h }).then(function (r) {
              return r.json().then(function (d) {
                return { ok: r.ok, d: d };
              });
            }),
          ]);
        })
        .then(function (pair) {
          var ar = pair[0];
          var lr = pair[1];
          var sumEl = document.getElementById("analytics-summary");
          var topWrap = document.getElementById("analytics-top-wrap");
          var topList = document.getElementById("analytics-top-list");
          if (ar.ok && ar.d) {
            if (sumEl)
              sumEl.textContent =
                ar.d.total_chats + " total chats — every visitor question is stored for analytics.";
            if (topList && topWrap) {
              topList.innerHTML = "";
              if (ar.d.top_questions && ar.d.top_questions.length) {
                topWrap.classList.remove("hidden");
                ar.d.top_questions.forEach(function (q) {
                  var li = document.createElement("li");
                  li.textContent = q.question + " · " + q.count + "×";
                  topList.appendChild(li);
                });
              } else {
                topWrap.classList.add("hidden");
              }
            }
          } else if (sumEl) {
            sumEl.textContent = "Could not load analytics.";
          }
          var leadsBody = document.getElementById("leads-table-body");
          var leadsEmpty = document.getElementById("leads-empty");
          var statLeads = document.getElementById("stat-leads");
          if (lr.ok && Array.isArray(lr.d) && leadsBody) {
            if (statLeads) statLeads.textContent = String(lr.d.length);
            leadsBody.innerHTML = "";
            if (!lr.d.length) {
              if (leadsEmpty) leadsEmpty.classList.remove("hidden");
            } else {
              if (leadsEmpty) leadsEmpty.classList.add("hidden");
              lr.d.forEach(function (lead) {
                var tr = document.createElement("tr");
                tr.className = "border-t border-slate-700/40";
                tr.innerHTML =
                  '<td class="py-2.5 pr-4 align-top">' +
                  escapeHtml(lead.name || "—") +
                  '</td><td class="py-2.5 pr-4 align-top">' +
                  escapeHtml(lead.email || "—") +
                  '</td><td class="py-2.5 align-top text-slate-500">' +
                  escapeHtml((lead.message || "").slice(0, 120)) +
                  (lead.message && lead.message.length > 120 ? "…" : "") +
                  "</td>";
                leadsBody.appendChild(tr);
              });
            }
          } else if (statLeads) {
            statLeads.textContent = "—";
          }
        })
        .catch(function (err) {
          if (window.CS && window.CS.toast) window.CS.toast(err.message, "error");
          window.location.href = "/dashboard";
        });
    },
  };

  async function loadChatbots() {
    var h = authHeaders();
    if (!h) return;
    var loading = document.getElementById("dashboard-loading");
    var empty = document.getElementById("dashboard-empty");
    var grid = document.getElementById("dashboard-grid");
    try {
      var res = await fetch("/api/v1/chatbots", { headers: h });
      var list = await res.json();
      if (!res.ok) throw new Error("Failed to load");
      if (loading) loading.classList.add("hidden");
      if (!list.length) {
        if (grid) {
          grid.innerHTML = "";
          grid.classList.add("hidden");
        }
        if (empty) empty.classList.remove("hidden");
        return;
      }
      if (empty) empty.classList.add("hidden");
      if (grid) {
        grid.classList.remove("hidden");
        grid.innerHTML = "";
        list.forEach(function (b) {
          var wrap = document.createElement("div");
          wrap.className =
            "tilt-card cs-glass group relative rounded-2xl transition hover:border-emerald-500/30 hover:shadow-glow";
          wrap.setAttribute("data-tilt", "");
          var a = document.createElement("a");
          a.href = "/chatbot/" + b.id;
          a.className = "block rounded-2xl p-6 pr-20";
          a.innerHTML =
            '<div class="tilt-card-inner"><h3 class="text-lg font-semibold text-white group-hover:text-emerald-400">' +
            escapeHtml(b.name) +
            "</h3>" +
            '<p class="mt-2 truncate text-sm text-slate-500">' +
            escapeHtml(b.website_url || "No URL") +
            "</p>" +
            '<p class="mt-4 text-xs font-medium text-emerald-500/80">Manage →</p></div>';
          var del = document.createElement("button");
          del.type = "button";
          del.className =
            "chatbot-delete-btn absolute right-3 top-3 z-10 rounded-lg border border-red-500/30 bg-red-950/80 px-2.5 py-1 text-xs font-medium text-red-200 transition hover:border-red-400/50 hover:bg-red-900/90";
          del.setAttribute("data-chatbot-id", String(b.id));
          del.setAttribute("aria-label", "Delete chatbot");
          del.textContent = "Delete";
          wrap.appendChild(a);
          wrap.appendChild(del);
          grid.appendChild(wrap);
        });
        if (window.CS && window.CS.initTiltCards) window.CS.initTiltCards();
      }
    } catch (e) {
      if (loading) loading.classList.add("hidden");
      if (empty) {
        empty.classList.remove("hidden");
        empty.querySelector("p").textContent = "Could not load chatbots.";
      }
    }
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }
})();
