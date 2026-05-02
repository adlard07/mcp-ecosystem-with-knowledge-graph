import logging
from datetime import datetime, timezone
from uuid import uuid4

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    # filename="/tmp/app.log",
)


def generate_uuid() -> str:
    """Generates a random UUID string."""
    return str(uuid4())


def get_current_datetime() -> datetime:
    return datetime.now(timezone.utc)


def get_current_timestamp() -> str:
    return get_current_datetime().isoformat()


def _build_update_expression(update_data: dict) -> tuple[str, dict, dict]:
    """Returns (update_expression, attr_names, attr_values)."""
    parts, names, values = [], {}, {}
    for key, value in update_data.items():
        if value is None:
            continue
        nk, vk = f"#{key}", f":{key}"
        parts.append(f"{nk} = {vk}")
        names[nk] = key
        values[vk] = value
    return "SET " + ", ".join(parts), names, values
