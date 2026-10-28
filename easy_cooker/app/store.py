"""In-memory state; all access is serialized by RestaurantService."""
from threading import RLock
from .domain import Chef


class MemoryStore:
    def __init__(self, chef_count):
        self.lock = RLock()
        self.sessions = {}
        self.active_tables = {}
        self.demands = {}
        self.tasks = {}
        self.orders = {}
        self.requests = {}
        self.chefs = {i: Chef(i) for i in range(1, chef_count + 1)}
        self.sequence = 0

    def next_sequence(self):
        self.sequence += 1
        return self.sequence
