"""
Test suite for the TSRN Smart Repair Pricing Engine.
Verifies that the pricing formula produces exact expected results.

Run: python test_pricing_engine.py
"""

import sys
from pricing_engine import (
    DamageClassification,
    PricingBreakdown,
    calculate_repair_cost,
    validate_classification,
    format_pricing_breakdown,
    format_pricing_for_chat,
)


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name, expected, got):
        self.failed += 1
        self.errors.append((name, expected, got))
        print(f"  ✗ {name}")
        print(f"    Expected: {expected}")
        print(f"    Got:      {got}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 50}")
        print(f"  Results: {self.passed}/{total} passed, {self.failed} failed")
        print(f"{'=' * 50}")
        if self.errors:
            print("\n  Failed tests:")
            for name, expected, got in self.errors:
                print(f"    • {name}: expected {expected}, got {got}")
        return self.failed == 0


def assert_price(result: TestResult, name: str, classification: DamageClassification, expected_price: float):
    """Helper: compute price and check against expected."""
    try:
        breakdown = calculate_repair_cost(classification)
        if abs(breakdown.final_price - expected_price) < 0.01:
            result.ok(name)
        else:
            result.fail(name, expected_price, breakdown.final_price)
    except Exception as e:
        result.fail(name, expected_price, f"ERROR: {e}")


def assert_manual_review(result: TestResult, name: str, classification: DamageClassification):
    """Helper: verify that manual review is flagged."""
    try:
        breakdown = calculate_repair_cost(classification)
        if breakdown.manual_review_required:
            result.ok(name)
        else:
            result.fail(name, "manual_review_required=True", "manual_review_required=False")
    except Exception as e:
        result.fail(name, "manual_review_required=True", f"ERROR: {e}")


def test_basic_pricing(result: TestResult):
    """Test basic pricing with no multipliers (all base/×1.0)."""
    print("\n── Basic Pricing (base values, no multipliers) ──")

    # Front Door, up to 5cm scratch, flat panel, solid paint, no blend
    # = 265 × 1.0 × 1.0 × 1.0 × 1.0 + 0 = 265
    assert_price(result, "Front Door — base only", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 265.0)

    # Front Wing = 195
    assert_price(result, "Front Wing — base only", DamageClassification(
        panel="front_wing",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 195.0)

    # Roof = 460
    assert_price(result, "Roof — base only", DamageClassification(
        panel="roof",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 460.0)

    # PDR = 120
    assert_price(result, "PDR — base only", DamageClassification(
        panel="pdr",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 120.0)


def test_size_multipliers(result: TestResult):
    """Test damage size multipliers."""
    print("\n── Damage Size Multipliers ──")

    # Front Door base=265, 5-15cm = ×1.10 → 265 × 1.10 = 291.50
    assert_price(result, "Front Door 5-15cm", DamageClassification(
        panel="front_door",
        damage_size="5cm_to_15cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 291.50)

    # Front Door base=265, 15-30cm = ×1.50 → 265 × 1.50 = 397.50
    assert_price(result, "Front Door 15-30cm", DamageClassification(
        panel="front_door",
        damage_size="15cm_to_30cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 397.50)

    # Front Door base=265, 30-50cm = ×2.00 → 265 × 2.00 = 530.00
    assert_price(result, "Front Door 30-50cm", DamageClassification(
        panel="front_door",
        damage_size="30cm_to_50cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 530.0)


def test_depth_multipliers(result: TestResult):
    """Test damage depth multipliers."""
    print("\n── Damage Depth Multipliers ──")

    # Front Door base=265, very shallow dent ×1.15 → 304.75
    assert_price(result, "Front Door very shallow dent", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="very_shallow_dent",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 304.75)

    # Front Door base=265, moderate dent ×1.50 → 397.50
    assert_price(result, "Front Door moderate dent", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="moderate_dent",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 397.50)

    # Front Door base=265, deep dent ×1.80 → 477.00
    assert_price(result, "Front Door deep dent", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="deep_dent",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 477.0)


def test_complexity_multipliers(result: TestResult):
    """Test panel complexity multipliers."""
    print("\n── Panel Complexity Multipliers ──")

    # Front Door base=265, curved ×1.05 → 278.25
    assert_price(result, "Front Door curved panel", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="curved_panel",
        paint_type="solid",
    ), 278.25)

    # Front Door base=265, complex contour ×1.40 → 371.00
    assert_price(result, "Front Door complex contour", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="complex_contour",
        paint_type="solid",
    ), 371.0)


def test_paint_multipliers(result: TestResult):
    """Test paint type multipliers."""
    print("\n── Paint Type Multipliers ──")

    # Front Door base=265, metallic ×1.20 → 318.00
    assert_price(result, "Front Door metallic", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="metallic",
    ), 318.0)

    # Front Door base=265, pearlescent ×1.50 → 397.50
    assert_price(result, "Front Door pearlescent", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="pearlescent",
    ), 397.50)


def test_blending_charges(result: TestResult):
    """Test blending charges (flat additions)."""
    print("\n── Blending Charges ──")

    # Front Door 265 + 1 panel blend (180) = 445
    assert_price(result, "Front Door + 1 panel blend", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        blending_panels=1,
    ), 445.0)

    # Front Door 265 + 2 panel blend (350) = 615
    assert_price(result, "Front Door + 2 panel blend", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        blending_panels=2,
    ), 615.0)


def test_minimum_charge(result: TestResult):
    """Test that minimum charge is enforced."""
    print("\n── Minimum Charge Enforcement ──")

    # Alloy Wheel Painted: base=80, min=70
    # With no multipliers: 80 (above minimum 70) → 80
    assert_price(result, "Alloy Wheel Painted — above minimum", DamageClassification(
        panel="alloy_wheel_painted",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ), 80.0)


def test_combined_multipliers(result: TestResult):
    """Test realistic scenarios with multiple multipliers."""
    print("\n── Combined Multiplier Scenarios ──")

    # Front Door: base=265
    # Size 5-15cm (×1.10) × Depth moderate (×1.50) × Bodyline (×1.10) × Metallic (×1.20)
    # = 265 × 1.10 × 1.50 × 1.10 × 1.20 = 576.18
    # + Blend 1 panel (180) = 756.18
    expected = round(265 * 1.10 * 1.50 * 1.10 * 1.20 + 180, 2)
    assert_price(result, "Front Door — full combo + blend", DamageClassification(
        panel="front_door",
        damage_size="5cm_to_15cm",
        damage_depth="moderate_dent",
        panel_complexity="bodyline_present",
        paint_type="metallic",
        blending_panels=1,
    ), expected)

    # Full Front Bumper: base=450
    # Size 15-30cm (×1.50) × Depth deep (×1.80) × Complex contour (×1.40) × Pearlescent (×1.50)
    # = 450 × 1.50 × 1.80 × 1.40 × 1.50 = 2551.50
    expected2 = round(450 * 1.50 * 1.80 * 1.40 * 1.50, 2)
    assert_price(result, "Full Front Bumper — heavy damage", DamageClassification(
        panel="full_front_bumper",
        damage_size="15cm_to_30cm",
        damage_depth="deep_dent",
        panel_complexity="complex_contour",
        paint_type="pearlescent",
    ), expected2)


def test_multiple_damage_multiplier(result: TestResult):
    """Test multiple damage multiplier."""
    print("\n── Multiple Damage Multiplier ──")

    # Front Door base=265, 2 damages (×1.05) → 265 × 1.05 = 278.25
    assert_price(result, "Front Door — 2 damages", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        num_damages=2,
    ), 278.25)

    # Front Door base=265, 4+ damages (×1.50) → 265 × 1.50 = 397.50
    assert_price(result, "Front Door — 4+ damages", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        num_damages=5,
    ), 397.50)


def test_manual_review_triggers(result: TestResult):
    """Test that manual review is correctly triggered."""
    print("\n── Manual Review Triggers ──")

    # Over 50cm → manual review
    assert_manual_review(result, "Over 50cm → manual review", DamageClassification(
        panel="front_door",
        damage_size="over_50cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ))

    # Severe dent → manual review
    assert_manual_review(result, "Severe dent → manual review", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="severe_dent",
        panel_complexity="flat_panel",
        paint_type="solid",
    ))

    # Low confidence (<80%) → manual review
    assert_manual_review(result, "Low confidence → manual review", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        confidence=75,
    ))

    # Not eligible for SMART repair → manual review
    assert_manual_review(result, "Not eligible → manual review", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        eligible_for_smart_repair=False,
    ))


