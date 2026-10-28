"""Domain records; one demand and one task per portion in V1."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Dish:
    id: str
    name: str
    duration_seconds: int


MENU = {
    dish.id: dish for dish in (
        Dish("fried_rice", "蛋炒饭", 300),
        Dish("tomato_eggs", "番茄炒蛋", 240),
        Dish("greens", "清炒时蔬", 180),
        Dish("braised_tofu", "红烧豆腐", 360),
        Dish("chicken", "宫保鸡丁", 420),
    )
}


@dataclass
class Session:
    id: str
    table_id: int
    ordered_at: float
    deadline: float
    sequence: int
    first_served_at: Optional[float] = None
    closed_at: Optional[float] = None
    demand_ids: list = field(default_factory=list)


@dataclass
class Demand:
    id: str
    session_id: str
    order_id: str
    dish_id: str
    ordered_at: float
    sequence: int
    status: str = "pending"
    task_id: Optional[str] = None
    served_at: Optional[float] = None


@dataclass
class Chef:
    id: int
    task_id: Optional[str] = None


@dataclass
class Task:
    id: str
    chef_id: int
    demand_id: str
    started_at: float
    expected_finished_at: float
    status: str = "cooking"
    completed_at: Optional[float] = None
