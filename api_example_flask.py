"""
Flask API Example - How to integrate with the Car Repair Estimator
This is a reference implementation showing how to build an API endpoint
"""

from flask import Flask, request, jsonify
from main_api_friendly import estimate_car_price, EstimationRequest, ResponseStatus
import os
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/estimate', methods=['POST'])
def estimate_repair_cost():
    """
    API Endpoint: Estimate car repair cost
    
    Request (Form Data):
    - image: Image file (required)
    - description: Text description of damage (required)
    - country: Country name (optional, defaults to Bangladesh)
    
    Response (JSON):
    {
        "status": "success|error|validation_error",
        "estimated_cost": 15000,
        "currency_country": "Bangladesh",
        "message": "Estimated repair cost in Bangladesh: 15000",
        "error_details": null
    }
    """
    try:
        # Validate form data
        if 'image' not in request.files:
            return jsonify({
                "status": "validation_error",
                "message": "Image file is required",
                "error_details": "No image provided"
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({
                "status": "validation_error",
                "message": "No image selected",
                "error_details": "Filename is empty"
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "status": "validation_error",
                "message": "Invalid file type",
                "error_details": f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        description = request.form.get('description', '').strip()
        if not description:
            return jsonify({
                "status": "validation_error",
                "message": "Description is required",
                "error_details": "Damage description cannot be empty"
            }), 400
        
        country = request.form.get('country', 'Bangladesh').strip()
        
        # Save temporary file
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # Create estimation request
            request_obj = EstimationRequest(
                image_path=temp_path,
                description=description,
                country=country
            )
            
            # Process estimation
            response = estimate_car_price(request_obj)
            
            # Return response
            return jsonify(response.to_dict()), \
                200 if response.status == ResponseStatus.SUCCESS.value else 422
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error_details": str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Car Repair Cost Estimator API"
    }), 200


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        "status": "validation_error",
        "message": "File too large",
        "error_details": "Maximum file size is 20MB"
    }), 413


if __name__ == '__main__':
    # For development only
    app.run(debug=True, host='0.0.0.0', port=5000)
