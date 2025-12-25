import json
import os
from typing import Dict, Any

def load_config(version: str = 'v1') -> Dict[str, Any]:
    file_path = f"data/sample_config_{version}.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        return {}