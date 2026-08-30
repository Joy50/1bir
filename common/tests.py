from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, override_settings
from django.urls import reverse

from common.compat import make_check_constraint
from common.models import Organization, Person
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
        battalion = make_org("1 BIR")
        company = make_org("A Company", parent=battalion)
        battalion.parent_organization = company
        with self.assertRaises(ValidationError):
            battalion.clean()

    def test_collect_descendants_uses_one_tree_walk(self):
        battalion = make_org("Audit Battalion")
        company = make_org("Audit Company", parent=battalion)
        platoon = make_org("Audit Platoon", parent=company)
        ids = collect_descendant_ids(battalion)
        self.assertEqual(ids, {battalion.pk, company.pk, platoon.pk})

    def test_companies_are_filtered_by_kind(self):
        admin = make_user("admin", role=User.ROLE_ADMIN)
        companies = get_accessible_companies(admin)
        self.assertTrue(companies.exists())
        self.assertTrue(
            all(item.unit_kind == Organization.KIND_COMPANY for item in companies)
        )

    def test_organization_type_requires_matching_parent(self):
        battalion = make_org("Type Battalion", kind=Organization.KIND_BATTALION)
        company = make_org("Type Company", parent=battalion)
        self.assertEqual(company.unit_kind, Organization.KIND_COMPANY)
        platoon = make_org("Type Platoon", parent=company)
        self.assertEqual(platoon.unit_kind, Organization.KIND_PLATOON)
        section = make_org("Type Section", parent=platoon)
        self.assertEqual(section.unit_kind, Organization.KIND_SECTION)

        invalid = Organization(
            organization_name="Misplaced Platoon",
            parent_organization=battalion,
            unit_kind=Organization.KIND_PLATOON,
        )
        with self.assertRaises(ValidationError):
            invalid.clean()

        unit = Organization(organization_name="Type Unit", unit_kind=Organization.KIND_UNIT)
        unit.parent_organization = battalion
        with self.assertRaises(ValidationError):
            unit.clean()


@override_settings(STORAGES=STORAGES)
class OrganizationCreateViewTests(TestCase):
    def test_create_form_lists_hierarchy_types(self):
        admin = make_user("orgadmin", role=User.ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.get(reverse("common:create_organization"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization type")
        for label in ("Unit", "Battalion", "Company", "Platoon", "Section"):
            self.assertContains(response, label)
        self.assertContains(response, "1 BIR (Unit)")
        unit = Organization.objects.get(organization_name="1 BIR")
        self.assertEqual(unit.unit_kind, Organization.KIND_UNIT)
        self.assertIn(
            unit,
            response.context["form"].fields["parent_organization"].queryset,
        )

    def test_battalion_can_use_unit_parent(self):
        admin = make_user("orgadmin_bn", role=User.ROLE_ADMIN)
        unit = Organization.objects.get(organization_name="1 BIR")
        self.client.force_login(admin)
        response = self.client.post(
            reverse("common:create_organization"),
            {
                "organization_name": "Attached Battalion",
                "unit_kind": Organization.KIND_BATTALION,
                "parent_organization": str(unit.pk),
            },
        )
        self.assertEqual(response.status_code, 302)
        battalion = Organization.objects.get(organization_name="Attached Battalion")
        self.assertEqual(battalion.parent_organization_id, unit.pk)

    def test_company_requires_battalion_parent(self):
        admin = make_user("orgadmin2", role=User.ROLE_ADMIN)
        battalion = make_org("Form Battalion", kind=Organization.KIND_BATTALION)
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
                "parent_organization": str(battalion.pk),
            },
        )
        self.assertEqual(created.status_code, 302)
        company = Organization.objects.get(organization_name="Form Company")
        self.assertEqual(company.unit_kind, Organization.KIND_COMPANY)
        self.assertEqual(company.parent_organization_id, battalion.pk)

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


class PersonTests(TestCase):
    def test_blank_unique_ids_become_null(self):
        battalion = make_org("1 BIR")
        first = make_soldier(battalion, army_number="BA1")
        first.passport_number = ""
        first.service_id_card_number = "   "
        first.save()
        first.refresh_from_db()
        self.assertIsNone(first.passport_number)
        self.assertIsNone(first.service_id_card_number)
        second = make_soldier(battalion, army_number="BA2")
        second.passport_number = ""
        second.save()

    def test_age_is_computed_from_dob(self):
        battalion = make_org("1 BIR")
        soldier = make_soldier(battalion)
        soldier.present_age = 1
        soldier.save(update_fields=["present_age"])
        soldier.refresh_from_db()
        self.assertGreater(soldier.age, 1)
        self.assertEqual(soldier.age, Person.years_since(date(2000, 1, 1)))

    def test_pdf_includes_dossier_sections(self):
        battalion = make_org("1 BIR")
        soldier = make_soldier(battalion, name="Pdf Soldier")
        pdf = build_soldier_pdf(soldier).read()
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)
        self.assertIn(b"Pdf Soldier", pdf)
