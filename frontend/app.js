import { categories, filterAndSortItems, nzPrice, sourceName } from "./coffee-utils.js";

export function createApp({
  documentRef = document,
  fetchImpl = fetch,
  dataPath = "./data/latest.json",
} = {}) {
  // Minimal client-side state for search and category filtering.
  const state = {
    items: [],
    activeCategory: "all",
    query: "",
  };

  const cardsEl = documentRef.getElementById("cards");
  const statsEl = documentRef.getElementById("stats");
  const resultCountEl = documentRef.getElementById("resultCount");
  const updatedEl = documentRef.getElementById("last-updated");
  const errorEl = documentRef.getElementById("errorMessage");
  const searchInput = documentRef.getElementById("searchInput");
  const filterWrap = documentRef.getElementById("categoryFilters");

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
    const rows = filterAndSortItems(state.items, state.activeCategory, state.query);

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

      card.innerHTML = `
        <h3>${item.title}</h3>
        <div class="badges">
          <span class="badge source">${sourceName(item.source)}</span>
          ${categoryBadges}
        </div>
        <p class="price">${nzPrice(item)}</p>
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

  filterWrap.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-category]");
    if (!button) return;
    state.activeCategory = button.dataset.category;

    filterWrap.querySelectorAll("button").forEach((node) => {
      node.classList.toggle("active", node === button);
    });

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
  );
}

// Initial render bootstrap in browser contexts.
if (typeof window !== "undefined" && typeof document !== "undefined" && hasRequiredDom(document)) {
  bootstrapApp();
}
