"""
TSRN Smart Repair — Unified Estimation & Chatbot Engine
Combines:
  1. Pricing Matrix Data Tables
  2. Pricing Calculation Logic
  3. Image Analysis / Damage Classifier
  4. Conversational Chatbot

Dependencies:
  pip install openai python-dotenv
"""

import os
import json
import base64
import uuid
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# ============================================================
# SECTION 1: PRICING MATRIX DATA (Official TSRN Tables)
# ============================================================

PANEL_PRICES = {
    "front_bumper_corner": {"base_price": 280, "minimum_charge": 265},
    "full_front_bumper":   {"base_price": 450, "minimum_charge": 400},
    "rear_bumper_corner":  {"base_price": 280, "minimum_charge": 265},
    "full_rear_bumper":    {"base_price": 450, "minimum_charge": 400},
    "front_wing":          {"base_price": 195, "minimum_charge": 185},
    "front_door":          {"base_price": 265, "minimum_charge": 250},
    "rear_door":           {"base_price": 265, "minimum_charge": 250},
    "rear_quarter_panel_4door": {"base_price": 230, "minimum_charge": 210},
    "rear_quarter_panel_2door": {"base_price": 290, "minimum_charge": 270},
    "sill_rail":           {"base_price": 220, "minimum_charge": 210},
    "roof":                {"base_price": 460, "minimum_charge": 450},
    "bonnet":              {"base_price": 460, "minimum_charge": 450},
    "alloy_wheel_painted": {"base_price": 80,  "minimum_charge": 70},
    "alloy_wheel_special": {"base_price": 150, "minimum_charge": 150},
    "diamond_cut_wheel":   {"base_price": 95,  "minimum_charge": 85},
    "pdr":                 {"base_price": 120, "minimum_charge": 100},
}

PANEL_DISPLAY_NAMES = {
    "front_bumper_corner": "Front Bumper (Corner)",
    "full_front_bumper":   "Full Front Bumper",
    "rear_bumper_corner":  "Rear Bumper (Corner)",
    "full_rear_bumper":    "Full Rear Bumper",
    "front_wing":          "Front Wing",
    "front_door":          "Front Door",
    "rear_door":           "Rear Door",
    "rear_quarter_panel_4door": "Rear Quarter Panel (4-Door Vehicle)",
    "rear_quarter_panel_2door": "Rear Quarter Panel (2-Door Vehicle)",
    "sill_rail":           "Sill / Rail",
    "roof":                "Roof",
    "bonnet":              "Bonnet",
    "alloy_wheel_painted": "Alloy Wheel Refurbishment (Painted)",
    "alloy_wheel_special": "Alloy Wheel Refurbishment (Special Finish)",
    "diamond_cut_wheel":   "Diamond Cut Wheel Refurbishment",
    "pdr":                 "Paintless Dent Repair (PDR)",
}

DAMAGE_SIZE_MULTIPLIERS = {
    "up_to_5cm":   1.0,   # "0" in PDF indicates no extra charge
    "5cm_to_15cm": 1.10,
    "15cm_to_30cm": 1.50,
    "30cm_to_50cm": 2.00,
    "over_50cm":   None,  # Triggers manual review
}

DAMAGE_SIZE_DISPLAY = {
    "up_to_5cm":    "Up to 5cm",
    "5cm_to_15cm":  "5cm – 15cm",
    "15cm_to_30cm": "15cm – 30cm",
    "30cm_to_50cm": "30cm – 50cm",
    "over_50cm":    "Over 50cm (Manual Review)",
}

DAMAGE_DEPTH_MULTIPLIERS = {
    "surface_scratch":   1.0,
    "very_shallow_dent": 1.15,
    "moderate_dent":     1.50,
    "deep_dent":         1.80,
    "severe_dent":       None,  # Triggers manual review
}

DAMAGE_DEPTH_DISPLAY = {
    "surface_scratch":   "Surface Scratch / Scuff Only",
    "very_shallow_dent": "Very Shallow Dent (Minimal Filler)",
    "moderate_dent":     "Moderate Dent (Light Filler)",
    "deep_dent":         "Deep Dent (Moderate Filler)",
    "severe_dent":       "Severe Dent (Manual Review)",
}

PANEL_COMPLEXITY_MULTIPLIERS = {
    "flat_panel":         1.0,
    "curved_panel":       1.05,
    "bodyline_present":   1.10,
    "multiple_bodylines": 1.30,
    "complex_contour":    1.40,
}

