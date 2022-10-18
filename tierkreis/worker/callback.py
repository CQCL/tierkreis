from typing import Optional


# This lives in its own file to prevent cyclic imports
class CallbackHook:
    callback: Optional[tuple[str, int]] = None
