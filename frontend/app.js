import {
  categories,
  filterCategories,
  filterAndSortItems,
  isBundleOrBoxSet,
  isDecaf,
  isOzoneConcentrate,
  isSubscription,
  metadataValue,
  nzPrice,
  pricePerGram,
  sizeLabel,
  sizePrices,
  sourceName,
} from "./coffee-utils.js";

export function createApp({
  documentRef = document,
  fetchImpl = fetch,
  dataPath = "./data/latest.json",
} = {}) {
  // Minimal client-side state for search and category filtering.
  const state = {
    items: [],
    activeCategory: "all",
    activeSource: "all",
    activeOrigin: "all",
    activeProcess: "all",
    activeVarietal: "all",
    activeBlend: "all",
    activeDecaf: "all",
    activeSort: "newest",
    query: "",
  };

  const cardsEl = documentRef.getElementById("cards");
  const statsEl = documentRef.getElementById("stats");
  const resultCountEl = documentRef.getElementById("resultCount");
  const updatedEl = documentRef.getElementById("last-updated");
  const errorEl = documentRef.getElementById("errorMessage");
  const searchInput = documentRef.getElementById("searchInput");
  const categoryFilters = documentRef.getElementById("categoryFilters");
  const blendSelect = documentRef.getElementById("blendFilter");
  const sourceSelect = documentRef.getElementById("sourceFilter");
  const originSelect = documentRef.getElementById("originFilter");
  const processSelect = documentRef.getElementById("processFilter");
  const varietalSelect = documentRef.getElementById("varietalFilter");
  const decafSelect = documentRef.getElementById("decafFilter");
  const sortSelect = documentRef.getElementById("sortFilter");
  if (!sortSelect.value || sortSelect.value === "title") {
    sortSelect.value = state.activeSort;
  } else {
    state.activeSort = sortSelect.value;
  }

  function populateSelect(select, values, allLabel, formatValue = (value) => value) {
    if (!select) return;
    select.innerHTML = `<option value="all">${allLabel}</option>`;
    [...values].sort((a, b) => a.localeCompare(b)).forEach((value) => {
      const option = documentRef.createElement("option");
      option.value = value;
      option.textContent = formatValue(value);
      select.appendChild(option);
    });
  }

  function populateCategoryButtons(items) {
    categoryFilters.innerHTML = "";
    const foundCategories = [...new Set(items.flatMap((item) => categories(item.category)))].sort((a, b) => a.localeCompare(b));
    ["all", ...foundCategories].forEach((category) => {
      const button = documentRef.createElement("button");
      button.className = `chip${category === state.activeCategory ? " active" : ""}`;
      button.dataset.category = category;
      button.textContent = category === "all"
        ? "All"
        : category.replace(/\b\w/g, (letter) => letter.toUpperCase());
      categoryFilters.appendChild(button);
    });
  }

  function renderStats(items, generatedAt) {
    // Build per-source summary cards from the already-filtered item list.
    const bySource = items.reduce((acc, item) => {
      acc[item.source] = (acc[item.source] || 0) + 1;
      return acc;
    }, {});

    statsEl.innerHTML = "";

    const total = documentRef.createElement("article");
    total.className = "stat";
    total.innerHTML = `<p class="label">Total Available</p><p class="value">${items.length}</p>`;
    statsEl.appendChild(total);

    Object.entries(bySource).forEach(([source, count]) => {
      const card = documentRef.createElement("article");
      card.className = "stat";
      card.innerHTML = `<p class="label">${sourceName(source)}</p><p class="value">${count}</p>`;
      statsEl.appendChild(card);
    });

    const generated = new Date(generatedAt);
    updatedEl.textContent = `Last updated: ${generated.toLocaleString()}`;
  }

  function renderCards() {
    const rows = filterAndSortItems(
      state.items,
      state.activeCategory,
      state.query,
      state.activeSource,
      state.activeVarietal,
      state.activeOrigin,
      "all",
      state.activeProcess,
      state.activeDecaf,
      state.activeBlend,
      state.activeSort,
    );

    resultCountEl.textContent = `${rows.length} result${rows.length === 1 ? "" : "s"}`;
    cardsEl.innerHTML = "";

    if (!rows.length) {
      const p = documentRef.createElement("p");
      p.textContent = "No coffees matched your filters.";
      cardsEl.appendChild(p);
      return;
    }

    rows.forEach((item) => {
      const card = documentRef.createElement("article");
      card.className = "card";

      const categoryBadges = categories(item.category)
        .map((cat) => `<span class="badge category" data-category="${cat.toLowerCase()}">${cat}</span>`)
        .join("");

      const originBadges = (item.origin_country && item.origin_country !== "unknown")
        ? item.origin_country.split(",").map((o) => `<span class="badge origin">${o.trim()}</span>`).join("")
        : "";

      const processBadges = (item.process && item.process !== "unknown")
        ? item.process.split(",").map((p) => `<span class="badge process">${p.trim()}</span>`).join("")
        : "";

      const varietalMeta = item.varietal && item.varietal !== "unknown"
        ? `<p class="card-meta"><strong>Variety:</strong> ${item.varietal}</p>`
        : "";

      const flavourNotes = item.flavour_notes && item.flavour_notes !== "unknown"
        ? `<p class="flavour-notes"><strong>Flavour:</strong> ${item.flavour_notes}</p>`
        : "";

      const prices = sizePrices(item);
      const priceDetails = prices.length
        ? `<ul class="size-prices">${prices.map((row) => `
            <li><span>${sizeLabel(row.size_grams)}</span><span>NZD $${Number(row.price_nzd).toFixed(2)} (${pricePerGram(row.price_nzd, row.size_grams)})</span></li>
          `).join("")}</ul>`
        : `<p class="price">${nzPrice(item)} <span class="price-note">Size pricing unavailable</span></p>`;
      const descriptionContent = item.description ? `<p>${item.description}</p>` : "";
      const description = descriptionContent
        ? `<button class="description-toggle" type="button" data-description-toggle>Show description</button><div class="description" hidden>${descriptionContent}</div>`
        : "";

      card.innerHTML = `
        <h3>${item.title}</h3>
        <div class="badges">
          <span class="badge source">${sourceName(item.source)}</span>
          ${categoryBadges}
          ${originBadges}
          ${processBadges}
        </div>
        ${varietalMeta}
        ${flavourNotes}
        ${description}
        ${priceDetails}
        <a href="${item.product_url}" target="_blank" rel="noreferrer">View Product</a>
      `;

      cardsEl.appendChild(card);
    });
  }

  async function loadData() {
    try {
      // Frontend is static, so it reads the latest generated snapshot JSON.
      const response = await fetchImpl(dataPath, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();

      state.items = (payload.items || []).filter((item) => (!isSubscription(item) && !isOzoneConcentrate(item) && !isBundleOrBoxSet(item)));
      populateCategoryButtons(state.items);
      populateSelect(sourceSelect, new Set(state.items.map((item) => item.source)), "All stores", sourceName);

      const origins = new Set(
        state.items.flatMap((item) => {
          const o = metadataValue(item, "origin_country");
          return o && o !== "unknown" ? o.split(",").map((s) => s.trim()) : [];
        })
      );
      populateSelect(originSelect, origins, "All origins", (v) => v.replace(/\b\w/g, (c) => c.toUpperCase()));

      const processes = new Set(
        state.items.flatMap((item) => {
          const p = metadataValue(item, "process");
          return p && p !== "unknown" ? p.split(",").map((s) => s.trim()) : [];
        })
      );
      populateSelect(processSelect, processes, "All processes", (v) => v.replace(/\b\w/g, (c) => c.toUpperCase()));

      const varietals = new Set(
        state.items.flatMap((item) => {
          const v = metadataValue(item, "varietal");
          return v && v !== "unknown" ? v.split(",").map((s) => s.trim()) : [];
        })
      );
      populateSelect(varietalSelect, varietals, "All varieties", (v) => v.replace(/\b\w/g, (c) => c.toUpperCase()));

      renderStats(state.items, payload.generated_at);
      renderCards();
    } catch (err) {
      errorEl.hidden = false;
      errorEl.textContent = `Could not load ${dataPath} (${err.message}). Run the scraper and commit latest.json.`;
    }
  }

  searchInput.addEventListener("input", (event) => {
    state.query = event.target.value;
    renderCards();
  });

  sourceSelect.addEventListener("change", (event) => {
    state.activeSource = event.target.value;
    renderCards();
  });

  if (originSelect) {
    originSelect.addEventListener("change", (event) => {
      state.activeOrigin = event.target.value;
      renderCards();
    });
  }

  if (processSelect) {
    processSelect.addEventListener("change", (event) => {
      state.activeProcess = event.target.value;
      renderCards();
    });
  }

  if (varietalSelect) {
    varietalSelect.addEventListener("change", (event) => {
      state.activeVarietal = event.target.value;
      renderCards();
    });
  }

  decafSelect.addEventListener("change", (event) => {
    state.activeDecaf = event.target.value;
    renderCards();
  });

  blendSelect.addEventListener("change", (event) => {
    state.activeBlend = event.target.value;
    renderCards();
  });

  sortSelect.addEventListener("change", (event) => {
    state.activeSort = event.target.value;
    renderCards();
  });

  categoryFilters.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-category]");
    if (!button) return;
    state.activeCategory = button.dataset.category;
    categoryFilters.querySelectorAll("button").forEach((node) => {
      node.classList.toggle("active", node === button);
    });
    renderCards();
  });

  cardsEl.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-description-toggle]");
    if (!toggle) return;
    const description = toggle.nextElementSibling;
    const isHidden = description.hidden;
    description.hidden = !isHidden;
    toggle.textContent = isHidden ? "Hide description" : "Show description";
  });

  return {
    state,
    loadData,
    renderCards,
  };
}

export async function bootstrapApp() {
  const app = createApp();
  await app.loadData();
  return app;
}

function hasRequiredDom(doc) {
  return Boolean(
    doc.getElementById("cards")
    && doc.getElementById("stats")
    && doc.getElementById("resultCount")
    && doc.getElementById("last-updated")
    && doc.getElementById("errorMessage")
    && doc.getElementById("searchInput")
    && doc.getElementById("categoryFilters")
    && doc.getElementById("categoryFilters")
    && doc.getElementById("blendFilter")
    && doc.getElementById("sourceFilter")
    && doc.getElementById("decafFilter")
    && doc.getElementById("sortFilter")
  );
}

// Initial render bootstrap in browser contexts.
if (typeof window !== "undefined" && typeof document !== "undefined" && hasRequiredDom(document)) {
  bootstrapApp();
}
