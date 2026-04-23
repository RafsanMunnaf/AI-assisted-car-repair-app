# Car Repair Cost Estimator - Simple Version

## 📝 Quick Overview

This is a **simple, easy-to-understand** version of the car repair cost estimator.

## 🎯 What It Does

1. Takes a car damage image
2. Takes a description of the damage
3. Sends to OpenAI GPT-4o for analysis
4. Returns estimated repair cost

## 🚀 How to Use

### Running the CLI

```bash
python main.py
```

Then enter:
- **Image path**: Path to your car damage photo (e.g., `car_damage.jpg`)
- **Damage description**: What's wrong (e.g., `Front bumper dented`)
- **Country**: Where to estimate cost (defaults to Bangladesh)

### Using in Your Code

```python
from main import estimate_car_price

cost = estimate_car_price("car.jpg", "Bumper dent", "Bangladesh")
print(f"Estimated cost: {cost}")
```

## 📂 File Structure

- **`main.py`** - Simple version (easy to understand) ✨ **USE THIS**
- **`main_simple.py`** - Backup of simple version
- **`main_api_friendly.py`** - Complex, production version
- **`requirements.txt`** - Dependencies (python-dotenv, openai)

## 💻 Code Breakdown

### Main Function: `estimate_car_price()`

```python
def estimate_car_price(image_path: str, description: str, country: str = "Bangladesh") -> str:
    # 1. Convert image to base64
    base64_image = encode_image(image_path)
    
    # 2. Create API message
    messages = [...]
    
    # 3. Call OpenAI API
    response = client.chat.completions.create(...)
    
    # 4. Extract and parse number
    result = response.choices[0].message.content.strip()
    return int(float(cleaned))
```

That's it! No complex classes, no extensive validation - just the essentials.

## 🔧 Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run
python main.py
```

## 📊 Example

```
Input:
  Image: car_damage.jpg
  Description: Front bumper severely dented
  Country: Bangladesh

Output:
  ✓ Estimated Repair Cost: 15000
    Country: Bangladesh
```

## 🎓 Lines of Code Comparison

| Version | Lines | Complexity |
|---------|-------|-----------|
| Simple (main.py) | ~70 | ⭐ Easy |
| Complex (main_api_friendly.py) | ~450 | ⭐⭐⭐⭐⭐ Hard |

## ✨ Features

- ✅ Simple and easy to understand
- ✅ Works locally with CLI
- ✅ ~70 lines of code
- ✅ Proper error handling
- ✅ Can be used in other code
- ✅ Clear function names

## 🚫 What's Removed (From Complex Version)

- No logging framework
- No data validation
- No data models/classes
- No extensive error handling
- No API examples
- No documentation files

## 💡 To Use as API

Just import the function:

```python
# In your Flask/FastAPI app
from main import estimate_car_price

@app.post("/estimate")
def api_estimate():
    cost = estimate_car_price(image_path, description, country)
    return {"cost": cost}
```

## 🎯 Next Steps

1. Set `OPENAI_API_KEY` environment variable
2. Run `python main.py`
3. Test with a car damage image
4. Use the function in your project

---

**Version**: Simple ✨  
**Lines of Code**: ~70  
**Complexity**: Easy ⭐
