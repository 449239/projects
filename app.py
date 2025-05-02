from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import re
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

# Health route
@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

# Routes
@app.route('/')
def home():
    return "Flask Reddit Scraper API is live."

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
    data = request.get_json(silent=True)
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    query = data['query'].lower()
    print(f"🔍 Searching Reddit for: {query}")
    keywords = query.split()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    search_url = f"https://www.reddit.com/r/FashionReps/search.json?q={'+'.join(keywords)}&restrict_sr=on&sort=relevance"
    marketplace_domains = ["taobao.com", "weidian.com", "tmall.com", "1688.com", "pandabuy.com"]

    try:
        res = requests.get(search_url, headers=headers)
        print(f"🔎 Reddit status: {res.status_code}")

        if res.status_code != 200:
            return jsonify({
                "error": "Reddit rejected the search request",
                "status_code": res.status_code,
                "response_sample": res.text[:200]
            }), 502

        try:
            posts = res.json().get('data', {}).get('children', [])
        except Exception as e:
            return jsonify({
                "error": f"Failed to parse Reddit JSON: {str(e)}",
                "raw_response": res.text[:200]
            }), 500

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
                try:
                    comments_data = comments_res.json()
                    if len(comments_data) > 1:
                        for comment in comments_data[1]['data']['children']:
                            body = comment['data'].get('body', '').lower()
                            if any(kw in body for kw in keywords):
                                found_links = re.findall(r'https?://\S+', body)
                                clean_links = [l.split(')')[0] for l in found_links if any(domain in l for domain in marketplace_domains)]
                                comment_links.extend(clean_links)
                except Exception as e:
                    print(f"⚠️ Failed to parse comment JSON: {e}")

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
        return jsonify({"error": f"Unhandled exception: {str(e)}"}), 500

if __name__ == '__main__':
    from waitress import serve
    print("✅ Server starting on http://127.0.0.1:5000")
    serve(app, host='0.0.0.0', port=5000)

