from flask import Flask, request, jsonify
from models import db, User
from waitress import serve
import os

print("✅ Starting app.py...")

app = Flask(__name__)

# Set up SQLite database
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'db', 'site.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
db.init_app(app)
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return "User API is running!"

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(name=data['name'], email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created"}), 201

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "name": u.name, "email": u.email} for u in users])

if __name__ == '__main__':
    print("✅ Launching server on port 5000...")
    serve(app, host='0.0.0.0', port=5000)
