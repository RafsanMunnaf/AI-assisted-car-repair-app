from dataclasses import dataclass, field
from typing import Optional, List
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
    MULTIPLE_DAMAGE_MULTIPLIERS,
    CONFIDENCE_THRESHOLDS,
)


# ============================================================
# DATA CLASSES
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


# ============================================================
# VALIDATION
# ============================================================

def validate_classification(classification: DamageClassification) -> List[str]:
    """
    Validate that all classification fields map to known lookup keys.
    Returns a list of error messages (empty if valid).
    """
    errors = []

    if classification.panel not in PANEL_PRICES:
        errors.append(
            f"Unknown panel '{classification.panel}'. "
            f"Valid: {list(PANEL_PRICES.keys())}"
        )

    if classification.damage_size not in DAMAGE_SIZE_MULTIPLIERS:
        errors.append(
            f"Unknown damage_size '{classification.damage_size}'. "
            f"Valid: {list(DAMAGE_SIZE_MULTIPLIERS.keys())}"
        )

    if classification.damage_depth not in DAMAGE_DEPTH_MULTIPLIERS:
        errors.append(
            f"Unknown damage_depth '{classification.damage_depth}'. "
            f"Valid: {list(DAMAGE_DEPTH_MULTIPLIERS.keys())}"
        )

    if classification.panel_complexity not in PANEL_COMPLEXITY_MULTIPLIERS:
        errors.append(
            f"Unknown panel_complexity '{classification.panel_complexity}'. "
            f"Valid: {list(PANEL_COMPLEXITY_MULTIPLIERS.keys())}"
        )

    if classification.paint_type not in PAINT_TYPE_MULTIPLIERS:
        errors.append(
            f"Unknown paint_type '{classification.paint_type}'. "
            f"Valid: {list(PAINT_TYPE_MULTIPLIERS.keys())}"
        )

    if not (0 <= classification.blending_panels <= 3):
        errors.append(
            f"blending_panels must be 0-3, got {classification.blending_panels}"
        )

    if classification.num_damages < 1:
        errors.append(
            f"num_damages must be >= 1, got {classification.num_damages}"
        )

    if not (0 <= classification.confidence <= 100):
        errors.append(
            f"confidence must be 0-100, got {classification.confidence}"
        )

    return errors


# ============================================================
# PRICING CALCULATION
# ============================================================

