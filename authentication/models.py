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
            extra_fields.setdefault("is_superuser", True)
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
            self.is_superuser = True
        else:
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_co(self):
        if self.role == self.ROLE_CO:
            return True
        appointment = (self.appointment or "").strip().lower()
        return appointment in {
            "co",
            "c.o",
            "c.o.",
            "oc",
            "commanding officer",
        } or "commanding officer" in appointment

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
