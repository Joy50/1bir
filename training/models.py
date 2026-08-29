from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from common.models import Person


def current_year():
    return timezone.localdate().year


# ============================================================
# Yearly Plan
# ============================================================

class YearlyPlan(models.Model):

    CYCLE_CHOICES = [
        ("1st Cycle", "1st Cycle"),
        ("2nd Cycle", "2nd Cycle"),
        ("3rd Cycle", "3rd Cycle"),
        ("4th Cycle", "4th Cycle"),
    ]

    OPTION_CHOICES = [
        ("PLve", "P/Lve"),
        ("GP Trg", "GP Trg"),
        ("Course", "Course"),
        ("Admin", "Admin"),
    ]

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="yearly_plans",
    )

    year = models.IntegerField()

    cycle = models.CharField(
        max_length=20,
        choices=CYCLE_CHOICES,
    )

    option = models.CharField(
        max_length=20,
        choices=OPTION_CHOICES,
    )

    class Meta:
        ordering = ["-year", "cycle"]
        verbose_name = "Yearly Plan"
        verbose_name_plural = "Yearly Plans"
        constraints = [
            models.UniqueConstraint(
                fields=["solider", "year", "cycle"],
                name="unique_yearly_plan_cycle",
            ),
        ]

    def __str__(self):
        return f"{self.solider} - {self.year} {self.cycle}"


class UnitTrainingCyclePlan(models.Model):
    CYCLE_CHOICES = [
        (1, "1st Trg Cycle"),
        (2, "2nd Trg Cycle"),
        (3, "3rd Trg Cycle"),
        (4, "4th Trg Cycle"),
    ]

    year = models.PositiveIntegerField()
    cycle = models.PositiveSmallIntegerField(choices=CYCLE_CHOICES)
    organization = models.ForeignKey(
        "common.Organization",
        on_delete=models.CASCADE,
        related_name="unit_training_cycle_plans",
<<<<<<< HEAD
=======
        blank=True,
        null=True,
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
    )
    bde_lvl_cadre = models.TextField(blank=True, verbose_name="Bde Lvl Cadre")
    div_lvl_cadre = models.TextField(blank=True, verbose_name="Div Lvl Cadre")
    pre_course_pe = models.TextField(blank=True, verbose_name="Pre-Course/PE")
    gpt = models.TextField(blank=True, verbose_name="GPT")
    misc_trg_event = models.TextField(blank=True, verbose_name="Misc Trg Event")

    class Meta:
        ordering = ["year", "cycle"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "cycle", "organization"],
                name="unique_unit_training_cycle_per_company_year",
            ),
        ]

    def __str__(self):
<<<<<<< HEAD
        unit = self.organization or "Battalion"
=======
        unit = self.organization or "1 BIR"
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
        return f"{unit} - {self.year} {self.get_cycle_display()}"


# ============================================================
# Participation in Major Competition
# ============================================================

class ParticipationInMajCom(models.Model):

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="major_competitions",
    )

    year = models.IntegerField()

    gp_trg = models.CharField(
        max_length=256,
        blank=True,
        verbose_name="GP Trg",
    )

    st = models.CharField(
        max_length=256,
        blank=True,
        verbose_name="ST",
    )

    wt = models.CharField(
        max_length=256,
        blank=True,
        verbose_name="WT",
    )

    fi = models.CharField(
        max_length=256,
        blank=True,
        verbose_name="FI",
    )

    ihwf = models.CharField(
        max_length=256,
        blank=True,
        verbose_name="IHWF",
    )

    ff = models.CharField(
        max_length=256,
        blank=True,
        verbose_name="FF",
    )

    class Meta:
        ordering = ["-year"]
        verbose_name = "Participation in Major Commitment"
        verbose_name_plural = "Participation in Major Commitments"
        constraints = [
            models.UniqueConstraint(
                fields=["solider", "year"],
                name="unique_majcom_per_soldier_year",
            ),
        ]

    def __str__(self):
        return f"{self.solider} - Major Commitment {self.year}"


# ============================================================
# Individual Course Level
# Example: Basic, Advanced, Special, Instructor
# ============================================================

