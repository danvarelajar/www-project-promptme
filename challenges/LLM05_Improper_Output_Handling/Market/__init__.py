import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'e-commerce.db')
app.config['SECRET_KEY'] = 's3cretK3y'
app.config['SESSION_PERMANENT'] = False

print(f"[DEBUG] DB path: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'LoginPage'
login_manager.login_message_category = 'info'

# Catalogue the shop starts with. The database itself is created on first
# start (it is not committed), so every attendee gets a fresh, unplayed shop.
SEED_ITEMS = [
    ("IPhone 15", "138729963", 3000), ("MacBook Air", "154843846", 8500),
    ("Galaxy Z Fold", "854615165", 7800), ("Apple iPad", "464147416", 1500),
    ("AirPods", "546541689", 600), ("Smart Watch", "695235148", 850),
    ("Google Pixel 6", "372864925", 900), ("PlayStation 5", "928457123", 500),
    ("Samsung 8K QLED TV", "731298571", 2500), ("Dell XPS 13 Laptop", "268935742", 1400),
    ("Canon EOS R5 Camera", "849372611", 3500), ("Amazon Echo Show 10", "629814726", 250),
    ("Bose Noise-Canceling Headphones", "365281493", 350), ("Nintendo Switch OLED", "158493726", 400),
    ("Sony WH-1000XM4 Headphones", "792614832", 300), ("Microsoft Surface Pro 8", "471982365", 1100),
    ("GoPro Hero 10", "643127489", 500), ("LG OLED 4K TV", "518936247", 2000),
    ("Fitbit Versa 4", "925618374", 200), ("HP Envy x360 Laptop", "386912478", 800),
]

from Market.models import Item  # noqa: E402  (needs db defined above)

try:
    with app.app_context():
        db.create_all()
        if Item.query.count() == 0:
            for n, (name, barcode, price) in enumerate(SEED_ITEMS, start=1):
                db.session.add(Item(name=name, barcode=barcode, price=price, description=f"Item {n}"))
            db.session.commit()
            print("[DEBUG] Seeded shop catalogue.")
        print("[DEBUG] Database initialized successfully.")
except Exception as e:
    print("[ERROR] Database init failed:", e)

from Market import routes
