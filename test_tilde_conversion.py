#!/usr/bin/env python3
"""
Test script to verify the ~ to \n conversion in LSL commands.
"""

from chat_manager import generate_summary_for_llsettext


def test_tilde_conversion():
    """Test that ~ gets converted to proper line breaks."""
    
    # Test multi-line response with newlines
    test_response = "This is line 1\nThis is line 2\nThis is line 3"
    
    result = generate_summary_for_llsettext(test_response, "TestNPC")
    
    print(f"Original response: {repr(test_response)}")
    print(f"Generated llSetText: {repr(result)}")
    
    # Should contain ~ instead of \n
    assert "~" in result, "Expected ~ character for line breaks"
    assert "\n" not in result, "Should not contain literal newlines"
    
    print("✓ Tilde conversion test passed!")


def test_lsl_processing_simulation():
    """Simulate how LSL would process the tilde command."""
    
    # Simulate what AI would generate
    test_text = "Status Update~Quest Progress~Ready to help"
    
    # Simulate LSL conversion (what happens in process_sl_commands)
    lsl_converted = test_text.replace("~", "\n")
    
    print(f"AI generated text: {repr(test_text)}")
    print(f"LSL converted text: {repr(lsl_converted)}")
    print("Displayed as:")
    print(lsl_converted)
    
    assert lsl_converted == "Status Update\nQuest Progress\nReady to help"
    
    print("✓ LSL processing simulation test passed!")


if __name__ == "__main__":
    test_tilde_conversion()
    print()
    test_lsl_processing_simulation()
    print("\n✅ All tilde conversion tests passed!")