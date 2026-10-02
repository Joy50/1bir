from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, override_settings
from django.urls import reverse

from common.compat import make_check_constraint
from common.forms import RankHistoryForm
from common.models import EREOrganization, Family, Organization, Person, ServiceHistory
from common.bangla_render import measure_bangla_text
from common.pdf import build_soldier_pdf
from common.scoping import collect_descendant_ids, get_accessible_companies
from common.test_factories import make_org, make_soldier, make_user
from authentication.models import User


STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


class CheckConstraintCompatTests(TestCase):
    def test_builds_named_constraint_on_this_django(self):
        constraint = make_check_constraint(
            models.Q(doe__gt=models.F("dob")),
            "person_doe_after_dob",
        )
        self.assertEqual(constraint.name, "person_doe_after_dob")


class OrganizationTests(TestCase):
    def test_rejects_self_parent(self):
        org = make_org("1 BIR")
        org.parent_organization = org
        with self.assertRaises(ValidationError):
            org.clean()

    def test_rejects_parent_cycle(self):
        unit = make_org("1 BIR")
        company = make_org("A Company", parent=unit)
        unit.parent_organization = company
        with self.assertRaises(ValidationError):
            unit.clean()

    def test_collect_descendants_uses_one_tree_walk(self):
        unit = make_org("1 BIR")
        company = make_org("Audit Company", parent=unit)
        platoon = make_org("Audit Platoon", parent=company)
        ids = collect_descendant_ids(unit)
        self.assertIn(unit.pk, ids)
        self.assertIn(company.pk, ids)
        self.assertIn(platoon.pk, ids)

    def test_companies_are_filtered_by_kind(self):
        admin = make_user("admin", role=User.ROLE_ADMIN)
        companies = get_accessible_companies(admin)
        self.assertTrue(companies.exists())
        self.assertTrue(
            all(item.unit_kind == Organization.KIND_COMPANY for item in companies)
        )

    def test_organization_type_requires_matching_parent(self):
        unit = make_org("1 BIR")
        company = make_org("Type Company", parent=unit)
        self.assertEqual(company.unit_kind, Organization.KIND_COMPANY)
        platoon = make_org("Type Platoon", parent=company)
        self.assertEqual(platoon.unit_kind, Organization.KIND_PLATOON)
        section = make_org("Type Section", parent=platoon)
        self.assertEqual(section.unit_kind, Organization.KIND_SECTION)

        invalid = Organization(
            organization_name="Misplaced Platoon",
            parent_organization=unit,
            unit_kind=Organization.KIND_PLATOON,
        )
        with self.assertRaises(ValidationError):
            invalid.clean()

        extra_unit = Organization(organization_name="Second Unit", unit_kind=Organization.KIND_UNIT)
        with self.assertRaises(ValidationError):
            extra_unit.clean()

    def test_ere_sits_under_the_unit(self):
        unit = make_org("1 BIR")
        ere = make_org("CMH Dhaka", parent=unit, kind=Organization.KIND_ERE)
        self.assertEqual(ere.unit_kind, Organization.KIND_ERE)
        self.assertTrue(ere.is_posting_place)
        self.assertTrue(ere.is_ere)
        misplaced = Organization(
            organization_name="Misplaced ERE",
            parent_organization=make_org("A Company", parent=unit),
            unit_kind=Organization.KIND_ERE,
        )
        with self.assertRaises(ValidationError):
            misplaced.clean()


