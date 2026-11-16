import unittest
from limits import RuntimeLimits, CapacityError

class LimitTests(unittest.TestCase):
    def test_budget_cost_and_expiry(self):
        now=[100]
        limits=RuntimeLimits(per_minute=5,clock=lambda:now[0])
        self.assertTrue(limits.admit(3));self.assertTrue(limits.admit(2))
        self.assertFalse(limits.admit())
        now[0]=159;self.assertFalse(limits.admit())
        now[0]=160;self.assertTrue(limits.admit(5))

    def test_capacity_released_on_exception(self):
        limits=RuntimeLimits(jobs=1)
        with self.assertRaises(RuntimeError):
            with limits.job():
                with self.assertRaises(CapacityError):
                    with limits.job():pass
                raise RuntimeError('failure')
        with limits.job():pass

if __name__=='__main__':unittest.main()
