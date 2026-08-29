from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone


# ============================================================
# User Manager
# ============================================================

class UserManager(BaseUserManager):

    def create_user(self, username, password=None, **extra_fields):

        if not username:
            raise ValueError("Username is required.")

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.ROLE_CLERK)

        if extra_fields["role"] == User.ROLE_ADMIN:
            extra_fields.setdefault("is_staff", True)
            extra_fields.setdefault("is_superuser", False)
        else:
            extra_fields.setdefault("is_staff", False)
            extra_fields.setdefault("is_superuser", False)

        user = self.model(
            username=self.model.normalize_username(username),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username, password=None, **extra_fields):

        extra_fields.setdefault("is_active", True)
        extra_fields["role"] = User.ROLE_ADMIN
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, password, **extra_fields)


# ============================================================
# User
# ============================================================

class User(AbstractBaseUser, PermissionsMixin):

    ROLE_ADMIN = "admin"
    ROLE_CO = "co"
    ROLE_OFFICER = "officer"
    ROLE_CLERK = "clerk"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_CO, "CO"),
        (ROLE_OFFICER, "Officer"),
        (ROLE_CLERK, "Clerk"),
    ]

    username_validator = UnicodeUsernameValidator()

    # --------------------------------------------------------
    # Login
    # --------------------------------------------------------

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[username_validator],
    )

    # --------------------------------------------------------
    # Profile
    # --------------------------------------------------------

    name = models.CharField(
        max_length=100
    )

    rank = models.ForeignKey(
        "common.Rank",
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True,
    )

    organizations = models.ManyToManyField(
        "common.Organization",
        related_name="users",
        blank=True,
    )

    appointment = models.CharField(
        max_length=100,
        blank=True,
    )

    sign = models.ImageField(
        upload_to="signatures/",
        blank=True,
        null=True,
        verbose_name="Signature",
    )

    photo = models.ImageField(
        upload_to="user_photos/",
        blank=True,
        null=True,
    )

    # --------------------------------------------------------
    # Role
    # --------------------------------------------------------

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CLERK,
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    is_active = models.BooleanField(
        default=True
    )

    is_staff = models.BooleanField(
        default=False
    )

    date_joined = models.DateTimeField(
        default=timezone.now
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        ordering = ["username"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        swappable = "AUTH_USER_MODEL"

    def __str__(self):
        return self.username

    def organization_list(self):
        return ", ".join(
            org.organization_name for org in self.organizations.all()
        )

    def save(self, *args, **kwargs):
        if self.role == self.ROLE_ADMIN:
            self.is_staff = True
        else:
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_co(self):
        return self.role == self.ROLE_CO

    @property
    def is_officer(self):
        return self.role == self.ROLE_OFFICER

    @property
    def is_clerk(self):
        return self.role == self.ROLE_CLERK

    @property
    def can_command(self):
        return self.is_admin or self.is_co

    @property
    def can_view_duty_map(self):
        return self.can_command

    @property
    def can_accept_posting(self):
        return self.role in {self.ROLE_ADMIN, self.ROLE_OFFICER}

    @property
    def can_assign_duty(self):
        return self.role in {self.ROLE_ADMIN, self.ROLE_CO, self.ROLE_OFFICER}

    @property
    def can_apply_leave(self):
        return self.role in {self.ROLE_ADMIN, self.ROLE_CO, self.ROLE_CLERK}

    @property
    def can_approve_leave(self):
        return self.role in {self.ROLE_ADMIN, self.ROLE_CO, self.ROLE_OFFICER}


class UnitProfile(models.Model):
    unit_name = models.CharField(
        max_length=150,
        default="1 Bangladesh Infantry Regiment",
    )
    short_name = models.CharField(max_length=40, default="1 BIR")
    motto = models.CharField(max_length=200, blank=True)
    location = models.CharField(
        max_length=150,
        blank=True,
        default="Ramu Cantonment, Cox's Bazar",
    )
    raised_on = models.CharField(max_length=80, blank=True)
    war_cry = models.CharField(max_length=120, blank=True)
    about = models.TextField(blank=True)
    crest = models.ImageField(upload_to="dashboard/crest/", blank=True, null=True)

    class Meta:
        verbose_name = "Unit profile"
        verbose_name_plural = "Unit profile"

    def __str__(self):
        return self.short_name or self.unit_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        profile, _created = cls.objects.get_or_create(pk=1)
        return profile


class DashboardSlide(models.Model):
    image = models.ImageField(upload_to="dashboard/slides/")
    title = models.CharField(max_length=120, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=10)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "pk"]
        verbose_name = "Dashboard slide"
        verbose_name_plural = "Dashboard slides"

    def __str__(self):
        return self.title or f"Slide {self.pk}"


class HallOfFameCO(models.Model):
    name = models.CharField(max_length=120)
    rank = models.CharField(max_length=80, blank=True)
    photo = models.ImageField(upload_to="dashboard/cos/", blank=True, null=True)
    tenure_start = models.DateField(blank=True, null=True)
    tenure_end = models.DateField(
        blank=True,
        null=True,
        help_text="Leave blank if this officer is still serving.",
    )
    quote = models.TextField(blank=True)
    citation = models.TextField(blank=True)
    is_current = models.BooleanField(
        default=False,
        help_text="Shown as the serving Commanding Officer on the dashboard.",
    )
    display_order = models.PositiveSmallIntegerField(default=10)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_current", "display_order", "-tenure_start", "pk"]
        verbose_name = "Hall of Fame CO"
        verbose_name_plural = "Hall of Fame COs"

    def __str__(self):
        title = f"{self.rank} {self.name}".strip()
        return title or self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            type(self).objects.exclude(pk=self.pk).filter(is_current=True).update(
                is_current=False
            )

    @property
    def tenure_label(self):
        start = self.tenure_start.strftime("%b %Y") if self.tenure_start else ""
        if self.is_current or not self.tenure_end:
            end = "Present" if start else ""
        else:
            end = self.tenure_end.strftime("%b %Y")
        if start and end:
            return f"{start} — {end}"
        return start or end or ""


class UnitAchievement(models.Model):
    title = models.CharField(max_length=160)
    year = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="dashboard/achievements/", blank=True, null=True)
    display_order = models.PositiveSmallIntegerField(default=10)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "-pk"]
        verbose_name = "Unit achievement"
        verbose_name_plural = "Unit achievements"

    def __str__(self):
        if self.year:
            return f"{self.year} · {self.title}"
        return self.title


class UnitHighlight(models.Model):
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40,
        blank=True,
        default="bi-award",
        help_text="Bootstrap icon class, for example bi-award or bi-shield-check.",
    )
    display_order = models.PositiveSmallIntegerField(default=10)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "pk"]
        verbose_name = "Unit highlight"
        verbose_name_plural = "Unit highlights"

    def __str__(self):
        return self.title
