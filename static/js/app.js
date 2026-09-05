/* SKYTICKETservice — UI helpers + autocomplete de países (i18n) */

function uiLang() {
  return window.SKYTICKET_LANG || "pt";
}

function i18n(key, fallback, vars) {
  const dict = window.SKYTICKET_I18N || {};
  let text = dict[key] || fallback || key;
  if (vars && typeof text === "string") {
    Object.keys(vars).forEach((k) => {
      text = text.split("{" + k + "}").join(String(vars[k]));
    });
  }
  return text;
}

function localeSort(a, b) {
  return String(a || "").localeCompare(String(b || ""), uiLang());
}

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => links.classList.toggle("open"));
  }

  document.querySelectorAll(".flash").forEach((el) => {
    // Erros de validação ficam mais tempo (utilizador precisa de ler)
    const isError =
      el.classList.contains("error") || el.classList.contains("danger");
    const ms = isError ? 14000 : 5000;
    if (isError) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    setTimeout(() => {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, ms);
  });

  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg =
        form.getAttribute("data-confirm") ||
        i18n("js_confirm", "Tem a certeza?");
      if (!confirm(msg)) e.preventDefault();
    });
  });

  try {
    initCountryPickers();
  } catch (err) {
    console.error("initCountryPickers", err);
  }
  try {
    initCityPickers();
  } catch (err) {
    console.error("initCityPickers", err);
  }
  try {
    initPhonePickers();
  } catch (err) {
    console.error("initPhonePickers", err);
  }
});

/** Lista global de países (injectada em base.html) — 197 países */
function getPaisesMundo() {
  const el = document.getElementById("skyticket-paises-json");
  if (!el) return [];
  try {
    const list = JSON.parse(el.textContent || "[]");
    return Array.isArray(list)
      ? list.slice().sort((a, b) => localeSort(a.nome, b.nome))
      : [];
  } catch (e) {
    return [];
  }
}

function findPaisByNome(paises, nome) {
  const t = (nome || "").trim().toLowerCase();
  if (!t) return null;
  return (
    paises.find((p) => {
      if ((p.nome || "").toLowerCase() === t) return true;
      if ((p.codigo || "").toLowerCase() === t) return true;
      const aliases = p.aliases || [];
      return aliases.some((a) => String(a || "").toLowerCase() === t);
    }) || null
  );
}

/**
 * Autocomplete de países (origem / destino).
 *
 * - Clique → lista inicial de sugestões
 * - Digitar → filtro em tempo real (ex.: "P" → Portugal, Peru, Paraguai…)
 * - Só aceita países da lista (197)
 * - Após seleccionar, o nome fica no campo
 *
 * HTML: <div class="country-picker" data-name="destino_pais" data-value="" data-required="1"></div>
 */
