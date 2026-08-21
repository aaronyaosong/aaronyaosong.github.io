from __future__ import annotations

import pytest

from nz_coffee_tracker.categorization import (
    ESPRESSO_ROAST,
    FILTER_ROAST,
    OMNI_ROAST,
    OTHER_CATEGORY,
    category_values,
    description_text,
    infer_flavour_notes,
    infer_origin_country,
    infer_process,
    infer_producer,
    infer_roast_category,
    infer_varietal,
)


@pytest.mark.unit
def test_infer_roast_category_filter_only() -> None:
    # Filter keyword in title should map to filter roast category when no tags present.
    product = {
        "title": "Colombia Single Origin Filter Roast",
        "variants": [{"title": "250g"}],
    }
    assert infer_roast_category(product) == FILTER_ROAST


@pytest.mark.unit
def test_infer_roast_category_espresso_only() -> None:
    # Espresso keyword in tags should still be discovered.
    product = {
        "title": "House Blend",
        "tags": "espresso,blend",
        "variants": [{"title": "1kg"}],
    }
    assert infer_roast_category(product) == ESPRESSO_ROAST


@pytest.mark.unit
def test_infer_roast_category_both_is_omni() -> None:
    # Dual-use roast descriptions should carry omni roast.
    product = {
        "title": "Omni Roast",
        "body_html": "Works as filter and espresso.",
        "variants": [{"title": "200g"}],
    }
    assert infer_roast_category(product) == OMNI_ROAST


@pytest.mark.unit
def test_infer_roast_category_other() -> None:
    # Non-coffee merch should not be tagged as a roast category.
    product = {
        "title": "Tea Towel",
        "tags": "merch,home",
        "variants": [{"title": "Standard"}],
    }
    assert infer_roast_category(product) == OTHER_CATEGORY


@pytest.mark.unit
def test_infer_roast_category_ignores_grind_options_and_variants() -> None:
    # An espresso blend that offers both Filter and Espresso grind options should remain Espresso Roast.
    product = {
        "title": "Supreme House Blend",
        "tags": ["blend"],
        "options": [
            {"name": "Grind", "values": ["Whole Bean", "Filter", "Espresso", "Plunger"]},
            {"name": "Size", "values": ["250g", "1kg"]},
        ],
        "variants": [
            {"title": "250g / Filter"},
            {"title": "250g / Espresso"},
            {"title": "1kg / Filter"},
        ],
    }
    assert infer_roast_category(product) == ESPRESSO_ROAST


@pytest.mark.unit
def test_infer_roast_category_checks_tags_first() -> None:
    # When explicit tags are present, they take priority
    assert infer_roast_category({"title": "Something", "tags": ["extraction-omni"]}) == OMNI_ROAST
    assert infer_roast_category({"title": "Something", "tags": ["extraction-filter"]}) == FILTER_ROAST
    assert infer_roast_category({"title": "Something", "tags": ["extraction-espresso"]}) == ESPRESSO_ROAST
    assert infer_roast_category({"title": "House Blend", "tags": ["Filter Roast"]}) == FILTER_ROAST


@pytest.mark.unit
def test_infer_roast_category_supports_roaster_tags() -> None:
    # Ozone tag style
    assert infer_roast_category({"title": "Popayan", "tags": ["brew method:Filter", "SINGLE ORIGIN"]}) == FILTER_ROAST
    assert infer_roast_category({"title": "Our House", "tags": ["brew method:Espresso", "blends"]}) == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Decaf", "tags": ["brew method:Espresso", "brew method:Filter"]}) == OMNI_ROAST

    # C4 tag style
    assert infer_roast_category({"title": "Santa Monica", "tags": ["extraction-filter", "micro-lot"]}) == FILTER_ROAST
    assert infer_roast_category({"title": "Stout Blend", "tags": ["extraction-espresso", "coffee-blend"]}) == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Huila Regional", "tags": ["extraction-omni", "single-origin"]}) == OMNI_ROAST


