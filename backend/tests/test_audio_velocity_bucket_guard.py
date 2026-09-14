import unittest

# Bucket Transition & Noise Constants
UNCONFIRMED_JUMP_THRESHOLD_USES = 500_000
UNCONFIRMED_JUMP_MIN_HOURS = 2.0
COARSE_BUCKET_STALE_ZERO_HOURS = 6.0

def compute_official_velocity(count, prev_count, precision_bucket, prev_bucket, time_diff_hours):
    """
    Pure implementation of official count velocity calculation with bucket guards.
    """
    count_diff = count - prev_count
    velocity = 0.0
    velocity_is_null = False

    if count_diff < 0:
        velocity_is_null = True
    elif count_diff == 0:
        if precision_bucket == 'exact':
            velocity = 0.0
        elif time_diff_hours >= COARSE_BUCKET_STALE_ZERO_HOURS:
            velocity = 0.0
        else:
            velocity_is_null = True
    elif count_diff > UNCONFIRMED_JUMP_THRESHOLD_USES and time_diff_hours < UNCONFIRMED_JUMP_MIN_HOURS:
        velocity_is_null = True
    else:
        velocity = count_diff / time_diff_hours

    return None if velocity_is_null else velocity


class TestAudioVelocityBucketGuard(unittest.TestCase):
    def test_exact_bucket_zero_diff(self):
        # Exact count zero diff should log true zero velocity
        vel = compute_official_velocity(count=500, prev_count=500, precision_bucket='exact', prev_bucket='exact', time_diff_hours=1.0)
        self.assertEqual(vel, 0.0)

    def test_coarse_bucket_short_window_zero_diff(self):
        # Coarse bucket 'K' zero diff under 6h is indeterminate (quantization step)
        vel = compute_official_velocity(count=15000, prev_count=15000, precision_bucket='K', prev_bucket='K', time_diff_hours=2.0)
        self.assertIsNone(vel)

    def test_coarse_bucket_long_window_flat(self):
        # Coarse bucket 'K' zero diff over 6h indicates genuinely flat trend -> 0.0
        vel = compute_official_velocity(count=15000, prev_count=15000, precision_bucket='K', prev_bucket='K', time_diff_hours=6.5)
        self.assertEqual(vel, 0.0)

    def test_negative_count_diff_glitch(self):
        # Negative count diff from HTML parsing glitch must be nulled
        vel = compute_official_velocity(count=14900, prev_count=899000, precision_bucket='K', prev_bucket='K', time_diff_hours=0.5)
        self.assertIsNone(vel)

    def test_wild_unconfirmed_bucket_jump(self):
        # >500k jump in <2h with bucket change must be nulled
        vel = compute_official_velocity(count=899000, prev_count=14700, precision_bucket='K', prev_bucket='exact', time_diff_hours=0.3)
        self.assertIsNone(vel)

    def test_valid_bucket_crossing(self):
        # Legitimate bucket crossing (990 exact -> 1200 K in 2h) = +210 diff / 2h = 105.0/hr
        vel = compute_official_velocity(count=1200, prev_count=990, precision_bucket='K', prev_bucket='exact', time_diff_hours=2.0)
        self.assertEqual(vel, 105.0)

if __name__ == "__main__":
    unittest.main()
