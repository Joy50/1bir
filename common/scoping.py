from .models import Organization


def collect_descendant_ids(organization, collected=None):
    if collected is None:
        collected = set()
    collected.add(organization.pk)
    for child in organization.child_organizations.all():
        collect_descendant_ids(child, collected)
    return collected


def get_accessible_organizations(user):
    queryset = Organization.objects.all().order_by("organization_name")
    if not user.is_authenticated:
        return queryset.none()
    if getattr(user, "is_admin", False) or getattr(user, "is_co", False):
        return queryset
    assigned = list(user.organizations.all())
    if not assigned:
        return queryset.none()
    ids = set()
    children_map = {
        org.pk: org
        for org in Organization.objects.select_related("parent_organization")
    }
    # Walk using parent links from a fresh tree
    by_parent = {}
    for org in Organization.objects.all():
        by_parent.setdefault(org.parent_organization_id, []).append(org)
    stack = list(assigned)
    while stack:
        current = stack.pop()
        if current.pk in ids:
            continue
        ids.add(current.pk)
        stack.extend(by_parent.get(current.pk, []))
    return queryset.filter(pk__in=ids)


def get_accessible_organization_ids(user):
    if getattr(user, "is_admin", False) or getattr(user, "is_co", False):
        return None
    return set(get_accessible_organizations(user).values_list("pk", flat=True))
