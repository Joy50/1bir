import re
from datetime import datetime
from dataclasses import dataclass
from functools import lru_cache

from django.apps import apps
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from common.models import Person
from common.scoping import collect_descendant_ids, get_accessible_organization_ids


SEARCH_APPS = ("common", "training", "duty")
SKIP_FIELD_NAMES = {
    "password",
    "sign",
    "photo",
    "document",
    "attachment",
    "image",
    "crest",
    "authorized_strength",
    "posted_strength",
    "absent_strength",
    "absence_details",
    "social_media_links",
}
SKIP_FIELD_TYPES = (
    models.FileField,
    models.ImageField,
    models.BinaryField,
    models.JSONField,
)
PERSON_LINK_NAMES = frozenset({"person", "solider", "soldier"})
STOPWORDS = frozenset({
    "a", "an", "the", "of", "for", "to", "from", "with", "and", "or", "in",
    "who", "which", "what", "whose", "whom", "that", "those", "these",
    "soldier", "soldiers", "solider", "soliders", "man", "men", "personnel",
    "got", "get", "have", "has", "had", "having", "show", "list", "find",
    "me", "please", "are", "is", "was", "were", "been", "being", "their",
    "them", "his", "her", "all", "any", "where", "when", "how", "did",
})
GRADE_RE = re.compile(r"^[A-Za-z]{1,3}[+\-]?$")
IN_RE = re.compile(r"^(?P<left>.+?)\s+in\s+(?P<right>.+)$", re.I)
SPLIT_AND_RE = re.compile(r"\s+(?:and|&)\s+", re.I)
SPLIT_OR_RE = re.compile(r"\s+or\s+", re.I)
TODAY_LEAVE_RE = re.compile(r"\b(on\s+leave|currently\s+on\s+leave)\b", re.I)
ON_DUTY_RE = re.compile(r"\bon\s+duty\b", re.I)
ON_MISSION_RE = re.compile(r"\b(on\s+mission|mission\s+yes)\b", re.I)


@dataclass(frozen=True)
class SearchPath:
    lookup: str
    label: str
    group: str
    kind: str


def _is_searchable(field):
    if field.name in SKIP_FIELD_NAMES or getattr(field, "primary_key", False):
        return False
    if isinstance(field, SKIP_FIELD_TYPES):
        return False
    return isinstance(
        field,
        (
            models.CharField,
            models.TextField,
            models.IntegerField,
            models.PositiveIntegerField,
            models.PositiveSmallIntegerField,
            models.SmallIntegerField,
            models.BooleanField,
            models.DateField,
            models.DateTimeField,
            models.DecimalField,
            models.FloatField,
            models.EmailField,
            models.SlugField,
            models.URLField,
        ),
    )


def _concrete_fields(model):
    return [field for field in model._meta.local_concrete_fields if _is_searchable(field)]


def _label_for(field, prefix=""):
    name = (field.verbose_name or field.name).replace("_", " ")
    return f"{prefix} {name}".strip() if prefix else name


MAX_RELATION_DEPTH = 4
INTEGER_KINDS = {
    "IntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "SmallIntegerField",
    "BigIntegerField",
}
DATE_KINDS = {"DateField", "DateTimeField"}


