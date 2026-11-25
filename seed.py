"""Builds the demo SQLite database: a small online shop with deterministic fake data."""
import random
import sqlite3
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE
);
CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    unit_price  REAL NOT NULL,
    stock       INTEGER NOT NULL
);
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    city        TEXT NOT NULL,
    signup_date TEXT NOT NULL
);
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('delivered','shipped','cancelled','returned'))
);
CREATE TABLE order_items (
    item_id    INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity   INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
"""

CATALOG = {
    "Electronics": ["Wireless Earbuds", "Smart Watch", "Bluetooth Speaker", "Power Bank", "Webcam", "Mechanical Keyboard", "Gaming Mouse", "USB-C Hub"],
    "Home & Kitchen": ["Air Fryer", "Pressure Cooker", "Mixer Grinder", "Water Bottle", "Non-stick Pan", "Lunch Box", "Storage Jars", "Electric Kettle"],
    "Books": ["Python Crash Course", "Atomic Habits", "The Pragmatic Programmer", "Deep Work", "Clean Code", "SQL Cookbook", "Data Science Handbook", "Designing Data-Intensive Apps"],
    "Fitness": ["Yoga Mat", "Dumbbell Set", "Resistance Bands", "Skipping Rope", "Foam Roller", "Running Shoes", "Gym Bag", "Protein Shaker"],
    "Fashion": ["Cotton T-Shirt", "Denim Jacket", "Sports Cap", "Leather Wallet", "Sunglasses", "Backpack", "Hoodie", "Canvas Sneakers"],
}
FIRST = ["Aarav", "Ananya", "Vihaan", "Diya", "Arjun", "Isha", "Kabir", "Meera", "Rohan", "Saanvi", "Aditya", "Kavya", "Nikhil", "Riya", "Siddharth", "Tara", "Varun", "Neha", "Yash", "Pooja"]
LAST = ["Sharma", "Iyer", "Reddy", "Nair", "Gupta", "Patel", "Rao", "Menon", "Joshi", "Kulkarni", "Singh", "Das", "Bhat", "Shetty", "Mehta"]
CITIES = ["Bengaluru", "Mysuru", "Mumbai", "Pune", "Chennai", "Hyderabad", "Delhi", "Kolkata", "Ahmedabad", "Jaipur"]


def build(path: str, seed: int = 7) -> None:
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    for cid, (cat, names) in enumerate(CATALOG.items(), start=1):
        con.execute("INSERT INTO categories VALUES (?, ?)", (cid, cat))
    pid = 0
    for cid, names in enumerate(CATALOG.values(), start=1):
        for name in names:
            pid += 1
            price = round(rng.uniform(149, 6999), 2) if cid != 3 else round(rng.uniform(249, 1299), 2)
            con.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?)", (pid, name, cid, price, rng.randint(0, 250)))

    start = date(2024, 1, 1)
    for i in range(1, 201):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        email = f"{name.lower().replace(' ', '.')}{i}@example.com"
        con.execute("INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                    (i, name, email, rng.choice(CITIES), (start + timedelta(days=rng.randint(0, 540))).isoformat()))

    item_id = 0
    for oid in range(1, 901):
        cust = rng.randint(1, 200)
        day = start + timedelta(days=rng.randint(0, 700))
        status = rng.choices(["delivered", "shipped", "cancelled", "returned"], [78, 10, 7, 5])[0]
        con.execute("INSERT INTO orders VALUES (?, ?, ?, ?)", (oid, cust, day.isoformat(), status))
        for _ in range(rng.randint(1, 4)):
            item_id += 1
            prod = rng.randint(1, pid)
            price = con.execute("SELECT unit_price FROM products WHERE product_id=?", (prod,)).fetchone()[0]
            con.execute("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", (item_id, oid, prod, rng.randint(1, 3), price))
    con.commit()
    con.close()


if __name__ == "__main__":
    build("shop.db")
    print("built shop.db")
