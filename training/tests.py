from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.template.defaultfilters import date as format_date
from django.urls import reverse
from django.utils import timezone

from authentication.models import User
from common.models import Organization
from common.test_factories import make_org, make_soldier, make_user
from training.models import LeaveState, UnitTrainingCyclePlan
from training.services import leave_board_url


STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


class TrainingHomeTests(TestCase):
    def test_g_matter_template_uses_numbered_section_cards(self):
        from django.template.loader import get_template

        source = get_template("training/training_home.html").template.source
        for label in (
            "Trg Plan",
            "IPFT State",
            "RET State",
            "Spd March State",
            "Aslt Course State",
            "Spl State",
        ):
            self.assertIn(label, source)
        self.assertEqual(source.count("section-card-link d-block h-100"), 6)
        self.assertEqual(source.count("card section-card h-100"), 6)
        for serial in range(1, 7):
            self.assertIn(f'data-serial="{serial:02d}"', source)


class LeavePermissionTests(TestCase):
    def setUp(self):
        self.company = make_org("A Company", parent=make_org("1 BIR"))
        self.soldier = make_soldier(self.company)
        self.admin = make_user("admin", role=User.ROLE_ADMIN)
        self.officer = make_user(
            "officer",
            role=User.ROLE_OFFICER,
            organizations=[self.company],
        )

    def test_admin_can_apply_hospital_leave(self):
        self.client.force_login(self.admin)
        today = timezone.localdate()
        response = self.client.post(
            reverse("training:leave_manage", args=[self.soldier.pk]),
            {
                "slot": LeaveState.SLOT_HOSP,
                "from_date": today.isoformat(),
                "to_date": (today + timedelta(days=2)).isoformat(),
                "remarks": "Ward",
            },
        )
        self.assertEqual(response.status_code, 302)
        leave = LeaveState.objects.get()
        self.assertEqual(leave.slot, LeaveState.SLOT_HOSP)
        self.assertEqual(leave.leave_type.name, "Hospital")
        self.assertEqual(leave.status, LeaveState.STATUS_PENDING)

    def test_admin_can_approve_leave(self):
        self.client.force_login(self.admin)
        today = timezone.localdate()
        self.client.post(
            reverse("training:leave_manage", args=[self.soldier.pk]),
            {
                "slot": LeaveState.SLOT_P_LEAVE,
                "from_date": today.isoformat(),
                "to_date": today.isoformat(),
            },
        )
        leave = LeaveState.objects.get()
        response = self.client.post(
            reverse("training:leave_decide", args=[leave.pk]),
            {"action": "approve", "next": "https://evil.example"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            leave_board_url(self.soldier, today.year),
        )
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveState.STATUS_APPROVED)


