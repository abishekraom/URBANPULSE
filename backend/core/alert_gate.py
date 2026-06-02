class AlertGate:
    """Small per-process alert cooldown gate.

    It suppresses repeated identical alert events while still allowing a new
    severity/reason/node combination through immediately. This is intentionally
    in-memory: good enough for demo stability, no DB migration required.
    """

    def __init__(self, cooldown_ms: int = 5000):
        self.cooldown_ms = int(cooldown_ms)
        self._last_emit = {}

    def should_emit(self, node_id: str, severity: str, reason: str, now_ms: int) -> bool:
        key = (str(node_id), str(severity), str(reason))
        last = self._last_emit.get(key)
        if last is not None and now_ms - last < self.cooldown_ms:
            return False
        self._last_emit[key] = int(now_ms)
        return True
