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
    return send_from_directory('.', 'main.html')

@app.route('/index.html')
def static_index():
    return send_from_directory('.', 'index.html')

@app.route('/data.json')
def serve_data_json():
    """Serve data.json so index.html (static version) can fetch album data locally too."""
    return send_from_directory('.', 'data.json', mimetype='application/json')

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

# ── Hero Images API ───────────────────────────────────────────────────────
HERO_DIR = os.path.join('assets', 'img', 'Hero')
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

@app.route('/api/hero-images', methods=['GET'])
def get_hero_images():
    os.makedirs(HERO_DIR, exist_ok=True)
    order_file = 'hero_order.json'
    if os.path.exists(order_file):
        with open(order_file, 'r') as f:
            try:
                return jsonify(json.load(f))
            except:
                pass

    images = []
    for f in sorted(os.listdir(HERO_DIR)):
        ext = os.path.splitext(f)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            images.append(f'assets/img/Hero/{f}')
    return jsonify(images)

@app.route('/api/hero-images', methods=['POST'])
@login_required
def update_hero_images():
    images = request.json or []
    os.makedirs(HERO_DIR, exist_ok=True)
    
    processed_images = []
    for img in images:
        if img.startswith('data:image'):
            import base64
            import hashlib
            
            header, encoded = img.split(",", 1)
            ext = 'jpg'
            if 'image/png' in header: ext = 'png'
            elif 'image/webp' in header: ext = 'webp'
            elif 'image/gif' in header: ext = 'gif'
            
            data_bytes = base64.b64decode(encoded)
            file_hash = hashlib.md5(data_bytes).hexdigest()[:10]
            filename = f"hero_{file_hash}.{ext}"
            filepath = os.path.join(HERO_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(data_bytes)
            processed_images.append(f'assets/img/Hero/{filename}')
        else:
            processed_images.append(img)
            
    # Delete removed images
    current_files = set(f'assets/img/Hero/{f}' for f in os.listdir(HERO_DIR) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS)
    new_files = set(processed_images)
    
    for old_f in current_files:
        if old_f not in new_files:
            try:
                os.remove(old_f)
            except:
                pass
                
    with open('hero_order.json', 'w') as f:
        json.dump(processed_images, f)
        
    return jsonify({'status': 'success'})

# ── Testimonials API ──────────────────────────────────────────────────────
TESTIMONIALS_FILE = 'testimonials.json'

def load_testimonials():
    if not os.path.exists(TESTIMONIALS_FILE):
        return []
    with open(TESTIMONIALS_FILE, 'r', encoding='utf-8') as f:
        try:    return json.load(f)
        except: return []

def save_testimonials(data):
    with open(TESTIMONIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

@app.route('/api/testimonials', methods=['GET'])
def get_testimonials():
    return jsonify(load_testimonials())

@app.route('/api/testimonials', methods=['POST'])
@login_required
def update_testimonials():
    testimonials = request.json or []
    for t in testimonials:
        if 'image' in t and (t['image'].startswith('data:image') or t['image'].startswith('data:video')):
            t['image'] = process_base64_media(t['image'], album_title="Testimonials")
    save_testimonials(testimonials)
    return jsonify({'status': 'success'})

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

# ── Sync Albums to HTML files ─────────────────────────────────────────────
@app.route('/api/sync-index', methods=['POST'])
@login_required
def sync_index():
    """Patch the hardcoded albums array in main.html and index.html from data.json."""
    import re
    albums = load_data()
    
    # Build a compact but readable JS array string
    lines = ['        let albums = [\n']
    for i, album in enumerate(albums):
        comma = '' if i == len(albums) - 1 else ','
        images_js = ',\n'.join(f'                    "{img}"' for img in album.get('images', []))
        lines.append(f'''            {{
                title: {json.dumps(album.get("title",""))},
                desc: {json.dumps(album.get("desc",""))},
                category: {json.dumps(album.get("category",""))},
                filterClass: {json.dumps(album.get("filterClass",""))},
                cover: {json.dumps(album.get("cover",""))},
                images: [
{images_js}
                ]
            }}{comma}\n''')
    lines.append('        ];')
    new_block = ''.join(lines)
    
    # Regex to match the full albums array (from "let albums = [" to "];")
    pattern_albums = re.compile(
        r'(// ===== ALBUM DATA =====\s*\n\s*)let albums = \[.*?\];',
        re.DOTALL
    )
    
    # 2. Hero Slides
    try:
        hero_images_response = get_hero_images()
        hero_list = hero_images_response.json
    except:
        hero_list = []
        
    hero_html = "\n"
    for idx, img in enumerate(hero_list):
        active_class = " active" if idx == 0 else ""
        hero_html += f"        <div class=\"hero-slide{active_class}\" style=\"background-image: url('{img}');\"></div>\n"
        
    pattern_hero = re.compile(r'<!-- ===== HERO SLIDES START ===== -->.*?<!-- ===== HERO SLIDES END ===== -->', re.DOTALL)
    replacement_hero = f'<!-- ===== HERO SLIDES START ===== -->{hero_html}        <!-- ===== HERO SLIDES END ===== -->'

    # 3. Testimonials
    testimonials = load_testimonials()
    test_html = "\n"
    for t in testimonials:
        test_html += f'''                        <div class="swiper-slide">
                            <div class="testimonial-item">
                                <img src="{t.get('image','')}" class="testimonial-img" alt="">
                                <h3>{t.get('name','')}</h3>
                                <h4>{t.get('title','')}</h4>
                                <p>
                                    <i class="bx bxs-quote-alt-left quote-icon-left"></i>
                                    {t.get('quote','')}
                                    <i class="bx bxs-quote-alt-right quote-icon-right"></i>
                                </p>
                            </div>
                        </div>\n\n'''
                        
    pattern_test = re.compile(r'<!-- ===== TESTIMONIALS START ===== -->.*?<!-- ===== TESTIMONIALS END ===== -->', re.DOTALL)
    
    updated = []
    errors = []
    for fname in ['main.html', 'index.html']:
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content, c1 = pattern_albums.subn(lambda m: m.group(1) + new_block, content)
            new_content, c2 = pattern_hero.subn(lambda m: f'<!-- ===== HERO SLIDES START ===== -->{hero_html}        <!-- ===== HERO SLIDES END ===== -->', new_content)
            new_content, c3 = pattern_test.subn(lambda m: f'<!-- ===== TESTIMONIALS START ===== -->{test_html}                        <!-- ===== TESTIMONIALS END ===== -->', new_content)
            
            if c1 == 0 and c2 == 0 and c3 == 0:
                errors.append(f'{fname}: patterns not found')
            else:
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                updated.append(fname)
        except Exception as e:
            errors.append(f'{fname}: {str(e)}')
    
    if errors:
        return jsonify({'status': 'partial', 'updated': updated, 'errors': errors}), 207
    return jsonify({'status': 'success', 'message': f'Synced to: {", ".join(updated)}', 'updated': updated})


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