@lru_cache(maxsize=1)
def person_search_paths():
    paths = []
    seen_lookups = set()

    def add_path(lookup, label, group, kind):
        if lookup in seen_lookups:
            return
        seen_lookups.add(lookup)
        paths.append(SearchPath(lookup, label, group, kind))

    def walk(model, prefix, prefix_label, group, depth, chain, allow_reverse):
        if model in chain or depth > MAX_RELATION_DEPTH:
            return
        if model._meta.app_label not in SEARCH_APPS and model is not Person:
            return
        next_chain = chain | {model}
        for field in _concrete_fields(model):
            lookup = f"{prefix}__{field.name}" if prefix else field.name
            add_path(
                lookup,
                _label_for(field, prefix_label),
                group,
                field.get_internal_type(),
            )
        if depth >= MAX_RELATION_DEPTH:
            return
        for field in model._meta.fields:
            if not field.is_relation or field.many_to_many or field.auto_created:
                continue
            if field.name in PERSON_LINK_NAMES:
                continue
            related = field.remote_field.model
            if related is Person or related._meta.app_label not in SEARCH_APPS:
                continue
            new_prefix = f"{prefix}__{field.name}" if prefix else field.name
            new_label = _label_for(field, prefix_label)
            new_group = group or new_prefix
            walk(
                related,
                new_prefix,
                new_label,
                new_group,
                depth + 1,
                next_chain,
                allow_reverse=False,
            )
        if not allow_reverse:
            return
        for rel in model._meta.related_objects:
            related = rel.related_model
            if related is Person or related._meta.app_label not in SEARCH_APPS:
                continue
            accessor = rel.get_accessor_name()
            if not accessor or accessor.endswith("+"):
                continue
            new_prefix = f"{prefix}__{accessor}" if prefix else accessor
            related_label = str(related._meta.verbose_name)
            new_label = (
                f"{prefix_label} {related_label}".strip()
                if prefix_label
                else related_label
            )
            walk(
                related,
                new_prefix,
                new_label,
                new_prefix,
                depth + 1,
                next_chain,
                allow_reverse=True,
            )

    walk(Person, "", "", "", 0, frozenset(), allow_reverse=True)
    return tuple(paths)


def _normalize(value):
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _strip_stopwords(text):
    tokens = [
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9+\-/.]*", text or "")
        if _normalize(token) not in STOPWORDS
    ]
    return " ".join(tokens)


def _value_lookup(lookup, value, kind=None):
    text = (value or "").strip()
    if not text:
        return Q()
    kind = kind or "CharField"
    lowered = text.lower()

    if kind == "BooleanField":
        if lowered in {"yes", "true", "y"}:
            return Q(**{lookup: True})
        if lowered in {"no", "false", "n"}:
            return Q(**{lookup: False})
        return Q()

    if kind in INTEGER_KINDS:
        if text.isdigit():
            return Q(**{lookup: int(text)})
        return Q()

    if kind in {"DecimalField", "FloatField"}:
        try:
            return Q(**{lookup: float(text)})
        except ValueError:
            return Q()

    if kind in DATE_KINDS:
        query = Q()
        if text.isdigit() and len(text) == 4:
            query |= Q(**{f"{lookup}__year": int(text)})
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(text, fmt).date()
            except ValueError:
                continue
            query |= Q(**{lookup: parsed})
            break
        return query

    if GRADE_RE.fullmatch(text):
        return Q(**{f"{lookup}__iexact": text}) | Q(**{f"{lookup}__icontains": text})
    return Q(**{f"{lookup}__icontains": text})


def _group_value_paths(group):
    return [
        path
        for path in person_search_paths()
        if path.group == group and "name" not in path.lookup.rsplit("__", 1)[-1]
    ]


