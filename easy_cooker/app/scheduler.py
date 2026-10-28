"""Conservative FIFO first-course policy, replaceable independently of APIs."""


class Scheduler:
    def choose(self, store, now):
        """Return one pending demand ID; caller commits and calls again.

        Only the earliest session without a first course may start a first
        course. Until that course completes, later first courses wait.
        Already-served sessions may use the other chefs in FIFO demand order.
        """
        waiting = [s for s in store.sessions.values()
                   if s.closed_at is None and s.first_served_at is None]
        first = min(waiting, key=lambda s: s.sequence) if waiting else None
        if first:
            in_progress = any(store.demands[j].status == "cooking" for j in first.demand_ids)
            if not in_progress:
                candidates = [store.demands[j] for j in first.demand_ids
                              if store.demands[j].status == "pending"]
                if candidates:
                    return min(candidates, key=lambda j: j.sequence).id
        candidates = [j for j in store.demands.values()
                      if j.status == "pending"
                      and store.sessions[j.session_id].first_served_at is not None]
        return min(candidates, key=lambda j: j.sequence).id if candidates else None
