from datetime import date

from django.core.exceptions import ValidationError
from django.db import models, transaction


def make_check_constraint(expression, name):
    """CheckConstraint: Django 4.x uses check=, Django 5.1+ uses condition=."""
    try:
        return models.CheckConstraint(check=expression, name=name)
    except TypeError:
        return models.CheckConstraint(condition=expression, name=name)


class Rank(models.Model):
    CATEGORY_OFFICER = "officer"
    CATEGORY_JCO = "jco"
    CATEGORY_OR = "or"
    CATEGORY_CHOICES = [
        (CATEGORY_OFFICER, "Officer"),
        (CATEGORY_JCO, "JCO"),
        (CATEGORY_OR, "OR"),
    ]

    rank_name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OR,
    )

    class Meta:
        ordering = ["rank_name"]

    def __str__(self):
        return self.rank_name


class Organization(models.Model):
    KIND_UNIT = "unit"
    KIND_COMPANY = "company"
    KIND_PLATOON = "platoon"
    KIND_SECTION = "section"
    KIND_ERE = "ere"
    KIND_CHOICES = [
        (KIND_UNIT, "Unit"),
        (KIND_COMPANY, "Company"),
        (KIND_PLATOON, "Platoon"),
        (KIND_SECTION, "Section"),
        (KIND_ERE, "ERE"),
    ]
    POSTING_KINDS = frozenset({KIND_COMPANY, KIND_PLATOON, KIND_SECTION, KIND_ERE})
    POSTING_ORDER_KINDS = frozenset({KIND_COMPANY, KIND_ERE})
    PARENT_KINDS = {
        KIND_UNIT: frozenset(),
        KIND_COMPANY: frozenset({KIND_UNIT}),
        KIND_PLATOON: frozenset({KIND_COMPANY}),
        KIND_SECTION: frozenset({KIND_PLATOON}),
        KIND_ERE: frozenset({KIND_UNIT}),
    }
    CHILD_KIND = {
        None: KIND_UNIT,
        KIND_UNIT: KIND_COMPANY,
        KIND_COMPANY: KIND_PLATOON,
        KIND_PLATOON: KIND_SECTION,
    }
    HQ_COMPANY_NAME = "HQ Company"

    organization_name = models.CharField(max_length=100)
    parent_organization = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="child_organizations",
        blank=True,
        null=True,
    )
    unit_kind = models.CharField(
        "organization type",
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_UNIT,
        help_text="Unit → Company → Platoon → Section. ERE organizations sit under the Unit.",
    )
    authorized_strength = models.JSONField(
        default=dict,
        blank=True,
        help_text="Company establishment (PE) by parade column. Unused on other types.",
    )

    class Meta:
        ordering = ["organization_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization_name", "parent_organization"],
                name="unique_org_name_per_parent",
            ),
            models.UniqueConstraint(
                fields=["organization_name"],
                condition=models.Q(parent_organization__isnull=True),
                name="unique_root_organization_name",
            ),
            models.UniqueConstraint(
                fields=["unit_kind"],
                condition=models.Q(unit_kind="unit"),
                name="unique_unit_organization",
            ),
        ]

    def __str__(self):
        return self.organization_name

    @property
    def is_posting_place(self):
        return self.unit_kind in self.POSTING_KINDS

    @property
    def is_ere(self):
        return self.unit_kind == self.KIND_ERE

    def allowed_parent_kinds(self):
        return self.PARENT_KINDS.get(self.unit_kind, frozenset())

    def allows_root_parent(self):
        return self.unit_kind == self.KIND_UNIT

    def clean(self):
        super().clean()
        parent = self.parent_organization
        allowed_parents = self.allowed_parent_kinds()
        if self.unit_kind == self.KIND_UNIT:
            siblings = Organization.objects.filter(unit_kind=self.KIND_UNIT)
            if self.pk:
                siblings = siblings.exclude(pk=self.pk)
            if siblings.exists():
                raise ValidationError(
                    {"unit_kind": "This installation already has a Unit. 1 BIR is the only unit."}
                )
        if parent is None:
            if not self.allows_root_parent():
                raise ValidationError(
                    {
                        "parent_organization": (
                            f"A {self.get_unit_kind_display()} must sit under a "
                            f"{self._parent_type_label()}."
                        )
                    }
                )
            return
        if self.unit_kind == self.KIND_UNIT:
            raise ValidationError(
                {"parent_organization": "A Unit is the top level and cannot have a parent."}
            )
        if self.pk and parent.pk == self.pk:
            raise ValidationError(
                {"parent_organization": "An organization cannot be its own parent."}
            )
        if parent.unit_kind not in allowed_parents:
            raise ValidationError(
                {
                    "parent_organization": (
                        f"A {self.get_unit_kind_display()} must sit under a "
                        f"{self._parent_type_label()}."
                    )
                }
            )
        seen = set()
        current = parent
        while current is not None:
            if self.pk and current.pk == self.pk:
                raise ValidationError(
                    {"parent_organization": "That parent would create a cycle."}
                )
            if current.pk in seen:
                break
            seen.add(current.pk)
            current = current.parent_organization

    def _parent_type_label(self):
        labels = dict(self.KIND_CHOICES)
        kinds = [labels[kind] for kind in self.allowed_parent_kinds()]
        if not kinds:
            return "no parent"
        if len(kinds) == 1:
            return kinds[0]
        return " or ".join(kinds)


