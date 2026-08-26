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
    organization_name = models.CharField(max_length=100)
    parent_organization = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="child_organizations",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["organization_name"]

    def __str__(self):
        return self.organization_name


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

    def save(self, *args, **kwargs):
        today = date.today()
        if self.dob:
            self.present_age = (
                today.year
                - self.dob.year
                - ((today.month, today.day) < (self.dob.month, self.dob.day))
            )
        if self.doe:
            self.present_service_years = (
                today.year
                - self.doe.year
                - ((today.month, today.day) < (self.doe.month, self.doe.day))
            )
        super().save(*args, **kwargs)

    @property
    def age(self):
        return self.present_age

    @property
    def service_years(self):
        return self.present_service_years

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
                | models.Q(end_date__gt=models.F("start_date")),
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