function initCountryPickers() {
  const paises = getPaisesMundo();
  if (!paises.length) return;

  // Só pickers de país — .city-picker também usa a classe country-picker no CSS
  document.querySelectorAll(".country-picker:not(.city-picker)").forEach((root) => {
    if (root.dataset.ready === "1") return;
    root.dataset.ready = "1";

    const name = root.dataset.name || "pais";
    let selectedNome = (root.dataset.value || "").trim();
    // Aceitar valor antigo noutro idioma via aliases → mostrar nome localizado
    const resolvedInit = findPaisByNome(paises, selectedNome);
    if (resolvedInit) {
      selectedNome = resolvedInit.nome;
    } else if (selectedNome) {
      selectedNome = "";
    }
    const required = root.dataset.required === "1";
    const placeholder =
      root.dataset.placeholder ||
      i18n("js_country_placeholder", "Clique para ver países ou digite para filtrar…");

    root.innerHTML = "";
    root.classList.add("country-picker--strict");

    const input = document.createElement("input");
    input.type = "text";
    input.className = "country-picker-input";
    input.placeholder = placeholder;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.value = selectedNome;

    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = name;
    hidden.value = selectedNome;
    // Nunca required em hidden: browsers bloqueiam o submit sem mensagens úteis
    if (required) {
      hidden.setAttribute("data-country-required", "1");
    }

    const dropdown = document.createElement("div");
    dropdown.className = "country-picker-dropdown";
    dropdown.hidden = true;
    dropdown.setAttribute("role", "listbox");

    const hint = document.createElement("p");
    hint.className = "country-picker-hint";
    updateHint();

    root.appendChild(input);
    root.appendChild(hidden);
    root.appendChild(dropdown);
    root.appendChild(hint);

    let activeIdx = -1;
    let currentList = [];

    function updateHint(msg) {
      if (msg) {
        hint.textContent = msg;
        return;
      }
      if (selectedNome) {
        hint.textContent = i18n(
          "js_country_selected",
          `✓ País seleccionado: ${selectedNome}`,
          { name: selectedNome }
        );
        hint.classList.add("is-selected");
      } else {
        hint.textContent = i18n(
          "js_country_hint",
          `${paises.length} países · seleccione apenas da lista (não pode inventar nomes)`,
          { n: paises.length }
        );
        hint.classList.remove("is-selected");
      }
    }

    /**
     * Filtra países pelas letras digitadas.
     * "P" → Portugal, Peru, Paraguai, Polónia…
     * Prioriza nomes que COMEÇAM pela pesquisa; depois os que CONTÊM.
     */
    function filterList(q) {
      const term = (q || "").trim().toLowerCase();
      if (!term) {
        // Lista inicial ao clicar: todos os países (A–Z), scrollável
        return paises.slice();
      }

      const starts = [];
      const contains = [];
      for (const p of paises) {
        const nome = p.nome.toLowerCase();
        const codigo = (p.codigo || "").toLowerCase();
        const aliases = (p.aliases || []).map((a) => String(a).toLowerCase());
        const hitAlias = aliases.some(
          (a) => a.startsWith(term) || a.includes(term)
        );
        if (nome.startsWith(term) || codigo.startsWith(term) || hitAlias) {
          if (nome.startsWith(term) || codigo.startsWith(term) || aliases.some((a) => a.startsWith(term))) {
            starts.push(p);
          } else {
            contains.push(p);
          }
        } else if (nome.includes(term)) {
          contains.push(p);
        }
      }
      return starts.concat(contains);
    }

    function render(list, q) {
      currentList = list;
      dropdown.innerHTML = "";
      activeIdx = -1;

      const head = document.createElement("div");
      head.className = "country-picker-empty";
      head.style.textAlign = "left";
      if (!(q || "").trim()) {
        head.textContent = i18n(
          "js_country_suggestions",
          `Sugestões (${list.length} países) — digite para filtrar:`,
          { n: list.length }
        );
      } else {
        head.textContent = list.length
          ? i18n(
              "js_country_results",
              `${list.length} resultado(s) para «${q.trim()}»`,
              { n: list.length, q: q.trim() }
            )
          : i18n(
              "js_country_none",
              `Nenhum país começa com «${q.trim()}»`,
              { q: q.trim() }
            );
      }
      dropdown.appendChild(head);

      if (!list.length) {
        const empty = document.createElement("div");
        empty.className = "country-picker-empty";
        empty.textContent = i18n(
          "js_country_only_list",
          "Escolha um país da lista oficial. Nomes fora da lista não são aceites."
        );
        dropdown.appendChild(empty);
        return;
      }

      list.forEach((p, i) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "country-picker-item";
        btn.setAttribute("role", "option");
        btn.dataset.index = String(i);
        btn.innerHTML = `<span class="nome">${highlightMatch(p.nome, q)}</span>
          <span class="meta">${escapeHtml(p.continente || "")} · ${escapeHtml(p.codigo || "")}</span>`;
        btn.addEventListener("mousedown", (e) => {
          e.preventDefault();
          selectCountry(p.nome);
        });
        dropdown.appendChild(btn);
      });
    }

    function selectCountry(nome) {
      const match = findPaisByNome(paises, nome);
      if (!match) return;
      selectedNome = match.nome;
      input.value = match.nome;
      hidden.value = match.nome;
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
      close();
      updateHint();
    }

    function open(q) {
      const query = typeof q === "string" ? q : input.value;
      // Se já tem país seleccionado e o texto é exactamente esse nome,
      // ao clicar mostra a lista completa para poder trocar.
      // Se está a digitar outra coisa, filtra em tempo real.
      let useQ = query;
      if (selectedNome && query === selectedNome) {
        useQ = "";
      }
      render(filterList(useQ), useQ);
      dropdown.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function close() {
      dropdown.hidden = true;
      input.setAttribute("aria-expanded", "false");
      activeIdx = -1;
    }

    /** Só aceita valor exacto da lista; senão reverte ou limpa */
    function enforceValidSelection() {
      const typed = input.value.trim();
      const match = findPaisByNome(paises, typed);
      if (match) {
        selectCountry(match.nome);
        return true;
      }
      // Texto livre inválido → não grava
      if (selectedNome && findPaisByNome(paises, selectedNome)) {
        input.value = selectedNome;
        hidden.value = selectedNome;
        input.classList.remove("is-invalid");
        updateHint(i18n("js_country_only_list", "Só é permitido escolher um país da lista. Valor restaurado."));
        setTimeout(() => updateHint(), 2500);
        return true;
      }
      // data-value inicial (ex.: Moçambique / Mozambique) se o utilizador só filtrou sem escolher
      const initial = (root.dataset.value || "").trim();
      if (initial && findPaisByNome(paises, initial)) {
        selectCountry(initial);
        return true;
      }
      input.value = "";
      hidden.value = "";
      selectedNome = "";
      input.classList.add("is-invalid");
      updateHint(i18n("js_pick_country_alert", "Seleccione um país da lista. Não pode escrever um país inexistente."));
      return !required;
    }

    // Usado no submit (evita race: blur com setTimeout vs clique em Continuar)
    root._skyticketEnforceCountry = enforceValidSelection;

    input.addEventListener("focus", () => open());
    input.addEventListener("click", () => open());

    input.addEventListener("input", () => {
      // Enquanto digita, o valor "oficial" só conta se for match exacto
      const typed = input.value.trim();
      const match = findPaisByNome(paises, typed);
      if (match) {
        hidden.value = match.nome;
        selectedNome = match.nome;
        input.classList.remove("is-invalid");
        input.classList.add("is-valid");
      } else {
        // Não grava texto parcial como país
        hidden.value = "";
        input.classList.remove("is-valid");
        if (typed) input.classList.add("is-invalid");
        else input.classList.remove("is-invalid");
      }
      open(input.value);
      updateHint(
        typed && !match
          ? `A filtrar «${typed}»… escolha um país da lista`
          : undefined
      );
    });

    input.addEventListener("blur", () => {
      setTimeout(() => {
        enforceValidSelection();
        close();
      }, 180);
    });

    input.addEventListener("keydown", (e) => {
      const items = dropdown.querySelectorAll(".country-picker-item");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (dropdown.hidden) open();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle("active", i === activeIdx));
        items[activeIdx]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
        items.forEach((el, i) => el.classList.toggle("active", i === activeIdx));
        items[activeIdx]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter") {
        if (activeIdx >= 0 && items[activeIdx] && !dropdown.hidden) {
          e.preventDefault();
          const p = currentList[activeIdx];
          if (p) selectCountry(p.nome);
        } else {
          // Enter sem item activo: só aceita se for match exacto
          const match = findPaisByNome(paises, input.value);
          if (match) {
            e.preventDefault();
            selectCountry(match.nome);
          } else if (input.value.trim()) {
            e.preventDefault();
            enforceValidSelection();
            open(input.value);
          }
        }
      } else if (e.key === "Escape") {
        enforceValidSelection();
        close();
      }
    });

    // Validação no submit do formulário pai
    const form = root.closest("form");
    if (form && !form.dataset.countryValidateBound) {
      form.dataset.countryValidateBound = "1";
      form.addEventListener(
        "submit",
        (e) => {
          let ok = true;
          let firstBad = null;
          // 1) Restaurar/sincronizar TODOS os pickers ANTES de validar
          //    (corrige clique em Continuar enquanto o campo país ainda tem filtro parcial)
          form
            .querySelectorAll(".country-picker:not(.city-picker)")
            .forEach((cp) => {
              if (typeof cp._skyticketEnforceCountry === "function") {
                cp._skyticketEnforceCountry();
              }
            });
          // 2) Validar
          form
            .querySelectorAll(".country-picker:not(.city-picker)")
            .forEach((cp) => {
              const h = cp.querySelector('input[type="hidden"]');
              const vis = cp.querySelector(".country-picker-input");
              const req = cp.dataset.required === "1";
              const val = (h && h.value) || "";
              if (req && !val) {
                ok = false;
                if (vis) {
                  vis.classList.add("is-invalid");
                  if (!firstBad) firstBad = vis;
                }
              } else if (val && !findPaisByNome(paises, val)) {
                ok = false;
                if (h) h.value = "";
                if (vis) {
                  vis.value = "";
                  vis.classList.add("is-invalid");
                  if (!firstBad) firstBad = vis;
                }
              }
            });
          if (!ok) {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (firstBad) {
              firstBad.focus();
              firstBad.scrollIntoView({ block: "center", behavior: "smooth" });
            }
            alert(i18n("js_pick_country_alert", "Seleccione um país válido da lista."));
          }
        },
        true
      );
    }
  });
}

