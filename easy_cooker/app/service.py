"""Single authority for order acceptance, assignment and completion."""
from dataclasses import asdict
from uuid import uuid4

from .clock import SystemClock
from .domain import MENU, Demand, Session, Task
from .schemas import DomainError, OrderRequest, integer
from .scheduler import Scheduler
from .store import MemoryStore


def new_id(prefix):
    return f"{prefix}_{uuid4().hex}"


class RestaurantService:
    def __init__(self, chef_count=2, table_count=8, first_course_seconds=900,
                 clock=None, scheduler=None):
        integer(chef_count, "chef_count", maximum=100)
        integer(table_count, "table_count", maximum=1000)
        integer(first_course_seconds, "first_course_seconds")
        self.store = MemoryStore(chef_count)
        self.menu = MENU.copy()
        self.table_count = table_count
        self.first_course_seconds = first_course_seconds
        self.clock = clock or SystemClock()
        self.scheduler = scheduler or Scheduler()

    def get_menu(self):
        return [asdict(d) for d in self.menu.values()]

    def submit_order(self, data):
        request = OrderRequest.parse(data, self.menu, self.table_count)
        with self.store.lock:
            old = self.store.requests.get(request.request_id)
            if old:
                if old[0] != request:
                    raise DomainError("request_id already used with different content", 409)
                return dict(old[1])
            now = self.clock.now()
            if request.session_id is None:
                if request.table_id in self.store.active_tables:
                    raise DomainError("Table occupied; add dishes using its session_id", 409)
                session = Session(new_id("session"), request.table_id, now,
                                  now + self.first_course_seconds,
                                  self.store.next_sequence())
                self.store.sessions[session.id] = session
                self.store.active_tables[request.table_id] = session.id
            else:
                session = self.store.sessions.get(request.session_id)
                if session is None:
                    raise DomainError("Session not found", 404)
                if session.table_id != request.table_id or session.closed_at is not None:
                    raise DomainError("Session is closed or belongs to another table", 409)
            order_id = new_id("order")
            demand_ids = []
            for dish_id, quantity in request.items:
                for _ in range(quantity):
                    demand = Demand(new_id("demand"), session.id, order_id, dish_id,
                                    now, self.store.next_sequence())
                    self.store.demands[demand.id] = demand
                    session.demand_ids.append(demand.id)
                    demand_ids.append(demand.id)
            self.store.orders[order_id] = {"order_id": order_id,
                "session_id": session.id, "ordered_at": now, "demand_ids": demand_ids}
            self._dispatch(now)
            response = {"accepted": True, "order_id": order_id,
                        "session_id": session.id, "ordered_at": now,
                        "first_course_deadline": session.deadline}
            self.store.requests[request.request_id] = (request, dict(response))
            return response

    def _dispatch(self, now):
        # Always called inside the same lock as the state transition.
        for chef in self.store.chefs.values():
            if chef.task_id is not None:
                continue
            demand_id = self.scheduler.choose(self.store, now)
            if demand_id is None:
                break
            demand = self.store.demands[demand_id]
            duration = self.menu[demand.dish_id].duration_seconds
            task = Task(new_id("task"), chef.id, demand.id, now, now + duration)
            self.store.tasks[task.id] = task
            chef.task_id = task.id
            demand.task_id = task.id
            demand.status = "cooking"

    def _task_view(self, task):
        result = asdict(task)
        demand = self.store.demands[task.demand_id]
        session = self.store.sessions[demand.session_id]
        result.update(dish_id=demand.dish_id, dish_name=self.menu[demand.dish_id].name,
                      session_id=session.id, table_id=session.table_id)
        return result

    def get_chef(self, chef_id):
        with self.store.lock:
            chef = self.store.chefs.get(chef_id)
            if chef is None:
                raise DomainError("Chef not found", 404)
            return {"chef_id": chef.id, "task": self._task_view(
                self.store.tasks[chef.task_id]) if chef.task_id else None}

    def complete_task(self, chef_id, task_id):
        with self.store.lock:
            chef = self.store.chefs.get(chef_id)
            task = self.store.tasks.get(task_id)
            if chef is None or task is None:
                raise DomainError("Chef or task not found", 404)
            if task.chef_id != chef_id:
                raise DomainError("Task belongs to another chef", 409)
            # A retry must never complete the chef's next task.
            if task.status == "completed":
                return self._task_view(task)
            now = self.clock.now()
            if now < task.expected_finished_at:
                raise DomainError("Known cooking duration has not elapsed", 409)
            if chef.task_id != task.id:
                raise DomainError("Task is not active", 409)
            task.status = "completed"
            task.completed_at = now
            demand = self.store.demands[task.demand_id]
            demand.status = "served"
            demand.served_at = now
            session = self.store.sessions[demand.session_id]
            if session.first_served_at is None:
                session.first_served_at = now
            chef.task_id = None
            self._dispatch(now)
            return self._task_view(task)

    def get_session(self, session_id):
        with self.store.lock:
            session = self.store.sessions.get(session_id)
            if session is None:
                raise DomainError("Session not found", 404)
            result = asdict(session)
            now = self.clock.now()
            pending_first = session.first_served_at is None
            result.update(
                first_course_status=("overdue" if now > session.deadline else "waiting")
                    if pending_first else
                    ("late" if session.first_served_at > session.deadline else "on_time"),
                first_course_wait_seconds=(now if pending_first else session.first_served_at)
                    - session.ordered_at,
                demands=[asdict(self.store.demands[j]) for j in session.demand_ids])
            return result

    def close_session(self, session_id):
        with self.store.lock:
            session = self.store.sessions.get(session_id)
            if session is None:
                raise DomainError("Session not found", 404)
            if any(self.store.demands[j].status != "served" for j in session.demand_ids):
                raise DomainError("Cannot close a session with outstanding dishes", 409)
            if session.closed_at is None:
                session.closed_at = self.clock.now()
                del self.store.active_tables[session.table_id]
            return self.get_session(session_id)

    def snapshot(self):
        with self.store.lock:
            return {"now": self.clock.now(),
                    "chefs": [self.get_chef(i) for i in self.store.chefs],
                    "sessions": [self.get_session(i) for i in self.store.sessions]}
