"""
Car Repair Cost Estimator — TSRN Smart Repair Pricing
Uses GPT-4o as a damage classifier and applies the exact TSRN pricing formula locally.
"""

import os
import json
import base64
from dotenv import load_dotenv
from openai import OpenAI
from pricing_data import (
    PANEL_PRICES,
    PANEL_DISPLAY_NAMES,
    DAMAGE_SIZE_MULTIPLIERS,
    DAMAGE_SIZE_DISPLAY,
    DAMAGE_DEPTH_MULTIPLIERS,
    DAMAGE_DEPTH_DISPLAY,
    PANEL_COMPLEXITY_MULTIPLIERS,
    PANEL_COMPLEXITY_DISPLAY,
    PAINT_TYPE_MULTIPLIERS,
    PAINT_TYPE_DISPLAY,
    ELIGIBLE_FOR_SMART_REPAIR,
    NOT_ELIGIBLE_FOR_SMART_REPAIR,
    PDR_REQUIREMENTS,
)
from pricing_engine import (
    DamageClassification,
    calculate_repair_cost,
    format_pricing_breakdown,
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================
# CLASSIFIER SYSTEM PROMPT
# ============================================================

CLASSIFIER_SYSTEM_PROMPT = """You are a car damage classifier for the TSRN Smart Repair system.
Your job is to analyze car damage images and return ONLY a structured JSON classification.
Do NOT estimate prices — just classify the damage accurately.

You must return a JSON object with these exact fields:

{
  "panel": "<panel_key>",
  "damage_size": "<size_key>",
  "damage_depth": "<depth_key>",
  "panel_complexity": "<complexity_key>",
  "paint_type": "<paint_key>",
  "blending_panels": <0-3>,
  "num_damages": <integer>,
  "eligible_for_smart_repair": <true/false>,
  "pdr_eligible": <true/false>,
  "confidence": <0-100>,
  "notes": "<brief observations>"
}

VALID KEYS:

panel (choose one):
  front_bumper_corner, full_front_bumper, rear_bumper_corner, full_rear_bumper,
  front_wing, front_door, rear_door, rear_quarter_panel_4door, rear_quarter_panel_2door,
  sill_rail, roof, bonnet, alloy_wheel_painted, alloy_wheel_special,
  diamond_cut_wheel, pdr

damage_size (choose one):
  up_to_5cm, 5cm_to_15cm, 15cm_to_30cm, 30cm_to_50cm, over_50cm

damage_depth (choose one):
  surface_scratch, very_shallow_dent, moderate_dent, deep_dent, severe_dent

panel_complexity (choose one):
  flat_panel, curved_panel, bodyline_present, multiple_bodylines, complex_contour

paint_type (choose one):
  solid, metallic, pearlescent, tri_coat

ELIGIBILITY RULES:

Eligible for SMART repair:
- Localised cosmetic damage, scratches, scuffs, paint damage, dents
- Wheel kerb damage
- Paintless dent removal (PDR) where paint is not broken

NOT eligible for SMART repair:
- Structural damage
- Panel replacement required
- Large-scale lacquer peel
- Significant corrosion
- Extensive previous repair work
- Damage exceeding repair size limits

PDR RULES — PDR eligible ONLY when ALL true:
- Paint is intact (no cracking, no paint fracture, no exposed metal)
- No previous filler damage
- Dent depth is Very Shallow Dent
If paint damage is detected, set pdr_eligible to false.

BLENDING RULES:
- Set blending_panels to the number of adjacent panels that require colour blending
- Usually 0 for isolated damage, 1 for damage near a panel edge

CONFIDENCE:
- 95-100: High confidence in classification
- 80-94: Moderate confidence, some uncertainty
- Below 80: Low confidence, may need manual review

Return ONLY the JSON object. No explanation, no markdown."""


# ============================================================
# IMAGE ENCODING
# ============================================================

def encode_image(image_path: str) -> str:
    """Convert image to base64."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


# ============================================================
# DAMAGE CLASSIFICATION
# ============================================================

def classify_damage(image_paths: list, description: str) -> DamageClassification:
    """
    Send images to GPT-4o and get a structured damage classification.

    Args:
        image_paths: List of image file paths.
        description: User's text description of the damage.

    Returns:
        DamageClassification object.

    Raises:
        ValueError: If GPT returns invalid/unparseable JSON.
    """
    # Build the user message with all images
    content = [
        {
            "type": "text",
            "text": (
                f"Classify this car damage for SMART repair pricing.\n"
                f"User description: {description}\n"
                f"Return ONLY the JSON classification object."
            ),
        }
    ]

    for image_path in image_paths:
        base64_image = encode_image(image_path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
        })

    messages = [
        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.1,  # Low temperature for consistent classification
        messages=messages,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT returned invalid JSON: {raw[:200]}") from e

    # Map to DamageClassification dataclass
    try:
        classification = DamageClassification(
            panel=data["panel"],
            damage_size=data["damage_size"],
            damage_depth=data["damage_depth"],
            panel_complexity=data["panel_complexity"],
            paint_type=data["paint_type"],
            blending_panels=data.get("blending_panels", 0),
            num_damages=data.get("num_damages", 1),
            eligible_for_smart_repair=data.get("eligible_for_smart_repair", True),
            pdr_eligible=data.get("pdr_eligible", False),
            confidence=data.get("confidence", 90),
            notes=data.get("notes", ""),
        )
    except KeyError as e:
        raise ValueError(f"GPT response missing required field: {e}") from e

    return classification


# ============================================================
# MAIN ESTIMATION FLOW
# ============================================================

def estimate_car_repair(image_paths: list, description: str) -> dict:
    """
    Full pipeline: classify damage → calculate exact price.

    Args:
        image_paths: List of image file paths.
        description: User's text description of the damage.

    Returns:
        Dictionary with classification, pricing breakdown, and formatted output.
    """
    # Step 1: Classify the damage using GPT-4o
    classification = classify_damage(image_paths, description)

    # Step 2: Calculate exact price using the TSRN formula
    breakdown = calculate_repair_cost(classification)

    # Step 3: Format for display
    formatted = format_pricing_breakdown(breakdown)

    return {
        "classification": classification,
        "breakdown": breakdown,
        "formatted_output": formatted,
    }


# ============================================================
# CLI INTERFACE
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 55)
    print("  TSRN Smart Repair — Car Damage Estimator")
    print("=" * 55 + "\n")

    image_paths = []
    while True:
        img_path = input("Enter image path (or press Enter to finish): ").strip()
        if not img_path:
            break
        if os.path.exists(img_path):
            image_paths.append(img_path)
            print(f"✓ Added: {img_path}")
        else:
            print(f"Error: File not found - {img_path}")

    if not image_paths:
        print("Error: No valid images provided")
    else:
        description = input("Enter damage description: ").strip()

        print("\nAnalysing damage...")
        try:
            result = estimate_car_repair(image_paths, description)

            # Show classification details
            c = result["classification"]
            print(f"\n── AI Classification ──")
            print(f"  Panel:       {PANEL_DISPLAY_NAMES.get(c.panel, c.panel)}")
            print(f"  Size:        {DAMAGE_SIZE_DISPLAY.get(c.damage_size, c.damage_size)}")
            print(f"  Depth:       {DAMAGE_DEPTH_DISPLAY.get(c.damage_depth, c.damage_depth)}")
            print(f"  Complexity:  {PANEL_COMPLEXITY_DISPLAY.get(c.panel_complexity, c.panel_complexity)}")
            print(f"  Paint:       {PAINT_TYPE_DISPLAY.get(c.paint_type, c.paint_type)}")
            print(f"  Confidence:  {c.confidence}%")
            if c.notes:
                print(f"  Notes:       {c.notes}")

            # Show pricing
            print(f"\n{result['formatted_output']}")

        except ValueError as e:
            print(f"\n❌ Classification Error: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")

    print()