@lru_cache(maxsize=1)
def _entity_catalog():
    catalog = []

    def add(kind, name, pk, name_lookup, group, extra=None, match_value=None):
        catalog.append(
            {
                "kind": kind,
                "name": name,
                "pk": pk,
                "normalized": _normalize(name),
                "name_lookup": name_lookup,
                "group": group,
                "match_value": match_value or name,
                "extra": extra or {},
            }
        )

    try:
        Course = apps.get_model("training", "IndividualCourseName")
        for row in Course.objects.select_related("level").all():
            add(
                "course",
                row.name,
                row.pk,
                "qualifications__courses__course_name__name",
                "qualifications__courses",
            )
            add(
                "course",
                str(row),
                row.pk,
                "qualifications__courses__course_name__name",
                "qualifications__courses",
                match_value=row.name,
            )
        Level = apps.get_model("training", "IndividualCourseLevel")
        for row in Level.objects.all():
            add(
                "course_level",
                row.name,
                row.pk,
                "qualifications__courses__course_name__level__name",
                "qualifications__courses",
            )
        LeaveType = apps.get_model("training", "LeaveType")
        for row in LeaveType.objects.all():
            add("leave_type", row.name, row.pk, "leave_states__leave_type__name", "leave_states")
        RETType = apps.get_model("training", "RETTrainingType")
        for row in RETType.objects.all():
            add("ret_type", row.name, row.pk, "ret_states__ret_trg_type__name", "ret_states")
    except LookupError:
        pass

    Rank = apps.get_model("common", "Rank")
    for row in Rank.objects.all():
        add("rank", row.rank_name, row.pk, "rank__rank_name", "rank")
    Organization = apps.get_model("common", "Organization")
    for row in Organization.objects.all():
        add(
            "organization",
            row.organization_name,
            row.pk,
            "organization__organization_name",
            "organization",
            extra={"org_id": row.pk},
        )
    Education = apps.get_model("common", "CivilEducationLevel")
    for row in Education.objects.all():
        add(
            "education",
            row.level_name,
            row.pk,
            "civil_educations__level__level_name",
            "civil_educations",
        )

    try:
        DutyPost = apps.get_model("duty", "DutyPost")
        for row in DutyPost.objects.all():
            add("duty_post", row.name, row.pk, "duty_assignments__post__name", "duty_assignments")
    except LookupError:
        pass
    return tuple(catalog)


def invalidate_search_catalog():
    person_search_paths.cache_clear()
    _entity_catalog.cache_clear()


