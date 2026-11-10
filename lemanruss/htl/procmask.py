"""Seeker-Proc v2.0 trigger masking switch.

v2.0 rule: no payload acts while the core's own reset is active (`trigger & ~reset_active`), so
the host's hold logic sees its original signals and its registers load known values. Setting
`LEMANRUSS_PROC_MASK=0` rebuilds a pre-v2.0 (unmasked) circuit, used only to re-run the released
rc3, Si rc2 and early v2.0 circuits through the strict four-state gates.
"""

from __future__ import annotations

import os


def masking_on() -> bool:
    return os.environ.get("LEMANRUSS_PROC_MASK", "1") != "0"
