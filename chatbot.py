"""
TSRN Smart Repair — Car Expert Chatbot
Integrates the TSRN pricing matrix for accurate repair cost estimates.
Supports both conversational Q&A and structured damage pricing.
"""

import json
import os
import uuid
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
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
    BLENDING_CHARGES,
)
from pricing_engine import (
    DamageClassification,
    calculate_repair_cost,
    format_pricing_for_chat,
)

load_dotenv()

# Configuration
STORAGE = Path("chat_history")
STORAGE.mkdir(exist_ok=True)

# ============================================================
# SYSTEM PROMPT — Pricing-Aware Car Expert
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

ELIGIBILITY RULES:

Eligible for SMART repair:
- Localised cosmetic damage, scratches, scuffs, paint damage, dents
- Wheel kerb damage
- Paintless dent removal (PDR) where paint is not broken

NOT eligible (set eligible_for_smart_repair to false):
- Structural damage, panel replacement required, large-scale lacquer peel
- Significant corrosion, extensive previous repair work, damage exceeding size limits

PDR eligible ONLY when: paint intact, no cracking, no exposed metal, no previous filler,
and dent depth is Very Shallow Dent. If paint damage detected → pdr_eligible = false.

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


# ============================================================
# JSON EXTRACTION FROM CHAT RESPONSES
# ============================================================

def extract_pricing_json(text: str) -> dict | None:
    """
    Extract a pricing classification JSON block from the assistant's response.
    Looks for ```json ... ``` blocks containing the required pricing fields.

    Returns:
        Parsed dict if found and valid, None otherwise.
    """
    import re

    # Look for ```json ... ``` blocks
    pattern = r'```json\s*(\{[^`]+\})\s*```'
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match)
            # Verify it has the required pricing fields
            required_fields = {"panel", "damage_size", "damage_depth",
                             "panel_complexity", "paint_type"}
            if required_fields.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            continue

    return None


def process_pricing_response(data: dict) -> str:
    """
    Take a parsed pricing JSON dict and run it through the pricing engine.

    Returns:
        Formatted pricing breakdown string.
    """
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


# ============================================================
# STORAGE FUNCTIONS
# ============================================================

def save_chat(session_id: str, messages: list):
    """Save conversation to JSON file"""
    path = STORAGE / f"{session_id}.json"
    with open(path, "w") as f:
        json.dump({"messages": messages}, f, indent=2)

def load_chat(session_id: str) -> list:
    """Load conversation from JSON file"""
    path = STORAGE / f"{session_id}.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f).get("messages", [])
    return []

def delete_chat(session_id: str):
    """Delete conversation file"""
    path = STORAGE / f"{session_id}.json"
    if path.exists():
        path.unlink()


# ============================================================
# MAIN CHAT FUNCTION
# ============================================================

def chat(session_id: str, user_message: str) -> dict:
    """
    Send one user input and get response with full conversation context.
    If the response contains a pricing classification, automatically
    calculate and append the exact TSRN price.
    """
    # Validate inputs
    if not user_message.strip():
        raise ValueError("Invalid message")

    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    client = OpenAI(api_key=api_key)

    # Load conversation history
    history = load_chat(session_id)

    # Build messages for API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message.strip()})

    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        top_p=0.95,
        presence_penalty=0.3,
        max_tokens=2000,
    )

    # Extract response
    assistant_response = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    # Check if the response contains a pricing classification
    pricing_data = extract_pricing_json(assistant_response)
    pricing_result = None

    if pricing_data:
        try:
            pricing_result = process_pricing_response(pricing_data)
        except (ValueError, KeyError) as e:
            pricing_result = f"⚠️ Pricing calculation error: {e}"

    # Build final response
    if pricing_result:
        # Remove the raw JSON block from the display and append the real pricing
        import re
        clean_response = re.sub(
            r'```json\s*\{[^`]+\}\s*```',
            '',
            assistant_response,
        ).strip()
        final_response = f"{clean_response}\n\n{pricing_result}"
    else:
        final_response = assistant_response

    # Save to history
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


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_history(session_id: str) -> dict:
    """Get conversation history"""
    messages = load_chat(session_id)
    if not messages:
        return None
    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "messages": messages,
    }

def clear_history(session_id: str):
    """Clear conversation"""
    delete_chat(session_id)

def new_session() -> str:
    """Create new session ID"""
    return str(uuid.uuid4())


# ============================================================
# INTERACTIVE CLI
# ============================================================

def run_interactive():
    """Run interactive chatbot in terminal"""
    print("\n" + "=" * 55)
    print("  TSRN SMART REPAIR — CAR EXPERT CHATBOT")
    print("=" * 55)
    print("\nAsk anything about cars. For repair quotes, describe the damage.")
    session_id = new_session()
    print(f"\nSession: {session_id[:8]}...")
    print("\nCommands: 'history' | 'clear' | 'exit'\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() == "exit":
                print("\nGoodbye!")
                break

            if user_input.lower() == "history":
                hist = get_history(session_id)
                if hist:
                    print(f"\n--- History ({hist['total_messages']} messages) ---")
                    for msg in hist['messages']:
                        print(f"\n[{msg['role'].upper()}]\n{msg['content']}\n")
                else:
                    print("No history yet.\n")
                continue

            if user_input.lower() == "clear":
                clear_history(session_id)
                session_id = new_session()
                print(f"✓ History cleared. New session: {session_id[:8]}...\n")
                continue

            # Send to chatbot
            print("\nLoading...")
            result = chat(session_id, user_input)

            if result.get("pricing_applied"):
                print(f"\nEXPERT + PRICING:\n{result['response']}\n")
            else:
                print(f"\nEXPERT:\n{result['response']}\n")

            print(f"[Tokens: {result['tokens']}]\n")

        except KeyboardInterrupt:
            print("\n\nSession ended.")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_interactive()
