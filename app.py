from flask import Flask, render_template, jsonify, g, request, redirect, session
import sqlite3, json, urllib.parse

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'dijlah.db'

# الاتصال بقاعدة البيانات
def get_db():
    if '_database' not in g:
        g._database = sqlite3.connect(DATABASE)
        g._database.row_factory = sqlite3.Row
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('_database', None)
    if db is not None:
        db.close()

# إنشاء جدول الطلبات
with sqlite3.connect(DATABASE) as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            address TEXT,
            products TEXT,
            total INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    print("✅ تم إنشاء جدول الطلبات بنجاح.")

# التأكد من وجود الأعمدة
def ensure_category_column():
    db = get_db()
    cur = db.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cur.fetchall()]
    if 'category' not in columns:
        db.execute("ALTER TABLE products ADD COLUMN category TEXT")
        db.commit()
        print("✅ تم إضافة العمود 'category' إلى جدول المنتجات.")

def ensure_sizes_column():
    db = get_db()
    cur = db.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cur.fetchall()]
    if 'sizes' not in columns:
        db.execute("ALTER TABLE products ADD COLUMN sizes TEXT")
        db.commit()
        print("✅ تم إضافة العمود 'sizes' إلى جدول المنتجات.")

# الصفحة الرئيسية
@app.route('/')
def home():
    categories = [
        {"name": "الموسم الحالي", "image": "class1.jpg", "description": "تصاميم عصرية وخامات عالية الجودة."},
        {"name": "نسخة لاعب", "image": "pants.jpg", "description": "بناطيل رياضية مرنة ومناسبة للتمارين."},
        {"name": "نسخة مشجع", "image": "jackets.jpg", "description": "جاكيتات مقاومة للرياح والبرد."},
        {"name": "كلاسيك", "image": "shoes.jpg", "description": "أحذية رياضية لجميع الأنشطة."},
        {"name": "منتخبات", "image": "accessories.jpg", "description": "قبعات، جوارب، حقائب والمزيد."},
        {"name": "تراكات", "image": "kids.jpg", "description": "ملابس رياضية للأطفال بجودة عالية."},
        {"name": "أطقم تدريبات", "image": "women.jpg", "description": "ملابس رياضية أنيقة للنساء."},
        {"name": "أحذية", "image": "men.jpg", "description": "أطقم رياضية للرجال بجميع المقاسات."}
    ]
    return render_template('index.html', categories=categories)

# عرض جميع المنتجات
@app.route('/products')
def products():
    db = get_db()
    cur = db.execute('SELECT * FROM products')
    rows = cur.fetchall()
    items = [{
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "old_price": row["old_price"],
        "new_price": row["new_price"],
        "images": json.loads(row["images"])
    } for row in rows]
    return render_template('products.html', products=items, category=None)

# عرض المنتجات حسب الفئة
@app.route('/category/<category_name>')
def products_by_category(category_name):
    db = get_db()
    cur = db.execute('SELECT * FROM products WHERE category LIKE ?', ('%' + category_name + '%',))
    rows = cur.fetchall()
    items = [{
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "old_price": row["old_price"],
        "new_price": row["new_price"],
        "images": json.loads(row["images"])
    } for row in rows]
    return render_template('products.html', products=items, category=category_name)

# تفاصيل منتج
@app.route('/product/<int:product_id>')
def product_details(product_id):
    db = get_db()
    cur = db.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    row = cur.fetchone()

    if row:
        sizes_raw = json.loads(row["sizes"]) if row["sizes"] else {}
        available_sizes = [size for size, qty in sizes_raw.items() if qty > 0]

        product = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "old_price": row["old_price"],
            "new_price": row["new_price"],
            "images": json.loads(row["images"]) if row["images"] else [],
            "sizes": available_sizes
        }

        return render_template('product_details.html', product=product)

    return "المنتج غير موجود", 404