class EREOrganization(models.Model):
    """Named extra-regimental employment destinations a soldier can be posted to."""

    name = models.CharField(max_length=150, unique=True)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="ere_entry",
        editable=False,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "ERE organization"
        verbose_name_plural = "ERE organizations"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        name = (self.name or "").strip()
        if not name:
            raise ValidationError({"name": "Enter the name of the ERE organization."})
        self.name = name
        if not self.organization_id:
            unit = Organization.objects.filter(unit_kind=Organization.KIND_UNIT).first()
            if unit is None:
                raise ValidationError(
                    "Create the Unit before adding ERE organizations."
                )

    def save(self, *args, **kwargs):
        self.name = (self.name or "").strip()
        with transaction.atomic():
            if not self.organization_id:
                unit = Organization.objects.filter(
                    unit_kind=Organization.KIND_UNIT
                ).first()
                if unit is None:
                    raise ValidationError(
                        "Create the Unit before adding ERE organizations."
                    )
                org = Organization(
                    organization_name=self.name,
                    parent_organization=unit,
                    unit_kind=Organization.KIND_ERE,
                )
                org.full_clean()
                org.save()
                self.organization = org
            super().save(*args, **kwargs)
            org = self.organization
            if (
                org.organization_name != self.name
                or org.unit_kind != Organization.KIND_ERE
            ):
                org.organization_name = self.name
                org.unit_kind = Organization.KIND_ERE
                org.save(update_fields=["organization_name", "unit_kind"])


class CivilEducationLevel(models.Model):
    level_name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["level_name"]

    def __str__(self):
        return self.level_name


class PersonQuerySet(models.QuerySet):
    def on_strength(self):
        return self.filter(on_strength=True)


