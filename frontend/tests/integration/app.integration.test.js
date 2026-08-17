import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApp } from "../../app.js";


function buildDom() {
  document.body.innerHTML = `
    <div id="stats"></div>
    <p id="last-updated"></p>
    <input id="searchInput" />
    <select id="sourceFilter"><option value="all">All stores</option></select>
    <select id="decafFilter"><option value="all">All coffees</option><option value="true">Decaf</option></select>
    <select id="blendFilter"><option value="all">All coffees</option><option value="true">Blends only</option><option value="false">No blends</option></select>
    <div id="categoryFilters">
      <select id="categoryFilter"><option value="all">All roast types</option></select>
    </div>
    <p id="resultCount"></p>
    <div id="cards"></div>
    <p id="errorMessage" hidden></p>
  `;
}


describe("app integration", () => {
  beforeEach(() => {
    buildDom();
  });

  it("loads payload, renders cards, and applies search filtering", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        generated_at: "2026-08-17T00:00:00+00:00",
        items: [
          {
            source: "rocketcoffee.co.nz",
            title: "Bravo Blend Espresso",
            category: "espresso roast",
            varietal: "castillo",
            origin_country: "colombia",
            producer: "bravo farm",
            process: "washed",
            decaf: false,
            size_prices: [{ size_grams: 250, price_nzd: 20 }],
            price_min_nzd: 20,
            price_max_nzd: 20,
            product_url: "https://example.com/b",
          },
          {
            source: "atomiccoffee.co.nz",
            title: "Alpha Filter",
            category: "filter roast",
            varietal: "caturra",
            origin_country: "brazil",
            producer: "alpha farm",
            process: "natural",
            decaf: true,
            size_prices: [{ size_grams: 250, price_nzd: 25 }, { size_grams: 1000, price_nzd: 30 }],
            price_min_nzd: 25,
            price_max_nzd: 30,
            product_url: "https://example.com/a",
          },
          {
            source: "rocketcoffee.co.nz",
            title: "Bravo Subscription",
            handle: "bravo-subscription",
            category: "espresso roast",
            price_min_nzd: 20,
            price_max_nzd: 20,
            product_url: "https://example.com/subscription",
          },
        ],
      }),
    });

    const app = createApp({ documentRef: document, fetchImpl: fetchMock, dataPath: "./data/latest.json" });
    await app.loadData();

    expect(document.getElementById("resultCount").textContent).toBe("2 results");
    expect(document.querySelectorAll(".card")).toHaveLength(2);
    expect(document.querySelector(".size-prices").textContent).toContain("250g");
    expect(document.querySelector(".size-prices").textContent).toContain("NZD $0.100/g");

    const categoryFilter = document.getElementById("categoryFilter");
    expect([...categoryFilter.options].map((option) => option.value)).toEqual([
      "all",
      "espresso roast",
      "filter roast",
    ]);
    const blendFilter = document.getElementById("blendFilter");
    blendFilter.value = "true";
    blendFilter.dispatchEvent(new Event("change"));
    expect(document.getElementById("resultCount").textContent).toBe("1 result");
    blendFilter.value = "all";
    blendFilter.dispatchEvent(new Event("change"));
    categoryFilter.value = "espresso roast";
    categoryFilter.dispatchEvent(new Event("change"));
    expect(document.getElementById("resultCount").textContent).toBe("1 result");
    categoryFilter.value = "all";
    categoryFilter.dispatchEvent(new Event("change"));

    const searchInput = document.getElementById("searchInput");
    searchInput.value = "alpha";
    searchInput.dispatchEvent(new Event("input"));

    expect(document.getElementById("resultCount").textContent).toBe("1 result");
    expect(document.querySelector(".card h3").textContent).toBe("Alpha Filter");

    const sourceFilter = document.getElementById("sourceFilter");
    sourceFilter.value = "atomiccoffee.co.nz";
    sourceFilter.dispatchEvent(new Event("change"));
    expect(document.getElementById("resultCount").textContent).toBe("1 result");

    searchInput.value = "";
    searchInput.dispatchEvent(new Event("input"));
    sourceFilter.value = "all";
    sourceFilter.dispatchEvent(new Event("change"));
    const decafFilter = document.getElementById("decafFilter");
    decafFilter.value = "true";
    decafFilter.dispatchEvent(new Event("change"));
    expect(document.getElementById("resultCount").textContent).toBe("1 result");
  });
});
