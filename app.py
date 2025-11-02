from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np
import os
import io
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_adaptive_thresholds(image):
    """
    Calculate adaptive Canny thresholds based on image statistics.
    Uses sigma-based approach for more robust threshold calculation.
    """
    median = np.median(image)
    sigma = 0.33
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))
    
    if upper < lower * 2:
        upper = min(255, lower * 2)
    
    if lower < 30:
        lower = 30
    if upper < 60:
        upper = 60
    
    return lower, upper


def detect_edges_from_image(image_array, lower_threshold=None, upper_threshold=None, 
                            blur_kernel=(5, 5), sigma=0, use_adaptive=False):
    """
    Perform Canny edge detection on an image array.
    
    Args:
        image_array: numpy array of the image (BGR format from OpenCV)
        lower_threshold: Lower threshold for Canny
        upper_threshold: Upper threshold for Canny
        blur_kernel: Gaussian blur kernel size
        sigma: Gaussian blur sigma
        use_adaptive: Use adaptive threshold calculation
    
    Returns:
        dict: Contains processed images and metadata
    """
    # Handle image format
    if len(image_array.shape) == 2:
        gray = image_array.copy()
    elif len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        raise ValueError(f"Unsupported image format with shape: {image_array.shape}")
    
    # Apply Gaussian blur
    if blur_kernel[0] > 1 or blur_kernel[1] > 1:
        blurred = cv2.GaussianBlur(gray, blur_kernel, sigma)
    else:
        blurred = gray.copy()
    
    # Calculate thresholds
    if use_adaptive:
        lower, upper = calculate_adaptive_thresholds(blurred)
    else:
        if lower_threshold is None:
            lower_threshold = 100
        if upper_threshold is None:
            upper_threshold = 200
        
        if upper_threshold < lower_threshold:
            upper_threshold = lower_threshold * 2
        
        lower_threshold = max(0, min(255, int(lower_threshold)))
        upper_threshold = max(0, min(255, int(upper_threshold)))
        lower, upper = lower_threshold, upper_threshold
    
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, lower, upper)
    
    # Convert grayscale images to BGR for consistent display
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    blurred_bgr = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    return {
        'original': image_array,
        'grayscale': gray_bgr,
        'blurred': blurred_bgr,
        'edges': edges_bgr,
        'thresholds': {'lower': lower, 'upper': upper}
    }


def image_to_base64(image_array):
    """Convert numpy image array to base64 string."""
    # Encode image to JPEG format
    _, buffer = cv2.imencode('.jpg', image_array)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{image_base64}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, WEBP'}), 400
        
        # Get parameters from form
        use_adaptive = request.form.get('adaptive', 'false').lower() == 'true'
        lower_threshold = request.form.get('lower_threshold', type=int)
        upper_threshold = request.form.get('upper_threshold', type=int)
        blur_kernel_size = request.form.get('blur_kernel', default=5, type=int)
        
        # Validate blur kernel (must be odd)
        if blur_kernel_size % 2 == 0:
            blur_kernel_size += 1
        blur_kernel = (blur_kernel_size, blur_kernel_size)
        
        # Read image
        file_bytes = file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': 'Could not decode image. Please check file format.'}), 400
        
        # Process image
        result = detect_edges_from_image(
            image,
            lower_threshold=lower_threshold,
            upper_threshold=upper_threshold,
            blur_kernel=blur_kernel,
            use_adaptive=use_adaptive
        )
        
        # Convert images to base64 for frontend
        response_data = {
            'original': image_to_base64(result['original']),
            'grayscale': image_to_base64(result['grayscale']),
            'blurred': image_to_base64(result['blurred']),
            'edges': image_to_base64(result['edges']),
            'thresholds': result['thresholds'],
            'image_size': f"{image.shape[1]}x{image.shape[0]}"
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download', methods=['POST'])
def download_image():
    try:
        data = request.get_json()
        image_data = data.get('image_data')
        
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Remove data URL prefix
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Return as file
        return send_file(
            io.BytesIO(image_bytes),
            mimetype='image/jpeg',
            as_attachment=True,
            download_name='edge_detected.jpg'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