class Person(models.Model):
    AL1_CHOICES = [
        ("Yes", "Yes"),
        ("No", "No"),
    ]
    HEIGHT_FEET_CHOICES = [(value, str(value)) for value in range(1, 13)]
    HEIGHT_INCH_CHOICES = [(value, str(value)) for value in range(1, 13)]

    objects = PersonQuerySet.as_manager()

    name = models.CharField(max_length=100)
    army_number = models.CharField(max_length=20, unique=True)
    rank = models.ForeignKey(
        Rank,
        on_delete=models.PROTECT,
        related_name="persons",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="persons",
    )
    photo = models.ImageField(upload_to="soldier_photos/", blank=True, null=True)
    dob = models.DateField()
    doe = models.DateField()
    batch = models.CharField(max_length=30, blank=True)
    present_age = models.PositiveIntegerField(blank=True, null=True, editable=False)
    present_service_years = models.PositiveIntegerField(
        blank=True,
        null=True,
        editable=False,
    )
    al1_13 = models.CharField(
        max_length=3,
        choices=AL1_CHOICES,
        blank=True,
        null=True,
    )
    dor = models.DateField(blank=True, null=True)
    discipline = models.TextField(blank=True, null=True)
    punishment = models.TextField(blank=True, null=True)
    mission = models.BooleanField(default=False)
    on_strength = models.BooleanField(default=True)
    height_feet = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        choices=HEIGHT_FEET_CHOICES,
    )
    height_inches = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        choices=HEIGHT_INCH_CHOICES,
    )
    overweight = models.CharField(max_length=30, blank=True)
    qualification_for_next_rank = models.BooleanField(default=False)
    reason_unqualified = models.TextField(blank=True)
    nid_number = models.CharField(max_length=30, blank=True)
    birth_certificate_number = models.CharField(max_length=30, blank=True)
    phone_registration_nid = models.CharField(max_length=30, blank=True)
    phone_imei = models.CharField(max_length=50, blank=True)
    social_media_links = models.TextField(blank=True)
    passport_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )
    passport_type = models.CharField(max_length=30, blank=True)
    service_id_card_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )
    present_address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["army_number"]
        constraints = [
            make_check_constraint(
                models.Q(doe__gt=models.F("dob")),
                "person_doe_after_dob",
            ),
        ]

    def __str__(self):
        return f"{self.army_number} {self.name}"

    @property
    def height_display(self):
        parts = []
        if self.height_feet is not None:
            parts.append(f"{self.height_feet} ft")
        if self.height_inches is not None:
            parts.append(f"{self.height_inches} in")
        return " ".join(parts)

    def clean(self):
        super().clean()
        if self.dob and self.doe and self.doe <= self.dob:
            raise ValidationError({"doe": "Date of enrollment must be after date of birth."})
        organization = self.organization
        if organization is not None and not organization.is_posting_place:
            raise ValidationError(
                {
                    "organization": (
                        "A soldier is posted to a company, platoon, section, or ERE organization. "
                        "Unit HQ staff belong in HQ Company."
                    )
                }
            )
        self._normalize_optional_unique_fields()

    def _normalize_optional_unique_fields(self):
        for field_name in ("passport_number", "service_id_card_number"):
            value = getattr(self, field_name)
            if value is not None and not str(value).strip():
                setattr(self, field_name, None)

    @staticmethod
    def years_since(start):
        if not start:
            return None
        today = date.today()
        return (
            today.year
            - start.year
            - ((today.month, today.day) < (start.month, start.day))
        )

    def save(self, *args, **kwargs):
        self._normalize_optional_unique_fields()
        self.present_age = self.years_since(self.dob)
        self.present_service_years = self.years_since(self.doe)
        super().save(*args, **kwargs)

    @property
    def age(self):
        return self.years_since(self.dob)

    @property
    def service_years(self):
        return self.years_since(self.doe)

    @property
    def civil_education(self):
        return "; ".join(
            f"{item.level}: {item.institution_name}"
            + (f" ({item.grade})" if item.grade else "")
            for item in self.civil_educations.all()
        )

    @property
    def physical_efficiency(self):
        return "; ".join(
            f"{item.year}: {item.pe}" for item in self.qualifications.all() if item.pe
        )

    def _qualification_courses(self, level_keyword):
        values = []
        for qualification in self.qualifications.all():
            for course in qualification.courses.all():
                if level_keyword.lower() in course.course_name.level.name.lower():
                    value = f"{course.course_name.name}"
                    if course.result:
                        value += f" ({course.result})"
                    values.append(value)
        return "; ".join(values)

    @property
    def army_courses(self):
        return self._qualification_courses("Army Lvl Course")

    @property
    def cadres(self):
        return self._qualification_courses("Cadre")

    @property
    def specialist_cadre(self):
        return "; ".join(
            f"{item.year}: {item.spl}" for item in self.qualifications.all() if item.spl
        )

    @property
    def all_apr(self):
        return "; ".join(
            f"{item.year}: {item.report or 'APR'}"
            + (f" ({item.score})" if item.score is not None else "")
            for item in self.annual_performance_reports.all()
        )

    @property
    def previous_unit_organizations(self):
        values = []
        for item in self.appointment_histories.all():
            legacy_prefix = "Previous unit/organization: "
            if item.appointment_name.startswith(legacy_prefix):
                value = item.appointment_name.removeprefix(legacy_prefix)
            else:
                value = str(item.organization)
            if item.appointment_name and not item.appointment_name.startswith(legacy_prefix):
                value = f"{value} ({item.appointment_name})"
            if value not in values:
                values.append(value)
        return "; ".join(values)

    def _ordered_rank_histories(self):
        histories = list(self.service_histories.all())
        return sorted(histories, key=lambda item: item.start_date, reverse=True)

    @property
    def present_rank_date(self):
        histories = self._ordered_rank_histories()
        current = next((item for item in histories if item.end_date is None), None)
        return (current or (histories[0] if histories else None)).start_date if histories else None

    @property
    def previous_rank_date(self):
        histories = self._ordered_rank_histories()
        present_date = self.present_rank_date
        previous = next(
            (item for item in histories if item.start_date != present_date),
            None,
        )
        return previous.start_date if previous else None


