import { describe, expect, it } from "vitest";

import {
  categories,
  filterCategories,
  filterAndSortItems,
  isBundleOrBoxSet,
  isBlend,
  isDecaf,
  isOzoneConcentrate,
  isSubscription,
  metadataValue,
  nzPrice,
  pricePerGram,
  sourceName,
  sizeLabel,
  sizePrices,
} from "../../coffee-utils.js";


describe("coffee-utils unit", () => {
  it("maps known sources to display names", () => {
    expect(sourceName("rocketcoffee.co.nz")).toBe("Rocket Coffee");
    expect(sourceName("atomiccoffee.co.nz")).toBe("Atomic Coffee");
    expect(sourceName("ozonecoffee.co.nz")).toBe("Ozone Coffee");
    expect(sourceName("coffeeembassy.co.nz")).toBe("Coffee Embassy");
    expect(sourceName("eternalcoffee.co.nz")).toBe("Eternal Coffee");
    expect(sourceName("slowcoffee.co.nz")).toBe("Slow Coffee");

    expect(sourceName("vanguardcoffee.co.nz")).toBe("Vanguard Coffee");
    expect(sourceName("c4coffee.co")).toBe("C4 Coffee");
    expect(sourceName("greyroastingco.com")).toBe("Grey Roasting Co");
    expect(sourceName("wolfcoffee.co.nz")).toBe("Wolf Coffee");
  });

  it("formats single and ranged NZD prices", () => {
    expect(nzPrice({ price_min_nzd: 22, price_max_nzd: 22 })).toBe("NZD $22.00");
    expect(nzPrice({ price_min_nzd: 20, price_max_nzd: 35 })).toBe("NZD $20.00 - $35.00");
  });

  it("formats available sizes and price per gram", () => {
    const item = {
      size_prices: [
        { size_grams: 1000, price_nzd: 60 },
        { size_grams: 250, price_nzd: 20 },
        { size_grams: 250, price_nzd: 20 },
      ],
    };

    expect(sizePrices(item)).toEqual([
      { size_grams: 250, price_nzd: 20 },
      { size_grams: 1000, price_nzd: 60 },
    ]);
    expect(sizeLabel(1000)).toBe("1kg");
    expect(pricePerGram(20, 250)).toBe("NZD $0.080/g");
  });

  it("splits comma-separated categories", () => {
    expect(categories("filter roast,espresso roast")).toEqual(["filter roast", "espresso roast"]);
  });

  it("adds blend as a filter category when product text identifies a blend", () => {
    expect(filterCategories({ title: "House Blend", category: "espresso roast" })).toEqual([
      "espresso roast",
      "blend",
    ]);
    expect(filterCategories({ title: "Single Origin", category: "filter roast" })).toEqual(["filter roast"]);
  });

  it("identifies blends in all available product metadata", () => {
    expect(isBlend({ description: "A seasonal blend of coffees" })).toBe(true);
    expect(isBlend({ description: "Our rotating blends change with the season" })).toBe(false);
    expect(isBlend({ flavour_notes: "Chocolate", tags: ["espresso", "blend"] })).toBe(true);
    expect(isBlend({ metafields: { recipe: "House Blend" } })).toBe(true);
    expect(isBlend({ source: "ozonecoffee.co.nz", handle: "ta-matou-ranunga-a-whare" })).toBe(true);
    expect(isBlend({ title: "Single Origin", description: "Bright and fruity" })).toBe(false);
  });

  it("identifies bundles, discovery boxes, box sets, and Atomic duo for hiding", () => {
    // discovery boxes
    expect(isBundleOrBoxSet({ source: "c4coffee.co", handle: "blends-discovery-box", title: "Blends Discovery Box" })).toBe(true);
    expect(isBundleOrBoxSet({ source: "c4coffee.co", handle: "origins-discovery-box", title: "Origins Discovery Box" })).toBe(true);
    // bundles
    expect(isBundleOrBoxSet({ source: "eternalcoffee.co.nz", handle: "ethiopia-natural-bundle", title: "Limited: Ethiopia Natural Bundle" })).toBe(true);
    // box sets
    expect(isBundleOrBoxSet({ source: "vanguardcoffee.co.nz", handle: "pekerau-hills-box-set", title: "Pekerau Hills Box Set" })).toBe(true);
    // selection box
    expect(isBundleOrBoxSet({ source: "ozonecoffee.co.nz", handle: "seasonal-coffee-selection-box", title: "Seasonal Selection Box" })).toBe(true);
    // Atomic Ultimate Coffee Duo (specific override)
    expect(isBundleOrBoxSet({ source: "atomiccoffee.co.nz", handle: "ultimate-coffee-duo", title: "Ultimate Coffee Duo" })).toBe(true);
    // regular products should not match
    expect(isBundleOrBoxSet({ source: "c4coffee.co", handle: "krank-blend", title: "Krank" })).toBe(false);
    expect(isBundleOrBoxSet({ source: "atomiccoffee.co.nz", handle: "veloce", title: "Veloce" })).toBe(false);
  });

  it("identifies subscriptions for hiding", () => {
    expect(isSubscription({ title: "Weekly Coffee Subscription" })).toBe(true);
    expect(isSubscription({ handle: "coffee-subscription" })).toBe(true);
    expect(isSubscription({ title: "Weekly Coffee", tags: "subscription" })).toBe(true);
    expect(isSubscription({ title: "Weekly Coffee" })).toBe(false);
  });

  it("identifies Ozone's cold brew concentrate for hiding", () => {
    expect(isOzoneConcentrate({ source: "ozonecoffee.co.nz", handle: "cold-brew-concentrate" })).toBe(true);
    expect(isOzoneConcentrate({ source: "rocketcoffee.co.nz", handle: "cold-brew-concentrate" })).toBe(false);
    expect(isOzoneConcentrate({ source: "ozonecoffee.co.nz", handle: "single-origin-filter" })).toBe(false);
  });

  it("filters and sorts items by active category and query", () => {
    const items = [
      { title: "Zulu Espresso", category: "espresso roast", source: "rocketcoffee.co.nz", varietal: "castillo" },
      { title: "Alpha Filter", category: "filter roast", source: "atomiccoffee.co.nz", varietal: "caturra" },
      { title: "Omega Omni", category: "omni roast", source: "c4coffee.co", varietal: "bourbon" },
      { title: "Other Item", category: "other", source: "atomiccoffee.co.nz", varietal: "castillo" },
    ];

    const filterRows = filterAndSortItems(items, "filter roast", "alpha");
    expect(filterRows).toHaveLength(1);
    expect(filterRows[0].title).toBe("Alpha Filter");

    const omniRows = filterAndSortItems(items, "omni roast", "omega");
    expect(omniRows).toHaveLength(1);
    expect(omniRows[0].title).toBe("Omega Omni");
  });

  it("sorts by newest, oldest, and price", () => {
    const items = [
      { title: "Older Cheap", updated_at: "2026-08-01", price_min_nzd: 15 },
      { title: "Newer Expensive", updated_at: "2026-08-17", price_min_nzd: 30 },
    ];

    expect(filterAndSortItems(items, "all", "", "all", "all", "all", "all", "all", "all", "all", "newest")[0].title)
      .toBe("Newer Expensive");
    expect(filterAndSortItems(items, "all", "", "all", "all", "all", "all", "all", "all", "all", "price-low")[0].title)
      .toBe("Older Cheap");
    expect(filterAndSortItems(items, "all", "", "all", "all", "all", "all", "all", "all", "all", "price-high")[0].title)
      .toBe("Newer Expensive");
  });

  it("sorts alphabetically in both directions", () => {
    const items = [{ title: "Alpha" }, { title: "Zulu" }];

    expect(filterAndSortItems(items, "all", "", "all", "all", "all", "all", "all", "all", "all", "title").map((item) => item.title))
      .toEqual(["Alpha", "Zulu"]);
    expect(filterAndSortItems(items, "all", "", "all", "all", "all", "all", "all", "all", "all", "title-desc").map((item) => item.title))
      .toEqual(["Zulu", "Alpha"]);
  });

  it("filters items by store and varietal", () => {
    const items = [
      { title: "Zulu Espresso", category: "espresso roast", source: "rocketcoffee.co.nz", varietal: "castillo" },
      { title: "Alpha Filter", category: "filter roast", source: "atomiccoffee.co.nz", varietal: "caturra,catuai" },
    ];

    const rows = filterAndSortItems(items, "all", "", "atomiccoffee.co.nz", "catuai");
    expect(rows.map((item) => item.title)).toEqual(["Alpha Filter"]);
  });

  it("filters items by origin, producer, process, and decaf", () => {
    const items = [
      {
        title: "Washed Colombia",
        category: "filter roast",
        source: "rocketcoffee.co.nz",
        origin_country: "colombia",
        producer: "Farm A",
        process: "washed",
        decaf: false,
      },
      {
        title: "Natural Brazil Decaf",
        category: "filter roast",
        source: "atomiccoffee.co.nz",
        origin_country: "brazil",
        producer: "Farm B",
        process: "natural",
        decaf: true,
      },
    ];

    const rows = filterAndSortItems(items, "all", "", "all", "all", "brazil", "farm b", "natural", "true");
    expect(rows.map((item) => item.title)).toEqual(["Natural Brazil Decaf"]);
  });

  it("filters blends separately from roast categories", () => {
    const items = [
      { title: "House Blend", category: "espresso roast" },
      { title: "Single Origin", category: "espresso roast" },
    ];

    expect(filterAndSortItems(items, "espresso roast", "", "all", "all", "all", "all", "all", "all", "true"))
      .toEqual([items[0]]);
    expect(filterAndSortItems(items, "espresso roast", "", "all", "all", "all", "all", "all", "all", "false"))
      .toEqual([items[1]]);
  });

  it("derives process and decaf values when metadata is absent", () => {
    const item = { title: "Arturo Arango - Colombia [natural] decaff" };
    expect(metadataValue(item, "origin_country")).toBe("colombia");
    expect(metadataValue(item, "producer")).toBe("arturo arango");
    expect(metadataValue(item, "process")).toBe("natural");
    expect(isDecaf(item)).toBe(true);
  });
});