@pytest.mark.unit
def test_infer_roast_category_supports_collection_handles() -> None:
    # Subcollection context should inform roast category when tags are not explicit
    assert infer_roast_category({"title": "Narino"}, collection_handle="single-origins") == FILTER_ROAST
    assert infer_roast_category({"title": "Seasonal Blend"}, collection_handle="house-blends") == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Tropical Rush"}, collection_handle="specialty-coffee-beans-nz") == FILTER_ROAST
    assert infer_roast_category({"title": "Tropical Rush"}, collection_handle="espresso-offerings-1") == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Koke Shalaye"}, collection_handle="filter-extraction") == FILTER_ROAST


@pytest.mark.unit
def test_infer_roast_category_recommended_brewing_in_description() -> None:
    # Atomic Decaf style: recommended use with espresso and filter
    atomic_decaf = {
        "title": "Decaf",
        "body_html": "<p>Characteristics: body silky. Recommended use Espresso, stovetop, plunger, Aeropress, filter</p>",
    }
    assert infer_roast_category(atomic_decaf) == OMNI_ROAST

    # C4 suitability style
    c4_omni = {
        "title": "Terra Nova",
        "body_html": "<p>Roast Level Medium Sutiable For Espresso, Plunger & Filter</p>",
    }
    assert infer_roast_category(c4_omni) == OMNI_ROAST

    # Slow roasted for espresso style: Raspberry Kiss is explicitly labeled as espresso roast only
    slow_espresso = {
        "title": "Raspberry Kiss | Ethiopia",
        "tags": ["espresso", "filter coffee"],
        "body_html": "<p>roasted for espresso, and brought to us by Cofinet. Part of Espresso Program Vol. 1 — single origins roasted for espresso.</p>",
    }
    assert infer_roast_category(slow_espresso, collection_handle="espresso-coffee") == ESPRESSO_ROAST
    assert infer_roast_category(slow_espresso, source="slowcoffee.co.nz") == ESPRESSO_ROAST
    assert infer_roast_category({"title": "Raspberry Kiss | Ethiopia", "tags": ["filter coffee", "espresso"]}) == ESPRESSO_ROAST


@pytest.mark.unit
def test_infer_roast_category_non_coffee_is_other() -> None:
    assert infer_roast_category({"title": "Hario V60 Filter Papers 100pk", "product_type": "Brew Gear"}) == OTHER_CATEGORY
    assert infer_roast_category({"title": "Gift Card", "product_type": "Gift Card"}) == OTHER_CATEGORY
    assert infer_roast_category({"title": "C4 Black Group Filter Brush", "product_type": "Espresso Equipment"}) == OTHER_CATEGORY


@pytest.mark.unit
def test_category_values_split_and_trim() -> None:
    assert category_values("filter roast, espresso roast") == {"filter roast", "espresso roast"}


@pytest.mark.unit
def test_infer_varietal_detects_multiple_varieties() -> None:
    product = {"title": "Don Claudio Project - Caturra - Catuai - Obata"}
    assert infer_varietal(product) == "Caturra, Catuai, Obata"


@pytest.mark.unit
def test_infer_varietal_unknown_when_not_present() -> None:
    assert infer_varietal({"title": "House Espresso Blend"}) == "unknown"


@pytest.mark.unit
def test_extracts_metadata_and_flavour_notes_from_description() -> None:
    product = {
        "title": "Elena Coffee",
        "body_html": "<p>Origin: Colombia</p><p>Producer: Elena Farm</p><p>Process: washed</p><p>Flavour notes: plum, cocoa and caramel</p>",
    }
    assert description_text(product) == "Origin: Colombia\n\nProducer: Elena Farm\n\nProcess: washed\n\nFlavour notes: plum, cocoa and caramel"
    assert infer_origin_country(product) == "Colombia"
    assert infer_producer(product) == "Elena Farm"
    assert infer_process(product) == "Washed"
    assert infer_flavour_notes(product) == "Plum, Cocoa, Caramel"


