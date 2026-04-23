# Car Repair Cost Estimator - API-Friendly Implementation

## Overview

This is a **production-ready, backend-developer-friendly** implementation of the Car Repair Cost Estimator. It separates business logic from presentation logic, making it easy to integrate with any web framework or API platform.

## Files Included

### Core Logic
- **`main_api_friendly.py`** - Main business logic (use this for your API)
  - Core estimation function: `estimate_car_price(request)`
  - Request/Response data models
  - Validation and error handling
  - Proper logging and configuration

### API Examples
- **`api_example_flask.py`** - Flask REST API example
- **`api_example_fastapi.py`** - FastAPI REST API example

### Original Files
- **`main.py`** - CLI version (original code with new input handling)
- **`requirements.txt`** - Python dependencies

---

## Quick Start for Backend Developers

### 1. Use the Core Logic

Instead of calling functions directly, use the API-friendly interface:

```python
from main_api_friendly import estimate_car_price, EstimationRequest, ResponseStatus

# Create a request object
request = EstimationRequest(
    image_path="/path/to/image.jpg",
    description="Front bumper damaged",
    country="Bangladesh"
)

# Call the estimation function
response = estimate_car_price(request)

# Check response
if response.status == ResponseStatus.SUCCESS.value:
    print(f"Cost: {response.estimated_cost}")
else:
    print(f"Error: {response.error_details}")

# Convert to JSON
json_response = response.to_dict()
```

### 2. Flask Integration

```bash
pip install flask
python api_example_flask.py
```

Then POST to `http://localhost:5000/api/estimate`:

```bash
curl -X POST http://localhost:5000/api/estimate \
  -F "image=@car.jpg" \
  -F "description=Front bumper damaged" \
  -F "country=Bangladesh"
```

### 3. FastAPI Integration

```bash
pip install fastapi uvicorn
uvicorn api_example_fastapi:app --reload
```

Then POST to `http://localhost:8000/api/estimate`:

```bash
curl -X POST http://localhost:8000/api/estimate \
  -F "image=@car.jpg" \
  -F "description=Front bumper damaged" \
  -F "country=Bangladesh"
```

---

## Architecture & Key Features

### Data Models (Type-Safe)

```python
# Input Model
EstimationRequest:
  - image_path: str (required)
  - description: str (required)
  - country: str (default: "Bangladesh")

# Output Model
EstimationResponse:
  - status: str ("success" | "error" | "validation_error")
  - estimated_cost: Optional[int]
  - currency_country: Optional[str]
  - message: Optional[str]
  - error_details: Optional[str]
  - to_dict() -> Dict # For JSON serialization
```

### Configuration Management

All configuration in one place:

```python
class Config:
    MODEL = "gpt-4o"
    TEMPERATURE = 0.2
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
    TIMEOUT = 30
    DEFAULT_COUNTRY = "Bangladesh"
```

### Error Handling

Three response status types:
- **success** - Estimation completed successfully
- **validation_error** - Input validation failed (400 status)
- **error** - Processing failed (422 or 500 status)

All errors include detailed error_details field.

### Logging

Comprehensive logging at all levels:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing estimation request")
logger.warning("Image validation failed")
logger.error("API call failed")
```

### Validation

Automatic validation of:
- Image file existence and size
- Description length and content
- Country name validity

---

## Integration with Different Frameworks

### Django

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from main_api_friendly import estimate_car_price, EstimationRequest

@require_http_methods(["POST"])
def estimate_view(request):
    image_file = request.FILES.get('image')
    description = request.POST.get('description')
    country = request.POST.get('country', 'Bangladesh')
    
    # Save image temporarily
    temp_path = save_uploaded_file(image_file)
    
    try:
        req = EstimationRequest(temp_path, description, country)
        response = estimate_car_price(req)
        return JsonResponse(response.to_dict())
    finally:
        os.remove(temp_path)
```

### AWS Lambda

```python
from main_api_friendly import estimate_car_price, EstimationRequest

def lambda_handler(event, context):
    image_base64 = event['image']
    description = event['description']
    country = event.get('country', 'Bangladesh')
    
    # Decode and save image
    import base64
    image_data = base64.b64decode(image_base64)
    temp_path = '/tmp/image.jpg'
    with open(temp_path, 'wb') as f:
        f.write(image_data)
    
    req = EstimationRequest(temp_path, description, country)
    response = estimate_car_price(req)
    
    return {
        'statusCode': 200,
        'body': response.to_dict()
    }
```

### Docker

```dockerfile
FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "api_example_fastapi:app", "--host", "0.0.0.0"]
```

---

## Response Examples

### Success Response

```json
{
    "status": "success",
    "estimated_cost": 15000,
    "currency_country": "Bangladesh",
    "message": "Estimated repair cost in Bangladesh: 15000",
    "error_details": null
}
```

### Validation Error Response

```json
{
    "status": "validation_error",
    "estimated_cost": null,
    "currency_country": null,
    "message": null,
    "error_details": "Image file not found: /path/to/missing.jpg"
}
```

### API Error Response

```json
{
    "status": "error",
    "estimated_cost": null,
    "currency_country": null,
    "message": "Failed to estimate repair cost",
    "error_details": "API rate limit exceeded. Please try again later."
}
```

---

## Testing

### Unit Test Example

```python
import pytest
from main_api_friendly import estimate_car_price, EstimationRequest, ResponseStatus

def test_validation_error():
    request = EstimationRequest(
        image_path="/nonexistent/path.jpg",
        description="Test damage",
        country="Bangladesh"
    )
    response = estimate_car_price(request)
    assert response.status == ResponseStatus.VALIDATION_ERROR.value
    assert response.error_details is not None

def test_success_response():
    request = EstimationRequest(
        image_path="./test_image.jpg",
        description="Minor scratch",
        country="Bangladesh"
    )
    response = estimate_car_price(request)
    assert response.status == ResponseStatus.SUCCESS.value
    assert response.estimated_cost is not None
```

---

## Configuration

Set environment variables:

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Optional (edit Config class if needed)
# MAX_IMAGE_SIZE, TIMEOUT, DEFAULT_COUNTRY, etc.
```

---

## Performance Considerations

1. **Image Encoding**: Images are converted to base64 for API transmission
2. **File Size Limit**: 20MB max by default (configurable)
3. **Timeout**: 30 seconds per request (configurable)
4. **Async Support**: Use FastAPI example for high concurrency

---

## Security Note

- Never expose `OPENAI_API_KEY` in frontend code
- Always validate file uploads on server
- Implement rate limiting on production endpoints
- Use HTTPS in production
- Implement authentication/authorization for your API

---

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify environment variables are set correctly
3. Test with the included Flask/FastAPI examples
4. Review the data model definitions

