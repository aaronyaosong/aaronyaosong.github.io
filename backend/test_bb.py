import sys
sys.path.append('src')
from nz_coffee_tracker.categorization import infer_process
bb_sorbet = {
    "title": "Blackberry Sorbet",
    "body_html": (
        "Vibrant flavours of Blackberries, Blueberries, Boysenberry Ice-cream, and Elderflower.\n\n"
        "A blend of 45% Blackberry and Wine Yeast Castillo from Santà Monica Colombia,\n"
        "35% Washed mix from the COMSA Co-Operative in Honduras,\n"
        "and 20% of our Colombian Aponte Honey."
    ),
}
beyond = {
    "title": "Beyond Blend",
    "body_html": "Beyond is currently made up of two Ethiopian coffees, Konga (washed) and Hatiso (natural).\n\nFlavour Profile - Dark Fruits, Floral, Brown Sugar",
}
ranger = {
    "title": "Ranger Blend",
    "body_html": "Brazil: Samba Reserve ... Process: Natural ... Ethiopia: Limu Kossa ... Process: Washed",
}
half_caff = {
    "title": "Half Caff: Blend",
    "body_html": (
        "Origin: Colombia, Guatemala\n\nTasting notes: Orange, honeycomb, milk chocolate\n\n"
        "FARM INFO\n\nProcess/Variety\n\nWashed Sugar Cane Decaffeinated / Caturra, Colombia\n\nWashed / Mixed varietals"
    ),
}
print("bb_sorbet:", infer_process(bb_sorbet))
print("beyond:", infer_process(beyond))
print("ranger:", infer_process(ranger))
print("half_caff:", infer_process(half_caff))