@pytest.mark.unit
def test_nlp_extracts_flavour_notes_without_explicit_label() -> None:
    # Rocket natural language style: 'with flavours of raspberry, passionfruit & turkish delight'
    rocket_prod = {
        "body_html": "<p>Arturo's natural Castillo is sweet & fruity with favours of raspberry, passionfruit & turkish delight. Roasted in H-town 17 AUG 2026</p>"
    }
    assert infer_flavour_notes(rocket_prod, use_llm=False) == "Raspberry, Passionfruit, Turkish Delight"

    # Slow PO 'In the cup:' style
    slow_prod = {
        "body_html": "<p>In the cup: lemonade ice block, gumball, blossom and creamy soda. It tastes like summer.</p>"
    }
    assert infer_flavour_notes(slow_prod, use_llm=False) == "Lemonade Ice Block, Gumball, Blossom, Creamy Soda"

    # Lexicon fallback style
    lexicon_prod = {
        "body_html": "<p>A bright washed coffee featuring stone fruit sweetness, rich chocolate and sweet apricot.</p>"
    }
    assert "Stone Fruit" in infer_flavour_notes(lexicon_prod, use_llm=False)
    assert "Chocolate" in infer_flavour_notes(lexicon_prod, use_llm=False)


@pytest.mark.unit
def test_extracts_co_ferment_from_blend_process_method() -> None:
    product = {
        "title": "Tropical Rush - Fruity Blend (Filter)",
        "body_html": "<p>Flavour: Pineapple, Mixed Berries</p><p>Process Method: Natural + Pineapple Honey Co-Fermentation</p><p>Varietal: Heirloom + Castillo</p>",
    }
    proc = infer_process(product)
    assert "Co-Ferment" in proc
    assert "Natural" in proc


@pytest.mark.unit
def test_extracts_laurina_varietal_from_description_block() -> None:
    product = {
        "title": "Lot 002 - Anaerobic Washed",
        "body_html": "<p>COUNTRY - Aotearoa NZ FARM - Pekerau Hills REGION - Kaitaia ALTITUDE - 160 M.A.S.L VARIETAL - Laurina FERMENTATION - Anaerobic PROCESSING METHOD - Washed</p>",
    }
    assert infer_varietal(product) == "Laurina"


@pytest.mark.unit
def test_rose_tea_honey_co_ferment_is_single_process() -> None:
    product = {
        "title": "Jairo Arcila - Rose Tea Honey Co-Ferment",
        "body_html": "<p>PROCESSING METHOD - Rose Tea Honey Co-Ferment VARIETAL - Pink Bourbon</p>",
    }
    assert infer_process(product) == "Co-Ferment"
    assert infer_varietal(product) == "Pink Bourbon"


@pytest.mark.unit
def test_infer_flavour_notes_c4_brazil_carnaval() -> None:
    brazil_product = {
        "title": "Brazil Carnaval",
        "body_html": "COFFEE\nCARNAVAL\nREGIONAL BRAZIL BLEND\nNotes of\nDark Chocolate, Burnt Caramel &\nSmoked Cedar\nWHOLE BEANS",
    }
    assert infer_flavour_notes(brazil_product, use_llm=False) == "Dark Chocolate, Burnt Caramel, Smoked Cedar"


@pytest.mark.unit
def test_infer_flavour_notes_c4_kenya_kainamu() -> None:
    # Kainamui description mentions cherry picking in an agricultural context, with tasting notes on the info card
    kenya_product = {
        "title": "Kenya Kainamu Factory PB",
        "body_html": (
            "<p>Every cherry is handpicked and delivered to the factory's wet mill, where the magic begins.</p>"
            "<p>KAINAMU : PB\nKENYA\nFeatured Origin\nSweet / Nutty\n\n"
            "Tasting Notes. Shortbread, Burnt Orange & Caramel\nOrigin. Mt Kenya, Kenya\nProcess. Washed\nRoast Profile Medium / Espresso</p>"
        ),
    }
    assert infer_flavour_notes(kenya_product, use_llm=False) == "Shortbread, Burnt Orange, Caramel"


@pytest.mark.unit
def test_infer_flavour_notes_c4_kenya_tatu() -> None:
    tatu_product = {
        "title": "Kenya: Tatu Natural",
        "body_html": "KIAMBU COUNTY\nTATU ESTATE\nSL 28,SL 34 - NATURAL\nNotes of\nChocolate, Dried Berries, with a\nWine like finish\nWHOLE BEANS",
    }
    assert infer_flavour_notes(tatu_product, use_llm=False) == "Chocolate, Dried Berries, With A Wine Like Finish"