PANEL_COMPLEXITY_DISPLAY = {
    "flat_panel":         "Flat Panel",
    "curved_panel":       "Curved Panel",
    "bodyline_present":   "Bodyline Present",
    "multiple_bodylines": "Multiple Bodylines",
    "complex_contour":    "Complex Contour",
}

PAINT_TYPE_MULTIPLIERS = {
    "solid":       1.0,
    "metallic":    1.20,
    "pearlescent": 1.50,
    "tri_coat":    1.50,
}

PAINT_TYPE_DISPLAY = {
    "solid":       "Solid Colour",
    "metallic":    "Metallic",
    "pearlescent": "Pearlescent",
    "tri_coat":    "Tri-Coat Pearl",
}

BLENDING_CHARGES = {
    0: 0,
    1: 180,
    2: 350,
    3: 500,
}

MULTIPLE_DAMAGE_MULTIPLIERS = {
    1: 1.0,
    2: 1.05,
    3: 1.10,
}

ELIGIBLE_FOR_SMART_REPAIR = [
    "Localised cosmetic damage",
    "Localised scratches",
    "Localised scuffs",
    "Localised paint damage",
    "Localised dents",
    "Wheel kerb damage",
    "Paintless dent removal (PDR) where paint is not broken",
]

NOT_ELIGIBLE_FOR_SMART_REPAIR = [
    "Structural damage",
    "Panel replacement required",
    "Large-scale lacquer peel",
    "Significant corrosion",
    "Extensive previous repair work",
    "Damage exceeding repair size limits",
]

PDR_REQUIREMENTS = [
    "Paint is intact",
    "No cracking",
    "No paint fracture",
    "No exposed metal",
    "No previous filler damage",
    "Dent depth is classified as Very Shallow Dent",
]

CONFIDENCE_THRESHOLDS = {
    "generate_estimate":    95,
    "flag_for_review":      80,
}


# ============================================================
# SECTION 2: DATACLASSES & PRICING ENGINE CALCULATIONS
# ============================================================

@dataclass
class DamageClassification:
    """Structured output expected from GPT-4o damage classifier."""
    panel: str                          # Key from PANEL_PRICES
    damage_size: str                    # Key from DAMAGE_SIZE_MULTIPLIERS
    damage_depth: str                   # Key from DAMAGE_DEPTH_MULTIPLIERS
    panel_complexity: str               # Key from PANEL_COMPLEXITY_MULTIPLIERS
    paint_type: str                     # Key from PAINT_TYPE_MULTIPLIERS
    blending_panels: int = 0            # Number of adjacent panels needing blend (0-3)
    num_damages: int = 1                # Total number of separate damages
    eligible_for_smart_repair: bool = True
    pdr_eligible: bool = False
    confidence: int = 95                # AI confidence percentage
    notes: str = ""                     # Any additional observations


@dataclass
class PricingBreakdown:
    """Detailed pricing breakdown returned to the user."""
    panel_name: str
    base_price: float
    damage_size_label: str
    damage_size_multiplier: float
    damage_depth_label: str
    damage_depth_multiplier: float
    panel_complexity_label: str
    panel_complexity_multiplier: float
    paint_type_label: str
    paint_type_multiplier: float
    subtotal_before_extras: float
    blending_panels: int
    blending_charge: float
    minimum_charge: float
    price_before_multi_damage: float
    num_damages: int
    multiple_damage_multiplier: float
    final_price: float
    confidence: int
    needs_review: bool
    manual_review_required: bool
    review_reasons: List[str] = field(default_factory=list)
    notes: str = ""


