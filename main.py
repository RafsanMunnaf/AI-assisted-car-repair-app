import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def encode_image(image_path: str) -> str:
    """Convert image to base64"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def estimate_car_price(image_path: str, description: str, country: str = "Bangladesh") -> str:
    """Estimate car repair cost using image and description"""
    
    # Convert image to base64
    base64_image = encode_image(image_path)
    
    # Create message for API
    messages = [     
        {
            "role": "system",
            "content": "You are a car repair cost estimator. Return ONLY a number."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Estimate car repair cost in {country}. Output ONLY a number."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                },
                   {"type": "text", "text": f"Damage: {description}"}
            ]
        }
    ]
    
    # Call API
    response = client.chat.completions.create(
        model="gpt-4o",  
        temperature=0.2,
        messages=messages
    )
    
    # Extract and parse result
    result = response.choices[0].message.content.strip()     
    
    try:
        
        cleaned = ''.join(c for c in result if c.isdigit() or c == '.') # Extract number from response
        return int(float(cleaned))
    except:
        return 0


if __name__ == "__main__":
    
    print("\n" + "="*50)
    print("Car Repair Cost Estimator")
    print("="*50 + "\n")
    
    img_path = input("Enter image path: ").strip()
    description = input("Enter damage description: ").strip()
    country = input("Enter country (default: Bangladesh): ").strip() or "Bangladesh"       
    
    # Check if file exists
    if not os.path.exists(img_path):
        print(f"Error: File not found - {img_path}")
    else:
        print("\nEstimating cost...")
        cost = estimate_car_price(img_path, description, country)
        print(f"\n✓ Estimated Repair Cost: {cost}")
        print(f"  Country: {country}")
        print("="*50 + "\n")