class IndividualCourseLevel(models.Model):

    name = models.CharField(
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Individual Course Level"
        verbose_name_plural = "Individual Course Levels"

    def __str__(self):
        return self.name


# ============================================================
# Individual Course Name
# Each course belongs to one course level.
# Example:
#   Basic -> Basic Training
#   Special -> Commando Course, Jungle Warfare Course
# ============================================================

class IndividualCourseName(models.Model):

    level = models.ForeignKey(
        IndividualCourseLevel,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    name = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = ["level__name", "name"]
        verbose_name = "Individual Course Name"
        verbose_name_plural = "Individual Course Names"
        constraints = [
            models.UniqueConstraint(
                fields=["level", "name"],
                name="unique_course_name_per_level",
            ),
        ]

    def __str__(self):
        return f"{self.level.name} - {self.name}"


# ============================================================
# Individual Qualification
# One header per soldier (year, SPL, next promotion) and many
# course rows (level + course name + result).
# ============================================================

class IndividualQual(models.Model):

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="qualifications",
    )

<<<<<<< HEAD
    year = models.PositiveIntegerField()
=======
    year = models.CharField(
        max_length=4,
    )
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf

    spl = models.CharField(
        max_length=255,
        blank=True,
    )

    qual_for_next_promotion = models.BooleanField(
        default=False,
    )

    pe = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="PE",
    )

    class Meta:
        ordering = ["-year"]
        verbose_name = "Individual Qualification"
        verbose_name_plural = "Individual Qualifications"
        constraints = [
            models.UniqueConstraint(
                fields=["solider", "year"],
                name="unique_person_qual_year",
            ),
        ]

    def clean(self):
        super().clean()
