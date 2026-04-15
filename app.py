from flask import Flask, render_template, request, redirect, session, send_file
import json
import qrcode
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret123"

with open("products.json") as f:
    products = json.load(f)

@app.route("/")
def home():
    return render_template("cart.html", cart=session.get("cart", []))

@app.route("/product/<int:pid>")
def product(pid):
    product = next((p for p in products if p["id"] == pid), None)
    return render_template("product.html", product=product)

@app.route("/add_to_cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))
    product = next((p for p in products if p["id"] == pid), None)

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

@app.route("/generate_qr/<int:pid>")
def generate_qr(pid):
    url = f"http://10.161.56.201:5000/product/{pid}"
    img = qrcode.make(url)
    img.save(f"static/qr_codes/product_{pid}.png")
    return "QR created"

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

@app.route("/clear")
def clear():
    session["cart"] = []
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")