@pytest.mark.unit
def test_infer_flavour_notes_wolf_local_blend() -> None:
    wolf_product = {
        "title": "Local Blend",
        "body_html": (
            "<p><strong>Origin:</strong> Colombia, Brazil<br />\n"
            "<strong>Varietal:</strong> Mixed<br />\n"
            "<strong>Process:</strong> Washed<br />\n"
            "<strong>Altitude:</strong> 1800-2500 MASL<br />\n"
            "<strong>Tasting Notes:</strong> Dark Choc, Raisin, Pecan, Roast Almond</p>\n\n"
            "<p><strong>Colombia Popayan Reserve</strong></p><p>Popayan Reserve is located in the region of Cauca at 1700 MASL.</p>"
        ),
    }
    assert infer_flavour_notes(wolf_product, use_llm=False) == "Dark Choc, Raisin, Pecan, Roast Almond"


@pytest.mark.unit
def test_infer_flavour_notes_eternal_peace_town() -> None:
    peace_product = {
        "title": "🆕 Ethiopia Peace Town 74158 72hr Dark Room Natural (Filter)",
        "body_html": (
            "<p>Boysenberry Yogurt, Pink Pomelo, Golden Kiwifruit</p>\n"
            "<ul>\n"
            "<li>Producer: Uncle Adumu, Peach Town</li>\n"
            "<li>Process Method: 72hr Dark Room Anaerobic Natural</li>\n"
            "<li>Varietal: 74158</li>\n"
            "</ul>"
        ),
    }
    assert infer_flavour_notes(peace_product, use_llm=False) == "Boysenberry Yogurt, Pink Pomelo, Golden Kiwifruit"


@pytest.mark.unit
def test_infer_flavour_notes_eternal_peachylicious() -> None:
    peachy_product = {
        "title": "Peachylicious - Fruity Blend (Filter)",
        "body_html": (
            "<p><span>Flavour: <meta charset=\"utf-8\"></span>"
            "<span class=\"a_GcMg\">Peach Jam, </span>"
            "<span class=\"a_GcMg\">Mixed Berries, </span>"
            "<span class=\"a_GcMg\">Oolong Tea</span>"
        ),
    }
    assert infer_flavour_notes(peachy_product, use_llm=False) == "Peach Jam, Mixed Berries, Oolong Tea"


@pytest.mark.unit
def test_infer_flavour_notes_ozone_cascadia_decaf() -> None:
    cascadia_product = {
        "title": "CASCADIA ORGANIC DECAF",
        "body_html": (
            "<p><strong>Tasting Notes</strong></p>\n"
            "<p>Expect aromas of dried fig and quince, with jammy apple, sultana and caramel sweetness then a soft milk chocolate finish.<br></p>\n"
            "<p><strong>Farm Info</strong></p>"
        ),
    }
    assert infer_flavour_notes(cascadia_product, use_llm=False) == "Milk Chocolate, Jammy Apple, Dried Fig, Caramel, Sultana, Quince"


@pytest.mark.unit
def test_infer_flavour_notes_atomic_supremo() -> None:
    supremo_product = {
        "title": "Supremo",
        "body_html": (
            "<div class=\"collapsible-content\">\n"
            "<p><strong>Origins<br/></strong>Peru, Rodríguez de Mendoza<br/>Guatemala, Huehuetenango<br/>"
            "<strong>Body</strong> Smooth &amp; creamy<br/>"
            "<strong>Acidity </strong>Medium<br/>"
            "<strong>Finish </strong>Sweet<br/>"
            "<strong>Flavour notes </strong>Cacao nibs, marshmallow, clove<br/>"
            "<strong>Recommended use </strong>Espresso, stovetop, plunger</p>\n"
            "</div>"
        ),
    }
    assert infer_flavour_notes(supremo_product, use_llm=False) == "Cacao Nibs, Marshmallow, Clove"


@pytest.mark.unit
def test_infer_flavour_notes_ozone_cachoeira_subheading() -> None:
    ozone_product = {
        "title": "Cachoeira da Grama, Yellow Bourbon",
        "body_html": (
            "<p><strong>Origin:</strong> Brazil</p>\n\n"
            "<p><strong>Tasting notes:</strong> Roasted hazelnut, toffee, dark chocolate</p>"
        ),
    }
    assert infer_flavour_notes(ozone_product, use_llm=False) == "Roasted Hazelnut, Toffee, Dark Chocolate"