<<<<<<< HEAD
        if self.year and not (1900 <= int(self.year) <= 2100):
            raise ValidationError({
                "year": "Year must be between 1900 and 2100."
=======

        if self.year and (
            len(self.year) != 4 or not self.year.isdigit()
        ):
            raise ValidationError({
                "year": "Year must be a 4-digit value, for example 2026."
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
            })

    def __str__(self):
        return f"{self.solider} - Qualification {self.year}"


class IndividualQualCourse(models.Model):

    qualification = models.ForeignKey(
        IndividualQual,
        on_delete=models.CASCADE,
        related_name="courses",
    )

    course_name = models.ForeignKey(
        IndividualCourseName,
        on_delete=models.PROTECT,
        related_name="qualification_entries",
    )

    result = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = [
            "course_name__level__name",
            "course_name__name",
        ]
        verbose_name = "Qualification Course"
        verbose_name_plural = "Qualification Courses"
        constraints = [
            models.UniqueConstraint(
                fields=["qualification", "course_name"],
                name="unique_qual_course",
            ),
        ]

    @property
    def course_level(self):
        return self.course_name.level

    def __str__(self):
        return f"{self.qualification} - {self.course_name.name}"


# ============================================================
# Leave Type
# Example: Recreational, Casual, Privilege, Medical
# ============================================================

class LeaveType(models.Model):

    name = models.CharField(
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"

    def __str__(self):
        return self.name


# ============================================================
# Leave State
# A soldier may have many leave periods. Days for this period
# are taken from from_date and to_date (inclusive).
# ============================================================

class LeaveState(models.Model):

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="leave_states",
    )

    SLOT_P_LEAVE = "P lve"
    SLOT_C_LEAVE_1 = "C lve-1"
    SLOT_C_LEAVE_2 = "C lve-2"
    SLOT_C_LEAVE_3 = "C lve-3"
    SLOT_C_LEAVE_4 = "C lve-4"
    SLOT_C_LEAVE_5 = "C lve-5"
<<<<<<< HEAD
    SLOT_J_LEAVE = "J/L"
    SLOT_M_LEAVE = "M/L"
    SLOT_COURSE = "Course"
    SLOT_CADRE = "Cadre"
    SLOT_COMD = "Comd"
    SLOT_ATT = "Att"
    SLOT_HOSP = "Hosp"
    SLOT_DEMOB = "Demob"
    SLOT_FDMN = "Fdmn"
    SLOT_TEKNAF = "Teknaf"
    SLOT_OSL = "OSL"
    CASUAL_SLOT_PREFIX = "C lve-"
=======
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
    SLOT_CHOICES = [
        (SLOT_P_LEAVE, "P lve"),
        (SLOT_C_LEAVE_1, "C lve-1"),
        (SLOT_C_LEAVE_2, "C lve-2"),
        (SLOT_C_LEAVE_3, "C lve-3"),
        (SLOT_C_LEAVE_4, "C lve-4"),
        (SLOT_C_LEAVE_5, "C lve-5"),
<<<<<<< HEAD
        (SLOT_J_LEAVE, "J/L"),
        (SLOT_M_LEAVE, "M/L"),
        (SLOT_COURSE, "Course"),
        (SLOT_CADRE, "Cadre"),
        (SLOT_COMD, "Comd"),
        (SLOT_ATT, "Att"),
        (SLOT_HOSP, "Hosp"),
        (SLOT_DEMOB, "Demob"),
        (SLOT_FDMN, "Fdmn"),
        (SLOT_TEKNAF, "Teknaf"),
        (SLOT_OSL, "OSL"),
    ]
    SLOT_ABSENCE_KEYS = {
        SLOT_P_LEAVE: "p_l",
        SLOT_C_LEAVE_1: "c_l",
        SLOT_C_LEAVE_2: "c_l",
        SLOT_C_LEAVE_3: "c_l",
        SLOT_C_LEAVE_4: "c_l",
        SLOT_C_LEAVE_5: "c_l",
        SLOT_J_LEAVE: "j_l",
        SLOT_M_LEAVE: "m_l",
        SLOT_COURSE: "course",
        SLOT_CADRE: "cadre",
        SLOT_COMD: "comd",
        SLOT_ATT: "att",
        SLOT_HOSP: "hosp",
        SLOT_DEMOB: "demob",
        SLOT_FDMN: "fdmn",
        SLOT_TEKNAF: "teknaf",
        SLOT_OSL: "osl",
    }

    @classmethod
    def casual_slot(cls, number):
        return f"{cls.CASUAL_SLOT_PREFIX}{int(number)}"

    @classmethod
    def casual_slot_number(cls, slot):
        if not slot or not str(slot).startswith(cls.CASUAL_SLOT_PREFIX):
            return None
        suffix = str(slot)[len(cls.CASUAL_SLOT_PREFIX):]
        if suffix.isdigit():
            return int(suffix)
        return None

    @classmethod
    def is_casual_slot(cls, slot):
        return cls.casual_slot_number(slot) is not None

    @classmethod
    def next_casual_slot_number(cls, soldier, year):
        numbers = []
        for slot in cls.objects.filter(
            solider=soldier,
            from_date__year=year,
        ).exclude(status=cls.STATUS_REJECTED).values_list("slot", flat=True):
            number = cls.casual_slot_number(slot)
            if number:
                numbers.append(number)
        return (max(numbers) if numbers else 0) + 1

    @classmethod
    def available_casual_slots(cls, soldier, year):
        used = set()
        for slot in cls.objects.filter(
            solider=soldier,
            from_date__year=year,
        ).exclude(status=cls.STATUS_REJECTED).values_list("slot", flat=True):
            number = cls.casual_slot_number(slot)
            if number:
                used.add(number)
        next_number = (max(used) if used else 0) + 1
        numbers = [number for number in range(1, next_number) if number not in used]
        numbers.append(next_number)
        return [(cls.casual_slot(number), cls.casual_slot(number)) for number in numbers]

    def get_slot_display(self):
        return dict(self.SLOT_CHOICES).get(self.slot, self.slot)
=======
    ]
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="leave_states",
    )

    slot = models.CharField(
        max_length=20,
<<<<<<< HEAD
=======
        choices=SLOT_CHOICES,
>>>>>>> 3bffeeaa23060e7395f7dcc79039b760bdbd78bf
        blank=True,
        verbose_name="Excel slot",
    )

    from_date = models.DateField()

    to_date = models.DateField()

    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="applied_leaves",
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_leaves",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    remarks = models.CharField(
        max_length=255,
        blank=True,
    )

    applied_at = models.DateTimeField(auto_now_add=True, null=True)

    decided_at = models.DateTimeField(null=True, blank=True)

    no_days = models.PositiveIntegerField(
        editable=False,
        help_text="Number of days in this leave period, including both dates.",
    )

    total_no_days = models.PositiveIntegerField(
        default=0,
        help_text="Total approved days of this leave type taken by the soldier.",
    )

    class Meta:
        ordering = ["-from_date"]
        verbose_name = "Leave State"
        verbose_name_plural = "Leave States"
        constraints = [
            models.CheckConstraint(
                condition=Q(to_date__gte=F("from_date")),
                name="leave_state_valid_dates",
            ),
        ]

    def clean(self):
        super().clean()

        if self.from_date and self.to_date:
            if self.to_date < self.from_date:
                raise ValidationError({
                    "to_date": "To Date must be on or after From Date."
                })

            self.no_days = (self.to_date - self.from_date).days + 1

    def save(self, *args, **kwargs):
        if self.from_date and self.to_date:
            self.no_days = (self.to_date - self.from_date).days + 1

        super().save(*args, **kwargs)

    def refresh_type_totals(self):
        from django.db.models import Sum

        total = (
            LeaveState.objects.filter(
                solider=self.solider,
                leave_type=self.leave_type,
                status=self.STATUS_APPROVED,
            ).aggregate(total=Sum("no_days"))["total"]
            or 0
        )
        LeaveState.objects.filter(
            solider=self.solider,
            leave_type=self.leave_type,
        ).update(total_no_days=total)
        self.total_no_days = total

    def __str__(self):
        return (
            f"{self.solider} - {self.leave_type} "
            f"({self.from_date} to {self.to_date})"
        )


