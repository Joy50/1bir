from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import Organization, Person


PARADE_RANK_COLUMNS = (
    ("offr", "Offr"), ("mwo", "MWO"), ("swo", "SWO"), ("wo", "WO"),
    ("sgt", "Sgt"), ("cpl", "Cpl"), ("lcpl", "Lcpl"), ("snk", "SNK"),
    ("clk", "Clk"), ("ck_u", "Ck (U)"), ("ck_m", "Ck (M)"),
    ("nc_e", "NC(E)"), ("nc_u", "NC(U)"), ("tdn", "Tdn"),
    ("att", "Att"), ("rco", "Rco"),
)

# Authorized establishment shown in the supplied BN PARADE STATE document.
PARADE_AUTHORIZED_DEFAULTS = {
    "offr": 21, "mwo": 1, "swo": 11, "wo": 12, "sgt": 54,
    "cpl": 62, "lcpl": 64, "snk": 439, "clk": 15, "ck_u": 26,
    "ck_m": 2, "nc_e": 15, "nc_u": 4, "tdn": 1, "att": 13, "rco": 1,
}

PARADE_ABSENCE_COLUMNS = (
    ("p_l", "P/L"), ("c_l", "C/L"), ("j_l", "J/L"), ("m_l", "M/L"),
    ("course", "Course"), ("cadre", "Cadre"), ("comd", "Comd"),
    ("att", "Att"), ("hosp", "Hosp"), ("demob", "Demob"),
    ("fdmn", "Fdmn"), ("teknaf", "Teknaf"), ("osl", "OSL"),
)


class DutyPost(models.Model):
    TYPE_UNIT = "unit"
    TYPE_STATION = "station"
    TYPE_CHOICES = [
        (TYPE_UNIT, "Unit Duty"),
        (TYPE_STATION, "Station Duty"),
    ]

    name = models.CharField(max_length=120, unique=True)
    display_order = models.PositiveSmallIntegerField(default=100)
    duty_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_UNIT)
    day_strength = models.PositiveIntegerField(default=0, verbose_name="Day")
    night_strength = models.PositiveIntegerField(default=0, verbose_name="Night")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="duty_posts",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["duty_type", "display_order", "name"]

    def __str__(self):
        return self.name

    @property
    def total_strength(self):
        return self.day_strength + self.night_strength

    def clean(self):
        super().clean()
        if self.latitude is not None and not (-90 <= float(self.latitude) <= 90):
            raise ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if self.longitude is not None and not (-180 <= float(self.longitude) <= 180):
            raise ValidationError({"longitude": "Longitude must be between -180 and 180."})


class SoldierPosting(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending acceptance"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    ]

    soldier = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="postings",
    )
    from_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="outgoing_postings",
    )
    to_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="incoming_postings",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="soldier_postings_made",
    )
    posted_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="soldier_postings_accepted",
        blank=True,
        null=True,
    )
    decided_at = models.DateTimeField(blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-posted_at"]

    def __str__(self):
        return f"{self.soldier} → {self.to_organization}"


class DutyTour(models.Model):
    STATUS_OPEN = "open"
    STATUS_REPORTED = "reported"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_REPORTED, "Reported"),
    ]

    number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    opened_at = models.DateTimeField(default=timezone.now)
    reported_at = models.DateTimeField(blank=True, null=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="duty_tours_reported",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["number"], name="unique_duty_tour_number"),
            models.UniqueConstraint(
                fields=["status"],
                condition=models.Q(status="open"),
                name="unique_open_duty_tour",
            ),
        ]

    def __str__(self):
        return f"Duty tour {self.number}"


class DutyAssignment(models.Model):
    SHIFT_DAY = "day"
    SHIFT_NIGHT = "night"
    SHIFT_CHOICES = [
        (SHIFT_DAY, "Day"),
        (SHIFT_NIGHT, "Night"),
    ]

    STATUS_ON_DUTY = "on_duty"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_ON_DUTY, "On duty"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    tour = models.ForeignKey(
        DutyTour,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    soldier = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="duty_assignments",
    )
    post = models.ForeignKey(
        DutyPost,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default=SHIFT_DAY)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="duty_assignments_made",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ON_DUTY,
    )
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tour", "soldier"],
                condition=models.Q(status__in=["on_duty", "completed"]),
                name="unique_soldier_per_open_tour",
            ),
        ]

    def __str__(self):
        return f"{self.soldier} @ {self.post}"


class ParadeState(models.Model):
    report_date = models.DateField(unique=True)
    authorized_strength = models.JSONField(default=dict, blank=True)
    attachment = models.FileField(upload_to="parade_state/", blank=True)
    remarks = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="parade_states_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date"]

    def __str__(self):
        return f"Daily Parade State - {self.report_date:%d %b %Y}"

    @property
    def authorized_total(self):
        return sum(int(value or 0) for value in self.authorized_strength.values())

    @property
    def posted_total(self):
        return sum(entry.posted_total for entry in self.company_states.all())

    @property
    def absent_total(self):
        return sum(entry.absent_total for entry in self.company_states.all())

    @property
    def present_total(self):
        return self.posted_total - self.absent_total


class ParadeStateCompany(models.Model):
    parade_state = models.ForeignKey(
        ParadeState,
        on_delete=models.CASCADE,
        related_name="company_states",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="parade_state_entries",
    )
    posted_strength = models.JSONField(default=dict, blank=True)
    absent_strength = models.JSONField(default=dict, blank=True)
    absence_details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["organization__organization_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parade_state", "organization"],
                name="unique_parade_state_company",
            ),
        ]

    def __str__(self):
        return f"{self.parade_state.report_date} - {self.organization}"

    @staticmethod
    def total(values):
        return sum(int(value or 0) for value in values.values())

    @property
    def posted_total(self):
        return self.total(self.posted_strength)

    @property
    def absent_total(self):
        return self.total(self.absent_strength)

    @property
    def present_total(self):
        return self.posted_total - self.absent_total


class ParadeAbsenceDocument(models.Model):
    parade_state = models.ForeignKey(
        ParadeState,
        on_delete=models.CASCADE,
        related_name="absence_documents",
    )
    title = models.CharField(max_length=160)
    document = models.FileField(upload_to="parade_state/absence/")
    document_date = models.DateField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="parade_absence_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-document_date", "-uploaded_at", "-pk"]

    def __str__(self):
        return self.title

    @property
    def file_name(self):
        name = self.document.name or ""
        return name.replace("\\", "/").rsplit("/", 1)[-1]

    @property
    def file_kind(self):
        lower = self.file_name.lower()
        if lower.endswith(".pdf"):
            return "PDF"
        if lower.endswith(".doc") or lower.endswith(".docx"):
            return "Word"
        return "File"
