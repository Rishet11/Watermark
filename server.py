from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tempfile
import uuid
import moviepy as mp

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
app.config['PROCESSED_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/processed')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def add_watermark_to_image(image_path, output_path):
    # Open the image
    img = Image.open(image_path)
    
    # Create a drawing context
    draw = ImageDraw.Draw(img)
    
    # Try to load a font (fallback to default if not available)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate position (bottom right corner)
    text = "Creativ Flow"
    # Use textbbox instead of textsize
    bbox = draw.textbbox((0, 0), text, font=font)
    textwidth = bbox[2] - bbox[0]
    textheight = bbox[3] - bbox[1]
    width, height = img.size
    x = width - textwidth - 10
    y = height - textheight - 10
    
    # Add watermark with increased opacity (reduced transparency)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 200))  # Increased opacity from 128 to 200
    
    # Save the watermarked image
    img.save(output_path)
    return output_path

def add_watermark_to_video(video_path, output_path):
    # Load the video
    video = mp.VideoFileClip(video_path)
    
    # Create a text clip for the watermark with increased opacity
    txt_clip = mp.TextClip("Creativ Flow", fontsize=30, color='white', font='Arial', 
                         bg_color='rgba(0,0,0,0.6)', opacity=0.9)  # Increased opacity from 0.7 to 0.9
    
    # Position the watermark in the bottom right corner
    txt_clip = txt_clip.set_position(('right', 'bottom')).set_duration(video.duration)
    
    # Composite the video with the watermark
    final_clip = mp.CompositeVideoClip([video, txt_clip])
    
    # Write the result to a file
    final_clip.write_videofile(output_path, codec='libx264')
    
    # Close the clips to free resources
    video.close()
    final_clip.close()
    
    return output_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Generate a unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Save the uploaded file
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(upload_path)
        
        # Generate output path
        output_filename = f"watermarked_{unique_filename}"
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        
        # Process the file based on its type
        if file_extension in ['png', 'jpg', 'jpeg']:
            add_watermark_to_image(upload_path, output_path)
        elif file_extension in ['mp4', 'mov', 'avi']:
            add_watermark_to_video(upload_path, output_path)
        
        # Return the URL to the processed file
        return jsonify({
            'success': True,
            'filename': output_filename,
            'url': f"/view/{output_filename}"
        })
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/view/<filename>')
def view_file(filename):
    file_extension = filename.rsplit('.', 1)[1].lower()
    file_type = 'video' if file_extension in ['mp4', 'mov', 'avi'] else 'image'
    return render_template('view.html', filename=filename, file_type=file_type)

@app.route('/static/processed/<path:filename>')
def serve_processed_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

@app.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)