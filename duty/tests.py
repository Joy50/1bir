from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from authentication.models import User
from common.models import ServiceHistory
from common.test_factories import make_org, make_soldier, make_user
from duty.models import DutyAssignment, DutyPost, DutyTour, ParadeState
from duty.services import generate_parade_state, get_or_create_open_tour


STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


@override_settings(STORAGES=STORAGES)
class ParadeStateWriteTests(TestCase):
    def setUp(self):
        self.battalion = make_org("1 BIR")
        self.company = make_org("A Company", parent=self.battalion)
        self.admin = make_user("admin", role=User.ROLE_ADMIN)
        self.soldier = make_soldier(self.company)

    def test_generate_does_not_rewrite_existing_state_without_refresh(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        state = generate_parade_state(self.admin, yesterday, refresh=True)
        original_updated = state.updated_at
        again = generate_parade_state(self.admin, yesterday)
        self.assertEqual(again.pk, state.pk)
        again.refresh_from_db()
        self.assertEqual(again.updated_at, original_updated)

    def test_auth_row_counts_live_personnel(self):
        state = generate_parade_state(self.admin, timezone.localdate(), refresh=True)
        self.client.force_login(self.admin)
        page = self.client.get(reverse("duty:parade_state_edit", args=[state.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["authorized_total"], 1)
        self.assertEqual(page.context["posted_grand_total"], 1)

        make_soldier(self.company, army_number="BA-LIVE")
        refreshed = self.client.get(reverse("duty:parade_state_edit", args=[state.pk]))
        self.assertEqual(refreshed.context["authorized_total"], 2)
        self.assertEqual(refreshed.context["posted_grand_total"], 2)
        self.assertEqual(ParadeState.objects.count(), 1)

    def test_viewing_parade_state_does_not_refresh(self):
        state = generate_parade_state(self.admin, timezone.localdate(), refresh=True)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("duty:parade_state_edit", args=[state.pk])
        )
        self.assertEqual(response.status_code, 200)
        state.refresh_from_db()
        self.assertEqual(ParadeState.objects.count(), 1)

    def test_view_shows_unit_and_company_not_platoons(self):
        platoon = make_org("View Pl", parent=self.company)
        make_soldier(platoon, army_number="BA-PL1")
        state = generate_parade_state(self.admin, timezone.localdate(), refresh=True)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("duty:parade_state_edit", args=[state.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A Company")
        self.assertContains(response, "1 BIR")
        self.assertNotContains(response, "View Pl")
        self.assertNotContains(response, ">Pl-1<")
        company_entry = state.company_states.get(organization=self.company)
        self.assertEqual(sum(company_entry.posted_strength.values()), 2)

    def test_platoon_strength_rolls_into_company(self):
        platoon = make_org("Roll Pl", parent=self.company)
        make_soldier(platoon, army_number="BA-ROLL")
        state = generate_parade_state(self.admin, timezone.localdate(), refresh=True)
        org_ids = set(
            state.company_states.values_list("organization__unit_kind", flat=True)
        )
        self.assertIn("company", org_ids)
        self.assertNotIn("platoon", org_ids)
        self.assertFalse(
            state.company_states.filter(organization=platoon).exists()
        )

    def test_absence_document_upload_appears_as_row(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from duty.models import ParadeAbsenceDocument

        state = generate_parade_state(self.admin, timezone.localdate(), refresh=True)
        self.client.force_login(self.admin)
        page = self.client.get(reverse("duty:parade_state_edit", args=[state.pk]))
        self.assertContains(page, "Details of absent")
        self.assertContains(page, 'name="title"')
        self.assertNotContains(page, "P/L")

        response = self.client.post(
            reverse("duty:parade_state_edit", args=[state.pk]),
            {
                "title": "A Coy casual leave",
                "document_date": timezone.localdate().isoformat(),
                "document": SimpleUploadedFile(
                    "leave.pdf",
                    b"%PDF-1.4 test",
                    content_type="application/pdf",
                ),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ParadeAbsenceDocument.objects.count(), 1)
        listed = self.client.get(reverse("duty:parade_state_edit", args=[state.pk]))
        self.assertContains(listed, "A Coy casual leave")
        self.assertContains(listed, "PDF")

        rejected = self.client.post(
            reverse("duty:parade_state_edit", args=[state.pk]),
            {
                "title": "Not allowed",
                "document_date": timezone.localdate().isoformat(),
                "document": SimpleUploadedFile(
                    "notes.txt",
                    b"hello",
                    content_type="text/plain",
                ),
            },
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(ParadeAbsenceDocument.objects.count(), 1)


@override_settings(STORAGES=STORAGES)
class DutyCompleteTests(TestCase):
    def setUp(self):
        self.battalion = make_org("1 BIR")
        self.company_a = make_org("A Company", parent=self.battalion)
        self.company_b = make_org("B Company", parent=self.battalion)
        self.officer_a = make_user(
            "offa",
            role=User.ROLE_OFFICER,
            organizations=[self.company_a],
        )
        self.soldier_b = make_soldier(self.company_b, army_number="BA2")
        self.post = DutyPost.objects.create(
            name="Gate",
            latitude=21.4,
            longitude=92.1,
            day_strength=1,
            night_strength=1,
        )
        self.tour = DutyTour.objects.create(number=1)
        self.assignment = DutyAssignment.objects.create(
            tour=self.tour,
            soldier=self.soldier_b,
            post=self.post,
            assigned_by=self.officer_a,
        )

    def test_officer_cannot_complete_duty_outside_scope(self):
        self.client.force_login(self.officer_a)
        response = self.client.post(
            reverse("duty:complete", args=[self.assignment.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, DutyAssignment.STATUS_ON_DUTY)

    def test_complete_rejects_external_next_url(self):
        admin = make_user("admin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.post(
            reverse("duty:complete", args=[self.assignment.pk]),
            {"next": "https://evil.example/phish"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("duty:assign"))


class PostingHistoryTests(TestCase):
    def test_same_day_accept_updates_open_history(self):
        battalion = make_org("1 BIR")
        company_a = make_org("A Company", parent=battalion)
        company_b = make_org("B Company", parent=battalion)
        soldier = make_soldier(company_a)
        today = timezone.localdate()
        ServiceHistory.objects.create(
            person=soldier,
            organization=company_a,
            rank=soldier.rank,
            start_date=today,
        )
        co = make_user("co", role=User.ROLE_CO)
        officer = make_user(
            "off",
            role=User.ROLE_OFFICER,
            organizations=[company_b],
        )
        self.client.force_login(co)
        self.client.post(
            reverse("duty:posting_create"),
            {
                "soldier": soldier.pk,
                "to_organization": company_b.pk,
                "remarks": "",
            },
        )
        from duty.models import SoldierPosting

        posting = SoldierPosting.objects.get()
        self.client.force_login(officer)
        response = self.client.post(
            reverse("duty:posting_decide", args=[posting.pk]),
            {"action": "accept"},
        )
        self.assertEqual(response.status_code, 302)
        soldier.refresh_from_db()
        self.assertEqual(soldier.organization_id, company_b.pk)
        self.assertEqual(ServiceHistory.objects.filter(person=soldier).count(), 1)
        history = ServiceHistory.objects.get(person=soldier)
        self.assertEqual(history.organization_id, company_b.pk)
        self.assertIsNone(history.end_date)


class DutyTourTests(TestCase):
    def test_get_or_create_reuses_open_tour(self):
        first = get_or_create_open_tour()
        second = get_or_create_open_tour()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(DutyTour.objects.filter(status=DutyTour.STATUS_OPEN).count(), 1)


@override_settings(STORAGES=STORAGES)
class DutyRosterTests(TestCase):
    def setUp(self):
        battalion = make_org("1 BIR")
        self.company_a = make_org("A Company", parent=battalion)
        self.company_b = make_org("B Company", parent=battalion)
        self.soldier_a = make_soldier(self.company_a, army_number="BA-A1", name="Alpha Duty")
        self.soldier_b = make_soldier(self.company_b, army_number="BA-B1", name="Bravo Duty")
        self.officer_a = make_user(
            "roster_off_a",
            role=User.ROLE_OFFICER,
            organizations=[self.company_a],
        )
        self.officer_b = make_user(
            "roster_off_b",
            role=User.ROLE_OFFICER,
            organizations=[self.company_b],
        )
        self.clerk = make_user("roster_clerk", role=User.ROLE_CLERK)
        self.post = DutyPost.objects.create(
            name="Roster Gate",
            latitude=21.4,
            longitude=92.1,
            day_strength=2,
            night_strength=2,
        )
        tour = DutyTour.objects.create(number=91)
        DutyAssignment.objects.create(
            tour=tour,
            soldier=self.soldier_a,
            post=self.post,
            shift=DutyAssignment.SHIFT_DAY,
            assigned_by=self.officer_a,
        )

    def test_officer_can_view_daily_and_monthly_roster(self):
        self.client.force_login(self.officer_a)
        daily = self.client.get(reverse("duty:roster_daily"))
        self.assertEqual(daily.status_code, 200)
        self.assertContains(daily, "Daily Duty Roster")
        self.assertContains(daily, "Alpha Duty")
        self.assertContains(daily, "Roster Gate")

        monthly = self.client.get(reverse("duty:roster_monthly"))
        self.assertEqual(monthly.status_code, 200)
        self.assertContains(monthly, "Monthly Duty Roster Summary")
        self.assertContains(monthly, "Alpha Duty")

    def test_officer_does_not_see_other_company_on_roster(self):
        self.client.force_login(self.officer_b)
        daily = self.client.get(reverse("duty:roster_daily"))
        self.assertEqual(daily.status_code, 200)
        self.assertNotContains(daily, "Alpha Duty")

    def test_clerk_cannot_open_roster(self):
        self.client.force_login(self.clerk)
        response = self.client.get(reverse("duty:roster_daily"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("authentication:home"))

    def test_daily_roster_pdf_downloads(self):
        self.client.force_login(self.officer_a)
        response = self.client.get(reverse("duty:roster_daily_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("attachment", response["Content-Disposition"])

    def test_monthly_roster_pdf_downloads(self):
        self.client.force_login(self.officer_a)
        response = self.client.get(reverse("duty:roster_monthly_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
