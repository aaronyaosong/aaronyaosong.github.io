import { describe, expect, it } from "vitest";

import {
  categories,
  filterCategories,
  filterAndSortItems,
  isDecaf,
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

  it("identifies subscriptions for hiding", () => {
    expect(isSubscription({ title: "Weekly Coffee Subscription" })).toBe(true);
    expect(isSubscription({ handle: "coffee-subscription" })).toBe(true);
    expect(isSubscription({ title: "Weekly Coffee", tags: "subscription" })).toBe(true);
    expect(isSubscription({ title: "Weekly Coffee" })).toBe(false);
  });

  it("filters and sorts items by active category and query", () => {
    const items = [
      { title: "Zulu Espresso", category: "espresso roast", source: "rocketcoffee.co.nz", varietal: "castillo" },
      { title: "Alpha Filter", category: "filter roast", source: "atomiccoffee.co.nz", varietal: "caturra" },
      { title: "Other Item", category: "other", source: "atomiccoffee.co.nz", varietal: "castillo" },
    ];

    const rows = filterAndSortItems(items, "filter roast", "alpha");
    expect(rows).toHaveLength(1);
    expect(rows[0].title).toBe("Alpha Filter");
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
