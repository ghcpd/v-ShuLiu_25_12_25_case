from typing import Dict, Any

def validate_config(config: Dict[str, Any]) -> bool:
    required_keys = ['version', 'module', 'parser_version', 'byte_order', 'parse_mode', 'signal_map']
    for key in required_keys:
        if key not in config:
            return False
    return True