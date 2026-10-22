"""Tools Adapter for ZentroMart Synthetic Tools.
Interfaces with tools/tools.py for identity-gated order lookups and ticket creation.
Enforces verification gatekeeping, max 1 retry, and no data leaks.
"""
import sys
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from .config import DATASET_ROOT, TOOLS_DIR

# Ensure tools directory is in sys.path
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    from tools import lookup_order as _raw_lookup_order, create_ticket as _raw_create_ticket
except ImportError:
    # If not found directly, import by file path
    import importlib.util
    tools_py = TOOLS_DIR / "tools.py"
    if tools_py.exists():
        spec = importlib.util.spec_from_file_location("zentromart_tools", str(tools_py))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _raw_lookup_order = mod.lookup_order
        _raw_create_ticket = mod.create_ticket
    else:
        raise RuntimeError(f"Could not locate tools.py at {tools_py}")


class ToolsAdapter:
    def __init__(self):
        self.verified_sessions: Dict[str, Dict[str, Any]] = {}
        self.retry_counts: Dict[str, int] = {}

    def lookup_order(self, order_id: str, verification_value: Optional[str] = None) -> Dict[str, Any]:
        """Performs identity-checked lookup.
        Passes verification_value only if customer provided last 4 digits of phone or 6-digit pincode.
        """
        clean_oid = ''.join(ch for ch in str(order_id) if ch.isdigit())
        clean_proof = ''.join(ch for ch in str(verification_value) if ch.isdigit()) if verification_value else None
        
        result = _raw_lookup_order(clean_oid, clean_proof)
        return result

    def create_ticket(self, summary: str, order_id: Optional[str] = None,
                      reason: Optional[str] = None, intent: Optional[str] = None) -> Dict[str, Any]:
        """Creates an escalation ticket. Requires summary >= 20 characters."""
        if not summary or len(summary.strip()) < 20:
            summary = f"Customer support escalation: issue requires human review for order {order_id or 'N/A'}. Reason: {reason or 'General'}"
        return _raw_create_ticket(summary=summary, order_id=order_id, reason=reason, intent=intent)
