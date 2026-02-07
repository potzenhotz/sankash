"""Default category definitions for easy editing."""

from sankash.core.models import Category

# --- Color palette (Kanagawa-inspired) ---
GREEN = "#98bb6c"
BLUE = "#7e9cd8"
FOREST = "#76946a"
SKY = "#7fb4ca"
RED = "#c34043"
PURPLE = "#957fb8"
YELLOW = "#e6c384"
GOLD = "#c0a36e"
LAVENDER = "#938aa9"
TEAL = "#6a9589"
CYAN = "#7aa89f"
BEIGE = "#c8c093"
GRAY = "#727169"

# German default categories with subcategories.
# Parents must appear before their children.
# Subcategories inherit their parent's color.
DEFAULT_CATEGORIES_DE: list[Category] = [
    # Einkommen
    Category(name="Einkommen", color=GREEN),
    Category(name="Gehalt", parent_category="Einkommen", color=GREEN),
    Category(name="Kapitalerträge", parent_category="Einkommen", color=GREEN),
    Category(name="Staatliche Leistungen", parent_category="Einkommen", color=GREEN),
    Category(name="Geschenke erhalten", parent_category="Einkommen", color=GREEN),
    Category(name="Sonstiges Einkommen", parent_category="Einkommen", color=GREEN),
    # Wohnen
    Category(name="Wohnen", color=BLUE),
    Category(name="Miete", parent_category="Wohnen", color=BLUE),
    Category(name="Nebenkosten", parent_category="Wohnen", color=BLUE),
    Category(name="Internet & Telefon", parent_category="Wohnen", color=BLUE),
    Category(name="Hausratversicherung", parent_category="Wohnen", color=BLUE),
    Category(name="Instandhaltung & Reparaturen", parent_category="Wohnen", color=BLUE),
    Category(name="Möbel & Haushalt", parent_category="Wohnen", color=BLUE),
    # Lebensmittel & Getränke
    Category(name="Lebensmittel & Getränke", color=FOREST),
    Category(name="Einkäufe", parent_category="Lebensmittel & Getränke", color=FOREST),
    Category(
        name="Restaurants & Essen gehen", parent_category="Lebensmittel & Getränke", color=FOREST
    ),
    Category(name="Kaffee & Snacks", parent_category="Lebensmittel & Getränke", color=FOREST),
    Category(name="Lieferservice", parent_category="Lebensmittel & Getränke", color=FOREST),
    # Mobilität
    Category(name="Mobilität", color=SKY),
    Category(name="Öffentlicher Nahverkehr", parent_category="Mobilität", color=SKY),
    Category(name="Tanken", parent_category="Mobilität", color=SKY),
    Category(name="Kfz-Versicherung", parent_category="Mobilität", color=SKY),
    Category(name="Kfz-Wartung & Reparaturen", parent_category="Mobilität", color=SKY),
    Category(name="Parken & Maut", parent_category="Mobilität", color=SKY),
    Category(name="Taxi & Fahrservice", parent_category="Mobilität", color=SKY),
    # Gesundheit
    Category(name="Gesundheit", color=RED),
    Category(name="Krankenversicherung", parent_category="Gesundheit", color=RED),
    Category(name="Arzt & Apotheke", parent_category="Gesundheit", color=RED),
    Category(name="Zahnarzt", parent_category="Gesundheit", color=RED),
    Category(name="Fitness & Sport", parent_category="Gesundheit", color=RED),
    # Freizeit & Unterhaltung
    Category(name="Freizeit & Unterhaltung", color=PURPLE),
    Category(name="Abonnements", parent_category="Freizeit & Unterhaltung", color=PURPLE),
    Category(name="Hobbys", parent_category="Freizeit & Unterhaltung", color=PURPLE),
    Category(name="Bücher & Medien", parent_category="Freizeit & Unterhaltung", color=PURPLE),
    Category(
        name="Veranstaltungen & Konzerte", parent_category="Freizeit & Unterhaltung", color=PURPLE
    ),
    Category(name="Bars & Nachtleben", parent_category="Freizeit & Unterhaltung", color=PURPLE),
    # Konsum
    Category(name="Konsum", color=YELLOW),
    Category(name="Kleidung & Schuhe", parent_category="Konsum", color=YELLOW),
    Category(name="Elektronik", parent_category="Konsum", color=YELLOW),
    Category(name="Körperpflege", parent_category="Konsum", color=YELLOW),
    Category(name="Geschenke", parent_category="Konsum", color=YELLOW),
    # Finanzen
    Category(name="Finanzen", color=GOLD),
    Category(name="Sparen & Investitionen", parent_category="Finanzen", color=GOLD),
    Category(name="Kreditrückzahlung", parent_category="Finanzen", color=GOLD),
    Category(name="Bankgebühren", parent_category="Finanzen", color=GOLD),
    Category(name="Steuern", parent_category="Finanzen", color=GOLD),
    # Bildung
    Category(name="Bildung", color=LAVENDER),
    Category(name="Kurse & Weiterbildung", parent_category="Bildung", color=LAVENDER),
    Category(name="Bücher & Materialien", parent_category="Bildung", color=LAVENDER),
    # Reisen
    Category(name="Reisen", color=TEAL),
    Category(name="Flüge & Bahn", parent_category="Reisen", color=TEAL),
    Category(name="Unterkunft", parent_category="Reisen", color=TEAL),
    Category(name="Aktivitäten & Ausflüge", parent_category="Reisen", color=TEAL),
    # Kinder
    Category(name="Kinder", color=CYAN),
    Category(name="Kinderbetreuung", parent_category="Kinder", color=CYAN),
    Category(name="Schule & Bildung", parent_category="Kinder", color=CYAN),
    Category(name="Kleidung & Spielzeug", parent_category="Kinder", color=CYAN),
    # Haustiere
    Category(name="Haustiere", color=BEIGE),
    Category(name="Futter & Zubehör", parent_category="Haustiere", color=BEIGE),
    Category(name="Tierarzt", parent_category="Haustiere", color=BEIGE),
    # Sonstiges
    Category(name="Sonstiges", color=GRAY),
    Category(name="Verschiedenes", parent_category="Sonstiges", color=GRAY),
    Category(name="Bargeldabhebung", parent_category="Sonstiges", color=GRAY),
]
