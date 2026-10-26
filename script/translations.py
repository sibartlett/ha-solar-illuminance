"""Generate translations/en.json from strings.json.

Home Assistant only resolves [%key:...] references for core integrations,
so custom integrations must ship them resolved.

Usage: python script/translations.py
"""

import json
from pathlib import Path
import re

import homeassistant

DOMAIN = "solar_illuminance"
ROOT = Path(__file__).parent.parent / "custom_components" / DOMAIN
COMMON = json.loads((Path(homeassistant.__file__).parent / "strings.json").read_text())
KEY_RE = re.compile(r"\[%key:([a-z0-9_:]+)%\]")


def lookup(key: str) -> str:
    """Return the string for a [%key:...%] reference.

    The reference is to Home Assistant's common strings, or, as in core, to
    another of this integration's strings.
    """
    node = COMMON
    if key.startswith(prefix := f"component::{DOMAIN}::"):
        node = strings
        key = key.removeprefix(prefix)
    for part in key.split("::"):
        node = node[part]
    return resolve(node)


def resolve(value):
    """Resolve the [%key:...%] references in a string, or a dict of them."""
    if isinstance(value, dict):
        return {k: resolve(v) for k, v in value.items()}
    return KEY_RE.sub(lambda m: lookup(m.group(1)), value)


strings = json.loads((ROOT / "strings.json").read_text())
(ROOT / "translations").mkdir(exist_ok=True)
(ROOT / "translations" / "en.json").write_text(
    json.dumps(resolve(strings), indent=2, ensure_ascii=False) + "\n"
)
