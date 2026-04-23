# Development Guide - Code Structure & Best Practices

## Project Structure

```
jake/
├── main.py                          # CLI version (original with input handling)
├── main_api_friendly.py             # ⭐ Main business logic (use this for APIs)
├── api_example_flask.py             # Flask REST API implementation example
├── api_example_fastapi.py           # FastAPI REST API implementation example
├── requirements.txt                 # Core dependencies
├── requirements_api.txt             # Optional API framework dependencies
├── .venv/                           # Python virtual environment
├── API_README.md                    # API integration guide
└── DEVELOPMENT.md                   # This file
```

---

## Code Organization

### Layer 1: Configuration & Models
```
ConfigManager
├── Config class (single source of truth)
│   ├── Model settings
│   ├── API parameters
│   └── Limits and timeouts
└── Data Models (Pydantic-like)
    ├── EstimationRequest (input)
    ├── EstimationResponse (output)
    └── ResponseStatus (enum)
```

### Layer 2: Utilities & Validation
```
Validation Layer
├── validate_image_file()
├── validate_description()
├── validate_country()
└── encode_image()

Helper Functions
├── parse_cost_response()
└── build_messages()
```

### Layer 3: API Communication
```
OpenAI Layer
├── get_estimate()               # Direct API call
└── Error handling
    ├── RateLimitError
    ├── APIConnectionError
    └── APIError
```

### Layer 4: Business Logic
```
Core Function
└── estimate_car_price(request: EstimationRequest) -> EstimationResponse
    ├── Input validation
    ├── API communication
    ├── Response parsing
    └── Error handling
```

### Layer 5: Interface
```
CLI Interface (main_api_friendly.py)
└── cli_interface()

REST API (api_example_*.py)
├── /api/estimate (POST)
├── /api/health (GET)
└── Error handlers
```

---

## Key Design Principles

### 1. Separation of Concerns
Each function has a single responsibility:
- `validate_*` - Input validation only
- `encode_image` - File encoding only
- `get_estimate` - API communication only
- `parse_cost_response` - Response parsing only
- `estimate_car_price` - Orchestration/business logic

### 2. Type Safety
```python
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class EstimationRequest:
    image_path: str
    description: str
    country: str = "Bangladesh"
```

### 3. Configuration Management
All settings in one place - no magic numbers:
```python
class Config:
    MODEL = "gpt-4o"
    TEMPERATURE = 0.2
    MAX_IMAGE_SIZE = 20 * 1024 * 1024
```

### 4. Explicit Error Handling
```python
try:
    # operation
except SpecificError as e:
    logger.error(f"Specific error: {e}")
    raise SpecificError(...) from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### 5. Logging at Every Layer
```python
logger = logging.getLogger(__name__)
logger.info("Processing started")
logger.warning("Validation failed")
logger.error("Critical error occurred")
logger.debug("Detailed debug info")
```

---

## Data Flow

```
CLIENT REQUEST
    ↓
[API Endpoint]
    ↓
[Input Validation Layer]
    ├─ validate_image_file()
    ├─ validate_description()
    └─ validate_country()
    ↓
[Core Business Logic]
    ├─ estimate_car_price()
    ├─ get_estimate()
    └─ parse_cost_response()
    ↓
[Response Formatting]
    └─ EstimationResponse.to_dict()
    ↓
[API Response]
    ↓
CLIENT RECEIVES RESPONSE
```

---

## Error Handling Strategy

### Validation Errors (400)
```python
# User provided invalid input
return EstimationResponse(
    status=ResponseStatus.VALIDATION_ERROR.value,
    error_details="Image file not found"
)
```

### Processing Errors (422)
```python
# Valid input but processing failed
return EstimationResponse(
    status=ResponseStatus.ERROR.value,
    message="Could not parse repair cost",
    error_details=api_response_text
)
```

### Server Errors (500)
```python
# Unexpected system error
return EstimationResponse(
    status=ResponseStatus.ERROR.value,
    message="Failed to estimate repair cost",
    error_details=str(exception)
)
```

---

## Adding New Features

### Example: Add country-specific multipliers

**Step 1:** Add to Config
```python
class Config:
    COUNTRY_MULTIPLIERS = {
        "Bangladesh": 1.0,
        "USA": 2.5,
        "UK": 2.3,
    }
```

**Step 2:** Update parsing logic
```python
def parse_cost_response(response: str, country: str) -> Optional[int]:
    base_cost = int(float(cleaned))
    multiplier = Config.COUNTRY_MULTIPLIERS.get(country, 1.0)
    return int(base_cost * multiplier)
