from datetime import date

from django.core.exceptions import ValidationError
from django.db import models


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
    KIND_BATTALION = "battalion"
    KIND_COMPANY = "company"
    KIND_PLATOON = "platoon"
    KIND_SECTION = "section"
    KIND_CHOICES = [
        (KIND_UNIT, "Unit"),
        (KIND_BATTALION, "Battalion"),
        (KIND_COMPANY, "Company"),
        (KIND_PLATOON, "Platoon"),
        (KIND_SECTION, "Section"),
    ]
    PARENT_KINDS = {
        KIND_UNIT: frozenset(),
        KIND_BATTALION: frozenset({KIND_UNIT}),
        KIND_COMPANY: frozenset({KIND_BATTALION}),
        KIND_PLATOON: frozenset({KIND_COMPANY}),
        KIND_SECTION: frozenset({KIND_PLATOON}),
    }
    CHILD_KIND = {
        None: KIND_UNIT,
        KIND_UNIT: KIND_BATTALION,
        KIND_BATTALION: KIND_COMPANY,
        KIND_COMPANY: KIND_PLATOON,
        KIND_PLATOON: KIND_SECTION,
    }

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
        help_text="Unit → Battalion → Company → Platoon → Section.",
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
        ]

    def __str__(self):
        return self.organization_name

    def allowed_parent_kinds(self):
        return self.PARENT_KINDS.get(self.unit_kind, frozenset())

    def allows_root_parent(self):
        return self.unit_kind in {self.KIND_UNIT, self.KIND_BATTALION}

    def clean(self):
        super().clean()
        parent = self.parent_organization
        allowed_parents = self.allowed_parent_kinds()
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


class CivilEducationLevel(models.Model):
    level_name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["level_name"]

    def __str__(self):
        return self.level_name


class Person(models.Model):
    AL1_CHOICES = [
        ("Yes", "Yes"),
        ("No", "No"),
    ]

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
    height = models.CharField(max_length=30, blank=True)
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
            models.CheckConstraint(
                condition=models.Q(doe__gt=models.F("dob")),
                name="person_doe_after_dob",
            ),
        ]

    def __str__(self):
        return f"{self.army_number} {self.name}"

    def clean(self):
        super().clean()
        if self.dob and self.doe and self.doe <= self.dob:
            raise ValidationError({"doe": "Date of enrollment must be after date of birth."})
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
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="service_histories",
    )
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="service_history_valid_dates",
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
            models.CheckConstraint(
                condition=models.Q(to_date__isnull=True)
                | models.Q(to_date__gt=models.F("from_date")),
                name="civil_education_valid_dates",
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
            models.CheckConstraint(
                condition=models.Q(to_date__isnull=True)
                | models.Q(to_date__gt=models.F("from_date")),
                name="medical_category_valid_dates",
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
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gt=models.F("start_date")),
                name="appointment_valid_dates",
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
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="family_members",
    )
    relation_name = models.CharField(max_length=150)
    occupation = models.CharField(max_length=150, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["relation_name", "id"]
        verbose_name = "Family member"
        verbose_name_plural = "Family members"

    def __str__(self):
        return f"{self.person} - {self.relation_name}"