@pytest.mark.unit
def test_infer_flavour_notes_embassy_beyond() -> None:
    beyond_product = {
        "title": "Beyond Blend",
        "body_html": (
            "<p>Beyond is a Seasonal Espresso Blend.<br><br>"
            "Flavour Profile - Dark Fruits, Floral, Brown Sugar<br><br>"
            "Score - 86.25</p>"
        ),
    }
    assert infer_flavour_notes(beyond_product, use_llm=False) == "Dark Fruits, Floral, Brown Sugar"


@pytest.mark.unit
def test_infer_flavour_notes_embassy_blend_pipe() -> None:
    embassy_product = {
        "title": "Embassy Blend",
        "body_html": "EMBASSY\nBLEND\nAPPLE CRUMBLE | VANILLA CUSTARD | DATES",
    }
    assert infer_flavour_notes(embassy_product, use_llm=False) == "Apple Crumble, Vanilla Custard, Dates"


@pytest.mark.unit
def test_infer_flavour_notes_c4_headset_card() -> None:
    headset_product = {
        "title": "Headset Fair Trade Organic",
        "body_html": (
            "HEADSET\nYear Round Blend\nCocoa / Sweet\n"
            "Tasting Notes.\nMilk Chocolate, Nougat & Vanilla Bean.\n"
            "Origin.\nMexico, Colombia, Ethiopia, Peru\nProcess.\nWashed"
        ),
    }
    assert infer_flavour_notes(headset_product, use_llm=False) == "Milk Chocolate, Nougat, Vanilla Bean"


@pytest.mark.unit
def test_infer_flavour_notes_ozone_half_caff_subheading() -> None:
    half_caff_product = {
        "title": "Half Caff: Blend",
        "body_html": (
            "<p><strong>Origin:</strong> Colombia, Guatemala</p>\n\n"
            "<p><strong>Tasting notes:</strong> Orange, honeycomb, milk chocolate</p>\n\n"
            "<p>All the flavour – half the caffeine.</p>"
        ),
    }
    assert infer_flavour_notes(half_caff_product, use_llm=False) == "Orange, Honeycomb, Milk Chocolate"


@pytest.mark.unit
def test_infer_flavour_notes_ozone_inglaterra_subheading() -> None:
    inglaterra_product = {
        "title": "Inglaterra",
        "body_html": (
            "<p><strong>Origin:</strong> Brazil</p>\n\n"
            "<p><strong>Tasting notes:</strong> Sugared almond, milk chocolate, raisin</p>\n\n"
            "<p>This unique terroir contributes to the coffee's distinct flavour profile: clean, sweet, and full of character.</p>"
        ),
    }
    assert infer_flavour_notes(inglaterra_product, use_llm=False) == "Sugared Almond, Milk Chocolate, Raisin"


@pytest.mark.unit
def test_infer_varietal_ozone_las_alasitas() -> None:
    las_alasitas_product = {
        "title": "Las Alasitas",
        "body_html": (
            "<p>Las Alasitas is now home to Agricafe's variety nursery, where agronomists cultivate seedlings of prized varietals like Geisha, Java, and San Bernardo to share with local farmers.</p>\n\n"
            "<p>The Yellow Caturra variety – a compact, golden-fruited mutation of Bourbon first selected in Brazil – tends toward tropical fruit sweetness at altitude.</p>\n\n"
            "<h3>Traceability</h3>\n"
            "<ul>\n"
            "<li>Country: Bolivia</li>\n"
            "<li>Region: Yungas</li>\n"
            "<li>Province: Caranavi</li>\n"
            "<li>Colony: Bolinda</li>\n"
            "<li>Farm: Las Alasitas</li>\n"
            "<li>Producers: Fincas Los Rodriguez</li>\n"
            "<li>Processing Method: Washed</li>\n"
            "<li>Varietal: Yellow Caturra</li>\n"
            "</ul>"
        ),
    }
    assert infer_varietal(las_alasitas_product, use_llm=False) == "Yellow Caturra"


