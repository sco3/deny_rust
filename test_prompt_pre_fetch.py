#!/usr/bin/env python3
"""Test script to verify prompt_pre_fetch returns correct structure."""

import sys
from deny_rust import DenyListPlugin, DenyListConfig, PluginResult, PluginViolation

def test_prompt_pre_fetch():
    """Test the prompt_pre_fetch method returns PluginResult structure."""
    
    # Create config with deny words
    config = DenyListConfig(words=["badword", "forbidden", "blocked"])
    
    # Create plugin
    plugin = DenyListPlugin(config, plugin_name="TestDenyPlugin")
    
    print("=" * 80)
    print("Testing prompt_pre_fetch method")
    print("=" * 80)
    
    # Test 1: Clean text (no violation)
    print("\n1. Testing clean text (should pass):")
    result = plugin.prompt_pre_fetch({"text": "This is a clean message"})
    print(f"   Type: {type(result)}")
    print(f"   continue_processing: {result.continue_processing}")
    print(f"   violation: {result.violation}")
    print(f"   modified_payload: {result.modified_payload}")
    print(f"   metadata: {result.metadata}")
    assert isinstance(result, PluginResult), "Result should be PluginResult"
    assert result.continue_processing == True, "Should continue processing"
    assert result.violation is None, "Should have no violation"
    print("   ✓ PASSED")
    
    # Test 2: Text with denied word (violation)
    print("\n2. Testing text with denied word (should block):")
    result = plugin.prompt_pre_fetch({"text": "This contains a badword in it"})
    print(f"   Type: {type(result)}")
    print(f"   continue_processing: {result.continue_processing}")
    print(f"   violation: {result.violation}")
    if result.violation:
        print(f"   violation.reason: {result.violation.reason}")
        print(f"   violation.description: {result.violation.description}")
        print(f"   violation.code: {result.violation.code}")
        print(f"   violation.plugin_name: {result.violation.plugin_name}")
    print(f"   modified_payload: {result.modified_payload}")
    print(f"   metadata: {result.metadata}")
    assert isinstance(result, PluginResult), "Result should be PluginResult"
    assert result.continue_processing == False, "Should NOT continue processing"
    assert result.violation is not None, "Should have a violation"
    assert isinstance(result.violation, PluginViolation), "Violation should be PluginViolation"
    assert result.violation.code == "DENY_LIST_VIOLATION", "Should have correct code"
    assert result.violation.plugin_name == "TestDenyPlugin", "Should have correct plugin name"
    print("   ✓ PASSED")
    
    # Test 3: Multiple fields
    print("\n3. Testing multiple fields:")
    result = plugin.prompt_pre_fetch({
        "text": "Clean text",
        "prompt": "Also clean",
        "message": "No issues here"
    })
    print(f"   continue_processing: {result.continue_processing}")
    print(f"   violation: {result.violation}")
    assert result.continue_processing == True, "Should continue processing"
    assert result.violation is None, "Should have no violation"
    print("   ✓ PASSED")
    
    # Test 4: Multiple fields with one violation
    print("\n4. Testing multiple fields with violation in one:")
    result = plugin.prompt_pre_fetch({
        "text": "Clean text",
        "prompt": "Contains forbidden word",
        "message": "No issues here"
    })
    print(f"   continue_processing: {result.continue_processing}")
    print(f"   violation: {result.violation}")
    assert result.continue_processing == False, "Should NOT continue processing"
    assert result.violation is not None, "Should have a violation"
    print("   ✓ PASSED")
    
    print("\n" + "=" * 80)
    print("All tests PASSED! ✓")
    print("=" * 80)
    print("\nThe prompt_pre_fetch method now returns the same PluginResult structure")
    print("as the Python deny.py implementation, with:")
    print("  - continue_processing: bool")
    print("  - violation: Optional[PluginViolation]")
    print("  - modified_payload: Optional[dict]")
    print("  - metadata: Optional[dict]")
    print("\nPluginViolation contains:")
    print("  - reason: str")
    print("  - description: str")
    print("  - code: str")
    print("  - plugin_name: str")
    print("  - details: Optional[dict]")
    print("  - mcp_error_code: Optional[int]")

if __name__ == "__main__":
    try:
        test_prompt_pre_fetch()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
