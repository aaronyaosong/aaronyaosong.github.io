import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApp } from "../../app.js";


function buildDom() {
  document.body.innerHTML = `
    <div id="stats"></div>
    <p id="last-updated"></p>
    <input id="searchInput" />
    <div id="categoryFilters">
      <button class="chip active" data-category="all" type="button">All</button>
      <button class="chip" data-category="filter roast" type="button">Filter Roast</button>
      <button class="chip" data-category="espresso roast" type="button">Espresso Roast</button>
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
            title: "Bravo Espresso",
            category: "espresso roast",
            price_min_nzd: 20,
            price_max_nzd: 20,
            product_url: "https://example.com/b",
          },
          {
            source: "atomiccoffee.co.nz",
            title: "Alpha Filter",
            category: "filter roast",
            price_min_nzd: 25,
            price_max_nzd: 30,
            product_url: "https://example.com/a",
          },
        ],
      }),
    });

    const app = createApp({ documentRef: document, fetchImpl: fetchMock, dataPath: "./data/latest.json" });
    await app.loadData();

    expect(document.getElementById("resultCount").textContent).toBe("2 results");
    expect(document.querySelectorAll(".card")).toHaveLength(2);

    const searchInput = document.getElementById("searchInput");
    searchInput.value = "alpha";
    searchInput.dispatchEvent(new Event("input"));

    expect(document.getElementById("resultCount").textContent).toBe("1 result");
    expect(document.querySelector(".card h3").textContent).toBe("Alpha Filter");
  });
});