@pytest.mark.unit
def test_infer_slow_coffee_badges_and_specs() -> None:
    custard = {
        "title": "Custard Slice | Brazil",
        "body_html": "<p><strong>Tasting notes:</strong> Buttery, Marzipan, Vanilla Custard, Cocoa</p><p>Variety Arara & Catuaí 62</p>",
    }
    assert infer_flavour_notes(custard, use_llm=False) == "Buttery, Marzipan, Vanilla Custard, Cocoa"

    studio = {
        "title": "Studio Blend",
        "body_html": "<p><strong>Tasting notes:</strong> Milk Chocolate, Hazelnut, Toffee, Brown Sugar</p><p>Variety Mixed (Acaiá, Castillo)</p>",
    }
    assert infer_flavour_notes(studio, use_llm=False) == "Milk Chocolate, Hazelnut, Toffee, Brown Sugar"
    assert infer_varietal(studio, use_llm=False) == "Acaiá, Castillo"

    pear = {
        "title": "Pear Pressure | Kenya",
        "body_html": "<p><strong>Tasting notes:</strong> Cola, Poached Pear, Plum Jam, Rooibos Tea</p><p>Variety SL28, SL34, Ruiru 11, Batian</p>",
    }
    assert infer_flavour_notes(pear, use_llm=False) == "Cola, Poached Pear, Plum Jam, Rooibos Tea"
    assert infer_varietal(pear, use_llm=False) == "SL28, SL34, Ruiru 11, Batian"


@pytest.mark.unit
def test_infer_embassy_jairo_arcila_cupping_notes() -> None:
    embassy_jairo = {
        "title": "Jairo Arcila",
        "body_html": (
            "<p>Cupping Notes –<br>"
            "Mandarin, Caramelised Apple, Apricot<br>"
            "Disclaimer: Cupping notes are a guide based on what we tasted whilst cupping this coffee.</p>"
        ),
    }
    assert infer_flavour_notes(embassy_jairo, use_llm=False) == "Mandarin, Caramelised Apple, Apricot"


@pytest.mark.unit
def test_infer_grey_roasting_cupping_notes() -> None:
    cata_lab = {
        "title": "Cata Lab LOT 2, Colombia - Washed, Mixed Varietal",
        "body_html": "Cupping Notes: Floral, Bergamot, Citrus, Black Tea\nVarietal: Mixed\nProcess: Advanced Washed",
    }
    assert infer_flavour_notes(cata_lab, use_llm=False) == "Floral, Bergamot, Citrus, Black Tea"

    don_claudio = {
        "title": "Don Claudio, Costa Rica - Washed",
        "body_html": "Cupping\xa0Notes: Tangerine, Plum, Black Tea\nVarietal: Caturra, Catuai, Obata\nProcess: Washed",
    }
    assert infer_flavour_notes(don_claudio, use_llm=False) == "Tangerine, Plum, Black Tea"


@pytest.mark.unit
def test_infer_vanguard_details() -> None:
    popayan_decaf = {
        "title": "Colombia Popayan Reserve Decaf",
        "body_html": "PROCESSING METHOD - Washed; Sugarcane EA Decaf\nTASTING NOTES - Citrus, Toffee, Chocolate Brownie",
    }
    assert infer_process(popayan_decaf) == "Washed, Sugar Cane Decaf"
    assert infer_flavour_notes(popayan_decaf, use_llm=False) == "Citrus, Toffee, Chocolate Brownie"

    sitio_colinas = {
        "title": "Brazil Sitio Colinas Yellow Arara Natural",
        "body_html": "TASTING NOTES - Yellow fruits, Macadamia, Milk Chocolate, Caramel",
    }
    assert infer_flavour_notes(sitio_colinas, use_llm=False) == "Yellow Fruits, Macadamia, Milk Chocolate, Caramel"


