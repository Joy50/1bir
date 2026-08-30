from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from authentication.models import HallOfFameCO, UnitAchievement, UnitProfile, User
from common.test_factories import make_user


STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


def tiny_png(name="slide.png"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (201, 168, 76)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class UserRoleTests(TestCase):
    def test_appointment_does_not_grant_co_access(self):
        clerk = make_user("clerk1", role=User.ROLE_CLERK, appointment="Commanding Officer")
        self.assertFalse(clerk.is_co)
        self.assertFalse(clerk.can_command)
        self.assertFalse(clerk.can_view_duty_map)

    def test_co_role_grants_command(self):
        co = make_user("co1", role=User.ROLE_CO)
        self.assertTrue(co.is_co)
        self.assertTrue(co.can_command)

    def test_portal_admin_is_staff_not_superuser(self):
        admin = make_user("admin1", role=User.ROLE_ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        self.assertTrue(admin.is_admin)

    def test_create_superuser_keeps_superuser_flag(self):
        superuser = User.objects.create_superuser(
            username="root",
            password="pass12345",
            name="Root",
        )
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        self.assertEqual(superuser.role, User.ROLE_ADMIN)

    def test_non_admin_cannot_remain_superuser_after_save(self):
        user = make_user("officer1", role=User.ROLE_OFFICER)
        user.is_superuser = True
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_leave_permissions_include_command_roles(self):
        admin = make_user("admin2", role=User.ROLE_ADMIN)
        co = make_user("co2", role=User.ROLE_CO)
        officer = make_user("off2", role=User.ROLE_OFFICER)
        clerk = make_user("clerk2", role=User.ROLE_CLERK)
        self.assertTrue(admin.can_apply_leave)
        self.assertTrue(admin.can_approve_leave)
        self.assertTrue(co.can_apply_leave)
        self.assertTrue(co.can_approve_leave)
        self.assertFalse(officer.can_apply_leave)
        self.assertTrue(officer.can_approve_leave)
        self.assertTrue(clerk.can_apply_leave)
        self.assertFalse(clerk.can_approve_leave)


@override_settings(STORAGES=STORAGES)
class UnitDashboardTests(TestCase):
    def setUp(self):
        self.admin = make_user("dashadmin", role=User.ROLE_ADMIN)
        self.clerk = make_user("dashclerk", role=User.ROLE_CLERK)

    def test_home_shows_unit_dashboard(self):
        self.client.force_login(self.clerk)
        response = self.client.get(reverse("authentication:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_unit_dashboard"])
        self.assertContains(response, "Hall of Fame")
        self.assertNotContains(response, "Edit dashboard")

    def test_admin_sees_edit_control_on_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("authentication:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit dashboard")

    def test_section_query_still_shows_module_cards(self):
        self.client.force_login(self.clerk)
        response = self.client.get(
            reverse("authentication:home"), {"section": "a-matter"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get("is_unit_dashboard"))
        self.assertContains(response, "Parade State")

    def test_clerk_cannot_manage_dashboard(self):
        self.client.force_login(self.clerk)
        response = self.client.get(reverse("authentication:dashboard_manage"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("authentication:home"))

    def test_admin_can_update_profile_and_add_co(self):
        self.client.force_login(self.admin)
        hub = self.client.get(reverse("authentication:dashboard_manage"))
        self.assertEqual(hub.status_code, 200)

        profile_response = self.client.post(
            reverse("authentication:dashboard_profile"),
            {
                "unit_name": "1 Bangladesh Infantry Regiment",
                "short_name": "1 BIR",
                "motto": "The Gallant One",
                "location": "Ramu Cantonment",
                "raised_on": "",
                "war_cry": "",
                "about": "Battalion dashboard.",
            },
        )
        self.assertEqual(profile_response.status_code, 302)
        self.assertEqual(UnitProfile.load().motto, "The Gallant One")

        create = self.client.post(
            reverse(
                "authentication:dashboard_resource_create", args=["hall-of-fame"]
            ),
            {
                "name": "Test CO",
                "rank": "Lt Col",
                "quote": "Lead from the front.",
                "citation": "",
                "is_current": "on",
                "display_order": "1",
                "is_published": "on",
            },
        )
        self.assertEqual(create.status_code, 302)
        self.assertEqual(HallOfFameCO.objects.count(), 1)
        serving = HallOfFameCO.objects.get()
        self.assertTrue(serving.is_current)
        self.assertEqual(serving.quote, "Lead from the front.")

        home = self.client.get(reverse("authentication:home"))
        self.assertContains(home, "Test CO")
        self.assertContains(home, "Lead from the front.")

    def test_only_one_current_co(self):
        first = HallOfFameCO.objects.create(
            name="First CO", rank="Lt Col", is_current=True, is_published=True
        )
        second = HallOfFameCO.objects.create(
            name="Second CO", rank="Lt Col", is_current=True, is_published=True
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)

    def test_admin_can_add_slide_and_achievement(self):
        self.client.force_login(self.admin)
        slide = self.client.post(
            reverse("authentication:dashboard_resource_create", args=["slides"]),
            {
                "image": tiny_png(),
                "title": "Parade",
                "caption": "Battalion parade",
                "display_order": "10",
                "is_published": "on",
            },
        )
        self.assertEqual(slide.status_code, 302)
        achievement = self.client.post(
            reverse(
                "authentication:dashboard_resource_create", args=["achievements"]
            ),
            {
                "title": "UN Mission",
                "year": "2018",
                "description": "Peacekeeping deployment.",
                "display_order": "10",
                "is_published": "on",
            },
        )
        self.assertEqual(achievement.status_code, 302)
        self.assertTrue(UnitAchievement.objects.filter(title="UN Mission").exists())
        home = self.client.get(reverse("authentication:home"))
        self.assertContains(home, "Parade")
        self.assertContains(home, "UN Mission")


@override_settings(STORAGES=STORAGES)
class ErrorPageTests(TestCase):
    def test_preview_pages_render(self):
        cases = {
            400: "This request cannot be processed",
            403: "You do not have permission",
            404: "This page is not on the portal",
            500: "Something went wrong",
        }
        for code, heading in cases.items():
            response = self.client.get(reverse("authentication:error_preview", args=[code]))
            self.assertEqual(response.status_code, code)
            self.assertContains(response, heading, status_code=code)
            self.assertContains(response, "1 BIR", status_code=code)

    def test_csrf_preview_uses_session_message(self):
        response = self.client.get(
            reverse("authentication:error_preview", args=[403]),
            {"csrf": "1"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "This form could not be verified", status_code=403)

    @override_settings(DEBUG=False)
    def test_unknown_url_uses_branded_404(self):
        response = self.client.get("/this-page-is-not-on-the-portal/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page is not on the portal", status_code=404)
        self.assertContains(response, "Return to login", status_code=404)

