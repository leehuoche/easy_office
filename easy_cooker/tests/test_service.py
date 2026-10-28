import unittest
from concurrent.futures import ThreadPoolExecutor
from app.clock import ManualClock
from app.service import RestaurantService
from app.schemas import DomainError


def order(key, table=1, quantity=1, session=None, dish='greens'):
    return dict(request_id=key, table_id=table, session_id=session,
                items=[dict(dish_id=dish, quantity=quantity)])


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.clock = ManualClock(1000)
        self.s = RestaurantService(clock=self.clock)

    def finish(self, chef=1):
        task = self.s.get_chef(chef)['task']
        self.clock.advance(max(0, task['expected_finished_at']-self.clock.now()))
        return self.s.complete_task(chef, task['id'])

    def test_fairness_and_cross_table_dispatch(self):
        a = self.s.submit_order(order('a', quantity=3))
        b = self.s.submit_order(order('b', table=2))
        self.assertIsNone(self.s.get_chef(2)['task'])
        self.finish()
        self.assertEqual(self.s.get_chef(1)['task']['session_id'], b['session_id'])
        self.assertEqual(self.s.get_chef(2)['task']['session_id'], a['session_id'])
        self.finish(2)
        self.assertIsNone(self.s.get_session(b['session_id'])['first_served_at'])
        self.finish(1)
        self.assertLessEqual(self.s.get_session(a['session_id'])['first_served_at'],
                             self.s.get_session(b['session_id'])['first_served_at'])

    def test_addition_preserves_first_course_and_deadline(self):
        a = self.s.submit_order(order('a'))
        self.finish()
        before = self.s.get_session(a['session_id'])
        self.clock.advance(100)
        self.s.submit_order(order('add', session=a['session_id']))
        after = self.s.get_session(a['session_id'])
        for key in ('first_served_at', 'ordered_at', 'deadline'):
            self.assertEqual(before[key], after[key])
        self.assertEqual(len(after['demands']), 2)
        self.assertGreater(after['demands'][1]['ordered_at'], before['ordered_at'])

    def test_concurrent_idempotency_and_conflict(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.s.submit_order(order('a')), range(30)))
        self.assertTrue(all(r == results[0] for r in results))
        self.assertEqual(len(self.s.store.demands), 1)
        with self.assertRaises(DomainError):
            self.s.submit_order(order('a', table=2))

    def test_validation_is_atomic(self):
        for request in (order('bad', dish='missing'), order('bad', quantity=True),
                        order('bad', dish=[]), order('bad', quantity=0),
                        {**order('bad'), 'ordered_at': 0}):
            with self.assertRaises(DomainError):
                self.s.submit_order(request)
        self.assertEqual(self.s.store.sessions, {})
        self.assertEqual(self.s.store.demands, {})

    def test_completion_ownership_duration_and_retry(self):
        self.s.submit_order(order('a', quantity=3))
        task = self.s.get_chef(1)['task']
        for chef in (1, 2):
            with self.assertRaises(DomainError):
                self.s.complete_task(chef, task['id'])
        completed = self.finish()
        next_task = self.s.get_chef(1)['task']
        self.assertNotEqual(next_task['id'], task['id'])
        self.assertEqual(self.s.complete_task(1, task['id']), completed)
        self.assertEqual(self.s.get_chef(1)['task'], next_task)

    def test_started_task_not_replaced(self):
        self.s.submit_order(order('a'))
        task = self.s.get_chef(1)['task']
        for i in range(2, 6):
            self.s.submit_order(order(str(i), table=i))
        self.assertEqual(self.s.get_chef(1)['task'], task)

    def test_session_lifecycle_and_wrong_table(self):
        a = self.s.submit_order(order('a'))
        with self.assertRaises(DomainError):
            self.s.close_session(a['session_id'])
        with self.assertRaises(DomainError):
            self.s.submit_order(order('new'))
        with self.assertRaises(DomainError):
            self.s.submit_order(order('wrong', table=2, session=a['session_id']))
        self.finish()
        self.s.close_session(a['session_id'])
        b = self.s.submit_order(order('new'))
        self.s.close_session(a['session_id'])
        self.assertEqual(self.s.store.active_tables[1], b['session_id'])
        with self.assertRaises(DomainError):
            self.s.submit_order(order('old-add', session=a['session_id']))

    def test_deadline_failure_is_visible(self):
        s = RestaurantService(first_course_seconds=60, clock=self.clock)
        a = s.submit_order(order('a'))
        self.clock.advance(61)
        self.assertEqual(s.get_session(a['session_id'])['first_course_status'], 'overdue')
        self.clock.advance(119)
        s.complete_task(1, s.get_chef(1)['task']['id'])
        self.assertEqual(s.get_session(a['session_id'])['first_course_status'], 'late')

    def test_concurrent_additions_no_duplicate_assignments(self):
        a = self.s.submit_order(order('a'))
        self.finish()
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: self.s.submit_order(order(str(i), session=a['session_id'])), range(20)))
        self.assertEqual(len(self.s.store.demands), 21)
        active = [t for t in self.s.store.tasks.values() if t.status == 'cooking']
        self.assertEqual(len(active), 2)
        self.assertEqual(len({t.demand_id for t in active}), 2)
        count = len(self.s.store.tasks)
        for _ in range(10):
            self.s.get_chef(1)
        self.assertEqual(len(self.s.store.tasks), count)
