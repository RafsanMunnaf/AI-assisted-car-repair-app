"""
TSRN AI Smart Repair Pricing Matrix — Data Tables
All values extracted directly from the official PDF.
Currency: GBP (£)
"""

# ============================================================
# PANEL BASE PRICES
# Each entry: { "base_price": £, "minimum_charge": £ }
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

# Human-readable display names for panels
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


# ============================================================
# DAMAGE SIZE MULTIPLIER
# AI measures the longest visible dimension of the damage.
# "0" in the PDF means base price (×1.0), not zero.
# ============================================================

DAMAGE_SIZE_MULTIPLIERS = {
    "up_to_5cm":   1.0,   # PDF says "0" — means no extra charge, use base
    "5cm_to_15cm": 1.10,
    "15cm_to_30cm": 1.50,
    "30cm_to_50cm": 2.00,
    "over_50cm":   None,  # Manual Review
}

DAMAGE_SIZE_DISPLAY = {
    "up_to_5cm":    "Up to 5cm",
    "5cm_to_15cm":  "5cm – 15cm",
    "15cm_to_30cm": "15cm – 30cm",
    "30cm_to_50cm": "30cm – 50cm",
    "over_50cm":    "Over 50cm (Manual Review)",
}


# ============================================================
# DAMAGE DEPTH MULTIPLIER
# "0" in the PDF means base price (×1.0).
# ============================================================

DAMAGE_DEPTH_MULTIPLIERS = {
    "surface_scratch":   1.0,   # Surface Scratch / Scuff Only
    "very_shallow_dent": 1.15,  # Minimal Filler Required
    "moderate_dent":     1.50,  # Light Filler Required
    "deep_dent":         1.80,  # Moderate Filler Required
    "severe_dent":       None,  # Manual Review — Heavy Filler Required
}

DAMAGE_DEPTH_DISPLAY = {
    "surface_scratch":   "Surface Scratch / Scuff Only",
    "very_shallow_dent": "Very Shallow Dent (Minimal Filler)",
    "moderate_dent":     "Moderate Dent (Light Filler)",
    "deep_dent":         "Deep Dent (Moderate Filler)",
    "severe_dent":       "Severe Dent (Manual Review)",
}


# ============================================================
# PANEL COMPLEXITY MULTIPLIER
# "0" in the PDF means base price (×1.0).
# ============================================================

PANEL_COMPLEXITY_MULTIPLIERS = {
    "flat_panel":         1.0,   # e.g. Bonnet centre, Roof centre
    "curved_panel":       1.05,  # e.g. Front wing, Rear quarter panel
    "bodyline_present":   1.10,  # e.g. Door crease, Wing bodyline
    "multiple_bodylines": 1.30,  # e.g. Modern SUV panels, Complex side panels
    "complex_contour":    1.40,  # e.g. Bumper corners, Highly sculpted areas
}

PANEL_COMPLEXITY_DISPLAY = {
    "flat_panel":         "Flat Panel",
    "curved_panel":       "Curved Panel",
    "bodyline_present":   "Bodyline Present",
    "multiple_bodylines": "Multiple Bodylines",
    "complex_contour":    "Complex Contour",
}


# ============================================================
# PAINT TYPE MULTIPLIER
# "0" in the PDF for Solid means base (×1.0).
# ============================================================

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


# ============================================================
# BLENDING CHARGES (flat £ additions)
# ============================================================

BLENDING_CHARGES = {
    0: 0,
    1: 180,
    2: 350,
    3: 500,
}


# ============================================================
# MULTIPLE DAMAGE MULTIPLIER
# "0" for 1 damage means base (×1.0).
# ============================================================

MULTIPLE_DAMAGE_MULTIPLIERS = {
    1: 1.0,
    2: 1.05,
    3: 1.10,
}
# 4+ defaults to 1.50 — handled in code


# ============================================================
# SMART REPAIR ELIGIBILITY
# ============================================================

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


# ============================================================
# PDR ELIGIBILITY RULES
# PDR may only be selected when ALL of these are true.
# ============================================================

PDR_REQUIREMENTS = [
    "Paint is intact",
    "No cracking",
    "No paint fracture",
    "No exposed metal",
    "No previous filler damage",
    "Dent depth is classified as Very Shallow Dent",
]
# If paint damage is detected → convert to SMART repair pricing


# ============================================================
# AI CONFIDENCE THRESHOLDS
# ============================================================

CONFIDENCE_THRESHOLDS = {
    "generate_estimate":    95,   # 95%+ → Generate Estimate
    "flag_for_review":      80,   # 80-94% → Generate Estimate & Flag for Review
    # Below 80% → Manual Review Required
}
