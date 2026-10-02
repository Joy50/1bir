from .models import Organization


def organization_children_map():
    children_map = {}
    for org in Organization.objects.only("id", "parent_organization_id"):
        children_map.setdefault(org.parent_organization_id, []).append(org.id)
    return children_map


def collect_descendant_ids(organization, collected=None, children_map=None):
    if collected is None:
        collected = set()
    org_id = organization.pk if hasattr(organization, "pk") else organization
    if org_id in collected:
        return collected
    if children_map is None:
        children_map = organization_children_map()
    collected.add(org_id)
    for child_id in children_map.get(org_id, []):
        collect_descendant_ids(child_id, collected, children_map)
    return collected


def descendant_ids_by_organization(organizations):
    children_map = organization_children_map()
    return {
        org.pk: collect_descendant_ids(org, children_map=children_map)
        for org in organizations
    }


def get_accessible_organizations(user):
    queryset = Organization.objects.all().order_by("organization_name")
    if not user.is_authenticated:
        return queryset.none()
    if getattr(user, "is_admin", False) or getattr(user, "is_co", False):
        return queryset
    assigned = list(user.organizations.all())
    if not assigned:
        return queryset.none()
    children_map = organization_children_map()
    ids = set()
    stack = [org.pk for org in assigned]
    while stack:
        current_id = stack.pop()
        if current_id in ids:
            continue
        ids.add(current_id)
        stack.extend(children_map.get(current_id, []))
    return queryset.filter(pk__in=ids)


def get_accessible_organization_ids(user):
    if getattr(user, "is_admin", False) or getattr(user, "is_co", False):
        return None
    return set(get_accessible_organizations(user).values_list("pk", flat=True))


def get_posting_organizations(user=None):
    """Companies of the unit, plus ERE organizations, for posting orders."""
    unit = Organization.objects.filter(unit_kind=Organization.KIND_UNIT).first()
    queryset = Organization.objects.filter(
        unit_kind__in=(Organization.KIND_COMPANY, Organization.KIND_ERE)
    ).select_related("parent_organization")
    if unit is not None:
        queryset = queryset.filter(parent_organization=unit)
    return queryset.order_by("unit_kind", "organization_name")


def get_accessible_companies(user):
    return get_accessible_organizations(user).filter(
        unit_kind=Organization.KIND_COMPANY
    )


def get_posting_record_organizations(user):
    return get_accessible_organizations(user).filter(
        unit_kind__in=(Organization.KIND_COMPANY, Organization.KIND_ERE)
    )


def get_company_of(organization):
    current = organization
    seen = set()
    while current is not None and getattr(current, "pk", None) not in seen:
        if current.pk:
            seen.add(current.pk)
        if current.unit_kind == Organization.KIND_COMPANY:
            return current
        current = current.parent_organization
    return None


PARADE_BOARD_KINDS = (Organization.KIND_COMPANY,)
BOARD_FILTER_KINDS = (Organization.KIND_UNIT, Organization.KIND_COMPANY)


def get_parade_organizations(user):
    return get_accessible_organizations(user).filter(
        unit_kind=Organization.KIND_COMPANY
    ).order_by("organization_name")


def get_board_organizations(user):
    from django.db.models import Case, IntegerField, Value, When

    return get_accessible_organizations(user).filter(
        unit_kind__in=BOARD_FILTER_KINDS
    ).annotate(
        parade_rank=Case(
            When(unit_kind=Organization.KIND_UNIT, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("parade_rank", "organization_name")


def organization_lookup():
    return {
        org.pk: org
        for org in Organization.objects.only("id", "unit_kind", "parent_organization_id")
    }


def rollup_to_parade_organization(organization, orgs_by_id=None):
    """Map a platoon or section onto its company. The unit is not a parade row."""
    if orgs_by_id is None:
        orgs_by_id = organization_lookup()
    if organization is None:
        return None
    current = organization if hasattr(organization, "unit_kind") else orgs_by_id.get(organization)
    seen = set()
    while current is not None and current.pk not in seen:
        seen.add(current.pk)
        if current.unit_kind == Organization.KIND_COMPANY:
            return current
        parent_id = current.parent_organization_id
        current = orgs_by_id.get(parent_id) if parent_id else None
    return None


def get_unit(user=None):
    queryset = Organization.objects.filter(unit_kind=Organization.KIND_UNIT)
    if user is not None:
        accessible = get_accessible_organizations(user)
        queryset = queryset.filter(pk__in=accessible.values("pk"))
    return queryset.order_by("organization_name").first()


def get_battalion(user=None):
    return get_unit(user)


def get_or_create_hq_company(unit=None):
    unit = unit or get_unit()
    if unit is None:
        return None
    company, _created = Organization.objects.get_or_create(
        organization_name=Organization.HQ_COMPANY_NAME,
        parent_organization=unit,
        defaults={"unit_kind": Organization.KIND_COMPANY},
    )
    if company.unit_kind != Organization.KIND_COMPANY:
        company.unit_kind = Organization.KIND_COMPANY
        company.save(update_fields=["unit_kind"])
    return company