class ParticipationInSportsTraining(models.Model):
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="sports_trainings"
    )

    year = models.PositiveIntegerField(default=current_year)

    cycle = models.CharField(
        max_length=20,
        choices=YearlyPlan.CYCLE_CHOICES,
        default="1st Cycle",
    )

    name_of_comp = models.CharField(
        max_length=255,
        verbose_name="Name of Competition/Training"
    )

    type_of_comp = models.CharField(
        max_length=20,
        choices=[
            ("sports", "Sports"),
            ("training", "Training"),
        ]
    )

    significant_achievement = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return f"{self.person} - {self.name_of_comp}"


# ============================================================
# IPFT
# Individual Physical Fitness Test.
# A soldier may have many IPFT records by type, chance, and date.
# ============================================================

class IPFT(models.Model):

    TYPE_FIRST_BIANNUAL = "1st Bi-annual"
    TYPE_SECOND_BIANNUAL = "2nd Bi-annual"
    TYPE_CHOICES = [
        (TYPE_FIRST_BIANNUAL, "1st Bi-annual"),
        (TYPE_SECOND_BIANNUAL, "2nd Bi-annual"),
    ]

    CHANCE_CHOICES = [
        ("1st Chance", "1st Chance"),
        ("2nd Chance", "2nd Chance"),
        ("3rd Chance", "3rd Chance"),
        ("4th Chance", "4th Chance"),
        ("5th Chance", "5th Chance"),
    ]

    RESULT_PASS = "Pass"
    RESULT_FAIL = "Fail"
    RESULT_CHOICES = [
        (RESULT_PASS, "Pass"),
        (RESULT_FAIL, "Fail"),
    ]

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="ipft_records",
    )

    type_of_ipft = models.CharField(
        max_length=255,
        choices=TYPE_CHOICES,
        verbose_name="Type of IPFT",
    )

    chance = models.CharField(
        max_length=255,
        choices=CHANCE_CHOICES,
    )

    date = models.DateField()

    result = models.CharField(
        max_length=255,
        choices=RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date", "type_of_ipft", "chance"]
        verbose_name = "IPFT"
        verbose_name_plural = "IPFT Records"

    def __str__(self):
        return (
            f"{self.solider} - {self.type_of_ipft} "
            f"{self.chance} ({self.date})"
        )


# ============================================================
# RET Training Type
# Example: Weapon training, range practice, refresher cadres.
# ============================================================

class RETTrainingType(models.Model):

    name = models.CharField(
        max_length=255,
        unique=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "RET Training Type"
        verbose_name_plural = "RET Training Types"

    def __str__(self):
        return self.name


# ============================================================
# RET State
# Landing module with four firing boards:
# GP Firing, SOSN Firing, CAS Trophy Firing, Grenade Firing.
# ============================================================

FIRING_RESULT_PASS = "Pass"
FIRING_RESULT_FAIL = "Fail"
FIRING_RESULT_CHOICES = [
    (FIRING_RESULT_PASS, "Pass"),
    (FIRING_RESULT_FAIL, "Fail"),
]
def practice_choices(count):
    return [(f"Prac-{index}", f"Prac-{index}") for index in range(1, count + 1)]


FIRING_ATTEMPT_CHOICES = practice_choices(5)
GP_ATTEMPT_CHOICES = practice_choices(5)
SOSN_ATTEMPT_CHOICES = practice_choices(3)
GRENADE_ATTEMPT_CHOICES = practice_choices(4)
SPEED_MARCH_ATTEMPT_CHOICES = practice_choices(6)
ASSAULT_COURSE_ATTEMPT_CHOICES = practice_choices(5)


class GPFiring(models.Model):

    TYPE_100M = "Gp Firing - 100m"
    TYPE_300M = "Gp Firing - 300m"
    TYPE_CHOICES = [
        (TYPE_100M, "Gp Firing - 100m"),
        (TYPE_300M, "Gp Firing - 300m"),
    ]

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="gp_firings",
    )
    type_of_gp = models.CharField(
        max_length=255,
        choices=TYPE_CHOICES,
        verbose_name="Type of GP",
    )
    attempt = models.CharField(
        max_length=255,
        choices=GP_ATTEMPT_CHOICES,
    )
    date_of_firing = models.DateField()
    result = models.CharField(
        max_length=255,
        choices=FIRING_RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_of_firing", "type_of_gp", "attempt"]
        verbose_name = "GP Firing"
        verbose_name_plural = "GP Firings"

    def __str__(self):
        return (
            f"{self.solider} - {self.type_of_gp} "
            f"{self.attempt} ({self.date_of_firing})"
        )


class SOSNFiring(models.Model):

    TYPE_100M = "SOSN Firing - 100m"
    TYPE_300M = "SOSN Firing - 300m"
    TYPE_CHOICES = [
        (TYPE_100M, "SOSN Firing - 100m"),
        (TYPE_300M, "SOSN Firing - 300m"),
    ]

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="sosn_firings",
    )
    type_of_gp = models.CharField(
        max_length=255,
        choices=TYPE_CHOICES,
        verbose_name="Type of SOSN",
    )
    attempt = models.CharField(
        max_length=255,
        choices=SOSN_ATTEMPT_CHOICES,
    )
    date_of_firing = models.DateField()
    gp = models.CharField(max_length=255, blank=True)
    hit = models.CharField(max_length=255, blank=True)
    total_marks = models.CharField(max_length=255, blank=True)
    result = models.CharField(
        max_length=255,
        choices=FIRING_RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_of_firing", "type_of_gp", "attempt"]
        verbose_name = "SOSN Firing"
        verbose_name_plural = "SOSN Firings"

    def __str__(self):
        return (
            f"{self.solider} - {self.type_of_gp} "
            f"{self.attempt} ({self.date_of_firing})"
        )


class CASTrophy(models.Model):

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="cas_trophies",
    )
    date_of_firing = models.DateField()
    gp = models.CharField(max_length=255, blank=True)
    hit = models.CharField(max_length=255, blank=True)
    total_marks = models.CharField(max_length=255, blank=True)
    result = models.CharField(
        max_length=255,
        choices=FIRING_RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_of_firing"]
        verbose_name = "CAS Trophy Firing"
        verbose_name_plural = "CAS Trophy Firings"

    def __str__(self):
        return f"{self.solider} - CAS Trophy ({self.date_of_firing})"


class GrenadeFiring(models.Model):

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="grenade_firings",
    )
    attempt = models.CharField(
        max_length=255,
        choices=GRENADE_ATTEMPT_CHOICES,
    )
    date_of_firing = models.DateField()
    result = models.CharField(
        max_length=255,
        choices=FIRING_RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_of_firing", "attempt"]
        verbose_name = "Grenade Firing"
        verbose_name_plural = "Grenade Firings"

    def __str__(self):
        return (
            f"{self.solider} - Grenade {self.attempt} "
            f"({self.date_of_firing})"
        )


class SpeedMarch(models.Model):

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="speed_marches",
    )
    attempt = models.CharField(
        max_length=255,
        choices=SPEED_MARCH_ATTEMPT_CHOICES,
    )
    date_of_event = models.DateField()
    result = models.CharField(
        max_length=255,
        choices=FIRING_RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_of_event", "attempt"]
        verbose_name = "Speed March"
        verbose_name_plural = "Speed Marches"

    def __str__(self):
        return (
            f"{self.solider} - Speed March {self.attempt} "
            f"({self.date_of_event})"
        )


class AssaultCourse(models.Model):

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="assault_courses",
    )
    attempt = models.CharField(
        max_length=255,
        choices=ASSAULT_COURSE_ATTEMPT_CHOICES,
    )
    date_of_event = models.DateField()
    time = models.CharField(max_length=255, blank=True)
    result = models.CharField(
        max_length=255,
        choices=FIRING_RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_of_event", "attempt"]
        verbose_name = "Assault Course"
        verbose_name_plural = "Assault Courses"

    def __str__(self):
        return (
            f"{self.solider} - Assault Course {self.attempt} "
            f"({self.date_of_event})"
        )


class RETState(models.Model):

    RESULT_PASS = "Pass"
    RESULT_FAIL = "Fail"
    RESULT_CHOICES = [
        (RESULT_PASS, "Pass"),
        (RESULT_FAIL, "Fail"),
    ]

    solider = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="ret_states",
    )

    ret_trg_type = models.ForeignKey(
        RETTrainingType,
        on_delete=models.PROTECT,
        related_name="ret_states",
        verbose_name="RET training type",
    )

    date_performed = models.DateField()

    result = models.CharField(
        max_length=255,
        choices=RESULT_CHOICES,
        blank=True,
    )

    class Meta:
        ordering = ["-date_performed", "ret_trg_type__name"]
        verbose_name = "RET State"
        verbose_name_plural = "RET States"

    def __str__(self):
        return (
            f"{self.solider} - {self.ret_trg_type} "
            f"({self.date_performed})"
        )