def validate_classification(classification: DamageClassification) -> List[str]:
    """Validate that all classification fields map to known lookup keys."""
    errors = []

    if classification.panel not in PANEL_PRICES:
        errors.append(f"Unknown panel '{classification.panel}'. Valid: {list(PANEL_PRICES.keys())}")

    if classification.damage_size not in DAMAGE_SIZE_MULTIPLIERS:
        errors.append(f"Unknown damage_size '{classification.damage_size}'. Valid: {list(DAMAGE_SIZE_MULTIPLIERS.keys())}")

    if classification.damage_depth not in DAMAGE_DEPTH_MULTIPLIERS:
        errors.append(f"Unknown damage_depth '{classification.damage_depth}'. Valid: {list(DAMAGE_DEPTH_MULTIPLIERS.keys())}")

    if classification.panel_complexity not in PANEL_COMPLEXITY_MULTIPLIERS:
        errors.append(f"Unknown panel_complexity '{classification.panel_complexity}'. Valid: {list(PANEL_COMPLEXITY_MULTIPLIERS.keys())}")

    if classification.paint_type not in PAINT_TYPE_MULTIPLIERS:
        errors.append(f"Unknown paint_type '{classification.paint_type}'. Valid: {list(PAINT_TYPE_MULTIPLIERS.keys())}")

    if not (0 <= classification.blending_panels <= 3):
        errors.append(f"blending_panels must be 0-3, got {classification.blending_panels}")

    if classification.num_damages < 1:
        errors.append(f"num_damages must be >= 1, got {classification.num_damages}")

    if not (0 <= classification.confidence <= 100):
        errors.append(f"confidence must be 0-100, got {classification.confidence}")

    return errors


def calculate_repair_cost(classification: DamageClassification) -> PricingBreakdown:
    """
    Calculate the exact repair cost using the TSRN pricing formula.
    
    Formula:
      subtotal = Base Price × Size × Depth × Complexity × Paint
      price    = max(subtotal, Minimum Charge) + Blending
      final    = price × Multiple Damage Multiplier
    """
    # Validate
    errors = validate_classification(classification)
    if errors:
        raise ValueError(f"Invalid classification: {'; '.join(errors)}")

    # Check for manual review triggers
    review_reasons = []
    manual_review_required = False

    size_mult = DAMAGE_SIZE_MULTIPLIERS[classification.damage_size]
    depth_mult = DAMAGE_DEPTH_MULTIPLIERS[classification.damage_depth]

    if size_mult is None:
        review_reasons.append("Damage size exceeds 50cm — requires manual review")
        manual_review_required = True
        size_mult = 1.0

    if depth_mult is None:
        review_reasons.append("Severe dent — requires manual review or bodyshop assessment")
        manual_review_required = True
        depth_mult = 1.0

    if classification.confidence < CONFIDENCE_THRESHOLDS["flag_for_review"]:
        review_reasons.append(f"AI confidence is {classification.confidence}% (below 80%) — manual review required")
        manual_review_required = True

    if not classification.eligible_for_smart_repair:
        review_reasons.append("Damage is NOT eligible for SMART repair")
        manual_review_required = True

    # Flag for review (not blocking) when confidence is 80-94%
    needs_review = False
    if CONFIDENCE_THRESHOLDS["flag_for_review"] <= classification.confidence < CONFIDENCE_THRESHOLDS["generate_estimate"]:
        needs_review = True
        review_reasons.append(f"AI confidence is {classification.confidence}% — estimate generated but flagged for review")

    # Look up values
    panel_data = PANEL_PRICES[classification.panel]
    base_price = panel_data["base_price"]
    minimum_charge = panel_data["minimum_charge"]

    complexity_mult = PANEL_COMPLEXITY_MULTIPLIERS[classification.panel_complexity]
    paint_mult = PAINT_TYPE_MULTIPLIERS[classification.paint_type]

    blending_charge = BLENDING_CHARGES.get(classification.blending_panels, 0)

    # Multiple damage multiplier
    if classification.num_damages >= 4:
        multi_damage_mult = 1.50
    else:
        multi_damage_mult = MULTIPLE_DAMAGE_MULTIPLIERS.get(classification.num_damages, 1.0)

    # PDR override: If PDR eligible, use PDR base pricing
    if classification.pdr_eligible and classification.panel != "pdr":
        panel_data = PANEL_PRICES["pdr"]
        base_price = panel_data["base_price"]
        minimum_charge = panel_data["minimum_charge"]

    # Calculate
    subtotal = base_price * size_mult * depth_mult * complexity_mult * paint_mult
    price_before_blend = max(subtotal, minimum_charge)
    price_before_multi = price_before_blend + blending_charge
    final_price = price_before_multi * multi_damage_mult
    final_price = round(final_price, 2)

    return PricingBreakdown(
        panel_name=PANEL_DISPLAY_NAMES.get(classification.panel, classification.panel),
        base_price=base_price,
        damage_size_label=DAMAGE_SIZE_DISPLAY.get(classification.damage_size, classification.damage_size),
        damage_size_multiplier=size_mult,
        damage_depth_label=DAMAGE_DEPTH_DISPLAY.get(classification.damage_depth, classification.damage_depth),
        damage_depth_multiplier=depth_mult,
        panel_complexity_label=PANEL_COMPLEXITY_DISPLAY.get(classification.panel_complexity, classification.panel_complexity),
        panel_complexity_multiplier=complexity_mult,
        paint_type_label=PAINT_TYPE_DISPLAY.get(classification.paint_type, classification.paint_type),
        paint_type_multiplier=paint_mult,
        subtotal_before_extras=round(subtotal, 2),
        blending_panels=classification.blending_panels,
        blending_charge=blending_charge,
        minimum_charge=minimum_charge,
        price_before_multi_damage=round(price_before_multi, 2),
        num_damages=classification.num_damages,
        multiple_damage_multiplier=multi_damage_mult,
        final_price=final_price,
        confidence=classification.confidence,
        needs_review=needs_review,
        manual_review_required=manual_review_required,
        review_reasons=review_reasons,
        notes=classification.notes,
    )


