from flask import Flask, render_template, request, redirect, session, send_file, abort
import psycopg2
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

ADMIN_PASS = "1234"  # 🔐 change this password


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
        name TEXT,
        price INTEGER,
        unit TEXT,
        image TEXT,
        stock INTEGER
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

    return "Database Ready!"


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect("/products")
        else:
            return "Wrong Password!"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")


# ---------------- ADMIN PRODUCT LIST ----------------

@app.route("/products")
def product_list():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, unit, image, stock FROM products")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "price": row[2],
            "unit": row[3],
            "image": row[4],
            "stock": row[5]
        })

    return render_template("products.html", products=products)


# ---------------- ADD PRODUCT ----------------

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO products (name, price, unit, image, stock) VALUES (%s, %s, %s, %s, %s)",
            (
                request.form["name"],
                request.form["price"],
                request.form["unit"],
                request.form["image"],
                request.form["stock"]
            )
        )

        conn.commit()
        cur.close()
        conn.close()

        return "Product Added Successfully!"

    return render_template("add_product.html")


# ---------------- CUSTOMER SHOP PAGE ----------------

@app.route("/shop")
def shop():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, unit, image, stock FROM products")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "price": row[2],
            "unit": row[3],
            "image": row[4],
            "stock": row[5]
        })

    return render_template("shop.html", products=products)


# ---------------- PRODUCT PAGE ----------------

@app.route("/product/<int:pid>")
def product(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, unit, image, stock FROM products WHERE id=%s", (pid,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        abort(404)

    product = {
        "id": row[0],
        "name": row[1],
        "price": row[2],
        "unit": row[3],
        "image": row[4],
        "stock": row[5]
    }

    return render_template("product.html", product=product)


# ---------------- ADD TO CART ----------------

@app.route("/add_to_cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, image, stock FROM products WHERE id=%s", (pid,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return "Product not found"

    if qty > row[4]:
        return "Not enough stock!"

    product = {
        "id": row[0],
        "name": row[1],
        "price": row[2],
        "image": row[3],
        "stock": row[4]
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
            "qty": qty,
            "image": product["image"]
        })

    session["cart"] = cart
    return redirect("/")


# ---------------- CART ----------------

@app.route("/")
def home():
    return render_template("cart.html", cart=session.get("cart", []))


# ---------------- EXPORT EXCEL ----------------

@app.route("/export_excel")
def export_excel():
    cart = session.get("cart", [])

    conn = get_db()
    cur = conn.cursor()

    data = []

    for item in cart:
        total = item["price"] * item["qty"]

        data.append({
            "Product Name": item["name"],
            "Price": item["price"],
            "Quantity": item["qty"],
            "Total": total
        })

        # 🔥 REDUCE STOCK HERE
        cur.execute(
            "UPDATE products SET stock = stock - %s WHERE id = %s",
            (item["qty"], item["id"])
        )

    conn.commit()
    cur.close()
    conn.close()

    # Create Excel
    df = pd.DataFrame(data)
    file = "bill.xlsx"
    df.to_excel(file, index=False)

    # Clear cart after purchase
    session["cart"] = []

    return send_file(file, as_attachment=True)


# ---------------- CLEAR CART ----------------

@app.route("/clear")
def clear():
    session["cart"] = []
    return redirect("/")


# ---------------- RUN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)