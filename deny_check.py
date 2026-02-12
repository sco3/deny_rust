#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
"""Benchmark script for deny_check functionality.

This script reads deny_check_config.json and creates DenyListPlugin instances
for every element of deny_word_lists.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Type

# Add parent directory to path to import plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.deny_filter.deny_rust import DenyListPluginRust
from mcpgateway.plugins.framework import PluginConfig, Plugin
from mcpgateway.plugins.framework.hooks.prompts import PromptHookType


def load_config(config_path: str = "deny_check_config.json") -> Dict[str, Any]:
    """Load the deny check configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        Dictionary containing the configuration.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        # Try relative to script location
        config_file = Path(__file__).parent.parent / config_path
    
    with open(config_file, 'r') as f:
        return json.load(f)


def create_plugin_instances(config: Dict[str, Any], plugin_type: Type[Plugin]) -> List[Plugin]:
    """Create DenyListPlugin instances for each deny word list.
    
    Args:
        config: The loaded configuration dictionary.
        plugin_type: The plugin class type to instantiate.
        
    Returns:
        List of plugin instances.
    """
    plugins = []
    
    for deny_list in config['deny_word_lists']:
        # Create PluginConfig for each deny word list (pattern from main_rs.py)
        plugin_config = PluginConfig(
            name=f"deny_filter_{deny_list['name']}",
            kind=f"{plugin_type.__module__}.{plugin_type.__name__}",
            hooks=[PromptHookType.PROMPT_PRE_FETCH],
            priority=100,
            config={
                "words": deny_list['words']
            }
        )
        
        # Create plugin instance
        plugin = plugin_type(config=plugin_config)
        plugins.append(plugin)
        
        #print(f"Created plugin for '{deny_list['name']}' with {len(deny_list['words'])} words")
    
    return plugins


async def main(plugin_type: Type[Plugin] = DenyListPluginRust):
    """Main benchmark function.
    
    Args:
        plugin_type: The plugin class type to instantiate (defaults to DenyListPluginRust).
    """
    print("Loading deny_check_config.json...")
    config = load_config()
    
    print(f"\nFound {len(config['deny_word_lists'])} deny word lists")
    print(f"Found {len(config['sample_texts'])} sample texts\n")
    
    print(f"Creating {plugin_type.__name__} instances...")
    plugins = create_plugin_instances(config, plugin_type)
    
    print(f"\nSuccessfully created {len(plugins)} plugin instances:")
    for i, plugin in enumerate(plugins, 1):
        print(f"  {i}. {plugin._config.name}")
    


if __name__ == "__main__":
    asyncio.run(main())