function highlightMatch(nome, q) {
  const term = (q || "").trim();
  if (!term) return escapeHtml(nome);
  const lower = nome.toLowerCase();
  const t = term.toLowerCase();
  const idx = lower.indexOf(t);
  if (idx < 0) return escapeHtml(nome);
  const before = nome.slice(0, idx);
  const mid = nome.slice(idx, idx + term.length);
  const after = nome.slice(idx + term.length);
  return `${escapeHtml(before)}<mark>${escapeHtml(mid)}</mark>${escapeHtml(after)}`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getCidadesPorPais() {
  const el = document.getElementById("skyticket-cidades-json");
  if (!el) return {};
  try {
    return JSON.parse(el.textContent || "{}");
  } catch (e) {
    return {};
  }
}

/**
 * Autocomplete de cidades restrito ao país seleccionado.
 *
 * data-country-input: name do hidden do país (ex.: origem_pais)
 * data-name: name do hidden da cidade (ex.: origem_cidade)
 */
function initCityPickers() {
  const cidadesMap = getCidadesPorPais();

  document.querySelectorAll(".city-picker").forEach((root) => {
    if (root.dataset.ready === "1") return;
    root.dataset.ready = "1";

    const name = root.dataset.name || "cidade";
    const countryName = root.dataset.countryInput || "";
    let selectedCity = (root.dataset.value || "").trim();
    const required = root.dataset.required === "1";
    const placeholder =
      root.dataset.placeholder ||
      i18n("js_city_placeholder", "Seleccione o país primeiro…");

    root.innerHTML = "";
    root.classList.add("country-picker", "city-picker--strict");

    const input = document.createElement("input");
    input.type = "text";
    input.className = "country-picker-input";
    input.placeholder = placeholder;
    input.autocomplete = "off";
    input.spellcheck = false;
    input.value = selectedCity;

    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = name;
    hidden.value = selectedCity;
    if (required) hidden.required = true;

    const dropdown = document.createElement("div");
    dropdown.className = "country-picker-dropdown";
    dropdown.hidden = true;

    const hint = document.createElement("p");
    hint.className = "country-picker-hint";

    root.appendChild(input);
    root.appendChild(hidden);
    root.appendChild(dropdown);
    root.appendChild(hint);

    let activeIdx = -1;
    let currentList = [];
    let lastCountry = "";

    function countryValue() {
      // hidden do país (não do city-picker, que também tem .country-picker)
      const h = document.querySelector(
        `.country-picker:not(.city-picker) input[type="hidden"][name="${countryName}"]`
      );
      return (h && h.value) || "";
    }

    function citiesForCountry(pais) {
      if (!pais) return [];
      const list = cidadesMap[pais];
      if (Array.isArray(list) && list.length) {
        return list.slice().sort(localeSort);
      }
      // match case-insensitive nas chaves (inclui aliases noutros idiomas)
      const key = Object.keys(cidadesMap).find(
        (k) => k.toLowerCase() === pais.toLowerCase()
      );
      return key ? cidadesMap[key].slice().sort(localeSort) : [];
    }

    function updateHint(msg) {
      if (msg) {
        hint.textContent = msg;
        return;
      }
      const pais = countryValue();
      const cities = citiesForCountry(pais);
      if (!pais) {
        hint.textContent = i18n(
          "js_city_need_country",
          "Seleccione primeiro o país."
        );
        hint.classList.remove("is-selected");
        return;
      }
      if (selectedCity) {
        hint.textContent = i18n(
          "js_city_selected",
          `✓ Cidade: ${selectedCity} (${pais})`,
          { city: selectedCity, country: pais }
        );
        hint.classList.add("is-selected");
      } else {
        hint.textContent = i18n(
          "js_city_hint",
          `${cities.length} cidades em ${pais} — digite para filtrar; só da lista.`,
          { n: cities.length, country: pais }
        );
        hint.classList.remove("is-selected");
      }
    }

    function filterList(q) {
      const pais = countryValue();
      const cities = citiesForCountry(pais);
      const term = (q || "").trim().toLowerCase();
      if (!term) return cities;
      const starts = [];
      const contains = [];
      for (const c of cities) {
        const n = c.toLowerCase();
        if (n.startsWith(term)) starts.push(c);
        else if (n.includes(term)) contains.push(c);
      }
      return starts.concat(contains);
    }

    function render(list, q) {
      currentList = list;
      dropdown.innerHTML = "";
      activeIdx = -1;
      const pais = countryValue();
      if (!pais) {
        const empty = document.createElement("div");
        empty.className = "country-picker-empty";
        empty.textContent = i18n(
          "js_city_need_country",
          "Seleccione primeiro o país."
        );
        dropdown.appendChild(empty);
        return;
      }
      const head = document.createElement("div");
      head.className = "country-picker-empty";
      head.style.textAlign = "left";
      head.textContent = list.length
        ? (q || "").trim()
          ? i18n("js_city_filter", `${list.length} cidade(s) em ${pais}`, {
              n: list.length,
              country: pais,
            })
          : i18n(
              "js_city_list",
              `Cidades de ${pais} (${list.length}) — digite para filtrar:`,
              { country: pais, n: list.length }
            )
        : i18n("js_city_none", `Nenhuma cidade encontrada em ${pais}`, {
            country: pais,
          });
      dropdown.appendChild(head);
      list.forEach((cidade, i) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "country-picker-item";
        btn.dataset.index = String(i);
        btn.innerHTML = `<span class="nome">${highlightMatch(cidade, q)}</span>
          <span class="meta">${escapeHtml(pais)}</span>`;
        btn.addEventListener("mousedown", (e) => {
          e.preventDefault();
          selectCity(cidade);
        });
        dropdown.appendChild(btn);
      });
    }

    function selectCity(cidade) {
      const cities = citiesForCountry(countryValue());
      if (!cities.some((c) => c.toLowerCase() === cidade.toLowerCase())) return;
      const canon = cities.find((c) => c.toLowerCase() === cidade.toLowerCase());
      selectedCity = canon;
      input.value = canon;
      hidden.value = canon;
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
      close();
      updateHint();
    }

    function open(q) {
      const pais = countryValue();
      // se o país mudou, limpar cidade inválida
      if (pais !== lastCountry) {
        lastCountry = pais;
        const cities = citiesForCountry(pais);
        if (
          selectedCity &&
          !cities.some((c) => c.toLowerCase() === selectedCity.toLowerCase())
        ) {
          selectedCity = "";
          input.value = "";
          hidden.value = "";
          input.classList.remove("is-valid");
        }
      }
      let useQ = typeof q === "string" ? q : input.value;
      if (selectedCity && useQ === selectedCity) useQ = "";
      render(filterList(useQ), useQ);
      dropdown.hidden = false;
    }

    function close() {
      dropdown.hidden = true;
      activeIdx = -1;
    }

    function enforceValid() {
      const pais = countryValue();
      const cities = citiesForCountry(pais);
      const typed = input.value.trim();
      const match = cities.find((c) => c.toLowerCase() === typed.toLowerCase());
      if (match) {
        selectCity(match);
        return true;
      }
      if (selectedCity && cities.some((c) => c.toLowerCase() === selectedCity.toLowerCase())) {
        input.value = selectedCity;
        hidden.value = selectedCity;
        input.classList.remove("is-invalid");
        updateHint("Só cidades da lista do país. Valor restaurado.");
        setTimeout(() => updateHint(), 2500);
        return true;
      }
      input.value = "";
      hidden.value = "";
      selectedCity = "";
      input.classList.add("is-invalid");
      updateHint(
        pais
          ? i18n("js_pick_city_alert", "Seleccione uma cidade da lista deste país.")
          : i18n("js_city_need_country", "Seleccione primeiro o país.")
      );
      return !required;
    }

    // observar mudanças no país (input no country-picker)
    function bindCountryWatch() {
      const h = document.querySelector(
        `.country-picker:not(.city-picker) input[type="hidden"][name="${countryName}"]`
      );
      if (!h) return;
      // poll leve: country picker actualiza hidden
      let prev = h.value;
      setInterval(() => {
        if (h.value !== prev) {
          prev = h.value;
          lastCountry = "";
          open(input.value);
          updateHint();
        }
      }, 300);
    }

    input.addEventListener("focus", () => open());
    input.addEventListener("click", () => open());
    input.addEventListener("input", () => {
      const typed = input.value.trim();
      const cities = citiesForCountry(countryValue());
      const match = cities.find((c) => c.toLowerCase() === typed.toLowerCase());
      if (match) {
        hidden.value = match;
        selectedCity = match;
        input.classList.remove("is-invalid");
        input.classList.add("is-valid");
      } else {
        hidden.value = "";
        input.classList.remove("is-valid");
        if (typed) input.classList.add("is-invalid");
        else input.classList.remove("is-invalid");
      }
      open(input.value);
      updateHint(
        typed && !match
          ? `A filtrar «${typed}»… escolha da lista`
          : undefined
      );
    });
    input.addEventListener("blur", () => {
      setTimeout(() => {
        enforceValid();
        close();
      }, 180);
    });
    input.addEventListener("keydown", (e) => {
      const items = dropdown.querySelectorAll(".country-picker-item");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (dropdown.hidden) open();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle("active", i === activeIdx));
        items[activeIdx]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
        items.forEach((el, i) => el.classList.toggle("active", i === activeIdx));
      } else if (e.key === "Enter") {
        if (activeIdx >= 0 && items[activeIdx] && !dropdown.hidden) {
          e.preventDefault();
          const c = currentList[activeIdx];
          if (c) selectCity(c);
        } else {
          e.preventDefault();
          enforceValid();
        }
      } else if (e.key === "Escape") {
        enforceValid();
        close();
      }
    });

    const form = root.closest("form");
    if (form && !form.dataset.cityValidateBound) {
      form.dataset.cityValidateBound = "1";
      form.addEventListener("submit", (e) => {
        let ok = true;
        form.querySelectorAll(".city-picker").forEach((cp) => {
          const h = cp.querySelector('input[type="hidden"]');
          const vis = cp.querySelector(".country-picker-input");
          const req = cp.dataset.required === "1";
          const countryN = cp.dataset.countryInput || "";
          const countryH =
            document.querySelector(
              `.country-picker:not(.city-picker) input[type="hidden"][name="${countryN}"]`
            ) ||
            document.querySelector(`input[type="hidden"][name="${countryN}"]`);
          const pais = (countryH && countryH.value) || "";
          const cities = citiesForCountry(pais);
          // Preferir hidden; se vazio, tentar texto visível (já seleccionado)
          let val = (h && h.value) || "";
          if (!val && vis) {
            const typed = vis.value.trim();
            const match = cities.find(
              (c) => c.toLowerCase() === typed.toLowerCase()
            );
            if (match) {
              val = match;
              if (h) h.value = match;
            }
          }
          const valid =
            val && cities.some((c) => c.toLowerCase() === val.toLowerCase());
          if ((req && !val) || (val && !valid)) {
            ok = false;
            if (h) h.value = "";
            if (vis) {
              vis.classList.add("is-invalid");
            }
          } else if (valid && h) {
            h.value = cities.find(
              (c) => c.toLowerCase() === val.toLowerCase()
            );
          }
        });
        if (!ok) {
          e.preventDefault();
          alert(
            "Seleccione uma cidade válida da lista do país escolhido.\n" +
              "Não é permitido escrever uma cidade que não esteja no sistema."
          );
        }
      });
    }

    bindCountryWatch();
    updateHint();
    // validar valor inicial
    if (selectedCity) {
      const cities = citiesForCountry(countryValue());
      if (!cities.some((c) => c.toLowerCase() === selectedCity.toLowerCase())) {
        selectedCity = "";
        input.value = "";
        hidden.value = "";
      } else {
        input.classList.add("is-valid");
      }
    }
  });
}