def format_pricing_breakdown(breakdown: PricingBreakdown) -> str:
    """Format a PricingBreakdown into a CLI-friendly detailed string."""
    lines = []
    lines.append("=" * 55)
    lines.append("  TSRN SMART REPAIR ESTIMATE")
    lines.append("=" * 55)

    if breakdown.manual_review_required:
        lines.append("")
        lines.append("⚠️  MANUAL REVIEW REQUIRED")
        for reason in breakdown.review_reasons:
            lines.append(f"   • {reason}")
        lines.append("")
        lines.append("  Please contact us for a manual assessment.")
        lines.append("=" * 55)
        return "\n".join(lines)

    lines.append("")
    lines.append(f"  Panel:              {breakdown.panel_name}")
    lines.append(f"  Base Price:         £{breakdown.base_price:.2f}")
    lines.append(f"  Minimum Charge:     £{breakdown.minimum_charge:.2f}")
    lines.append("")
    lines.append("  ── Multipliers Applied ──")
    lines.append(f"  Damage Size:        {breakdown.damage_size_label}  (×{breakdown.damage_size_multiplier:.2f})")
    lines.append(f"  Damage Depth:       {breakdown.damage_depth_label}  (×{breakdown.damage_depth_multiplier:.2f})")
    lines.append(f"  Panel Complexity:   {breakdown.panel_complexity_label}  (×{breakdown.panel_complexity_multiplier:.2f})")
    lines.append(f"  Paint Type:         {breakdown.paint_type_label}  (×{breakdown.paint_type_multiplier:.2f})")
    lines.append("")
    lines.append(f"  Subtotal:           £{breakdown.subtotal_before_extras:.2f}")

    if breakdown.blending_panels > 0:
        lines.append(f"  Blending ({breakdown.blending_panels} panel{'s' if breakdown.blending_panels > 1 else ''}):      + £{breakdown.blending_charge:.2f}")

    if breakdown.num_damages > 1:
        lines.append(f"  Multiple Damages:   {breakdown.num_damages} damages  (×{breakdown.multiple_damage_multiplier:.2f})")

    lines.append("")
    lines.append("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"  ESTIMATED TOTAL:    £{breakdown.final_price:.2f}")
    lines.append("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"  AI Confidence:      {breakdown.confidence}%")

    if breakdown.needs_review:
        lines.append("")
        lines.append("  ⚠️  Flagged for review:")
        for reason in breakdown.review_reasons:
            lines.append(f"     • {reason}")

    if breakdown.notes:
        lines.append(f"\n  Notes: {breakdown.notes}")

    lines.append("=" * 55)
    return "\n".join(lines)


def format_pricing_for_chat(breakdown: PricingBreakdown) -> str:
    """Format a PricingBreakdown into a concise, chat-friendly Markdown string."""
    if breakdown.manual_review_required:
        reasons = "\n".join(f"• {r}" for r in breakdown.review_reasons)
        return (
            f"⚠️ **Manual Review Required**\n\n"
            f"{reasons}\n\n"
            f"This damage requires a manual assessment by a technician. "
            f"Please contact us to arrange an inspection."
        )

    msg = (
        f"**TSRN Smart Repair Estimate**\n\n"
        f"**Panel:** {breakdown.panel_name}\n"
        f"**Base Price:** £{breakdown.base_price:.2f}\n\n"
        f"**Multipliers Applied:**\n"
        f"• Damage Size: {breakdown.damage_size_label} (×{breakdown.damage_size_multiplier:.2f})\n"
        f"• Damage Depth: {breakdown.damage_depth_label} (×{breakdown.damage_depth_multiplier:.2f})\n"
        f"• Panel Complexity: {breakdown.panel_complexity_label} (×{breakdown.panel_complexity_multiplier:.2f})\n"
        f"• Paint Type: {breakdown.paint_type_label} (×{breakdown.paint_type_multiplier:.2f})\n"
    )

    if breakdown.blending_panels > 0:
        msg += f"• Blending ({breakdown.blending_panels} panel{'s' if breakdown.blending_panels > 1 else ''}): + £{breakdown.blending_charge:.2f}\n"

    if breakdown.num_damages > 1:
        msg += f"• Multiple Damages: {breakdown.num_damages} (×{breakdown.multiple_damage_multiplier:.2f})\n"

    msg += f"\n**Estimated Total: £{breakdown.final_price:.2f}**\n"
    msg += f"AI Confidence: {breakdown.confidence}%"

    if breakdown.needs_review:
        msg += "\n\n⚠️ *This estimate has been flagged for review.*"

    return msg


# ============================================================
# SECTION 3: IMAGE ANALYSIS PIPELINE (GPT-4o Classifier)
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
panel:
  front_bumper_corner, full_front_bumper, rear_bumper_corner, full_rear_bumper,
  front_wing, front_door, rear_door, rear_quarter_panel_4door, rear_quarter_panel_2door,
  sill_rail, roof, bonnet, alloy_wheel_painted, alloy_wheel_special,
  diamond_cut_wheel, pdr

damage_size:
  up_to_5cm, 5cm_to_15cm, 15cm_to_30cm, 30cm_to_50cm, over_50cm

damage_depth:
  surface_scratch, very_shallow_dent, moderate_dent, deep_dent, severe_dent

panel_complexity:
  flat_panel, curved_panel, bodyline_present, multiple_bodylines, complex_contour

paint_type:
  solid, metallic, pearlescent, tri_coat

Return ONLY the JSON object. No explanation, no markdown."""


def encode_image(image_path: str) -> str:
    """Convert local image to base64."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def classify_damage(image_paths: List[str], description: str) -> DamageClassification:
    """Send images and description to GPT-4o for structured damage classification."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    client = OpenAI(api_key=api_key)

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

    for path in image_paths:
        base64_image = encode_image(path)
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
        temperature=0.1,
        messages=messages,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"GPT returned invalid JSON: {raw[:200]}") from e

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


def estimate_car_repair(image_paths: List[str], description: str) -> dict:
    """Full image pipeline: Classify damage using GPT-4o → Calculate exact price."""
    classification = classify_damage(image_paths, description)
    breakdown = calculate_repair_cost(classification)
    formatted = format_pricing_breakdown(breakdown)

    return {
        "classification": classification,
        "breakdown": breakdown,
        "formatted_output": formatted,
    }


# ============================================================
# SECTION 4: CONVERSATIONAL CHATBOT LOGIC
# ============================================================

SYSTEM_PROMPT = """You are a professional car expert assistant for TSRN Smart Repair. You sound natural and human.

You have TWO modes:

═══ MODE 1: GENERAL CAR EXPERT ═══
For general car questions (buying, maintenance, diagnostics, etc.), respond naturally as a knowledgeable car expert. Use short answers for simple questions and detailed answers for complex ones.

═══ MODE 2: SMART REPAIR PRICING ═══
When the user describes car damage and wants a repair quote or estimate, you MUST collect enough information to classify the damage, then output a SPECIAL JSON BLOCK that our pricing system will process.

To generate a quote, you need these details:
1. What panel is damaged? (bumper, door, wing, bonnet, roof, etc.)
2. How big is the damage? (approximate size in cm)
3. How deep is the damage? (surface scratch, shallow dent, moderate dent, deep dent)
4. What type of paint? (solid, metallic, pearlescent, tri-coat) — if unknown, assume metallic
5. Is blending needed? (damage near panel edges may need adjacent panel blending)
6. How many separate damages? (1, 2, 3, or 4+)

If the user hasn't provided enough information, ask brief, natural follow-up questions to gather what you need. Don't ask all questions at once — be conversational.

Once you have enough information, output EXACTLY this JSON block wrapped in ```json markers:

```json
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
  "notes": "<your observations>"
}
```

VALID KEYS:
panel: front_bumper_corner, full_front_bumper, rear_bumper_corner, full_rear_bumper,
  front_wing, front_door, rear_door, rear_quarter_panel_4door, rear_quarter_panel_2door,
  sill_rail, roof, bonnet, alloy_wheel_painted, alloy_wheel_special,
  diamond_cut_wheel, pdr

damage_size: up_to_5cm, 5cm_to_15cm, 15cm_to_30cm, 30cm_to_50cm, over_50cm

damage_depth: surface_scratch, very_shallow_dent, moderate_dent, deep_dent, severe_dent

panel_complexity: flat_panel, curved_panel, bodyline_present, multiple_bodylines, complex_contour

paint_type: solid, metallic, pearlescent, tri_coat

IMPORTANT: Include a brief natural-language comment before the JSON block explaining what you found. After the JSON block, do NOT add price calculations — our system handles that.

PANEL COMPLEXITY GUIDE:
- flat_panel: Bonnet centre, Roof centre
- curved_panel: Front wing, Rear quarter panel
- bodyline_present: Door crease, Wing bodyline
- multiple_bodylines: Modern SUV panels, Complex side panels
- complex_contour: Bumper corners, Highly sculpted areas

CONFIDENCE GUIDE:
- 95-100: You are very sure about classification
- 80-94: Some uncertainty, but reasonable classification
- Below 80: Significant uncertainty, needs manual review"""


STORAGE_DIR = Path("chat_history")
STORAGE_DIR.mkdir(exist_ok=True)


def save_chat(session_id: str, messages: list):
    """Save conversation history to a JSON file."""
    path = STORAGE_DIR / f"{session_id}.json"
    with open(path, "w") as f:
        json.dump({"messages": messages}, f, indent=2)


def load_chat(session_id: str) -> list:
    """Load conversation history from a JSON file."""
    path = STORAGE_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f).get("messages", [])
    return []


def delete_chat(session_id: str):
    """Delete a conversation history file."""
    path = STORAGE_DIR / f"{session_id}.json"
    if path.exists():
        path.unlink()


def extract_pricing_json(text: str) -> dict | None:
    """Extract a pricing classification JSON block from the assistant's text."""
    pattern = r'```json\s*(\{[^`]+\})\s*```'
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match)
            required_fields = {"panel", "damage_size", "damage_depth", "panel_complexity", "paint_type"}
            if required_fields.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            continue
    return None


def process_pricing_response(data: dict) -> str:
    """Take a parsed JSON damage classification and process it through the engine."""
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
    breakdown = calculate_repair_cost(classification)
    return format_pricing_for_chat(breakdown)


def chat(session_id: str, user_message: str) -> dict:
    """
    Send a message to the AI chatbot, get a response, and automatically
    append the exact calculated repair quote if pricing information was generated.
    """
    if not user_message.strip():
        raise ValueError("Invalid message")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    client = OpenAI(api_key=api_key)

    history = load_chat(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message.strip()})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        top_p=0.95,
        presence_penalty=0.3,
        max_tokens=2000,
    )

    assistant_response = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    pricing_data = extract_pricing_json(assistant_response)
    pricing_result = None

    if pricing_data:
        try:
            pricing_result = process_pricing_response(pricing_data)
        except Exception as e:
            pricing_result = f"⚠️ Pricing calculation error: {e}"

    if pricing_result:
        clean_response = re.sub(r'```json\s*\{[^`]+\}\s*```', '', assistant_response).strip()
        final_response = f"{clean_response}\n\n{pricing_result}"
    else:
        final_response = assistant_response

    history.append({"role": "user", "content": user_message.strip()})
    history.append({"role": "assistant", "content": assistant_response})
    save_chat(session_id, history)

    return {
        "session_id": session_id,
        "user_message": user_message,
        "response": final_response,
        "tokens": tokens_used,
        "pricing_applied": pricing_result is not None,
    }


def get_history(session_id: str) -> dict | None:
    """Get conversation history."""
    messages = load_chat(session_id)
    if not messages:
        return None
    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "messages": messages,
    }


def clear_history(session_id: str):
    """Clear conversation history."""
    delete_chat(session_id)


def new_session() -> str:
    """Create a new unique session ID."""
    return str(uuid.uuid4())