```

**Step 3:** Update estimate_car_price()
```python
cost = parse_cost_response(result, request.country)
```

**Step 4:** Test
```python
def test_country_multiplier():
    request = EstimationRequest(..., country="USA")
    response = estimate_car_price(request)
    assert response.estimated_cost > 0  # Should be 2.5x Bangladesh
```

---

## Best Practices for Backend Developers

### ✅ DO

1. **Always use EstimationRequest and EstimationResponse**
   ```python
   request = EstimationRequest(image_path, description, country)
   response = estimate_car_price(request)
   ```

2. **Check response status before accessing data**
   ```python
   if response.status == ResponseStatus.SUCCESS.value:
       cost = response.estimated_cost
   ```

3. **Log important operations**
   ```python
   logger.info(f"Processing estimate for {request.country}")
   ```

4. **Use Config class for settings**
   ```python
   timeout = Config.TIMEOUT
   ```

5. **Handle all exception types**
   ```python
   except RateLimitError:
       # Handle rate limit
   except APIError:
       # Handle API error
   ```

### ❌ DON'T

1. **Don't pass raw arguments**
   ```python
   # Bad
   response = estimate_car_price(path, desc, country)
   
   # Good
   request = EstimationRequest(path, desc, country)
   response = estimate_car_price(request)
   ```

2. **Don't ignore error_details**
   ```python
   # Bad
   if response.status != "success":
       return "Error"
   
   # Good
   if response.status != "success":
       return response.error_details
   ```

3. **Don't hardcode configuration**
   ```python
   # Bad
   if file_size > 20971520:  # What's this number?
   
   # Good
   if file_size > Config.MAX_IMAGE_SIZE:
   ```

4. **Don't suppress exceptions**
   ```python
   # Bad
   except Exception:
       pass
   
   # Good
   except Exception as e:
       logger.error(f"Error: {e}")
       raise
   ```

---

## Performance Tips

### 1. Image Optimization
- Compress images before sending (if possible)
- Use appropriate image format (JPEG for quality photos)
- Resize large images before uploading

### 2. Caching
```python
@functools.lru_cache(maxsize=100)
def get_cached_estimate(image_hash: str) -> int:
    """Cache estimates for same image"""
    pass
```

### 3. Async Operations
```python
import asyncio

async def estimate_multiple(requests: List[EstimationRequest]):
    tasks = [
        asyncio.to_thread(estimate_car_price, req)
        for req in requests
    ]
    return await asyncio.gather(*tasks)
```

### 4. Batch Processing
```python
def batch_estimate(requests: List[EstimationRequest]):
    """Process multiple requests efficiently"""
    results = []
    for request in requests:
        response = estimate_car_price(request)
        results.append(response)
    return results
```

---

## Testing

### Unit Tests
```python
def test_validate_image_file():
    assert validate_image_file("") == "Image path cannot be empty"
    assert validate_image_file("/missing.jpg") == "Image file not found: ..."
    assert validate_image_file("/valid.jpg") is None

def test_parse_cost_response():
    assert parse_cost_response("15000") == 15000
    assert parse_cost_response("15000.50") == 15000
    assert parse_cost_response("invalid") is None
```

### Integration Tests
```python
def test_estimate_car_price_end_to_end():
    request = EstimationRequest(
        image_path="./test_image.jpg",
        description="Minor scratch",
        country="Bangladesh"
    )
    response = estimate_car_price(request)
    assert response.status == ResponseStatus.SUCCESS.value
    assert response.estimated_cost > 0
```

### API Tests
```python
def test_flask_api_estimate():
    response = client.post(
        '/api/estimate',
        data={
            'description': 'Test damage',
            'country': 'Bangladesh'
        },
        files={'image': open('test.jpg', 'rb')}
    )
    assert response.status_code == 200
    assert response.json['status'] == 'success'
```

---

## Deployment

### Development
```bash
python main_api_friendly.py  # CLI
```

### Production (Flask)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_example_flask:app
```

### Production (FastAPI)
```bash
pip install uvicorn
uvicorn api_example_fastapi:app --host 0.0.0.0 --workers 4
```

### Docker
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api_example_fastapi:app", "--host", "0.0.0.0"]
```

---

## Troubleshooting

### Common Issues

**Issue: "OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY="your-key-here"
# Or in Windows
set OPENAI_API_KEY=your-key-here
```

**Issue: "Image file not found"**
- Ensure absolute path is used
- Check file permissions
- Verify file exists

**Issue: "Rate limit exceeded"**
- Implement retry logic with exponential backoff
- Add request queuing

**Issue: "Timeout"**
- Image might be too large
- Network connection slow
- Increase Config.TIMEOUT

---

## Contributing

When adding new features:
1. Follow the existing code structure
2. Add type hints
3. Add logging statements
4. Add unit tests
5. Update documentation
6. Update CHANGELOG

