"""Create config/users.json with hashed API keys and print plaintext keys ONCE.
Run:  python scripts/bootstrap_users.py          (add --force to overwrite)
Plaintext keys are written to .demo_keys.txt (git-ignored). Only hashes are committed.
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from src.security import hash_key, new_api_key

OUT = "config/users.json"
KEYS_FILE = ".demo_keys.txt"

USERS = {
    "admin": {"sources": ["*"], "rate_limit_per_min": 30},
    "alice": {"sources": ["Health Protector Policy Wording.pdf",
                          "a-plus-health-insurance-policy-wording.pdf"],
              "rate_limit_per_min": 20},
    "bob": {"sources": ["religare-health-care-advantage-policy-wordings.pdf",
                        "20240325_Prospectus_IHIP.pdf"],
            "rate_limit_per_min": 20},
    "guest": {"sources": [], "rate_limit_per_min": 5},
}

if os.path.exists(OUT) and "--force" not in sys.argv:
    sys.exit(f"{OUT} exists. Re-run with --force to regenerate (old keys stop working).")

plain, users = {}, {}
for name, cfg in USERS.items():
    key = new_api_key()
    plain[name] = key
    users[name] = {"key_hash": hash_key(key), **cfg}

os.makedirs("config", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"users": users}, f, indent=2)
with open(KEYS_FILE, "w", encoding="utf-8") as f:
    for name, key in plain.items():
        f.write(f"{name}: {key}\n")
print(f"Wrote {OUT} (hashes only). Plaintext keys saved to {KEYS_FILE}:")
for name, key in plain.items():
    print(f"  {name}: {key}")