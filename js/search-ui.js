/* global PIApi */
(function (global) {
  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function rub(n) {
    if (n == null) return "—";
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: "RUB",
      maximumFractionDigits: 0,
    }).format(n);
  }

  function dt(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString("ru-RU");
  }

  function addDays(isoDate, days) {
    if (!isoDate) return null;
    var d = new Date(isoDate + "T00:00:00");
    if (isNaN(d.getTime())) return null;
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
  }

  function ensureAuthModal() {
    if (document.getElementById("pi-auth-modal")) return;
    var html = [
      '<div id="pi-auth-modal" style="display:none;position:fixed;inset:0;z-index:10100;background:rgba(0,0,0,.45);align-items:center;justify-content:center;padding:16px;">',
      '  <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:16px;max-width:420px;width:100%;padding:20px;box-shadow:var(--shadow-lg);">',
      '    <h3 style="margin:0 0 8px 0;font-family:var(--font-display);">Вход администратора</h3>',
      '    <p style="margin:0 0 16px 0;color:var(--color-text-muted);font-size:14px;">Для запуска поиска нужен доступ к API.</p>',
      '    <label style="display:block;font-size:12px;margin-bottom:6px;color:var(--color-text-muted);">Логин</label>',
      '    <input id="pi-auth-user" style="width:100%;padding:10px;border:1px solid var(--color-border);border-radius:10px;margin-bottom:10px;background:var(--color-surface);" autocomplete="username">',
      '    <label style="display:block;font-size:12px;margin-bottom:6px;color:var(--color-text-muted);">Пароль</label>',
      '    <input id="pi-auth-pass" type="password" style="width:100%;padding:10px;border:1px solid var(--color-border);border-radius:10px;margin-bottom:14px;background:var(--color-surface);" autocomplete="current-password">',
      '    <div style="display:flex;gap:8px;justify-content:flex-end;">',
      '      <button id="pi-auth-cancel" class="btn-secondary" type="button">Отмена</button>',
      '      <button id="pi-auth-submit" class="btn-primary" style="border:none;" type="button">Войти</button>',
      "    </div>",
      "  </div>",
      "</div>",
    ].join("");
    document.body.insertAdjacentHTML("beforeend", html);
    document.getElementById("pi-auth-cancel").addEventListener("click", function () {
      document.getElementById("pi-auth-modal").style.display = "none";
    });
  }

  function ensureAuth() {
    if (sessionStorage.getItem("pi_basic")) return Promise.resolve();
    ensureAuthModal();
    var modal = document.getElementById("pi-auth-modal");
    var user = document.getElementById("pi-auth-user");
    var pass = document.getElementById("pi-auth-pass");
    modal.style.display = "flex";
    user.focus();
    return new Promise(function (resolve, reject) {
      function done(ok) {
        submit.removeEventListener("click", onSubmit);
        modal.removeEventListener("click", onBackdrop);
        if (ok) resolve();
        else reject(new Error("Требуется авторизация"));
      }
      function onBackdrop(e) {
        if (e.target === modal) {
          modal.style.display = "none";
          done(false);
        }
      }
      function onSubmit() {
        var u = user.value.trim();
        var p = pass.value;
        if (!u || !p) return;
        sessionStorage.setItem("pi_basic", btoa(unescape(encodeURIComponent(u + ":" + p))));
        modal.style.display = "none";
        done(true);
      }
      var submit = document.getElementById("pi-auth-submit");
      submit.addEventListener("click", onSubmit);
      modal.addEventListener("click", onBackdrop);
    });
  }

  async function pollScenario(scenarioId, onTick) {
    for (var i = 0; i < 120; i += 1) {
      var sc = await PIApi.api("/api/scenarios/" + scenarioId, { method: "GET" });
      if (onTick) onTick(sc, i);
      if (sc.status === "success" || sc.status === "error") return sc;
      await new Promise(function (r) {
        setTimeout(r, 2000);
      });
    }
    throw new Error("Таймаут ожидания обработки");
  }

  function renderResults(targetTbody, scenario) {
    var run = scenario.latest_run;
    if (!run || !run.results || !run.results.length) {
      targetTbody.innerHTML = '<tr><td colspan="4" style="color:var(--color-text-muted)">Результатов пока нет.</td></tr>';
      return;
    }
    targetTbody.innerHTML = "";
    run.results.forEach(function (r) {
      var tr = document.createElement("tr");
      if (r.platform.code === "vtb") tr.className = "vtb-row";
      tr.innerHTML =
        "<td>" + esc(r.platform.display_name) + "</td>" +
        "<td class=\"price-cell\">" + (r.error_text ? "—" : rub(r.price_rub)) + "</td>" +
        "<td>" +
        (r.offer_url
          ? '<a href="' + esc(r.offer_url) + '" target="_blank" rel="noopener">Открыть</a>'
          : "—") +
        "</td>" +
        "<td>" + (r.error_text ? '<span style="color:var(--color-error)">' + esc(r.error_text) + "</span>" : "") + "</td>";
      targetTbody.appendChild(tr);
    });
  }

  function defaultByProduct(productType, formData) {
    var out = Object.assign({}, formData);
    if (productType === "hotel") {
      out.origin_label = out.origin_label || "";
      out.origin_code = out.origin_code || "";
      out.cabin_class = "hotel";
    }
    if (productType === "rail") {
      out.cabin_class = out.cabin_class || "2_class";
    }
    if (productType === "tour") {
      out.cabin_class = out.cabin_class || "tour";
      if (!out.date_return && out.nights) {
        var dr = addDays(out.date_departure, Number(out.nights));
        if (dr) out.date_return = dr;
      }
    }
    return out;
  }

  function collectFormData(form) {
    var fd = new FormData(form);
    var out = {};
    fd.forEach(function (v, k) {
      out[k] = typeof v === "string" ? v.trim() : v;
    });
    out.direct_only = Boolean(fd.get("direct_only"));
    out.baggage_included = Boolean(fd.get("baggage_included"));
    out.passengers_adults = Number(out.passengers_adults || 1);
    return out;
  }

  function mapPayload(productType, data) {
    var type = productType === "tour" ? "hotel" : productType;
    return {
      product_type: type,
      origin_label: data.origin_label || "",
      origin_code: data.origin_code || "",
      destination_label: data.destination_label || "",
      destination_code: data.destination_code || "",
      date_departure: data.date_departure,
      date_return: data.date_return || null,
      time_departure_pref: data.time_departure_pref || null,
      time_return_pref: data.time_return_pref || null,
      passengers_adults: data.passengers_adults || 1,
      cabin_class: data.cabin_class || "economy",
      direct_only: Boolean(data.direct_only),
      baggage_included: Boolean(data.baggage_included),
      tariff_notes: data.tariff_notes || null,
    };
  }

  function initSearchPage(options) {
    var form = document.getElementById(options.formId || "search-form");
    var findBtn = document.getElementById(options.findButtonId || "btn-find");
    var statusEl = document.getElementById(options.statusId || "search-status");
    var metaEl = document.getElementById(options.metaId || "search-meta");
    var tbody = document.getElementById(options.tbodyId || "results-body");
    if (!form || !findBtn || !statusEl || !tbody) return;

    function setStatus(txt, isErr) {
      statusEl.textContent = txt;
      statusEl.style.color = isErr ? "var(--color-error)" : "var(--color-text-muted)";
    }

    findBtn.addEventListener("click", async function () {
      try {
        await ensureAuth();
        findBtn.disabled = true;
        setStatus("Создаю сценарий…", false);
        if (metaEl) metaEl.textContent = "";
        var raw = collectFormData(form);
        var prepped = defaultByProduct(options.productType, raw);
        var payload = mapPayload(options.productType, prepped);
        if (!payload.destination_label || !payload.date_departure) {
          throw new Error("Заполните минимум: пункт назначения и дату отправления");
        }
        var created = await PIApi.api("/api/scenarios", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        var sid = created.id;
        if (metaEl) metaEl.textContent = "Сценарий #" + sid;

        setStatus("Ставлю задачу в обработку…", false);
        await PIApi.api("/api/scenarios/" + sid + "/run", { method: "POST" });

        setStatus("Собираю ответы площадок…", false);
        var finalScenario = await pollScenario(sid, function (sc) {
          if (metaEl) {
            metaEl.textContent =
              "Сценарий #" + sc.id +
              " · статус: " + sc.status +
              (sc.latest_run ? " · прогон #" + sc.latest_run.id : "");
          }
        });
        renderResults(tbody, finalScenario);
        setStatus(
          finalScenario.status === "success"
            ? "Готово. Результаты получены."
            : "Завершено с ошибкой. Смотрите примечания в таблице.",
          finalScenario.status !== "success"
        );
      } catch (e) {
        setStatus((e && e.message) || "Ошибка", true);
      } finally {
        findBtn.disabled = false;
      }
    });
  }

  global.SearchUI = { initSearchPage: initSearchPage };
})(window);
