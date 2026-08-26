from django.test import SimpleTestCase

from .models import (
    PARADE_ABSENCE_COLUMNS,
    PARADE_AUTHORIZED_DEFAULTS,
    PARADE_RANK_COLUMNS,
    ParadeStateCompany,
    DutyPost,
    DutyAssignment,
)
from .services import parade_rank_key


class ParadeStateTests(SimpleTestCase):
    def test_reference_document_columns_are_available(self):
        self.assertEqual(len(PARADE_RANK_COLUMNS), 16)
        self.assertEqual(len(PARADE_ABSENCE_COLUMNS), 13)
        self.assertIn(("offr", "Offr"), PARADE_RANK_COLUMNS)
        self.assertIn(("teknaf", "Teknaf"), PARADE_ABSENCE_COLUMNS)
        self.assertEqual(sum(PARADE_AUTHORIZED_DEFAULTS.values()), 741)

    def test_present_strength_is_posted_less_absent(self):
        entry = ParadeStateCompany(
            posted_strength={"offr": 4, "cpl": 20},
            absent_strength={"offr": 1, "cpl": 3},
        )
        self.assertEqual(entry.posted_total, 24)
        self.assertEqual(entry.absent_total, 4)
        self.assertEqual(entry.present_total, 20)

    def test_personnel_ranks_map_to_parade_columns(self):
        self.assertEqual(parade_rank_key("Maj"), "offr")
        self.assertEqual(parade_rank_key("Lcpl"), "lcpl")
        self.assertEqual(parade_rank_key("Cook (U)"), "ck_u")

    def test_duty_post_combines_day_and_night_strength(self):
        post = DutyPost(day_strength=2, night_strength=6)
        self.assertEqual(post.total_strength, 8)

    def test_duty_assignment_has_day_and_night_shifts(self):
        self.assertEqual(
            dict(DutyAssignment.SHIFT_CHOICES),
            {"day": "Day", "night": "Night"},
        )
