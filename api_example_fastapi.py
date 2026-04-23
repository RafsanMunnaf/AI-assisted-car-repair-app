"""
FastAPI Example - How to integrate with the Car Repair Estimator
This is a modern, async alternative to Flask
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from main_api_friendly import estimate_car_price, EstimationRequest, ResponseStatus
import os
import tempfile
from pathlib import Path

app = FastAPI(
    title="Car Repair Cost Estimator API",
    description="Estimate car repair costs using AI",
    version="1.0.0"
)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.post("/api/estimate")
async def estimate_repair_cost(
    image: UploadFile = File(...),
    description: str = Form(...),
    country: str = Form(default="Bangladesh")
):
    """
    Estimate car repair cost from image and description.
    
    **Request:**
    - image: Image file (required)
    - description: Description of damage (required)
    - country: Country name (optional, defaults to Bangladesh)
    
    **Response:**
    
    Success (200):
    ```json
    {
        "status": "success",
        "estimated_cost": 15000,
        "currency_country": "Bangladesh",
        "message": "Estimated repair cost in Bangladesh: 15000",
        "error_details": null
    }
    ```
    
    Validation Error (400):
    ```json
    {
        "status": "validation_error",
        "estimated_cost": null,
        "currency_country": null,
        "message": "Description cannot be empty",
        "error_details": "Description is required"
    }
    ```
    """
    
    try:
        # Validate image
        if not image.filename:
            raise HTTPException(
                status_code=400,
                detail="No image provided"
            )
        
        if not allowed_file(image.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Validate file size
        content = await image.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Validate description
        if not description or not description.strip():
            raise HTTPException(
                status_code=400,
                detail="Description cannot be empty"
            )
        
        # Save temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{image.filename.rsplit('.', 1)[1].lower()}"
        )
        temp_file.write(content)
        temp_file.close()
        temp_path = temp_file.name
        
        try:
            # Create estimation request
            request_obj = EstimationRequest(
                image_path=temp_path,
                description=description.strip(),
                country=country.strip() or "Bangladesh"
            )
            
            # Process estimation
            response = estimate_car_price(request_obj)
            
            # Return response with appropriate status code
            status_code = 200 if response.status == ResponseStatus.SUCCESS.value else 422
            return JSONResponse(
                status_code=status_code,
                content=response.to_dict()
            )
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "estimated_cost": None,
                "currency_country": None,
                "message": "Internal server error",
                "error_details": str(e)
            }
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Car Repair Cost Estimator API"
    }


@app.get("/docs")
async def swagger_docs():
    """Swagger documentation"""
    pass


if __name__ == "__main__":
    import uvicorn
    # For development: uvicorn api_example_fastapi:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
