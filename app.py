from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import re
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)

# Initialize DB
with app.app_context():
    os.makedirs("db", exist_ok=True)
    db.create_all()

# Routes
@app.route('/')
def home():
    return "OpenAI Flask API is running!"

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

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    user = User.query.get(user_id)
    if user:
        user.name = data['name']
        user.email = data['email']
        db.session.commit()
        return jsonify({"message": "User updated"})
    return jsonify({"error": "User not found"}), 404

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted"})
    return jsonify({"error": "User not found"}), 404

@app.route('/reddit-search', methods=['POST'])
def reddit_search():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON format"}), 400

    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query = data['query'].lower()
    keywords = query.split()
    headers = {'User-Agent': 'Mozilla/5.0'}
    search_url = f"https://www.reddit.com/r/FashionReps/search.json?q={'+'.join(keywords)}&restrict_sr=on&sort=relevance"
    marketplace_domains = ["taobao.com", "weidian.com", "tmall.com", "1688.com", "pandabuy.com"]

    try:
        res = requests.get(search_url, headers=headers)
        posts = res.json().get('data', {}).get('children', [])
        formatted_results = []

        for post in posts:
            post_data = post['data']
            post_url = "https://www.reddit.com" + post_data['permalink']
            post_title = post_data.get('title', 'Untitled')
            post_selftext = post_data.get('selftext', '').lower()

            body_links = []
            if any(kw in post_selftext for kw in keywords):
                all_links = re.findall(r'https?://\S+', post_selftext)
                body_links = [l.split(')')[0] for l in all_links if any(domain in l for domain in marketplace_domains)]

            comment_links = []
            comments_url = f"https://www.reddit.com{post_data['permalink']}.json"
            comments_res = requests.get(comments_url, headers=headers)
            if comments_res.status_code == 200:
                comments_data = comments_res.json()
                if len(comments_data) > 1:
                    for comment in comments_data[1]['data']['children']:
                        body = comment['data'].get('body', '').lower()
                        if any(kw in body for kw in keywords):
                            found_links = re.findall(r'https?://\S+', body)
                            clean_links = [l.split(')')[0] for l in found_links if any(domain in l for domain in marketplace_domains)]
                            comment_links.extend(clean_links)

            if body_links or comment_links:
                formatted_results.append({
                    "post_title": post_title,
                    "post_url": post_url,
                    "links_in_post": list(set(body_links)),
                    "links_in_comments": list(set(comment_links)),
                    "summary_and_rating": "Reddit post matched query."
                })

        if not formatted_results:
            return jsonify({"status": "unavailable", "results": []})

        return jsonify({"status": "success", "results": formatted_results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