@override_settings(STORAGES=STORAGES)
class ClerkLeaveWorkflowTests(TestCase):
    def setUp(self):
        battalion = make_org("1 BIR")
        self.company = make_org("A Company", parent=battalion)
        self.other_company = make_org("B Company", parent=battalion)
        self.soldier = make_soldier(self.company)
        self.clerk = make_user(
            "coy_clerk",
            role=User.ROLE_CLERK,
            organizations=[self.company],
        )
        self.officer = make_user(
            "coy_officer",
            role=User.ROLE_OFFICER,
            organizations=[self.company],
        )
        self.other_officer = make_user(
            "other_officer",
            role=User.ROLE_OFFICER,
            organizations=[self.other_company],
        )
        self.co = make_user("unit_co", role=User.ROLE_CO)

    def _apply_leave(self, slot, from_date=None, to_date=None):
        today = timezone.localdate()
        from_date = from_date or today
        to_date = to_date or today
        self.client.force_login(self.clerk)
        return self.client.post(
            reverse("training:leave_manage", args=[self.soldier.pk]),
            {
                "slot": slot,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
            },
        )

    def test_clerk_apply_form_offers_only_p_and_c_leave(self):
        self.client.force_login(self.clerk)
        response = self.client.get(
            reverse("training:leave_manage", args=[self.soldier.pk])
        )
        self.assertEqual(response.status_code, 200)
        slots = [value for value, _label in response.context["form"].fields["slot"].choices]
        self.assertEqual(slots[0], LeaveState.SLOT_P_LEAVE)
        self.assertIn(LeaveState.SLOT_C_LEAVE_1, slots)
        self.assertNotIn(LeaveState.SLOT_HOSP, slots)
        self.assertNotIn(LeaveState.SLOT_COURSE, slots)

    def test_clerk_can_apply_privilege_leave(self):
        today = timezone.localdate()
        response = self._apply_leave(LeaveState.SLOT_P_LEAVE)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, leave_board_url(self.soldier, today.year))
        leave = LeaveState.objects.get()
        self.assertEqual(leave.slot, LeaveState.SLOT_P_LEAVE)
        self.assertEqual(leave.status, LeaveState.STATUS_PENDING)
        self.assertEqual(leave.applied_by, self.clerk)

        board = self.client.get(response.url)
        self.assertEqual(board.status_code, 200)
        self.assertContains(board, "Pending Leave Applications")
        self.assertContains(board, self.soldier.name)

    def test_clerk_can_apply_casual_leave(self):
        response = self._apply_leave(LeaveState.SLOT_C_LEAVE_1)
        self.assertEqual(response.status_code, 302)
        leave = LeaveState.objects.get()
        self.assertEqual(leave.slot, LeaveState.SLOT_C_LEAVE_1)
        self.assertEqual(leave.status, LeaveState.STATUS_PENDING)

    def test_clerk_cannot_apply_hospital_or_course_leave(self):
        for slot in (LeaveState.SLOT_HOSP, LeaveState.SLOT_COURSE):
            response = self._apply_leave(slot)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(LeaveState.objects.count(), 0)
            self.assertTrue(response.context["form"].has_error("slot"))

    def test_company_officer_can_approve_and_leave_state_updates(self):
        today = timezone.localdate()
        self._apply_leave(
            LeaveState.SLOT_P_LEAVE,
            from_date=today,
            to_date=today + timedelta(days=4),
        )
        leave = LeaveState.objects.get()
        self.client.force_login(self.officer)
        board_url = leave_board_url(self.soldier, today.year)
        response = self.client.post(
            reverse("training:leave_decide", args=[leave.pk]),
            {"action": "approve", "next": board_url},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, board_url)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveState.STATUS_APPROVED)
        self.assertEqual(leave.approved_by, self.officer)

        page = self.client.get(board_url)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "Pending Leave Applications")
        row = next(soldier for soldier in page.context["soldiers"] if soldier.pk == self.soldier.pk)
        self.assertEqual(row.p_leave.pk, leave.pk)
        self.assertEqual(row.p_leave_days, 5)
        self.assertContains(page, format_date(today, "d M Y"))

    def test_other_company_officer_cannot_approve(self):
        self._apply_leave(LeaveState.SLOT_P_LEAVE)
        leave = LeaveState.objects.get()
        self.client.force_login(self.other_officer)
        response = self.client.post(
            reverse("training:leave_decide", args=[leave.pk]),
            {"action": "approve"},
        )
        self.assertEqual(response.status_code, 404)
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveState.STATUS_PENDING)

    def test_co_can_approve_leave(self):
        today = timezone.localdate()
        self._apply_leave(LeaveState.SLOT_C_LEAVE_1)
        leave = LeaveState.objects.get()
        self.client.force_login(self.co)
        response = self.client.post(
            reverse("training:leave_decide", args=[leave.pk]),
            {"action": "approve"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, leave_board_url(self.soldier, today.year))
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveState.STATUS_APPROVED)
        self.assertEqual(leave.approved_by, self.co)

        page = self.client.get(leave_board_url(self.soldier, today.year))
        row = next(soldier for soldier in page.context["soldiers"] if soldier.pk == self.soldier.pk)
        self.assertEqual(row.c_leave_days, leave.no_days)
        self.assertIsNotNone(row.casual_by_number.get(1))


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class CasualLeaveColumnTests(TestCase):
    def setUp(self):
        self.company = make_org("A Company", parent=make_org("1 BIR"))
        self.soldier = make_soldier(self.company)
        self.admin = make_user("admin", role=User.ROLE_ADMIN)

    def test_board_shows_individual_casual_leave_columns(self):
        self.client.force_login(self.admin)
        start = date(timezone.localdate().year, 1, 1)
        for index in range(1, 7):
            from_date = start + timedelta(days=index * 10)
            response = self.client.post(
                reverse("training:leave_manage", args=[self.soldier.pk]),
                {
                    "slot": LeaveState.casual_slot(index),
                    "from_date": from_date.isoformat(),
                    "to_date": (from_date + timedelta(days=1)).isoformat(),
                },
            )
            self.assertEqual(response.status_code, 302)
            leave = LeaveState.objects.get(slot=LeaveState.casual_slot(index))
            self.client.post(
                reverse("training:leave_decide", args=[leave.pk]),
                {"action": "approve"},
            )

        page = self.client.get(
            reverse("training:leave_list"),
            {"company": self.company.pk, "year": timezone.localdate().year},
        )
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "C Lve-1 Dt")
        self.assertContains(page, "C Lve-2 Dt")
        self.assertContains(page, "C Lve-6 Dt")
        self.assertNotContains(page, "C Lve-2,3,4,5")
        self.assertEqual(page.context["casual_colspan"], 12)


class YearlyPlanGetTests(TestCase):
    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        }
    )
    def test_get_does_not_create_cycle_rows(self):
        make_org("1 BIR")
        admin = make_user("admin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.get(reverse("training:yearly_plan_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UnitTrainingCyclePlan.objects.count(), 0)


@override_settings(STORAGES=STORAGES)
class RelatedFormTemplateTests(TestCase):
    def test_ipft_edit_renders(self):
        soldier = make_soldier(make_org("A Company", parent=make_org("1 BIR")))
        admin = make_user("ipftadmin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.get(reverse("training:ipft_edit", args=[soldier.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IPFT")
        self.assertContains(response, "Add more")


