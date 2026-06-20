import os
import json
import base64
import uuid
from flask import Flask, send_from_directory, request, jsonify

app = Flask(__name__, static_folder='assets', static_url_path='/assets')

DATA_FILE = 'data.json'
IMG_DIR = os.path.join('assets', 'img', 'portfolio')

# Ensure image directory exists
os.makedirs(IMG_DIR, exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def process_base64_image(img_str):
    """
    If img_str is a base64 data URL, decode it, save it to assets/img/portfolio/,
    and return the new relative path. Otherwise, return the original string.
    """
    if not img_str or not img_str.startswith('data:image'):
        return img_str

    try:
        # Extract the base64 part
        header, encoded = img_str.split(',', 1)
        # Determine extension from header (e.g., data:image/png;base64)
        ext = 'jpg'
        if 'image/png' in header:
            ext = 'png'
        elif 'image/jpeg' in header:
            ext = 'jpg'
        elif 'image/gif' in header:
            ext = 'gif'
        elif 'image/webp' in header:
            ext = 'webp'

        filename = f"{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(IMG_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(base64.b64decode(encoded))
            
        return f"assets/img/portfolio/{filename}"
    except Exception as e:
        print(f"Error processing base64 image: {e}")
        return img_str

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/api/albums', methods=['GET'])
def get_albums():
    return jsonify(load_data())

@app.route('/api/albums', methods=['POST'])
def update_albums():
    albums = request.json
    
    # Process base64 images in the incoming data
    for album in albums:
        if 'cover' in album and album['cover'].startswith('data:image'):
            album['cover'] = process_base64_image(album['cover'])
            
        if 'images' in album:
            new_images = []
            for img in album['images']:
                new_images.append(process_base64_image(img))
            album['images'] = new_images

    save_data(albums)
    return jsonify({"status": "success", "message": "Albums updated successfully"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
