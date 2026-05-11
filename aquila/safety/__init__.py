"""Safety Kernel — centralized "no trade signals" enforcer.

Closes audit gaps #4 / #16. Inspects every `LayerOutput` payload before it
is dispatched on the event bus. Rejects any payload whose serialized form
contains forbidden field names.
"""

from aquila.safety.kernel import (
    FORBIDDEN_SIGNAL_FIELDS,
    SafetyKernel,
    SafetyVerdict,
)

__all__ = ["FORBIDDEN_SIGNAL_FIELDS", "SafetyKernel", "SafetyVerdict"]
