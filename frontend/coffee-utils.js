export function sourceName(raw) {
  if (raw.includes("rocket")) return "Rocket Coffee";
  if (raw.includes("atomic")) return "Atomic Coffee";
  if (raw.includes("ozone")) return "Ozone Coffee";
  if (raw.includes("coffeeembassy")) return "Coffee Embassy";
  if (raw.includes("eternal")) return "Eternal Coffee";
  if (raw.includes("slowcoffee")) return "Slow Coffee";
  if (raw.includes("vanguardcoffee")) return "Vanguard Coffee";
  if (raw.includes("c4coffee")) return "C4 Coffee";
  if (raw.includes("greyroasting")) return "Grey Roasting Co";
  if (raw.includes("wolfcoffee")) return "Wolf Coffee";
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

function searchableText(value, seen = new Set()) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (typeof value !== "object" || seen.has(value)) return "";

  seen.add(value);
  return Object.values(value).map((entry) => searchableText(entry, seen)).join(" ");
}

export function isBlend(item) {
  const isOzoneRanunga = item.source === "ozonecoffee.co.nz"
    && item.handle === "ta-matou-ranunga-a-whare";
  const isWolfMoreFM = item.source === "wolfcoffee.co.nz"
    && item.handle === "morefm-koha-coffee";
  return isOzoneRanunga || isWolfMoreFM || /\bblend\b/i.test([item.title, item.handle, item.product_type, item.tags, item.vendor, item.description, ...(item.metafields ? Object.values(item.metafields) : [])].filter(Boolean).join(" "));
}

export function isSubscription(item) {
  return /\bsubscription\b/i.test([item.title, item.handle, item.product_type, item.tags].filter(Boolean).join(" "));
}

export function isBundleOrBoxSet(item) {
  const text = [item.title, item.handle].filter(Boolean).join(" ");
  const isAtomicDuo = item.source === "atomiccoffee.co.nz"
    && item.handle === "ultimate-coffee-duo";
  return isAtomicDuo || /\b(bundle|discovery[\s-]box|box[\s-]set|selection[\s-]box)\b/i.test(text);
}

export function isOzoneConcentrate(item) {
  return item.source === "ozonecoffee.co.nz" && item.handle === "cold-brew-concentrate";
}

export function filterCategories(item) {
  const values = categories(item.category);
  if (isBlend(item)) values.push("blend");
  return [...new Set(values)];
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
  activeBlend = "all",
  activeSort = "title",
) {
  const term = query.toLowerCase();
  return items
    .filter((item) => {
      const categoryMatch = activeCategory === "all" || filterCategories(item).includes(activeCategory);
      const sourceMatch = activeSource === "all" || item.source === activeSource;
      const varietalMatch = activeVarietal === "all"
        || (metadataValue(item, "varietal") || "").toLowerCase().split(",").map((v) => v.trim()).includes(activeVarietal.toLowerCase());
      const originMatch = activeOriginCountry === "all"
        || (metadataValue(item, "origin_country") || "").toLowerCase().split(",").map((o) => o.trim()).includes(activeOriginCountry.toLowerCase());
      const producerMatch = activeProducer === "all" || metadataValue(item, "producer") === activeProducer;
      const processMatch = activeProcess === "all"
        || (metadataValue(item, "process") || "").toLowerCase().split(",").map((p) => p.trim()).includes(activeProcess.toLowerCase());
      const decafMatch = activeDecaf === "all" || String(isDecaf(item)) === activeDecaf;
      const blendMatch = activeBlend === "all"
        || (activeBlend === "true" && isBlend(item))
        || (activeBlend === "false" && !isBlend(item));
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
        && blendMatch
        && searchText.includes(term);
    })
    .sort((a, b) => {
      if (activeSort === "newest" || activeSort === "oldest") {
        const difference = new Date(a.updated_at || 0) - new Date(b.updated_at || 0);
        if (difference) return activeSort === "newest" ? -difference : difference;
      } else if (activeSort === "price-high" || activeSort === "price-low") {
        const difference = Number(a.price_min_nzd || 0) - Number(b.price_min_nzd || 0);
        if (difference) return activeSort === "price-high" ? -difference : difference;
      }
      const titleOrder = a.title.localeCompare(b.title);
      return activeSort === "title-desc" ? -titleOrder : titleOrder;
    });
}