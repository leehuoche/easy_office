"""Validate complete requests before any state is changed."""
from dataclasses import dataclass


class DomainError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def integer(value, name, minimum=1, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise DomainError(f"{name} must be an integer in the allowed range")
    return value


def identifier(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise DomainError(f"{name} must be a nonempty string of at most 128 characters")
    return value


@dataclass(frozen=True)
class OrderRequest:
    request_id: str
    table_id: int
    session_id: object
    items: tuple

    @classmethod
    def parse(cls, data, menu, table_count):
        if not isinstance(data, dict):
            raise DomainError("Request must be a JSON object")
        if set(data) - {"request_id", "table_id", "session_id", "items"}:
            raise DomainError("Unknown request fields; ordered_at is assigned by the server")
        request_id = identifier(data.get("request_id"), "request_id")
        table_id = integer(data.get("table_id"), "table_id", maximum=table_count)
        session_id = data.get("session_id")
        if session_id is not None:
            session_id = identifier(session_id, "session_id")
        rows = data.get("items")
        if not isinstance(rows, list) or not rows or len(rows) > 100:
            raise DomainError("items must contain 1 to 100 entries")
        quantities = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"dish_id", "quantity"}:
                raise DomainError("Each item requires dish_id and quantity")
            dish_id = row["dish_id"]
            if not isinstance(dish_id, str) or dish_id not in menu:
                raise DomainError("Unknown dish_id")
            quantity = integer(row["quantity"], "quantity", maximum=100)
            quantities[dish_id] = quantities.get(dish_id, 0) + quantity
        if sum(quantities.values()) > 100:
            raise DomainError("An order may contain at most 100 portions")
        return cls(request_id, table_id, session_id, tuple(sorted(quantities.items())))
