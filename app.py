from flask import Flask, render_template, request, redirect, session, send_file, abort
import psycopg2
import os
import qrcode
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


@app.route("/init_db")
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        unit TEXT NOT NULL
    )
    """)
    conn.commit()
    cur.close()
    conn.close()
    return "Database Ready!"


# ---------------- HOME (CART) ----------------

@app.route("/")
def home():
    return render_template("cart.html", cart=session.get("cart", []))


# ---------------- PRODUCT LIST ----------------

@app.route("/products")
def product_list():
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, price, unit FROM products")
        rows = cur.fetchall()

        products = []
        for row in rows:
            products.append({
                "id": row[0],
                "name": row[1],
                "price": row[2],
                "unit": row[3]
            })

    except Exception as e:
        return f"Error: {e}"

    finally:
        cur.close()
        conn.close()

    return render_template("products.html", products=products)


# ---------------- PRODUCT PAGE ----------------

@app.route("/product/<int:pid>")
def product(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    row = cur.fetchone()
    cur.close()
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


# ---------------- ADD PRODUCT ----------------

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        unit = request.form.get("unit")

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, price, unit) VALUES (%s, %s, %s)",
            (name, price, unit)
        )
        conn.commit()
        cur.close()
        conn.close()

        return "Product Added Successfully!"

    return render_template("add_product.html")


# ---------------- ADD TO CART ----------------

@app.route("/add_to_cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    row = cur.fetchone()
    cur.close()
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


# ---------------- EXPORT EXCEL ----------------

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
    base_url = request.host_url.rstrip("/")
    url = f"{base_url}/product/{pid}"

    img = qrcode.make(url)
    img.save(f"static/qr_codes/product_{pid}.png")

    return "QR created!"


# ---------------- RUN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)