def test_pdr_override(result: TestResult):
    """Test PDR pricing override."""
    print("\n── PDR Override ──")

    # PDR-eligible on front_door should use PDR pricing (base=120, min=100)
    # 120 × 1.0 × 1.0 × 1.0 × 1.0 = 120
    assert_price(result, "PDR-eligible front_door uses PDR pricing", DamageClassification(
        panel="front_door",
        damage_size="up_to_5cm",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
        pdr_eligible=True,
    ), 120.0)


def test_validation(result: TestResult):
    """Test validation catches bad input."""
    print("\n── Input Validation ──")

    errors = validate_classification(DamageClassification(
        panel="invalid_panel",
        damage_size="invalid_size",
        damage_depth="surface_scratch",
        panel_complexity="flat_panel",
        paint_type="solid",
    ))
    if len(errors) == 2:  # Should catch panel and size
        result.ok("Validation catches 2 invalid fields")
    else:
        result.fail("Validation catches 2 invalid fields", "2 errors", f"{len(errors)} errors")


def test_formatting(result: TestResult):
    """Test that formatting functions don't crash."""
    print("\n── Formatting ──")

    breakdown = calculate_repair_cost(DamageClassification(
        panel="front_door",
        damage_size="5cm_to_15cm",
        damage_depth="moderate_dent",
        panel_complexity="bodyline_present",
        paint_type="metallic",
        blending_panels=1,
    ))

    cli_output = format_pricing_breakdown(breakdown)
    if "TSRN SMART REPAIR ESTIMATE" in cli_output and "£" in cli_output:
        result.ok("CLI formatting works")
    else:
        result.fail("CLI formatting works", "Contains header and £", cli_output[:100])

    chat_output = format_pricing_for_chat(breakdown)
    if "TSRN Smart Repair Estimate" in chat_output and "£" in chat_output:
        result.ok("Chat formatting works")
    else:
        result.fail("Chat formatting works", "Contains header and £", chat_output[:100])


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  TSRN Pricing Engine — Test Suite")
    print("=" * 50)

    result = TestResult()

    test_basic_pricing(result)
    test_size_multipliers(result)
    test_depth_multipliers(result)
    test_complexity_multipliers(result)
    test_paint_multipliers(result)
    test_blending_charges(result)
    test_minimum_charge(result)
    test_combined_multipliers(result)
    test_multiple_damage_multiplier(result)
    test_manual_review_triggers(result)
    test_pdr_override(result)
    test_validation(result)
    test_formatting(result)

    success = result.summary()
    sys.exit(0 if success else 1)