@override_settings(STORAGES=STORAGES)
class OrganizationCreateViewTests(TestCase):
    def test_create_form_lists_hierarchy_types(self):
        admin = make_user("orgadmin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.get(reverse("common:create_organization"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization type")
        for label in ("Company", "Platoon", "Section"):
            self.assertContains(response, label)
        self.assertNotContains(response, ">Battalion<")
        self.assertContains(response, "1 BIR (Unit)")
        unit = Organization.objects.get(organization_name="1 BIR")
        self.assertEqual(unit.unit_kind, Organization.KIND_UNIT)
        self.assertIn(
            unit,
            response.context["form"].fields["parent_organization"].queryset,
        )
        choices = [value for value, _label in response.context["form"].fields["unit_kind"].choices]
        self.assertNotIn(Organization.KIND_UNIT, choices)
        self.assertNotIn(Organization.KIND_ERE, choices)

    def test_rejects_second_unit(self):
        admin = make_user("orgadmin_unit2", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.post(
            reverse("common:create_organization"),
            {
                "organization_name": "2 BIR",
                "unit_kind": Organization.KIND_UNIT,
                "parent_organization": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Organization.objects.filter(organization_name="2 BIR").exists())

    def test_company_requires_unit_parent(self):
        admin = make_user("orgadmin2", role=User.ROLE_ADMIN)
        unit = Organization.objects.get(organization_name="1 BIR")
        self.client.force_login(admin)
        response = self.client.post(
            reverse("common:create_organization"),
            {
                "organization_name": "Form Company",
                "unit_kind": Organization.KIND_COMPANY,
                "parent_organization": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Organization.objects.filter(organization_name="Form Company").exists()
        )
        created = self.client.post(
            reverse("common:create_organization"),
            {
                "organization_name": "Form Company",
                "unit_kind": Organization.KIND_COMPANY,
                "parent_organization": str(unit.pk),
            },
        )
        self.assertEqual(created.status_code, 302)
        company = Organization.objects.get(organization_name="Form Company")
        self.assertEqual(company.unit_kind, Organization.KIND_COMPANY)
        self.assertEqual(company.parent_organization_id, unit.pk)

    def test_company_can_use_unit_parent(self):
        admin = make_user("orgadmin_unit", role=User.ROLE_ADMIN)
        unit = Organization.objects.get(organization_name="1 BIR")
        self.client.force_login(admin)
        response = self.client.post(
            reverse("common:create_organization"),
            {
                "organization_name": "Direct Company",
                "unit_kind": Organization.KIND_COMPANY,
                "parent_organization": str(unit.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        company = Organization.objects.get(organization_name="Direct Company")
        self.assertEqual(company.parent_organization_id, unit.pk)

    def test_ere_requires_unit_parent(self):
        admin = make_user("orgadmin_ere", role=User.ROLE_ADMIN)
        unit = Organization.objects.get(organization_name="1 BIR")
        misplaced = Organization(
            organization_name="Misplaced ERE Form",
            parent_organization=make_org("A Company", parent=unit),
            unit_kind=Organization.KIND_ERE,
        )
        with self.assertRaises(ValidationError):
            misplaced.clean()


class EREOrganizationTests(TestCase):
    def test_co_can_add_ere_name(self):
        make_org("1 BIR")
        co = make_user("ere_co", role=User.ROLE_CO)
        self.client.force_login(co)
        created = self.client.post(
            reverse("common:create_ere"),
            {"name": "CMH Dhaka"},
        )
        self.assertEqual(created.status_code, 302)
        ere = EREOrganization.objects.get(name="CMH Dhaka")
        self.assertEqual(ere.organization.unit_kind, Organization.KIND_ERE)
        self.assertEqual(ere.organization.parent_organization.unit_kind, Organization.KIND_UNIT)

    def test_officer_cannot_add_ere_name(self):
        make_org("1 BIR")
        officer = make_user("ere_off", role=User.ROLE_OFFICER)
        self.client.force_login(officer)
        response = self.client.post(
            reverse("common:create_ere"),
            {"name": "SI&T"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EREOrganization.objects.exists())

    def test_admin_can_add_ere_from_admin_panel(self):
        make_org("1 BIR")
        admin = make_user("ere_admin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        home = self.client.get(reverse("authentication:home") + "?section=misc")
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "Create ERE Organization")
        page = self.client.get(reverse("common:create_ere"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Create ERE Organization")
        created = self.client.post(
            reverse("common:create_ere"),
            {"name": "CMH Dhaka"},
        )
        self.assertEqual(created.status_code, 302)
        ere = EREOrganization.objects.get(name="CMH Dhaka")
        self.assertEqual(ere.organization.unit_kind, Organization.KIND_ERE)


class PersonTests(TestCase):
    def test_blank_unique_ids_become_null(self):
        unit = make_org("1 BIR")
        company = make_org("A Company", parent=unit)
        first = make_soldier(company, army_number="BA1")
        first.passport_number = ""
        first.service_id_card_number = "   "
        first.save()
        first.refresh_from_db()
        self.assertIsNone(first.passport_number)
        self.assertIsNone(first.service_id_card_number)
        second = make_soldier(company, army_number="BA2")
        second.passport_number = ""
        second.save()

    def test_soldier_cannot_be_posted_to_the_unit(self):
        unit = make_org("1 BIR")
        soldier = make_soldier(make_org("A Company", parent=unit), army_number="BA-UNIT")
        soldier.organization = unit
        with self.assertRaises(ValidationError):
            soldier.clean()

    def test_age_is_computed_from_dob(self):
        unit = make_org("1 BIR")
        soldier = make_soldier(make_org("A Company", parent=unit))
        soldier.present_age = 1
        soldier.save(update_fields=["present_age"])
        soldier.refresh_from_db()
        self.assertGreater(soldier.age, 1)
        self.assertEqual(soldier.age, Person.years_since(date(2000, 1, 1)))

    def test_pdf_includes_dossier_sections(self):
        unit = make_org("1 BIR")
        soldier = make_soldier(make_org("A Company", parent=unit), name="Pdf Soldier")
        pdf = build_soldier_pdf(soldier).read()
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 2000)

    def test_bangla_text_measurements_use_shaped_width(self):
        plain = measure_bangla_text("abc", 12)
        shaped = measure_bangla_text("সংক্ষিপ্ত", 12)
        self.assertGreater(shaped, plain)

    @override_settings(STORAGES=STORAGES)
    def test_pdf_embeds_soldier_photo(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        unit = make_org("1 BIR")
        soldier = make_soldier(make_org("A Company", parent=unit), name="Photo Soldier")
        buffer = BytesIO()
        Image.new("RGB", (80, 100), (12, 64, 32)).save(buffer, format="JPEG")
        soldier.photo.save(
            "portrait.jpg",
            SimpleUploadedFile(
                "portrait.jpg",
                buffer.getvalue(),
                content_type="image/jpeg",
            ),
            save=True,
        )
        pdf = build_soldier_pdf(soldier).read()
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"/Image", pdf)


@override_settings(STORAGES=STORAGES)
class UnitSearchTests(TestCase):
    def setUp(self):
        from training.models import (
            IndividualCourseLevel,
            IndividualCourseName,
            IndividualQual,
            IndividualQualCourse,
        )

        self.unit = make_org("1 BIR")
        self.company = make_org("A Company", parent=self.unit)
        self.admin = make_user("searchadmin", role=User.ROLE_ADMIN)
        self.hit = make_soldier(self.company, army_number="BA-HIT", name="Hit Soldier")
        self.miss = make_soldier(self.company, army_number="BA-MISS", name="Miss Soldier")
        level, _created = IndividualCourseLevel.objects.get_or_create(
            name="Army Lvl Course"
        )
        self.btt, _created = IndividualCourseName.objects.get_or_create(
            level=level, name="BTT"
        )
        self.att, _created = IndividualCourseName.objects.get_or_create(
            level=level, name="ATT"
        )
        qual = IndividualQual.objects.create(solider=self.hit, year=2026)
        IndividualQualCourse.objects.create(
            qualification=qual, course_name=self.btt, result="B+"
        )
        IndividualQualCourse.objects.create(
            qualification=qual, course_name=self.att, result="Y+"
        )
        other = IndividualQual.objects.create(solider=self.miss, year=2026)
        IndividualQualCourse.objects.create(
            qualification=other, course_name=self.btt, result="C"
        )

    def test_natural_language_course_and_query(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("common:search"),
            {"q": "Which soliders got B+ in BTT and Y+ in ATT"},
        )
        self.assertEqual(response.status_code, 200)
        army_numbers = [soldier.army_number for soldier in response.context["soldiers"]]
        self.assertEqual(army_numbers, ["BA-HIT"])
        self.assertTrue(response.context["interpretations"])

    def test_name_search_still_works(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("common:search"), {"q": "Miss Soldier"})
        army_numbers = [soldier.army_number for soldier in response.context["soldiers"]]
        self.assertEqual(army_numbers, ["BA-MISS"])

    def test_suggest_returns_courses_and_soldiers(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("common:search_suggest"), {"q": "BTT"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        texts = [item["text"] for item in payload["suggestions"]]
        self.assertTrue(any("BTT" in text for text in texts))

    def test_search_box_is_on_the_dashboard_shell(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("common:soldier_list"))
        self.assertContains(response, 'data-unit-search')
        self.assertContains(response, reverse("common:search"))

    def test_company_user_cannot_see_another_company(self):
        other = make_org("B Company", parent=self.unit)
        outsider = make_soldier(other, army_number="BA-OUT", name="Out Soldier")
        clerk = make_user(
            "searchclerk",
            role=User.ROLE_CLERK,
            organizations=[self.company],
        )
        self.client.force_login(clerk)
        hidden = self.client.get(reverse("common:search"), {"q": "Out Soldier"})
        self.assertNotIn(
            outsider.army_number,
            [soldier.army_number for soldier in hidden.context["soldiers"]],
        )
        visible = self.client.get(reverse("common:search"), {"q": "Hit Soldier"})
        self.assertEqual(
            [soldier.army_number for soldier in visible.context["soldiers"]],
            ["BA-HIT"],
        )


class FamilyMemberTests(TestCase):
    def test_enlist_form_has_relation_dropdown_name_and_mobile(self):
        unit = make_org("1 BIR")
        company = make_org("A Company", parent=unit)
        admin = make_user("family_admin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        page = self.client.get(reverse("common:soldier_create"))
        self.assertEqual(page.status_code, 200)
        form = page.context["family_formset"].empty_form
        choice_values = [
            value for value, _label in form.fields["relation"].choices if value
        ]
        self.assertEqual(
            choice_values[:3],
            [Family.RELATION_FATHER, Family.RELATION_MOTHER, Family.RELATION_WIFE],
        )
        self.assertIn("name", form.fields)
        self.assertIn("mobile_number", form.fields)
        self.assertContains(page, "Father")
        self.assertContains(page, "Mother")
        self.assertContains(page, "Wife")

    def test_family_member_stores_relation_name_and_mobile(self):
        unit = make_org("1 BIR")
        soldier = make_soldier(make_org("A Company", parent=unit), army_number="BA-FAM")
        member = Family.objects.create(
            person=soldier,
            relation=Family.RELATION_FATHER,
            name="Abdul Karim",
            mobile_number="01711111111",
        )
        self.assertEqual(str(member), "Father: Abdul Karim")
        self.client.force_login(make_user("family_view", role=User.ROLE_ADMIN))
        detail = self.client.get(reverse("common:soldier_detail", args=[soldier.pk]))
        self.assertContains(detail, "Abdul Karim")
        self.assertContains(detail, "01711111111")
        self.assertContains(detail, "Father")


class HeightTradeAndDeleteIDTests(TestCase):
    def setUp(self):
        self.unit = make_org("1 BIR")
        self.company = make_org("A Company", parent=self.unit)
        self.admin = make_user("height_admin", role=User.ROLE_ADMIN)
        self.soldier = make_soldier(self.company, army_number="BA-DEL")

    def test_height_dropdowns_are_feet_and_inches_one_to_twelve(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse("common:soldier_create"))
        form = page.context["form"]
        self.assertEqual(
            [value for value, _label in form.fields["height_feet"].choices if value],
            list(range(1, 13)),
        )
        self.assertEqual(
            [value for value, _label in form.fields["height_inches"].choices if value],
            list(range(1, 13)),
        )
        self.assertContains(page, "Height (Feet)")
        self.assertContains(page, "Height (Inches)")

    def test_height_display_joins_feet_and_inches(self):
        self.soldier.height_feet = 5
        self.soldier.height_inches = 11
        self.soldier.save()
        self.assertEqual(self.soldier.height_display, "5 ft 11 in")

    def test_rank_history_trade_is_cook_clk_gd(self):
        form = RankHistoryForm()
        self.assertEqual(
            [value for value, _label in form.fields["trade"].choices if value],
            [ServiceHistory.TRADE_COOK, ServiceHistory.TRADE_CLK, ServiceHistory.TRADE_GD],
        )
        self.client.force_login(self.admin)
        page = self.client.get(reverse("common:soldier_create"))
        self.assertContains(page, "Trade")
        self.assertContains(page, "COOK")
        self.assertContains(page, "CLK")
        self.assertContains(page, "GD")

    def test_rank_history_stores_trade(self):
        history = ServiceHistory.objects.create(
            person=self.soldier,
            organization=self.company,
            rank=self.soldier.rank,
            trade=ServiceHistory.TRADE_COOK,
            start_date=date(2020, 1, 1),
        )
        self.client.force_login(self.admin)
        detail = self.client.get(reverse("common:soldier_detail", args=[self.soldier.pk]))
        self.assertContains(detail, "COOK")
        self.assertEqual(history.get_trade_display(), "COOK")

    def test_delete_id_hides_soldier_posted_to_another_unit(self):
        self.client.force_login(self.admin)
        confirm = self.client.get(reverse("common:soldier_delete", args=[self.soldier.pk]))
        self.assertEqual(confirm.status_code, 200)
        self.assertContains(confirm, "posted to another unit")
        deleted = self.client.post(reverse("common:soldier_delete", args=[self.soldier.pk]))
        self.assertEqual(deleted.status_code, 302)
        self.soldier.refresh_from_db()
        self.assertFalse(self.soldier.on_strength)
        listing = self.client.get(reverse("common:soldier_list"))
        self.assertEqual(list(listing.context["soldiers"]), [])
        self.assertEqual(listing.context["stats"]["total"], 0)
        self.assertContains(listing, "No soldiers found.")
        search = self.client.get(reverse("common:search"), {"q": "BA-DEL"})
        self.assertEqual(list(search.context["soldiers"]), [])
        self.assertFalse(
            Person.objects.on_strength().filter(pk=self.soldier.pk).exists()
        )
        self.assertTrue(Person.objects.filter(pk=self.soldier.pk, on_strength=False).exists())
