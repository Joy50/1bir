from datetime import date

from authentication.models import User
from common.models import Organization, Person, Rank


def make_rank(name="Sgt"):
    rank, _created = Rank.objects.get_or_create(rank_name=name)
    return rank


def make_org(name, parent=None, kind=None):
    if kind is None:
        if parent is None:
            kind = Organization.KIND_BATTALION
        else:
            kind = Organization.CHILD_KIND.get(
                parent.unit_kind, Organization.KIND_COMPANY
            )
    org, created = Organization.objects.get_or_create(
        organization_name=name,
        parent_organization=parent,
        defaults={"unit_kind": kind},
    )
    if not created and org.unit_kind != kind:
        org.unit_kind = kind
        org.save(update_fields=["unit_kind"])
    return org


def make_user(username, role=User.ROLE_CLERK, password="pass12345", **extra):
    organizations = extra.pop("organizations", None)
    user = User.objects.create_user(
        username=username,
        password=password,
        name=username,
        role=role,
        **extra,
    )
    if organizations:
        user.organizations.set(organizations)
    return user


def make_soldier(organization, army_number="BA1001", name="Test Soldier"):
    return Person.objects.create(
        name=name,
        army_number=army_number,
        rank=make_rank(),
        organization=organization,
        dob=date(2000, 1, 1),
        doe=date(2018, 6, 1),
    )
