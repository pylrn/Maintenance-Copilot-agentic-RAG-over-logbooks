import os
from pathlib import Path

from dotenv import dotenv_values

# Automatically load isolated test environment if TEST_DATABASE_URL is not already set
ROOT = Path(__file__).resolve().parents[1]
env_test_path = ROOT / ".env.test"
if env_test_path.exists():
    for k, v in dotenv_values(env_test_path).items():
        if k and v and k not in os.environ:
            os.environ[k] = v