# إضافة منتج
@app.route('/admin/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        old_price = int(request.form['old_price'])
        new_price = int(request.form['new_price'])
        images = request.form['images'].split(',')
        category = request.form['category']
        sizes = request.form.getlist('sizes')
        db = get_db()
        db.execute('''
            INSERT INTO products (name, description, old_price, new_price, images, category, sizes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, old_price, new_price, json.dumps(images), category, json.dumps(sizes)))
        db.commit()
        return redirect('/admin/products')
    return render_template('add_product.html')

# لوحة التحكم للمنتجات
@app.route('/admin/products')
def admin_products():
    db = get_db()
    cur = db.execute('SELECT * FROM products')
    rows = cur.fetchall()
    items = [{
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "new_price": row["new_price"]
    } for row in rows]
    return render_template('admin_products.html', products=items)

# إضافة إلى السلة
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    selected_size = request.form['selected_size']
    cart = session.get('cart', [])
    cart.append({"id": product_id, "size": selected_size})
    session['cart'] = cart
    return redirect('/cart')

# عرض السلة
@app.route('/cart')
def cart():
    cart = session.get('cart', [])
    db = get_db()
    products = []
    subtotal = 0
    for item in cart:
        pid = item["id"]
        size = item["size"]
        cur = db.execute('SELECT * FROM products WHERE id = ?', (pid,))
        row = cur.fetchone()
        if row:
            products.append({
                "id": row["id"],
                "name": row["name"],
                "new_price": row["new_price"],
                "size": size
            })
            subtotal += row["new_price"]
    delivery_fee = 5000
    total = subtotal + delivery_fee
    return render_template('cart.html', products=products, subtotal=subtotal, delivery_fee=delivery_fee, total=total)

# حذف منتج من السلة
@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    product_id = request.form['product_id']
    cart = session.get('cart', [])
    cart = [item for item in cart if item["id"] != product_id]
    session['cart'] = cart
    return redirect('/cart')

# صفحة إتمام الطلب
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        cart = session.get('cart', [])
        db = get_db()

        products = []
        total = 5000
        for item in cart:
            pid = item["id"]
            size = item["size"]
            cur = db.execute('SELECT * FROM products WHERE id = ?', (pid,))
            row = cur.fetchone()
            if row:
                sizes = json.loads(row["sizes"]) if row["sizes"] else {}
                if sizes.get(size, 0) > 0:
                    sizes[size] -= 1
                    db.execute("UPDATE products SET sizes = ? WHERE id = ?", (json.dumps(sizes), pid))
                    db.commit()

                    products.append(f"{row['name']} - قياس: {size} ({row['new_price']} د.ع)")
                    total += row["new_price"]
                else:
                    print(f"⚠️ القياس {size} غير متوفر للمنتج {row['name']}")

        db.execute('''
            INSERT INTO orders (name, phone, address, products, total)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, phone, address, json.dumps(products), total))
        db.commit()

        message = f"""طلب جديد:
الاسم: {name}
الهاتف: {phone}
العنوان: {address}
المنتجات:
- {'\n- '.join(products)}
المجموع الكلي: {total} د.ع
"""
        whatsapp_number = "9647510590334"  # ← ضع رقمك هنا بدون +
        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"https://api.whatsapp.com/send?phone={whatsapp_number}&text={encoded_message}"

        session['cart'] = []
        return redirect(whatsapp_url)

    return render_template('checkout.html')

#صفحة الطلبات الخاصة بالأدمن
@app.route('/admin/orders')
def admin_orders():
    db = get_db()
    cur = db.execute('SELECT * FROM orders ORDER BY created_at DESC')
    rows = cur.fetchall()
    orders = []
    for row in rows:
        orders.append({
            "name": row["name"],
            "phone": row["phone"],
            "address": row["address"],
            "products": json.loads(row["products"]),
            "total": row["total"],
            "created_at": row["created_at"]
        })
    return render_template('admin_orders.html', orders=orders)

def ensure_status_column():
    db = get_db()
    cur = db.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cur.fetchall()]
    if 'status' not in columns:
        db.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'pending'")
        db.commit()
        print("✅ تم إضافة العمود 'status' إلى جدول الطلبات.")

@app.route('/admin/mark-delivered', methods=['POST'])
def mark_delivered():
    order_id = request.form['order_id']
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', ('delivered', order_id))
    db.commit()
    return redirect('/admin/orders')

# تشغيل التطبيق
if __name__ == '__main__':
    with app.app_context():
        ensure_category_column()
        ensure_sizes_column()
    app.run(debug=True)