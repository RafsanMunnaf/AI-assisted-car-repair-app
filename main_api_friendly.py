"""
Car Repair Cost Estimator - API-Friendly Implementation
Production-ready code with proper error handling, logging, and validation
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError

# ========================
# CONFIGURATION
# ========================

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """API and application configuration"""
    MODEL = "gpt-4o"
    TEMPERATURE = 0.2
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
    TIMEOUT = 30
    DEFAULT_COUNTRY = "Bangladesh"


class ResponseStatus(Enum):
    """Response status enumeration"""
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"


# ========================
# DATA MODELS
# ========================

@dataclass
class EstimationRequest:
    """API Request model for car repair estimation"""
    image_path: str
    description: str
    country: str = Config.DEFAULT_COUNTRY


@dataclass
class EstimationResponse:
    """API Response model for car repair estimation"""
    status: str
    estimated_cost: Optional[int] = None
    currency_country: Optional[str] = None
    message: Optional[str] = None
    error_details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization"""
        return {
            "status": self.status,
            "estimated_cost": self.estimated_cost,
            "currency_country": self.currency_country,
            "message": self.message,
            "error_details": self.error_details
        }


# ========================
# INITIALIZATION
# ========================

# Initialize OpenAI client
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None


# ========================
# VALIDATION & UTILITIES
# ========================

def validate_image_file(image_path: str) -> Optional[str]:
    """
    Validate image file exists and is within size limits.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Error message if invalid, None if valid
    """
    if not image_path or not image_path.strip():
        return "Image path cannot be empty"
    
    if not os.path.exists(image_path):
        return f"Image file not found: {image_path}"
    
    if not os.path.isfile(image_path):
        return f"Path is not a file: {image_path}"
    
    file_size = os.path.getsize(image_path)
    if file_size > Config.MAX_IMAGE_SIZE:
        return f"Image too large. Max size: {Config.MAX_IMAGE_SIZE / 1024 / 1024}MB, Got: {file_size / 1024 / 1024:.2f}MB"
    
    if file_size == 0:
        return "Image file is empty"
    
    return None


def validate_description(description: str) -> Optional[str]:
    """
    Validate description string.
    
    Args:
        description: Description of damage
        
    Returns:
        Error message if invalid, None if valid
    """
    if not description or not description.strip():
        return "Description cannot be empty"
    
    if len(description) > 1000:
        return "Description too long (max 1000 characters)"
    
    return None


def validate_country(country: str) -> Optional[str]:
    """
    Validate country string.
    
    Args:
        country: Country name
        
    Returns:
        Error message if invalid, None if valid
    """
    if not country or not country.strip():
        return "Country cannot be empty"
    
    if len(country) > 100:
        return "Country name too long"
    
    return None


def encode_image(image_path: str) -> str:
    """
    Convert image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
        
    Raises:
        FileNotFoundError: If image file doesn't exist
        IOError: If file cannot be read
    """
    logger.info(f"Encoding image: {image_path}")
    try:
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode("utf-8")
            logger.debug(f"Image encoded successfully, size: {len(encoded)} bytes")
            return encoded
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        raise
    except IOError as e:
        logger.error(f"Failed to read image file: {e}")
        raise


# ========================
# MESSAGE BUILDING
# ========================

def build_messages(image_path: str, description: str, country: str = Config.DEFAULT_COUNTRY) -> list:
    """
    Build message payload for OpenAI API.
    
    Args:
        image_path: Path to the image file
        description: Description of car damage
        country: Country for cost estimation
        
    Returns:
        List of message dictionaries for OpenAI API
    """
    base64_image = encode_image(image_path)

    prompt = f"""
Estimate total car repair cost in {country}.

Rules:
- Output ONLY a number (no words, no currency symbol)
- This number is total estimated repair cost in local currency
- Use both image and description together
- Be realistic and consistent
- Assume standard sedan car (Toyota/Honda level)
"""
    
    return [
        {
            "role": "system",
            "content": "You are a highly accurate car repair cost estimator. Analyze the damage and provide ONLY a single number representing the estimated repair cost."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                },
                {"type": "text", "text": f"User description: {description}"}
            ]
        }
    ]


# ========================
# API CALLS & PROCESSING
# ========================

