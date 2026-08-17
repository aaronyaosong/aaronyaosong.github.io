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

export function sizePrices(item) {
  const seen = new Set();
  return (item.size_prices || [])
    .filter((row) => Number(row.size_grams) > 0 && Number.isFinite(Number(row.price_nzd)))
    .filter((row) => {
      const key = `${Number(row.size_grams)}:${Number(row.price_nzd)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort((a, b) => Number(a.size_grams) - Number(b.size_grams));
}

export function pricePerGram(price, sizeGrams) {
  return `NZD $${(Number(price) / Number(sizeGrams)).toFixed(3)}/g`;
}

export function sizeLabel(sizeGrams) {
  const grams = Number(sizeGrams);
  return grams >= 1000 && grams % 1000 === 0 ? `${grams / 1000}kg` : `${grams}g`;
}

export function categories(categoryStr) {
  return String(categoryStr || "").split(",").map((part) => part.trim()).filter(Boolean);
}

export function metadataValue(item, field) {
  if (item[field]) return String(item[field]).trim().toLowerCase();
  if (field === "origin_country") {
    const text = [item.title, item.handle].filter(Boolean).join(" ").toLowerCase();
    const countries = ["brazil", "colombia", "costa rica", "ecuador", "ethiopia", "guatemala", "honduras", "kenya", "peru", "rwanda", "tanzania"];
    return countries.find((country) => text.includes(country)) || String(item.origin || "unknown").trim().toLowerCase();
  }
  if (field === "producer") {
    const titlePrefix = String(item.title || "").split(" - ")[0].trim();
    return titlePrefix && !/^(decaf|espresso blend|espresso dulce)$/i.test(titlePrefix)
      ? titlePrefix.toLowerCase()
      : "unknown";
  }
  if (field === "process") {
    const match = String(item.title || "").match(/\[([^\]]+)\]/);
    return match ? match[1].split(/\s+/)[0].toLowerCase() : "unknown";
  }
  return "unknown";
}

export function isDecaf(item) {
  if (typeof item.decaf === "boolean") return item.decaf;
  return /\bdecaf(?:f)?\b/i.test([item.title, item.handle, item.tags].filter(Boolean).join(" "));
}

export function filterAndSortItems(
  items,
  activeCategory,
  query,
  activeSource = "all",
  activeVarietal = "all",
  activeOriginCountry = "all",
  activeProducer = "all",
  activeProcess = "all",
  activeDecaf = "all",
) {
  const term = query.toLowerCase();
  return items
    .filter((item) => {
      const categoryMatch = activeCategory === "all" || categories(item.category).includes(activeCategory);
      const sourceMatch = activeSource === "all" || item.source === activeSource;
      const varietalMatch = activeVarietal === "all" || categories(item.varietal || "").includes(activeVarietal);
      const originMatch = activeOriginCountry === "all" || metadataValue(item, "origin_country") === activeOriginCountry;
      const producerMatch = activeProducer === "all" || metadataValue(item, "producer") === activeProducer;
      const processMatch = activeProcess === "all" || metadataValue(item, "process") === activeProcess;
      const decafMatch = activeDecaf === "all" || String(isDecaf(item)) === activeDecaf;
      const searchText = [
        item.title,
        item.category,
        item.source,
        item.varietal,
        item.origin_country,
        item.origin,
        item.producer,
        item.process,
        item.description,
        item.flavour_notes,
      ].join(" ").toLowerCase();
      return categoryMatch
        && sourceMatch
        && varietalMatch
        && originMatch
        && producerMatch
        && processMatch
        && decafMatch
        && searchText.includes(term);
    })
    .sort((a, b) => a.title.localeCompare(b.title));
}