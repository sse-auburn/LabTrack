from django.db import models


class Project(models.Model):
    """A lab project that members work on, which can use equipment."""

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('ON_HOLD', 'On Hold'),
        ('CANCELLED', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_projects',
    )
    members = models.ManyToManyField(
        'accounts.CustomUser',
        through='ProjectMember',
        related_name='projects',
        blank=True,
    )
    equipment = models.ManyToManyField(
        'equipment.Equipment',
        related_name='projects',
        blank=True,
    )
    kits = models.ManyToManyField(
        'kits.Kit',
        related_name='projects',
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class ProjectMember(models.Model):
    """Through model representing a user's membership in a project."""

    ROLE_CHOICES = [
        ('LEAD', 'Lead'),
        ('MEMBER', 'Member'),
        ('OBSERVER', 'Observer'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_members',
    )
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='project_memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} in {self.project.name}"

    class Meta:
        unique_together = ['project', 'user']
