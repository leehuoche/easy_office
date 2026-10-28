"""Deterministic end-to-end example without a server or real-time waiting."""
import json
from app.clock import ManualClock
from app.service import RestaurantService


def main():
    clock = ManualClock(0)
    service = RestaurantService(clock=clock)
    def order(key, table, dish, quantity=1, session=None):
        return service.submit_order(dict(request_id=key, table_id=table, session_id=session,
            items=[dict(dish_id=dish, quantity=quantity)]))
    a = order('a', 1, 'greens', 3)
    order('b', 2, 'tomato_eggs')
    added = False
    while True:
        tasks = [c['task'] for c in service.snapshot()['chefs'] if c['task']]
        if not tasks:
            break
        task = min(tasks, key=lambda t: (t['expected_finished_at'], t['chef_id']))
        clock.advance(max(0, task['expected_finished_at']-clock.now()))
        service.complete_task(task['chef_id'], task['id'])
        print(f"t={clock.now():.0f}s: chef {task['chef_id']} served table "
              f"{task['table_id']} {task['dish_name']}")
        if not added:
            order('add-a', 1, 'fried_rice', session=a['session_id'])
            added = True
    print(json.dumps(service.snapshot(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