def _match_entities(text):
    needle = _normalize(text)
    if not needle:
        return []
    ranked = []
    for item in _entity_catalog():
        name = item["normalized"]
        if name == needle:
            ranked.append((0, len(name), item))
        elif name.startswith(needle) or needle.startswith(name):
            ranked.append((1, -len(name), item))
        elif needle in name or name in needle:
            ranked.append((2, -len(name), item))
    ranked.sort(key=lambda row: (row[0], row[1], row[2]["kind"], row[2]["name"], row[2]["pk"]))
    seen = set()
    result = []
    for _rank, _length, item in ranked:
        key = (item["kind"], item["pk"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _match_field_paths(text):
    needle = _normalize(text)
    if not needle:
        return []
    hits = []
    for path in person_search_paths():
        label = _normalize(path.label)
        tail = path.lookup.rsplit("__", 1)[-1].replace("_", " ")
        if needle == label or needle == tail or needle in label:
            hits.append(path)
    return hits


def _role_q(text):
    key = _normalize(text)
    if key in {"officer", "officers", "offr"}:
        return Q(rank__category="officer")
    if key in {"jco", "jcos"}:
        return Q(rank__category="jco")
    return None


def _combine_or(pieces):
    query = Q()
    found = False
    for piece in pieces:
        if piece:
            query |= piece
            found = True
    return query if found else Q()


def _entity_q(entity, value=None):
    if entity["kind"] == "organization":
        org_id = entity["extra"]["org_id"]
        try:
            ids = collect_descendant_ids(org_id)
        except Exception:
            ids = {org_id}
        query = Q(organization_id__in=ids)
        if value:
            role = _role_q(value)
            query &= role or (
                _any_field_q(value, group="organization")
                | _value_lookup("rank__rank_name", value, "CharField")
            )
        return query
    match_value = entity.get("match_value") or entity["name"]
    query = Q(**{f"{entity['name_lookup']}__iexact": match_value})
    if value:
        role = _role_q(value)
        if role:
            query &= role
            return query
        value_query = _combine_or(
            _value_lookup(path.lookup, value, path.kind)
            for path in _group_value_paths(entity["group"])
        )
        if entity["kind"] in {"course", "course_level"}:
            value_query |= _value_lookup(
                f"{entity['group']}__result", value, "CharField"
            )
        if not value_query:
            value_query = _any_field_q(value)
        query &= value_query
    return query


def _any_field_q(value, group=None):
    paths = person_search_paths()
    if group is not None:
        paths = [
            path
            for path in paths
            if path.group == group or path.lookup.startswith(group)
        ]
    return _combine_or(_value_lookup(path.lookup, value, path.kind) for path in paths)


def _special_q(text):
    today = timezone.localdate()
    if TODAY_LEAVE_RE.search(text):
        return Q(
            leave_states__status="approved",
            leave_states__from_date__lte=today,
            leave_states__to_date__gte=today,
        )
    if ON_DUTY_RE.search(text):
        return Q(duty_assignments__status="on_duty")
    if ON_MISSION_RE.search(text):
        return Q(mission=True)
    return None


def _clause_q(clause):
    raw = clause.strip()
    if not raw:
        return Q(), ""
    special = _special_q(raw)
    if special is not None:
        return special, raw.strip()

    in_match = IN_RE.match(raw)
    if in_match:
        value = _strip_stopwords(in_match.group("left")) or in_match.group("left").strip()
        container = _strip_stopwords(in_match.group("right")) or in_match.group("right").strip()
        entities = _match_entities(container)
        if entities:
            query = Q()
            labels = []
            for entity in entities[:4]:
                query |= _entity_q(entity, value)
                labels.append(f"{entity['name']} is {value}")
            return query, " or ".join(labels)
        fields = _match_field_paths(container)
        if fields:
            query = _combine_or(
                _value_lookup(path.lookup, value, path.kind) for path in fields[:8]
            )
            return query, f"{fields[0].label} is {value}"
        return _any_field_q(value) & _any_field_q(container), f"{value} in {container}"

    entities = _match_entities(raw)
    leftover = raw
    chosen = None
    for entity in entities:
        pattern = re.compile(re.escape(entity["name"]), re.I)
        if pattern.search(leftover):
            leftover = pattern.sub(" ", leftover, count=1)
            chosen = entity
            break
    leftover = _strip_stopwords(leftover)
    if chosen:
        return _entity_q(chosen, leftover or None), (
            f"{chosen['name']} is {leftover}" if leftover else chosen["name"]
        )

    tokens = [
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9+\-/.]*", raw)
        if _normalize(token) not in STOPWORDS
    ]
    if not tokens:
        return Q(), ""
    query = Q()
    first = True
    for token in tokens:
        token_q = _any_field_q(token)
        query = token_q if first else query & token_q
        first = False
    return query, " ".join(tokens)


def parse_query(query):
    text = (query or "").strip()
    if not text:
        return []
    parts = SPLIT_AND_RE.split(text)
    clauses = []
    for part in parts:
        or_parts = SPLIT_OR_RE.split(part)
        if len(or_parts) == 1:
            clauses.append(("and", part.strip()))
        else:
            clauses.append(("or", [item.strip() for item in or_parts if item.strip()]))
    return clauses


def scoped_people(user):
    queryset = Person.objects.on_strength().select_related("rank", "organization")
    allowed = get_accessible_organization_ids(user)
    if allowed is not None:
        queryset = queryset.filter(organization_id__in=allowed)
    return queryset


def search_soldiers(user, query):
    invalidate_search_catalog()
    clauses = parse_query(query)
    queryset = scoped_people(user)
    interpretations = []
    if not clauses:
        return queryset.none(), interpretations

    for op, payload in clauses:
        if op == "or":
            branch = Q()
            labels = []
            for item in payload:
                item_q, label = _clause_q(item)
                if item_q:
                    branch |= item_q
                if label:
                    labels.append(label)
            if branch:
                queryset = queryset.filter(branch)
            interpretations.append(" or ".join(labels))
        else:
            clause_q, label = _clause_q(payload)
            if label:
                interpretations.append(label)
            if clause_q:
                queryset = queryset.filter(clause_q)

    return queryset.distinct().order_by("army_number"), interpretations


def match_reasons(soldier, query):
    reasons = []
    clauses = parse_query(query)
    tokens = []
    for op, payload in clauses:
        if op == "or":
            tokens.extend(payload)
        else:
            tokens.append(payload)
    for qualification in soldier.qualifications.all():
        for course in qualification.courses.all():
            course_label = str(course.course_name)
            for token in tokens:
                token = (token or "").strip()
                match = IN_RE.match(token)
                if match:
                    value = _strip_stopwords(match.group("left")) or match.group("left")
                    container = _strip_stopwords(match.group("right")) or match.group("right")
                    container_ok = (
                        _normalize(container) in _normalize(course_label)
                        or _normalize(container) in _normalize(course.course_name.name)
                    )
                    result = course.result or ""
                    value_ok = (
                        not value
                        or _normalize(value) in _normalize(result)
                        or _normalize(result) in _normalize(value)
                    )
                    if container_ok and value_ok:
                        reasons.append(f"{course.course_name.name}: {course.result or '—'}")
                        break
                elif _normalize(course.course_name.name) in _normalize(token):
                    reasons.append(f"{course.course_name.name}: {course.result or '—'}")
                    break
    if soldier.mission and ON_MISSION_RE.search(query or ""):
        reasons.append("On mission")
    if not reasons:
        bits = [str(soldier.rank), str(soldier.organization), soldier.army_number]
        reasons.append(" · ".join(bit for bit in bits if bit))
    seen = []
    for reason in reasons:
        if reason not in seen:
            seen.append(reason)
    return seen[:8]


def suggest_search(user, query, limit=8):
    invalidate_search_catalog()
    text = (query or "").strip()
    suggestions = []
    if len(text) < 1:
        for example in (
            "Which soldiers got B+ in BTT and Y+ in ATT",
            "Soldiers currently on leave",
            "HQ Company officers",
        ):
            suggestions.append({"type": "example", "text": example, "query": example})
        return suggestions

    needle = _normalize(text)
    for entity in _entity_catalog():
        if needle in entity["normalized"] or entity["normalized"].startswith(needle):
            if entity["kind"] == "course":
                query_text = f"in {entity['name']}"
            else:
                query_text = entity["name"]
            suggestions.append(
                {
                    "type": entity["kind"],
                    "text": entity["name"],
                    "query": query_text,
                }
            )
        if len(suggestions) >= limit:
            break

    remainder = text
    in_match = IN_RE.match(text)
    prefix = ""
    if in_match:
        prefix = in_match.group("left").strip()
        remainder = in_match.group("right").strip()
    elif GRADE_RE.fullmatch(text.split()[-1] if text.split() else ""):
        prefix = text.split()[-1]
        remainder = ""
    if prefix and GRADE_RE.fullmatch(prefix):
        for entity in _entity_catalog():
            if entity["kind"] != "course":
                continue
            if remainder and _normalize(remainder) not in entity["normalized"]:
                continue
            suggestions.append(
                {
                    "type": "query",
                    "text": f"{prefix} in {entity['name']}",
                    "query": f"{prefix} in {entity['name']}",
                }
            )
            if len(suggestions) >= limit:
                break

    soldiers = scoped_people(user).filter(
        Q(name__icontains=text) | Q(army_number__icontains=text)
    )[:5]
    for soldier in soldiers:
        suggestions.append(
            {
                "type": "soldier",
                "text": f"{soldier.army_number}  {soldier.rank} {soldier.name}",
                "url": reverse("common:soldier_detail", args=[soldier.pk]),
                "query": soldier.army_number,
            }
        )

    seen = set()
    unique = []
    for item in suggestions:
        key = (item.get("type"), item.get("query") or item.get("url"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique
