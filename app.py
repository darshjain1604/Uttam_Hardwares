from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import qrcode
import pandas as pd

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
        id INTEGER PRIMARY KEY,
        name TEXT,
        price INTEGER,
        unit TEXT
    )
    """)
    conn.close()
    return "Database Ready!"


# ---------------- HOME (CART) ----------------

@app.route("/")
def home():
    return render_template("cart.html", cart=session.get("cart", []))


# ---------------- PRODUCT PAGE ----------------

@app.route("/product/<int:pid>")
def product(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()

    if row:
        product = {
            "id": row[0],
            "name": row[1],
            "price": row[2],
            "unit": row[3]
        }
    else:
        product = None

    return render_template("product.html", product=product)


# ---------------- ADD PRODUCT (ADMIN) ----------------

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO products (id, name, price, unit) VALUES (?, ?, ?, ?)",
            (
                request.form["id"],
                request.form["name"],
                request.form["price"],
                request.form["unit"]
            )
        )
        conn.commit()
        conn.close()

        return "Product Added Successfully!"

    return render_template("add_product.html")


# ---------------- ADD TO CART ----------------

@app.route("/add_to_cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "Product not found"

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

    data = []
    for item in cart:
        data.append({
            "Product Name": item["name"],
            "Price": item["price"],
            "Quantity": item["qty"],
            "Total": item["price"] * item["qty"]
        })

    df = pd.DataFrame(data)
    file = "bill.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)


# ---------------- CLEAR CART ----------------

@app.route("/clear")
def clear():
    session["cart"] = []
    return redirect("/")


# ---------------- GENERATE QR ----------------

@app.route("/generate_qr/<int:pid>")
def generate_qr(pid):
    url = f"https://qr-shop-system.onrender.com/product/{pid}"
    img = qrcode.make(url)
    img.save(f"static/qr_codes/product_{pid}.png")
    return "QR created successfully!"


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)