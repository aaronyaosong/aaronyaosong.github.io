export function sourceName(raw) {
  if (raw.includes("rocket")) return "Rocket Coffee";
  if (raw.includes("atomic")) return "Atomic Coffee";
  return raw;
}

export function nzPrice(item) {
  if (item.price_min_nzd === item.price_max_nzd) {
    return `NZD $${Number(item.price_min_nzd).toFixed(2)}`;
  }
  return `NZD $${Number(item.price_min_nzd).toFixed(2)} - $${Number(item.price_max_nzd).toFixed(2)}`;
}

export function categories(categoryStr) {
  return categoryStr.split(",").map((part) => part.trim()).filter(Boolean);
}

export function filterAndSortItems(items, activeCategory, query, activeSource = "all", activeVarietal = "all") {
  const term = query.toLowerCase();
  return items
    .filter((item) => {
      const categoryMatch = activeCategory === "all" || categories(item.category).includes(activeCategory);
      const sourceMatch = activeSource === "all" || item.source === activeSource;
      const varietalMatch = activeVarietal === "all" || categories(item.varietal || "").includes(activeVarietal);
      const searchText = [item.title, item.category, item.source].join(" ").toLowerCase();
      return categoryMatch && sourceMatch && varietalMatch && searchText.includes(term);
    })
    .sort((a, b) => a.title.localeCompare(b.title));
}