from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser with email as the unique identifier."""

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user model using email as the primary identifier."""

    ROLE_CHOICES = [
        ('MEMBER', 'Member'),
        ('ADMIN', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    class Meta:
        ordering = ['username']


class UserProfile(models.Model):
    """Extended profile information for a CustomUser."""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)

    # Global notification toggles
    in_app_notifications = models.BooleanField(
        default=True,
        help_text='Receive in-app notifications.',
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text='Receive email notifications.',
    )

    # Per-category notification preferences
    notify_borrowing = models.BooleanField(
        default=True,
        help_text='Borrow requests, approvals, returns, and overdue alerts.',
    )
    notify_reservations = models.BooleanField(
        default=True,
        help_text='Reservation confirmations, cancellations, and returns.',
    )
    notify_incidents = models.BooleanField(
        default=True,
        help_text='Incident reports, assignments, and resolutions.',
    )
    notify_equipment = models.BooleanField(
        default=True,
        help_text='New equipment, edits, moves, and deletions.',
    )
    notify_kits = models.BooleanField(
        default=True,
        help_text='Kit creations, updates, and deletions.',
    )
    notify_consumables = models.BooleanField(
        default=True,
        help_text='Consumable usage, restocking, and low-stock alerts.',
    )
    notify_projects = models.BooleanField(
        default=True,
        help_text='Project creations and updates.',
    )
    notify_system = models.BooleanField(
        default=True,
        help_text='User management, role changes, and system events.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"