def make_state_board_tree(prefix):
    unit = make_org(f"{prefix} Unit", kind=Organization.KIND_UNIT)
    company = make_org(
        f"{prefix} Company",
        parent=unit,
        kind=Organization.KIND_COMPANY,
    )
    platoon = make_org(
        f"{prefix} Pl-1",
        parent=company,
        kind=Organization.KIND_PLATOON,
    )
    return unit, company, platoon


@override_settings(STORAGES=STORAGES)
class TrainingStateBoardTests(TestCase):
    def _assert_board_dropdown(self, response, unit, company, platoon):
        names = [str(organization) for organization in response.context["organizations"]]
        self.assertIn(str(unit), names)
        self.assertIn(str(company), names)
        self.assertNotIn(str(platoon), names)

    def test_ipft_summary_shows_unit_and_company_not_platoon(self):
        unit, company, platoon = make_state_board_tree("IPFT Board")
        make_soldier(unit, army_number="BA-IPFT-U", name="Unit HQ Soldier")
        make_soldier(platoon, army_number="BA-IPFT-P", name="Platoon Soldier")
        admin = make_user("ipftboard", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(reverse("training:ipft_list"))

        self.assertEqual(response.status_code, 200)
        labels = [str(row["label"]) for row in response.context["summary_rows"]]
        self.assertIn(str(unit), labels)
        self.assertIn(str(company), labels)
        self.assertNotIn(str(platoon), labels)
        self.assertNotContains(response, "Coy HQ")
        self.assertNotContains(response, ">Pl-1<")
        self._assert_board_dropdown(response, unit, company, platoon)
        posted = {
            str(row["label"]): row["posted"] for row in response.context["summary_rows"]
        }
        self.assertEqual(posted[str(unit)], 1)
        self.assertEqual(posted[str(company)], 1)

    def test_ipft_company_filter_includes_platoon_soldiers(self):
        _unit, company, platoon = make_state_board_tree("IPFT Drill")
        make_soldier(platoon, army_number="BA-IPFT-D", name="Drill Soldier")
        admin = make_user("ipftdrill", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(
            reverse("training:ipft_list"),
            {"organization": str(company.pk)},
        )

        self.assertEqual(response.status_code, 200)
        soldiers = response.context["individual_soldiers"]
        self.assertEqual(len(soldiers), 1)
        self.assertEqual(soldiers[0].army_number, "BA-IPFT-D")

    def test_ret_summary_shows_unit_and_company_not_platoon(self):
        unit, company, platoon = make_state_board_tree("RET Board")
        make_soldier(platoon, army_number="BA-RET-P", name="RET Platoon Soldier")
        admin = make_user("retboard", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(reverse("training:ret_list"))

        self.assertEqual(response.status_code, 200)
        labels = [str(row["label"]) for row in response.context["classification_rows"]]
        self.assertIn(str(unit), labels)
        self.assertIn(str(company), labels)
        self.assertNotIn(str(platoon), labels)
        self._assert_board_dropdown(response, unit, company, platoon)

    def test_speed_march_summary_shows_unit_and_company_not_platoon(self):
        unit, company, platoon = make_state_board_tree("March Board")
        make_soldier(platoon, army_number="BA-SPD-P", name="March Platoon Soldier")
        admin = make_user("marchboard", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(reverse("training:speed_march_list"))

        self.assertEqual(response.status_code, 200)
        labels = [str(row["label"]) for row in response.context["rows"]]
        self.assertIn(str(unit), labels)
        self.assertIn(str(company), labels)
        self.assertNotIn(str(platoon), labels)
        self._assert_board_dropdown(response, unit, company, platoon)

    def test_assault_course_summary_shows_unit_and_company_not_platoon(self):
        unit, company, platoon = make_state_board_tree("Aslt Board")
        make_soldier(platoon, army_number="BA-ASLT-P", name="Aslt Platoon Soldier")
        admin = make_user("asltboard", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(reverse("training:assault_course_list"))

        self.assertEqual(response.status_code, 200)
        labels = [str(row["label"]) for row in response.context["rows"]]
        self.assertIn(str(unit), labels)
        self.assertIn(str(company), labels)
        self.assertNotIn(str(platoon), labels)
        self._assert_board_dropdown(response, unit, company, platoon)

    def test_qual_filter_lists_unit_and_company_and_includes_platoon_soldiers(self):
        unit, company, platoon = make_state_board_tree("Qual Board")
        make_soldier(platoon, army_number="BA-QUAL-P", name="Qual Platoon Soldier")
        admin = make_user("qualboard", role=User.ROLE_ADMIN)
        self.client.force_login(admin)

        listing = self.client.get(reverse("training:qual_list"))
        self.assertEqual(listing.status_code, 200)
        self._assert_board_dropdown(listing, unit, company, platoon)

        filtered = self.client.get(
            reverse("training:qual_list"),
            {"organization": str(company.pk)},
        )
        self.assertEqual(filtered.status_code, 200)
        army_numbers = [soldier.army_number for soldier in filtered.context["soldiers"]]
        self.assertIn("BA-QUAL-P", army_numbers)
