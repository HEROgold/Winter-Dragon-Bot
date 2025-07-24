#!/usr/bin/env python3
"""
Simple test to verify that the Config system can read our timer configurations.
This test doesn't require Discord.py to be installed.
"""

import sys
import os
from pathlib import Path

# Add the bot source to Python path
sys.path.insert(0, str(Path(__file__).parent / "bot" / "src"))

try:
    from winter_dragon.bot.config import Config, ConfigParser
    from winter_dragon.bot.constants import BOT_CONFIG
    
    # Use our test config instead of the default one
    test_config_path = Path(__file__).parent / "test_config.ini"
    Config.set_file(test_config_path)
    Config.set_parser(ConfigParser())
    
    # Test that we can create config objects similar to the ones in our classes
    class TestBotC:
        gather_metrics_interval = Config(180, float)
        periodic_time = Config(180, float)
    
    class TestAutoReloader:
        auto_reload_interval = Config(5, float)
    
    class TestDatabaseManager:
        database_update_interval = Config(3600, float)
    
    # Instantiate the test classes
    bot_c = TestBotC()
    auto_reloader = TestAutoReloader()
    db_manager = TestDatabaseManager()
    
    # Test reading the values
    print("Testing config values:")
    print(f"BotC.gather_metrics_interval: {bot_c.gather_metrics_interval}")
    print(f"BotC.periodic_time: {bot_c.periodic_time}")
    print(f"AutoReloader.auto_reload_interval: {auto_reloader.auto_reload_interval}")
    print(f"DatabaseManager.database_update_interval: {db_manager.database_update_interval}")
    
    # Check if values match what we expect from test_config.ini
    expected_values = {
        'gather_metrics_interval': 240.0,
        'periodic_time': 300.0,
        'auto_reload_interval': 10.0,
        'database_update_interval': 7200.0,
    }
    
    actual_values = {
        'gather_metrics_interval': bot_c.gather_metrics_interval,
        'periodic_time': bot_c.periodic_time,
        'auto_reload_interval': auto_reloader.auto_reload_interval,
        'database_update_interval': db_manager.database_update_interval,
    }
    
    print("\nValidation:")
    all_passed = True
    for key, expected in expected_values.items():
        actual = actual_values[key]
        if actual == expected:
            print(f"✓ {key}: {actual} (matches expected)")
        else:
            print(f"✗ {key}: {actual} (expected {expected})")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All config values are working correctly!")
        exit(0)
    else:
        print("\n❌ Some config values don't match expectations")
        exit(1)
        
except Exception as e:
    print(f"❌ Error testing config system: {e}")
    import traceback
    traceback.print_exc()
    exit(1)