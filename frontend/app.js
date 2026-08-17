import {
  categories,
  filterCategories,
  filterAndSortItems,
  isDecaf,
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
    activeVarietal: "all",
    activeOriginCountry: "all",
    activeProducer: "all",
    activeProcess: "all",
    activeDecaf: "all",
    query: "",
  };

  const cardsEl = documentRef.getElementById("cards");
  const statsEl = documentRef.getElementById("stats");
  const resultCountEl = documentRef.getElementById("resultCount");
  const updatedEl = documentRef.getElementById("last-updated");
  const errorEl = documentRef.getElementById("errorMessage");
  const searchInput = documentRef.getElementById("searchInput");
  const categorySelect = documentRef.getElementById("categoryFilter");
  const sourceSelect = documentRef.getElementById("sourceFilter");
  const varietalSelect = documentRef.getElementById("varietalFilter");
  const originCountrySelect = documentRef.getElementById("originCountryFilter");
  const producerSelect = documentRef.getElementById("producerFilter");
  const processSelect = documentRef.getElementById("processFilter");
  const decafSelect = documentRef.getElementById("decafFilter");

  function populateSelect(select, values, allLabel, formatValue = (value) => value) {
    select.innerHTML = `<option value="all">${allLabel}</option>`;
    [...values].sort((a, b) => a.localeCompare(b)).forEach((value) => {
      const option = documentRef.createElement("option");
      option.value = value;
      option.textContent = formatValue(value);
      select.appendChild(option);
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
      state.activeOriginCountry,
      state.activeProducer,
      state.activeProcess,
      state.activeDecaf,
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
        .map((cat) => `<span class="badge category">${cat}</span>`)
        .join("");

      const prices = sizePrices(item);
      const priceDetails = prices.length
        ? `<ul class="size-prices">${prices.map((row) => `
            <li><span>${sizeLabel(row.size_grams)}</span><span>NZD $${Number(row.price_nzd).toFixed(2)} (${pricePerGram(row.price_nzd, row.size_grams)})</span></li>
          `).join("")}</ul>`
        : `<p class="price">${nzPrice(item)} <span class="price-note">Size pricing unavailable</span></p>`;
      const description = item.description
        ? `<p class="description">${item.description}</p>`
        : "";
      const flavourNotes = item.flavour_notes && item.flavour_notes !== "unknown"
        ? `<p class="flavour-notes"><strong>Flavour notes:</strong> ${item.flavour_notes}</p>`
        : "";

      card.innerHTML = `
        <h3>${item.title}</h3>
        <div class="badges">
          <span class="badge source">${sourceName(item.source)}</span>
          ${categoryBadges}
        </div>
        ${description}
        ${flavourNotes}
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

      state.items = payload.items || [];
      populateSelect(
        categorySelect,
        new Set(state.items.flatMap((item) => filterCategories(item))),
        "All roast types",
        (value) => value.replace(/\b\w/g, (letter) => letter.toUpperCase()),
      );
      populateSelect(sourceSelect, new Set(state.items.map((item) => item.source)), "All stores", sourceName);
      populateSelect(
        varietalSelect,
        new Set(state.items.flatMap((item) => categories(item.varietal || ""))),
        "All varietals",
      );
      populateSelect(originCountrySelect, new Set(state.items.map((item) => metadataValue(item, "origin_country"))), "All origin countries");
      populateSelect(producerSelect, new Set(state.items.map((item) => metadataValue(item, "producer"))), "All producers");
      populateSelect(processSelect, new Set(state.items.map((item) => metadataValue(item, "process"))), "All processes");
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

  varietalSelect.addEventListener("change", (event) => {
    state.activeVarietal = event.target.value;
    renderCards();
  });

  originCountrySelect.addEventListener("change", (event) => {
    state.activeOriginCountry = event.target.value;
    renderCards();
  });

  producerSelect.addEventListener("change", (event) => {
    state.activeProducer = event.target.value;
    renderCards();
  });

  processSelect.addEventListener("change", (event) => {
    state.activeProcess = event.target.value;
    renderCards();
  });

  decafSelect.addEventListener("change", (event) => {
    state.activeDecaf = event.target.value;
    renderCards();
  });

  categorySelect.addEventListener("change", (event) => {
    state.activeCategory = event.target.value;
    renderCards();
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
    && doc.getElementById("categoryFilter")
    && doc.getElementById("sourceFilter")
    && doc.getElementById("varietalFilter")
    && doc.getElementById("originCountryFilter")
    && doc.getElementById("producerFilter")
    && doc.getElementById("processFilter")
    && doc.getElementById("decafFilter")
  );
}

// Initial render bootstrap in browser contexts.
if (typeof window !== "undefined" && typeof document !== "undefined" && hasRequiredDom(document)) {
  bootstrapApp();
}
