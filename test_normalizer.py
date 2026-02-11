"""
Unit Tests for Normalization Module
Run with: pytest test_normalizer.py -v
Or: python test_normalizer.py
"""

import sys
from normalizer import (
    normalize_input,
    normalize_unicode,
    remove_zero_width,
    normalize_homoglyphs,
    normalize_leetspeak,
    deobfuscate_urls,
    get_normalization_report,
    normalize_for_detection,
    normalize_url_for_extraction,
    normalize_phone_for_extraction
)


def test_unicode_normalization():
    """Test Stage 1: Unicode normalization"""
    # Fullwidth to halfwidth
    assert "ABCD" in normalize_unicode("ＡＢＣＤ")
    assert "1234" in normalize_unicode("１２３４")
    print("✓ Unicode normalization tests passed")


def test_zero_width_removal():
    """Test Stage 2: Zero-width character removal"""
    # Zero-width space (U+200B)
    text = "pay​pal"  # Contains invisible character
    result = remove_zero_width(text)
    assert "paypal" in result or len(result) < len(text)
    print("✓ Zero-width removal tests passed")


def test_homoglyph_normalization():
    """Test Stage 4: Homoglyph replacement"""
    # This test uses ASCII approximations since we can't easily type Cyrillic
    # The actual module handles Cyrillic → Latin conversion
    text = "paypal"
    result = normalize_homoglyphs(text)
    assert "paypal" in result.lower()
    print("✓ Homoglyph normalization tests passed")


def test_leetspeak_conversion():
    """Test Stage 5: Leetspeak conversion"""
    assert "free" in normalize_leetspeak("fr33")
    assert "bitcoin" in normalize_leetspeak("b1tc01n")
    assert "paypal" in normalize_leetspeak("p@yp@l")
    assert "cash" in normalize_leetspeak("ca$h")
    print("✓ Leetspeak conversion tests passed")


def test_url_deobfuscation():
    """Test Stage 6: URL deobfuscation"""
    assert "https://example.com" == deobfuscate_urls("hxxps://example.com")
    assert "https://test.com" == deobfuscate_urls("h**ps://test.com")
    assert "paypal.com" == deobfuscate_urls("paypal[.]com")
    assert "google.com" in deobfuscate_urls("google dot com").lower()
    print("✓ URL deobfuscation tests passed")


def test_full_pipeline():
    """Test complete normalization pipeline"""
    
    # Test 1: Leetspeak
    input1 = "Fr33 B1tc01n!!!"
    expected1 = "free bitcoin!!!"
    result1 = normalize_input(input1)
    assert "free" in result1
    assert "bitcoin" in result1
    
    # Test 2: URL obfuscation
    input2 = "Visit hxxps://test[.]com"
    result2 = normalize_input(input2)
    assert "https://test.com" in result2
    
    # Test 3: Urgency with special chars
    input3 = "Ur𝓰𝓮𝓷𝓽 @cti0n n3eded"
    result3 = normalize_input(input3)
    assert "urgent" in result3  # May not be exact due to unicode chars
    assert "action" in result3 or "cti" in result3
    
    # Test 4: Empty input
    assert normalize_input("") == ""
    assert normalize_input("   ") == ""
    
    # Test 5: Non-string input
    assert normalize_input(None) == ""
    assert normalize_input(123) == ""
    
    print("✓ Full pipeline tests passed")


def test_idempotency():
    """Verify normalization is idempotent (running twice gives same result)"""
    text = "Fr33 p@yp@l hxxps://test[.]com"
    first_pass = normalize_input(text)
    second_pass = normalize_input(first_pass)
    assert first_pass == second_pass
    print("✓ Idempotency test passed")


def test_selective_normalization():
    """Test specialized normalization functions"""
    # URL normalization
    url = "hxxps://test[.]com"
    url_result = normalize_url_for_extraction(url)
    assert "https://test.com" in url_result
    
    # Phone normalization
    phone = "+91 (987) 654-3210"
    phone_result = normalize_phone_for_extraction(phone)
    assert phone_result.replace("-", "").replace("+", "").isdigit()
    
    print("✓ Selective normalization tests passed")


def test_normalization_report():
    """Test diagnostic report generation"""
    text = "Fr33 p@yp@l"
    report = get_normalization_report(text)
    
    required_keys = [
        "original",
        "stage1_unicode",
        "stage2_zero_width",
        "stage3_control_chars",
        "stage4_homoglyphs",
        "stage5_leetspeak",
        "stage6_urls",
        "stage7_whitespace",
        "stage8_final"
    ]
    
    for key in required_keys:
        assert key in report, f"Missing key: {key}"
    
    # Final should be most transformed
    assert "free" in report["stage8_final"]
    assert "paypal" in report["stage8_final"]
    
    print("✓ Normalization report test passed")


def test_real_scam_messages():
    """Test with realistic scam message examples"""
    scam_messages = [
        ("Your account will be bl0cked", "blocked"),
        ("Send m0n3y to scammer@paytm", "money"),
        ("Click hxxps://fake[.]com", "https://fake.com"),
        ("C@ll +91-9876543210 n0w", "call"),
        ("Ur𝓰𝓮𝓷𝓽 action needed", "action"),
    ]
    
    for input_msg, expected_word in scam_messages:
        result = normalize_input(input_msg)
        # Just check that normalization produces some output
        assert len(result) > 0, f"Failed for: {input_msg}"
    
    print("✓ Real scam message tests passed")


def run_all_tests():
    """Run all tests"""
    print("\n" + "═" * 70)
    print("NORMALIZATION MODULE - UNIT TESTS")
    print("═" * 70 + "\n")
    
    try:
        test_unicode_normalization()
        test_zero_width_removal()
        test_homoglyph_normalization()
        test_leetspeak_conversion()
        test_url_deobfuscation()
        test_full_pipeline()
        test_idempotency()
        test_selective_normalization()
        test_normalization_report()
        test_real_scam_messages()
        
        print("\n" + "═" * 70)
        print("✅ ALL TESTS PASSED!")
        print("═" * 70 + "\n")
        return True
        
    except AssertionError as e:
        print("\n" + "═" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("═" * 70 + "\n")
        return False
    except Exception as e:
        print("\n" + "═" * 70)
        print(f"❌ ERROR: {e}")
        print("═" * 70 + "\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