def calculate_repair_cost(classification: DamageClassification) -> PricingBreakdown:
    """
    Calculate the exact repair cost using the TSRN pricing formula.

    Formula:
      subtotal = Base Price × Size × Depth × Complexity × Paint
      price    = max(subtotal, Minimum Charge) + Blending
      final    = price × Multiple Damage Multiplier

    Args:
        classification: Structured damage classification from GPT-4o.

    Returns:
        PricingBreakdown with full cost details.

    Raises:
        ValueError: If classification contains invalid keys.
    """
    # --- Validate ---
    errors = validate_classification(classification)
    if errors:
        raise ValueError(f"Invalid classification: {'; '.join(errors)}")

    # --- Check for manual review triggers ---
    review_reasons = []
    manual_review_required = False

    size_mult = DAMAGE_SIZE_MULTIPLIERS[classification.damage_size]
    depth_mult = DAMAGE_DEPTH_MULTIPLIERS[classification.damage_depth]

    if size_mult is None:
        review_reasons.append("Damage size exceeds 50cm — requires manual review")
        manual_review_required = True
        size_mult = 1.0  # Placeholder; price won't be used

    if depth_mult is None:
        review_reasons.append("Severe dent — requires manual review or bodyshop assessment")
        manual_review_required = True
        depth_mult = 1.0  # Placeholder; price won't be used

    if classification.confidence < CONFIDENCE_THRESHOLDS["flag_for_review"]:
        review_reasons.append(
            f"AI confidence is {classification.confidence}% (below 80%) — manual review required"
        )
        manual_review_required = True

    if not classification.eligible_for_smart_repair:
        review_reasons.append("Damage is NOT eligible for SMART repair")
        manual_review_required = True

    # Flag for review (not blocking) when confidence is 80-94%
    needs_review = False
    if (CONFIDENCE_THRESHOLDS["flag_for_review"]
            <= classification.confidence
            < CONFIDENCE_THRESHOLDS["generate_estimate"]):
        needs_review = True
        review_reasons.append(
            f"AI confidence is {classification.confidence}% — estimate generated but flagged for review"
        )

    # --- Look up values ---
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
        multi_damage_mult = MULTIPLE_DAMAGE_MULTIPLIERS.get(
            classification.num_damages, 1.0
        )

    # --- PDR override ---
    # If PDR eligible, use PDR base pricing directly
    if classification.pdr_eligible and classification.panel != "pdr":
        # Override to PDR pricing
        panel_data = PANEL_PRICES["pdr"]
        base_price = panel_data["base_price"]
        minimum_charge = panel_data["minimum_charge"]

    # --- Calculate ---
    subtotal = base_price * size_mult * depth_mult * complexity_mult * paint_mult

    # Enforce minimum charge
    price_before_blend = max(subtotal, minimum_charge)

    # Add blending
    price_before_multi = price_before_blend + blending_charge

    # Apply multiple damage multiplier
    final_price = price_before_multi * multi_damage_mult

    # Round to nearest penny
    final_price = round(final_price, 2)

    return PricingBreakdown(
        panel_name=PANEL_DISPLAY_NAMES.get(classification.panel, classification.panel),
        base_price=base_price,
        damage_size_label=DAMAGE_SIZE_DISPLAY.get(
            classification.damage_size, classification.damage_size
        ),
        damage_size_multiplier=size_mult,
        damage_depth_label=DAMAGE_DEPTH_DISPLAY.get(
            classification.damage_depth, classification.damage_depth
        ),
        damage_depth_multiplier=depth_mult,
        panel_complexity_label=PANEL_COMPLEXITY_DISPLAY.get(
            classification.panel_complexity, classification.panel_complexity
        ),
        panel_complexity_multiplier=complexity_mult,
        paint_type_label=PAINT_TYPE_DISPLAY.get(
            classification.paint_type, classification.paint_type
        ),
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


# ============================================================
# FORMATTED OUTPUT
# ============================================================

def format_pricing_breakdown(breakdown: PricingBreakdown) -> str:
    """
    Format a PricingBreakdown into a human-readable string
    suitable for chatbot or CLI display.
    """
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
    lines.append(
        f"  Damage Size:        {breakdown.damage_size_label}"
        f"  (×{breakdown.damage_size_multiplier:.2f})"
    )
    lines.append(
        f"  Damage Depth:       {breakdown.damage_depth_label}"
        f"  (×{breakdown.damage_depth_multiplier:.2f})"
    )
    lines.append(
        f"  Panel Complexity:   {breakdown.panel_complexity_label}"
        f"  (×{breakdown.panel_complexity_multiplier:.2f})"
    )
    lines.append(
        f"  Paint Type:         {breakdown.paint_type_label}"
        f"  (×{breakdown.paint_type_multiplier:.2f})"
    )
    lines.append("")
    lines.append(f"  Subtotal:           £{breakdown.subtotal_before_extras:.2f}")

    if breakdown.blending_panels > 0:
        lines.append(
            f"  Blending ({breakdown.blending_panels} panel{'s' if breakdown.blending_panels > 1 else ''})"
            f":      + £{breakdown.blending_charge:.2f}"
        )

    if breakdown.num_damages > 1:
        lines.append(
            f"  Multiple Damages:   {breakdown.num_damages} damages"
            f"  (×{breakdown.multiple_damage_multiplier:.2f})"
        )

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
    """
    Format a PricingBreakdown into a concise, chat-friendly string.
    """
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