class ServiceHistory(models.Model):
    TRADE_COOK = "COOK"
    TRADE_CLK = "CLK"
    TRADE_GD = "GD"
    TRADE_CHOICES = [
        (TRADE_COOK, "COOK"),
        (TRADE_CLK, "CLK"),
        (TRADE_GD, "GD"),
    ]

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="service_histories",
    )
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT)
    trade = models.CharField(max_length=8, choices=TRADE_CHOICES, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            make_check_constraint(
                models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                "service_history_valid_dates",
            ),
        ]

    def __str__(self):
        return f"{self.person} · {self.organization}"


class CivilEducation(models.Model):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="civil_educations",
    )
    level = models.ForeignKey(CivilEducationLevel, on_delete=models.PROTECT)
    institution_name = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(blank=True, null=True)
    grade = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-from_date"]
        constraints = [
            make_check_constraint(
                models.Q(to_date__isnull=True)
                | models.Q(to_date__gt=models.F("from_date")),
                "civil_education_valid_dates",
            ),
        ]


class MedicalCategory(models.Model):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="medical_categories",
    )
    type = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-from_date"]
        constraints = [
            make_check_constraint(
                models.Q(to_date__isnull=True)
                | models.Q(to_date__gt=models.F("from_date")),
                "medical_category_valid_dates",
            ),
        ]


class AnnualPerformanceReport(models.Model):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="annual_performance_reports",
    )
    year = models.PositiveIntegerField()
    report = models.TextField(blank=True, null=True)
    score = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["-year"]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "year"],
                name="unique_person_apr_year",
            ),
        ]


class AppointmentHistory(models.Model):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="appointment_histories",
    )
    appointment_name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            make_check_constraint(
                models.Q(end_date__isnull=True)
                | models.Q(end_date__gt=models.F("start_date")),
                "appointment_valid_dates",
            ),
        ]


class MobileNumber(models.Model):
    TYPE_PERSONAL = "personal"
    TYPE_NOK = "nok"
    TYPE_CHOICES = [
        (TYPE_PERSONAL, "Personal"),
        (TYPE_NOK, "Next of kin"),
    ]

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="mobile_numbers",
    )
    type_of_number = models.CharField(max_length=20, choices=TYPE_CHOICES)
    mobile_number = models.CharField(max_length=15)

    def __str__(self):
        return self.mobile_number


class Family(models.Model):
    RELATION_FATHER = "father"
    RELATION_MOTHER = "mother"
    RELATION_WIFE = "wife"
    RELATION_HUSBAND = "husband"
    RELATION_SON = "son"
    RELATION_DAUGHTER = "daughter"
    RELATION_BROTHER = "brother"
    RELATION_SISTER = "sister"
    RELATION_CHOICES = [
        (RELATION_FATHER, "Father"),
        (RELATION_MOTHER, "Mother"),
        (RELATION_WIFE, "Wife"),
        (RELATION_HUSBAND, "Husband"),
        (RELATION_SON, "Son"),
        (RELATION_DAUGHTER, "Daughter"),
        (RELATION_BROTHER, "Brother"),
        (RELATION_SISTER, "Sister"),
    ]

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="family_members",
    )
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)
    name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=15, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["relation", "name", "id"]
        verbose_name = "Family member"
        verbose_name_plural = "Family members"

    def __str__(self):
        return f"{self.get_relation_display()}: {self.name}"
