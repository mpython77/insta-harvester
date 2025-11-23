"""
Test script to verify ScraperConfig has all required attributes
"""

from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()

# Check all required attributes
required_attrs = [
    'headless',
    'viewport_width',
    'viewport_height',
    'user_agent',
    'default_timeout',
    'popup_animation_delay',
    'popup_content_load_delay',
    'error_recovery_delay_min',
    'error_recovery_delay_max',
    'post_open_delay',
    'ui_element_load_delay'
]

print("=" * 60)
print("CHECKING ScraperConfig ATTRIBUTES")
print("=" * 60)

all_good = True
for attr in required_attrs:
    if hasattr(config, attr):
        value = getattr(config, attr)
        print(f"✅ {attr:30s} = {value}")
    else:
        print(f"❌ {attr:30s} = MISSING!")
        all_good = False

print("=" * 60)
if all_good:
    print("✅ ALL ATTRIBUTES PRESENT - Config is OK!")
else:
    print("❌ SOME ATTRIBUTES MISSING - This is the problem!")
print("=" * 60)

# Test creating config with all parameters
try:
    test_config = ScraperConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
        user_agent='test',
        default_timeout=30000,
        popup_animation_delay=1.5,
        popup_content_load_delay=0.5,
        error_recovery_delay_min=1.0,
        error_recovery_delay_max=2.0,
        post_open_delay=3.0,
        ui_element_load_delay=0.1
    )
    print("\n✅ Config creation with all parameters: SUCCESS")
    print(f"   error_recovery_delay_min = {test_config.error_recovery_delay_min}")
    print(f"   error_recovery_delay_max = {test_config.error_recovery_delay_max}")
except Exception as e:
    print(f"\n❌ Config creation FAILED: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
