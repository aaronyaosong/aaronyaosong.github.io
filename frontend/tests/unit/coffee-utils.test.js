import { describe, expect, it } from "vitest";

import { categories, filterAndSortItems, nzPrice, sourceName } from "../../coffee-utils.js";


describe("coffee-utils unit", () => {
  it("maps known sources to display names", () => {
    expect(sourceName("rocketcoffee.co.nz")).toBe("Rocket Coffee");
    expect(sourceName("atomiccoffee.co.nz")).toBe("Atomic Coffee");
  });

  it("formats single and ranged NZD prices", () => {
    expect(nzPrice({ price_min_nzd: 22, price_max_nzd: 22 })).toBe("NZD $22.00");
    expect(nzPrice({ price_min_nzd: 20, price_max_nzd: 35 })).toBe("NZD $20.00 - $35.00");
  });

  it("splits comma-separated categories", () => {
    expect(categories("filter roast,espresso roast")).toEqual(["filter roast", "espresso roast"]);
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

  it("filters items by store and varietal", () => {
    const items = [
      { title: "Zulu Espresso", category: "espresso roast", source: "rocketcoffee.co.nz", varietal: "castillo" },
      { title: "Alpha Filter", category: "filter roast", source: "atomiccoffee.co.nz", varietal: "caturra,catuai" },
    ];

    const rows = filterAndSortItems(items, "all", "", "atomiccoffee.co.nz", "catuai");
    expect(rows.map((item) => item.title)).toEqual(["Alpha Filter"]);
  });
});