@pytest.mark.unit
def test_infer_eternal_split_profile_and_toh() -> None:
    peachylicious = {
        "title": "Peachylicious - Fruity Blend (Espresso)",
        "body_html": "Flavour:\n\n- Black:\xa0 Peach Milk Candy, Mixed Berries\n\n- Milk: Citrus, Peach, Mixed Berries\n\nOrigin: Ethiopia + Colombia",
    }
    assert infer_flavour_notes(peachylicious, use_llm=False) == "Black: Peach Milk Candy, Mixed Berries | Milk: Citrus, Peach, Mixed Berries"

    toh = {
        "title": "Ethiopia TOH#1 Natural Lulo Coffee",
        "body_html": "Flavour: Mango, Orah Mandarin, Jujube Date\n\nProducer: Lulo Coffee, Robel Kidane\n\nProcess Method: Natural",
    }
    assert infer_flavour_notes(toh, use_llm=False) == "Mango, Orah Mandarin, Jujube Date"

    peace_town = {
        "title": "🆕 Ethiopia Peace Town 74158 72hr Dark Room Natural (Filter)",
        "body_html": "Boysenberry Yogurt, Pink Pomelo, Golden Kiwifruit\n\nProducer: Uncle Adumu, Peach Town\n\nR egion: Amfo, Hambela",
    }
    assert infer_flavour_notes(peace_town, use_llm=False) == "Boysenberry Yogurt, Pink Pomelo, Golden Kiwifruit"


@pytest.mark.unit
def test_infer_atomic_and_rocket_rich_notes() -> None:
    atomic_yolan = {
        "title": "Indonesia Yolan Tirta | Filter Roast",
        "body_html": "Tasting notes: Red Pear, Hazelnut, Hot Chocolate\nRecomending use: Filter",
    }
    assert infer_flavour_notes(atomic_yolan, use_llm=False) == "Red Pear, Hazelnut, Hot Chocolate"

    rocket_diofanor = {
        "title": "Diofanor Ruiz - Castillo [washed] filter roast",
        "body_html": "This washed Castillo is sweet with flavours of strawberry, raspberry & panela.\n\nRoasted in H-town 17 AUG 2026",
    }
    assert infer_flavour_notes(rocket_diofanor, use_llm=False) == "Strawberry, Raspberry, Panela"


@pytest.mark.unit
def test_infer_blackberry_sorbet_browser_embassy_half_caff() -> None:
    # 1. C4 Blackberry Sorbet
    bb_sorbet = {
        "title": "Blackberry Sorbet",
        "body_html": (
            "Vibrant flavours of Blackberries, Blueberries, Boysenberry Ice-cream, and Elderflower.\n\n"
            "A blend of 45% Blackberry and Wine Yeast Castillo from Santà Monica Colombia,\n"
            "35% Washed mix from the COMSA Co-Operative in Honduras,\n"
            "and 20% of our Colombian Aponte Honey."
        ),
    }
    assert infer_process(bb_sorbet) == "Wine Yeast, Honey, Washed"
    assert infer_flavour_notes(bb_sorbet, use_llm=False) == "Blackberries, Blueberries, Boysenberry Ice-Cream, And Elderflower"

    # 2. C4 The Browser (manual exclusion)
    browser = {
        "title": "The Browser",
        "handle": "the-browser",
        "body_html": "The coffee of readers, browsers, gift-givers.\n\nA special collaboration between C4 Coffee Co. and Scorpio Books.",
    }
    assert infer_flavour_notes(browser, use_llm=False) == "unknown"

    # 3. Coffee Embassy Blends (Washed + Natural components)
    beyond = {
        "title": "Beyond Blend",
        "body_html": "Beyond is currently made up of two Ethiopian coffees, Konga (washed) and Hatiso (natural).\n\nFlavour Profile - Dark Fruits, Floral, Brown Sugar",
    }
    assert infer_process(beyond) == "Washed, Natural"

    ranger = {
        "title": "Ranger Blend",
        "body_html": "Brazil: Samba Reserve ... Process: Natural ... Ethiopia: Limu Kossa ... Process: Washed",
    }
    assert infer_process(ranger) == "Washed, Natural"

    # 4. Ozone Half Caff (Washed Sugar Cane Decaf in farm info)
    half_caff = {
        "title": "Half Caff: Blend",
        "body_html": (
            "Origin: Colombia, Guatemala\n\nTasting notes: Orange, honeycomb, milk chocolate\n\n"
            "FARM INFO\n\nProcess/Variety\n\nWashed Sugar Cane Decaffeinated / Caturra, Colombia\n\nWashed / Mixed varietals"
        ),
    }
    assert infer_process(half_caff) == "Washed, Sugar Cane Decaf"







