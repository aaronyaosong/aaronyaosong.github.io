// Minimal client-side state for search and category filtering.
const state = {
  items: [],
  activeCategory: "all",
  query: "",
};

const cardsEl = document.getElementById("cards");
const statsEl = document.getElementById("stats");
const resultCountEl = document.getElementById("resultCount");
const updatedEl = document.getElementById("last-updated");
const errorEl = document.getElementById("errorMessage");
const searchInput = document.getElementById("searchInput");
const filterWrap = document.getElementById("categoryFilters");

function sourceName(raw) {
  if (raw.includes("rocket")) return "Rocket Coffee";
  if (raw.includes("atomic")) return "Atomic Coffee";
  return raw;
}

function nzPrice(item) {
  if (item.price_min_nzd === item.price_max_nzd) {
    return `NZD $${Number(item.price_min_nzd).toFixed(2)}`;
  }
  return `NZD $${Number(item.price_min_nzd).toFixed(2)} - $${Number(item.price_max_nzd).toFixed(2)}`;
}

function categories(categoryStr) {
  return categoryStr.split(",").map((part) => part.trim()).filter(Boolean);
}

function renderStats(items, generatedAt) {
  // Build per-source summary cards from the already-filtered item list.
  const bySource = items.reduce((acc, item) => {
    acc[item.source] = (acc[item.source] || 0) + 1;
    return acc;
  }, {});

  statsEl.innerHTML = "";

  const total = document.createElement("article");
  total.className = "stat";
  total.innerHTML = `<p class="label">Total Available</p><p class="value">${items.length}</p>`;
  statsEl.appendChild(total);

  Object.entries(bySource).forEach(([source, count]) => {
    const card = document.createElement("article");
    card.className = "stat";
    card.innerHTML = `<p class="label">${sourceName(source)}</p><p class="value">${count}</p>`;
    statsEl.appendChild(card);
  });

  const generated = new Date(generatedAt);
  const formatted = generated.toLocaleString();
  updatedEl.textContent = `Last updated: ${formatted}`;
}

function renderCards() {
  // Apply search + category filters before rendering cards.
  const term = state.query.toLowerCase();
  const rows = state.items.filter((item) => {
    const categoryMatch =
      state.activeCategory === "all" || categories(item.category).includes(state.activeCategory);

    const searchText = [
      item.title,
      item.category,
      item.source,
    ].join(" ").toLowerCase();

    return categoryMatch && searchText.includes(term);
  });

  resultCountEl.textContent = `${rows.length} result${rows.length === 1 ? "" : "s"}`;
  cardsEl.innerHTML = "";

  if (!rows.length) {
    const p = document.createElement("p");
    p.textContent = "No coffees matched your filters.";
    cardsEl.appendChild(p);
    return;
  }

  rows
    .sort((a, b) => a.title.localeCompare(b.title))
    .forEach((item) => {
      const card = document.createElement("article");
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
    const response = await fetch("./data/latest.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();

    state.items = payload.items || [];
    renderStats(state.items, payload.generated_at);
    renderCards();
  } catch (err) {
    errorEl.hidden = false;
    errorEl.textContent = `Could not load data/latest.json (${err.message}). Run the scraper and commit latest.json.`;
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

// Initial render bootstrap.
loadData();
