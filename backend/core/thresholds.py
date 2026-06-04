from copy import deepcopy


def thresholds_for_node(config: dict, node_id: str) -> dict:
    """Return global thresholds merged with optional per-node overrides."""
    thresholds = deepcopy(config.get("thresholds", {}))
    overrides = thresholds.pop("node_overrides", {}) or {}
    node_override = overrides.get(str(node_id), {}) or {}

    for section, values in node_override.items():
        if isinstance(values, dict):
            base = thresholds.setdefault(section, {})
            if isinstance(base, dict):
                base.update(values)
            else:
                thresholds[section] = deepcopy(values)
        else:
            thresholds[section] = values

    return thresholds