/** Códigos telefónicos de todos os países (injectados em base) */
function getPhoneCountries() {
  const el = document.getElementById("skyticket-phone-json");
  if (!el) return [];
  try {
    return JSON.parse(el.textContent || "[]");
  } catch (e) {
    return [];
  }
}

/**
 * Contacto internacional: select de código (+xxx) + número nacional.
 * data-name, data-value (+258…), data-default-iso (ex. MZ)
 */
function initPhonePickers() {
  const countries = getPhoneCountries();
  if (!countries.length) return;

  // dial → lista de países (pode haver vários com +1)
  const byDial = {};
  countries.forEach((c) => {
    if (!byDial[c.dial]) byDial[c.dial] = [];
    byDial[c.dial].push(c);
  });

  // opções por ordem alfabética do nome do país
  const options = countries.slice().sort((a, b) =>
    String(a.nome || "").localeCompare(String(b.nome || ""), uiLang(), {
      sensitivity: "base",
    })
  );

  function parseE164(raw, defaultIso) {
    let s = String(raw || "").trim();
    s = s.replace(/[^\d+]/g, "");
    if (s.startsWith("00")) s = "+" + s.slice(2);
    const digits = s.replace(/\D/g, "");
    if (!digits) {
      return { dial: dialForIso(defaultIso), national: "", e164: "" };
    }
    // Match longest dial code prefix
    let best = "";
    Object.keys(byDial).forEach((d) => {
      if (digits.startsWith(d) && d.length > best.length) best = d;
    });
    if (s.startsWith("+") && best) {
      return {
        dial: best,
        national: digits.slice(best.length).replace(/^0+/, ""),
        e164: "+" + best + digits.slice(best.length).replace(/^0+/, ""),
      };
    }
    if (best && digits.length > best.length + 5) {
      return {
        dial: best,
        national: digits.slice(best.length).replace(/^0+/, ""),
        e164: "+" + best + digits.slice(best.length).replace(/^0+/, ""),
      };
    }
    const d0 = dialForIso(defaultIso);
    return {
      dial: d0,
      national: digits.replace(/^0+/, ""),
      e164: d0 && digits ? "+" + d0 + digits.replace(/^0+/, "") : "",
    };
  }

  function dialForIso(iso) {
    const c = countries.find((x) => x.codigo === (iso || "").toUpperCase());
    return c ? c.dial : "258";
  }

  function isoForDial(dial, preferredIso) {
    const list = byDial[dial] || [];
    if (!list.length) return preferredIso || "MZ";
    const pref = list.find((x) => x.codigo === (preferredIso || "").toUpperCase());
    return (pref || list[0]).codigo;
  }

  document.querySelectorAll(".phone-picker").forEach((root) => {
    if (root.dataset.ready === "1") return;
    root.dataset.ready = "1";

    const name = root.dataset.name || "telefone";
    const required = root.dataset.required === "1";
    const defaultIso = (root.dataset.defaultIso || "MZ").toUpperCase();
    const initial = parseE164(root.dataset.value || "", defaultIso);

    root.innerHTML = "";

    const select = document.createElement("select");
    select.className = "phone-picker-dial";
    select.setAttribute("aria-label", "Código do país");
    // Agrupar visualmente: +dial · País
    options.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.dial + "|" + c.codigo;
      opt.textContent = `${c.nome} (+${c.dial})`;
      opt.dataset.dial = c.dial;
      opt.dataset.iso = c.codigo;
      select.appendChild(opt);
    });

    // seleccionar dial inicial
    let selVal = `${initial.dial}|${isoForDial(initial.dial, defaultIso)}`;
    if (![...select.options].some((o) => o.value === selVal)) {
      // fallback MZ
      selVal = `${dialForIso(defaultIso)}|${defaultIso}`;
    }
    select.value = selVal;
    // se o dial existe noutro ISO, escolher a opção correcta
    for (let i = 0; i < select.options.length; i++) {
      const o = select.options[i];
      if (o.dataset.dial === initial.dial) {
        if (o.dataset.iso === defaultIso || !initial.e164) {
          select.selectedIndex = i;
          if (o.dataset.iso === defaultIso) break;
        } else if (!select.value.startsWith(initial.dial + "|")) {
          select.selectedIndex = i;
        }
      }
    }
    // Prefer exact dial match first option with that dial
    for (let i = 0; i < select.options.length; i++) {
      if (select.options[i].dataset.dial === initial.dial) {
        select.selectedIndex = i;
        break;
      }
    }

    const national = document.createElement("input");
    national.type = "tel";
    national.className = "phone-picker-national";
    national.placeholder = "Número (sem o código do país)";
    national.autocomplete = "tel-national";
    national.inputMode = "tel";
    national.value = initial.national || "";
    if (required) national.required = true;

    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = name;
    hidden.value = initial.e164 || "";

    const preview = document.createElement("p");
    preview.className = "phone-picker-preview";

    function currentDial() {
      const v = (select.value || "").split("|")[0];
      return v || dialForIso(defaultIso);
    }

    function sync() {
      const dial = currentDial();
      // Aceitar espaços/hífens; se colar E.164 no campo nacional, reparsear
      let rawNat = (national.value || "").trim();
      if (rawNat.startsWith("+") || rawNat.startsWith("00")) {
        const parsed = parseE164(rawNat, defaultIso);
        if (parsed.dial && parsed.national) {
          for (let i = 0; i < select.options.length; i++) {
            if (select.options[i].dataset.dial === parsed.dial) {
              select.selectedIndex = i;
              break;
            }
          }
          rawNat = parsed.national;
        }
      }
      let nat = rawNat.replace(/[^\d]/g, "").replace(/^0+/, "");
      // Se o utilizador incluiu o código do país no número nacional (ex. 258849…)
      const dialNow = currentDial();
      if (dialNow && nat.startsWith(dialNow) && nat.length > dialNow.length + 4) {
        nat = nat.slice(dialNow.length).replace(/^0+/, "");
      }
      national.value = nat;
      const dialFinal = currentDial();
      if (dialFinal && nat && nat.length >= 6) {
        hidden.value = `+${dialFinal}${nat}`;
        const ctry = byDial[dialFinal] || [];
        const names = ctry
          .slice(0, 3)
          .map((c) => c.nome)
          .join(", ");
        preview.textContent = `✓ Número internacional: ${hidden.value}${
          names ? " · " + names + (ctry.length > 3 ? "…" : "") : ""
        }`;
        preview.className = "phone-picker-preview";
        national.classList.remove("is-invalid");
      } else if (nat) {
        hidden.value = "";
        preview.textContent =
          "Introduza o número completo (mín. 6 dígitos; o código do país já está seleccionado).";
        preview.className = "phone-picker-preview is-warn";
      } else {
        hidden.value = "";
        preview.textContent = `Código seleccionado: +${dialFinal} — aceite para qualquer país da lista.`;
        preview.className = "phone-picker-preview is-warn";
      }
    }

    root._skyticketSyncPhone = sync;

    // Se o utilizador colar +351912... no campo nacional, reconhecer
    national.addEventListener("paste", () => {
      setTimeout(sync, 0);
    });

    national.addEventListener("input", sync);
    national.addEventListener("change", sync);
    // Autofill do browser por vezes não dispara "input"
    national.addEventListener("blur", sync);
    select.addEventListener("change", sync);

    root.appendChild(select);
    root.appendChild(national);
    root.appendChild(hidden);
    root.appendChild(preview);
    sync();

    // Validação no submit (capture: corre antes de outros handlers e do POST)
    const form = root.closest("form");
    if (form && !form.dataset.phoneValidateBound) {
      form.dataset.phoneValidateBound = "1";
      form.addEventListener(
        "submit",
        (e) => {
          let ok = true;
          let firstBad = null;
          form.querySelectorAll(".phone-picker").forEach((pp) => {
            if (typeof pp._skyticketSyncPhone === "function") {
              pp._skyticketSyncPhone();
            }
            const h = pp.querySelector('input[type="hidden"]');
            const nat = pp.querySelector(".phone-picker-national");
            const req = pp.dataset.required === "1";
            const val = (h && h.value) || "";
            // E.164: + e 8–15 dígitos (ITU-T)
            if (req && (!val || !/^\+\d{8,15}$/.test(val))) {
              ok = false;
              if (nat) {
                nat.classList.add("is-invalid");
                if (!firstBad) firstBad = nat;
              }
            }
          });
          if (!ok) {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (firstBad) {
              firstBad.focus();
              firstBad.scrollIntoView({ block: "center", behavior: "smooth" });
            }
            alert(
              "Indique um telefone internacional válido (contacto e emergência).\n" +
                "1) Escolha o país na lista (ex.: Moçambique +258)\n" +
                "2) Escreva só o número nacional (ex.: 849053340)"
            );
          }
        },
        true
      );
    }
  });
}
