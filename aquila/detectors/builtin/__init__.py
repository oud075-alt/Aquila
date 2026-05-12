"""Built-in detector definitions.

Each detector lives in its own module and exposes a ``DEFINITION``
plus a ``trigger`` callable so it can be auto-registered.
"""

from aquila.detectors.builtin import mspis_a_001

__all__ = ["mspis_a_001"]
