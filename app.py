from flask import Flask, render_template, request, redirect, session, send_file, abort
import sqlite3
import qrcode
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect("database.db")
    return conn


@app.route("/init_db")
def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        unit TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()
    return "Database Ready!"


# ---------------- HOME (CART) ----------------

@app.route("/")
def home():
    return render_template("cart.html", cart=session.get("cart", []))


# ---------------- PRODUCTS LIST ----------------

@app.route("/products")
def product_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "price": row[2],
            "unit": row[3]
        })

    return render_template("products.html", products=products)


# ---------------- PRODUCT PAGE ----------------

@app.route("/product/<int:pid>")
def product(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        abort(404)

    product = {
        "id": row[0],
        "name": row[1],
        "price": row[2],
        "unit": row[3]
    }

    return render_template("product.html", product=product)


# ---------------- ADD PRODUCT (ADMIN) ----------------

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        unit = request.form.get("unit", "").strip()

        if not name or not price or not unit:
            return "All fields are required", 400

        try:
            price = int(price)
        except ValueError:
            return "Price must be a number", 400

        conn = get_db()
        conn.execute(
            "INSERT INTO products (name, price, unit) VALUES (?, ?, ?)",
            (name, price, unit)
        )
        conn.commit()
        conn.close()

        return "Product Added Successfully!"

    return render_template("add_product.html")


# ---------------- ADD TO CART ----------------

@app.route("/add_to_cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = request.form.get("qty", "1").strip()

    try:
        qty = int(qty)
        if qty < 1:
            raise ValueError
    except ValueError:
        return "Quantity must be a positive number", 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "Product not found", 404

    product = {
        "id": row[0],
        "name": row[1],
        "price": row[2],
        "unit": row[3]
    }

    cart = session.get("cart", [])

    for item in cart:
        if item["id"] == pid:
            item["qty"] += qty
            break
    else:
        cart.append({
            "id": pid,
            "name": product["name"],
            "price": product["price"],
            "qty": qty
        })

    session["cart"] = cart
    return redirect("/")


# ---------------- EXPORT TO EXCEL ----------------

@app.route("/export_excel")
def export_excel():
    cart = session.get("cart", [])

    if not cart:
        return "Cart is empty", 400

    data = []
    for item in cart:
        data.append({
            "Product Name": item["name"],
            "Price": item["price"],
            "Quantity": item["qty"],
            "Total": item["price"] * item["qty"]
        })

    df = pd.DataFrame(data)
    file_path = "bill.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ---------------- CLEAR CART ----------------

@app.route("/clear")
def clear():
    session["cart"] = []
    return redirect("/")


# ---------------- GENERATE QR ----------------

@app.route("/generate_qr/<int:pid>")
def generate_qr(pid):
    base_url = request.host_url.rstrip("/")
    url = f"{base_url}/product/{pid}"

    img = qrcode.make(url)
    qr_path = f"static/qr_codes/product_{pid}.png"
    img.save(qr_path)

    return f"QR created successfully for product {pid}"


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)