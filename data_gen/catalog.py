"""Static reference lists used to build fictional stores and products.

Every name here is invented. Nothing refers to a real retailer, brand or person.
"""

from __future__ import annotations

# category -> (margin range, price range, quantity boost, item nouns)
CATEGORIES: dict[str, dict] = {
    "Grocery": {
        "margin": (0.18, 0.32),
        "price": (1.5, 12.0),
        "qty_lambda": 0.9,
        "items": ["Pasta", "Rice", "Cereal", "Olive Oil", "Granola", "Coffee Beans",
                  "Peanut Butter", "Crackers", "Tomato Sauce", "Oat Bars"],
    },
    "Beverages": {
        "margin": (0.25, 0.40),
        "price": (1.0, 9.0),
        "qty_lambda": 0.9,
        "items": ["Sparkling Water", "Cold Brew", "Green Tea", "Orange Juice",
                  "Cola", "Energy Drink", "Lemonade", "Kombucha"],
    },
    "Household": {
        "margin": (0.30, 0.45),
        "price": (2.5, 18.0),
        "qty_lambda": 0.4,
        "items": ["Dish Soap", "Paper Towels", "Laundry Pods", "Trash Bags",
                  "Sponges", "Surface Spray", "Light Bulbs"],
    },
    "Personal Care": {
        "margin": (0.35, 0.55),
        "price": (3.0, 25.0),
        "qty_lambda": 0.3,
        "items": ["Shampoo", "Toothpaste", "Body Wash", "Deodorant",
                  "Hand Cream", "Sunscreen", "Razor Pack"],
    },
    "Electronics": {
        "margin": (0.12, 0.28),
        "price": (15.0, 250.0),
        "qty_lambda": 0.05,
        "items": ["Earbuds", "Phone Charger", "Power Bank", "Bluetooth Speaker",
                  "HDMI Cable", "Smart Plug", "USB Hub"],
    },
    "Apparel": {
        "margin": (0.45, 0.65),
        "price": (8.0, 80.0),
        "qty_lambda": 0.2,
        "items": ["T-Shirt", "Hoodie", "Socks 3-Pack", "Beanie", "Rain Jacket",
                  "Leggings", "Cap"],
    },
    "Home & Garden": {
        "margin": (0.35, 0.50),
        "price": (5.0, 90.0),
        "qty_lambda": 0.15,
        "items": ["Planter", "Candle", "Throw Blanket", "Storage Box",
                  "Garden Gloves", "Picture Frame", "Doormat"],
    },
    "Toys": {
        "margin": (0.30, 0.50),
        "price": (6.0, 60.0),
        "qty_lambda": 0.1,
        "items": ["Puzzle", "Building Blocks", "Plush Bear", "Board Game",
                  "Art Kit", "Toy Car"],
    },
}

CATEGORY_NAMES: list[str] = list(CATEGORIES)

# Basket affinity: products tend to be bought with items from this category.
COMPLEMENTS: dict[str, str] = {
    "Grocery": "Beverages",
    "Beverages": "Grocery",
    "Household": "Personal Care",
    "Personal Care": "Household",
    "Electronics": "Electronics",
    "Apparel": "Apparel",
    "Home & Garden": "Household",
    "Toys": "Grocery",
}

BRANDS: list[str] = ["Alderleaf", "Brightfield", "Cobaltine", "Dunmore", "Everfern",
                     "Foxglen", "Greyharbor", "Hollowell", "Ivymark", "Juniper Row"]

SIZES: list[str] = ["Small", "Regular", "Large", "Value Pack", "Mini"]

# Fictional towns and regions.
STORE_LOCATIONS: list[tuple[str, str]] = [
    ("Northfield", "North"),
    ("Riverside", "East"),
    ("Oakhaven", "West"),
    ("Millbrook", "South"),
    ("Lakemont", "North"),
    ("Stonebridge", "East"),
    ("Westvale", "West"),
    ("Ashgrove", "South"),
    ("Pinecrest", "North"),
    ("Harborview", "East"),
    ("Elmstead", "West"),
    ("Brookfall", "South"),
]

STORE_FORMATS: dict[str, dict] = {
    "flagship": {"traffic": 1.6, "sqft": (40_000, 60_000)},
    "standard": {"traffic": 1.0, "sqft": (18_000, 30_000)},
    "express": {"traffic": 0.6, "sqft": (4_000, 8_000)},
}

LOYALTY_TIERS: list[str] = ["bronze", "silver", "gold"]
AGE_BANDS: list[str] = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
CHANNELS: list[str] = ["in_store", "online"]
