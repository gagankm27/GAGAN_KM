import os
import json
import base64
import uuid
from functools import wraps
from flask import Flask, send_from_directory, request, jsonify, session, redirect

app = Flask(__name__, static_folder='assets', static_url_path='/assets')
app.secret_key = 'gagan_admin_secret_2025_xK9#mP'   # change this if deploying publicly

@app.after_request
def add_header(response):
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    response.cache_control.must_revalidate = True
    response.cache_control.max_age = 0
    return response

DATA_FILE  = 'data.json'
IMG_DIR    = os.path.join('assets', 'img', 'portfolio')

# ── Admin credentials (change these!) ──────────────────────────────────────
ADMIN_USERNAME = 'gagan'
ADMIN_PASSWORD = 'admin@2025'
# ───────────────────────────────────────────────────────────────────────────

os.makedirs(IMG_DIR, exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:    return json.load(f)
        except: return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def process_base64_media(media_str, album_title=None):
    if not media_str or not (media_str.startswith('data:image') or media_str.startswith('data:video')):
        return media_str
    try:
        header, encoded = media_str.split(',', 1)
        ext = 'jpg'
        if   'image/png'  in header: ext = 'png'
        elif 'image/jpeg' in header: ext = 'jpg'
        elif 'image/gif'  in header: ext = 'gif'
        elif 'image/webp' in header: ext = 'webp'
        elif 'video/mp4'  in header: ext = 'mp4'
        elif 'video/webm' in header: ext = 'webm'
        elif 'video/ogg'  in header: ext = 'ogv'
        elif 'video/quicktime' in header: ext = 'mov'
        
        filename = f"{uuid.uuid4().hex[:10]}.{ext}"
        
        if album_title:
            safe_title = "".join(c for c in album_title if c.isalnum() or c in " _-").strip()
            if not safe_title:
                safe_title = "Untitled"
            target_dir = os.path.join('assets', 'img', 'ALBUM', safe_title)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(encoded))
            url_path = f"assets/img/ALBUM/{safe_title}/{filename}".replace('\\', '/')
            return url_path
        else:
            filepath = os.path.join(IMG_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(encoded))
            return f"assets/img/portfolio/{filename}"
    except Exception as e:
        print(f"Image error: {e}")
        return img_str

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ── Public pages ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/login')
def login_page():
    if session.get('logged_in'):
        return redirect('/admin')
    return send_from_directory('.', 'login.html')

# ── Admin pages (protected) ───────────────────────────────────────────────
@app.route('/admin')
@login_required
def admin():
    return send_from_directory('.', 'admin.html')

# ── Auth API ──────────────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def do_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session.permanent = True
        session['logged_in'] = True
        session['user'] = username
        return jsonify({'success': True, 'message': 'Login successful'})
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def do_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth-check')
def auth_check():
    return jsonify({'logged_in': bool(session.get('logged_in'))})

# ── Albums API (protected) ────────────────────────────────────────────────
@app.route('/api/albums', methods=['GET'])
def get_albums():
    return jsonify(load_data())

@app.route('/api/albums', methods=['POST'])
@login_required
def update_albums():
    albums = request.json or []
    for album in albums:
        title = album.get('title', 'Unknown_Album')
        if 'cover' in album and (album['cover'].startswith('data:image') or album['cover'].startswith('data:video')):
            album['cover'] = process_base64_media(album['cover'], album_title=title)
        if 'images' in album:
            album['images'] = [process_base64_media(img, album_title=title) for img in album['images']]
    save_data(albums)
    return jsonify({'status': 'success', 'message': 'Albums saved successfully'})

# ── Profile API (protected) ───────────────────────────────────────────────
PROFILE_FILE = 'profile.json'

def load_profile():
    if not os.path.exists(PROFILE_FILE):
        return {}
    with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
        try:    return json.load(f)
        except: return {}

def save_profile(data):
    with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route('/api/profile', methods=['GET'])
def get_profile():
    return jsonify(load_profile())

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    save_profile(data)
    return jsonify({'status': 'success', 'message': 'Profile saved'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