def get_estimate(image_path: str, description: str, country: str = Config.DEFAULT_COUNTRY) -> str:
    """
    Call OpenAI API to get repair cost estimate.
    
    Args:
        image_path: Path to the image file
        description: Description of car damage
        country: Country for cost estimation
        
    Returns:
        Raw response content from OpenAI
        
    Raises:
        APIError: If API call fails
    """
    if not client:
        raise RuntimeError("OpenAI client not initialized")
    
    logger.info(f"Requesting estimate for {country}")
    
    try:
        messages = build_messages(image_path, description, country)
        
        response = client.chat.completions.create(
            model=Config.MODEL,
            temperature=Config.TEMPERATURE,
            messages=messages,
            timeout=Config.TIMEOUT
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"API response received: {result}")
        return result
        
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        raise APIError(f"API rate limit exceeded. Please try again later.") from e
    except APIConnectionError as e:
        logger.error(f"API connection error: {e}")
        raise APIError(f"Failed to connect to API. Please check your connection.") from e
    except APIError as e:
        logger.error(f"API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during API call: {e}")
        raise APIError(f"Unexpected error during estimation: {str(e)}") from e


# ========================
# CORE BUSINESS LOGIC
# ========================

def parse_cost_response(response: str) -> Optional[int]:
    """
    Parse and validate the cost response from API.
    
    Args:
        response: Raw response text from OpenAI
        
    Returns:
        Integer cost value, or None if parsing fails
    """
    try:
        # Remove any non-numeric characters except decimal point
        cleaned = ''.join(c for c in response if c.isdigit() or c == '.')
        
        if not cleaned:
            logger.warning(f"Could not extract number from response: {response}")
            return None
        
        cost = int(float(cleaned))
        
        if cost < 0:
            logger.warning(f"Negative cost received: {cost}")
            return None
        
        return cost
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse cost from response '{response}': {e}")
        return None


def estimate_car_price(request: EstimationRequest) -> EstimationResponse:
    """
    Core function to estimate car repair price.
    This is the main API endpoint logic.
    
    Args:
        request: EstimationRequest object with image_path, description, country
        
    Returns:
        EstimationResponse with result or error details
    """
    logger.info(f"Processing estimation request for {request.country}")
    
    # Validate inputs
    image_error = validate_image_file(request.image_path)
    if image_error:
        logger.warning(f"Image validation failed: {image_error}")
        return EstimationResponse(
            status=ResponseStatus.VALIDATION_ERROR.value,
            error_details=image_error
        )
    
    desc_error = validate_description(request.description)
    if desc_error:
        logger.warning(f"Description validation failed: {desc_error}")
        return EstimationResponse(
            status=ResponseStatus.VALIDATION_ERROR.value,
            error_details=desc_error
        )
    
    country_error = validate_country(request.country)
    if country_error:
        logger.warning(f"Country validation failed: {country_error}")
        return EstimationResponse(
            status=ResponseStatus.VALIDATION_ERROR.value,
            error_details=country_error
        )
    
    # Process estimation
    try:
        result = get_estimate(request.image_path, request.description, request.country)
        cost = parse_cost_response(result)
        
        if cost is None:
            logger.error(f"Could not parse cost from API response")
            return EstimationResponse(
                status=ResponseStatus.ERROR.value,
                message="Could not parse repair cost from AI response",
                error_details=result
            )
        
        logger.info(f"Estimation successful: {cost}")
        return EstimationResponse(
            status=ResponseStatus.SUCCESS.value,
            estimated_cost=cost,
            currency_country=request.country,
            message=f"Estimated repair cost in {request.country}: {cost}"
        )
        
    except Exception as e:
        logger.error(f"Estimation failed: {e}")
        return EstimationResponse(
            status=ResponseStatus.ERROR.value,
            message="Failed to estimate repair cost",
            error_details=str(e)
        )


# ========================
# CLI INTERFACE
# ========================

def cli_interface():
    """
    Command-line interface for manual testing and debugging.
    This uses the core API logic for testing purposes.
    """
    print("\n" + "="*50)
    print("Car Repair Cost Estimator")
    print("="*50 + "\n")
    
    try:
        img_path = input("Enter the path to the car image: ").strip()
        desc = input("Enter a description of the damage: ").strip()
        loc = input("Enter the country (default: Bangladesh): ").strip() or Config.DEFAULT_COUNTRY

        # Create request
        request = EstimationRequest(
            image_path=img_path,
            description=desc,
            country=loc
        )
        
        print("\nEstimating repair cost...")
        response = estimate_car_price(request)
        
        print("\n" + "="*50)
        print(f"Status: {response.status}")
        
        if response.status == ResponseStatus.SUCCESS.value:
            print(f"Estimated Cost: {response.estimated_cost}")
            print(f"Country: {response.currency_country}")
            print(f"Message: {response.message}")
        else:
            print(f"Error: {response.error_details or response.message}")
        print("="*50 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        logger.info("CLI operation cancelled")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.error(f"CLI error: {e}")


if __name__ == "__main__":
    cli_interface()
