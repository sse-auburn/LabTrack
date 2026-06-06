"""Views for the accounts app."""

from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import admin_required
from apps.accounts.forms import (
    CustomUserCreationForm,
    LoginForm,
    ProfileUpdateForm,
    RoleAssignForm,
    UserUpdateForm,
)
from apps.accounts.models import CustomUser, UserProfile
from apps.activity.utils import log_activity
from apps.notifications.utils import notify, notify_admins
from apps.reservations.models import Reservation


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def register_view(request):
    """Register a new user, create their profile, log them in, and redirect."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.save()

            # Ensure a profile exists (signal may have already created one)
            UserProfile.objects.get_or_create(user=user)

            user.is_active = False
            user.save(update_fields=['is_active'])

            ip = _get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')

            log_activity(
                actor=user,
                action='USER_REGISTERED',
                description=f'New user registered (pending approval): {user.email}',
                content_type_label='customuser',
                object_id=user.pk,
                object_repr=str(user),
                request=request,
            )

            notify_admins(
                title='New User Pending Approval',
                message=(
                    f'{user.full_name} ({user.email}) registered and is awaiting account approval.\n\n'
                    f'---\n'
                    f'IP Address: {ip or "unknown"}\n'
                    f'Device: {user_agent}'
                ),
                level='info',
                link='/accounts/users/?status=pending',
                category='system',
                send_email=True,
            )

            messages.success(
                request,
                'Your account has been created and is pending admin approval. '
                'You will be notified once your account is activated.',
            )
            return redirect('accounts:login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Authenticate a user via email and password."""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username_or_email'].lower().strip()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            # Resolve username → email since USERNAME_FIELD is 'email'
            if '@' in username_or_email:
                email = username_or_email
            else:
                try:
                    user_lookup = CustomUser.objects.get(username__iexact=username_or_email)
                    email = user_lookup.email
                except CustomUser.DoesNotExist:
                    email = None

            user = authenticate(request, username=email, password=password) if email else None
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if not remember_me:
                        # Session expires when the browser closes
                        request.session.set_expiry(0)
                    messages.success(request, f'Welcome back, {user.full_name}!')
                    next_url = request.GET.get('next', 'dashboard:index')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Your account is pending admin approval. You will be notified once your account is activated.')
            else:
                messages.error(request, 'Invalid username, email, or password. Please try again.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def logout_view(request):
    """Log the current user out and redirect to the login page."""
    if request.user.is_authenticated:
        messages.info(request, 'You have been logged out.')
        logout(request)
    return redirect('accounts:login')


# ---------------------------------------------------------------------------
# Profile views
# ---------------------------------------------------------------------------

@login_required
def profile_view(request, pk=None):
    """Display a user's profile. Any authenticated member can view any profile."""
    if pk:
        profile_user = get_object_or_404(CustomUser, pk=pk)
    else:
        profile_user = request.user

    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    reservations = Reservation.objects.filter(requester=profile_user).select_related('equipment', 'kit').order_by('-created_at')
    today = date.today()

    # Equipment owned by this user
    from apps.equipment.models import Equipment
    owned_equipment = Equipment.objects.filter(owner=profile_user).select_related('category', 'location')[:20]

    # Kits created by this user
    from apps.kits.models import Kit
    owned_kits = Kit.objects.filter(created_by=profile_user).prefetch_related('items__equipment')[:20]

    # Recent activity by this user
    recent_activities = profile_user.activities.order_by('-timestamp')[:20]

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'profile_user': profile_user,
        'total_borrows': reservations.count(),
        'active_borrows': reservations.filter(status__in=['ACTIVE', 'RETURN_PENDING']).count(),
        'pending_borrows': reservations.filter(status='PENDING').count(),
        'overdue_borrows': reservations.filter(status__in=['CONFIRMED', 'ACTIVE'], end_date__lt=today).count(),
        'active_borrow_list': reservations.filter(status='ACTIVE'),
        'recent_borrows': reservations[:10],
        'owned_equipment': owned_equipment,
        'owned_kits': owned_kits,
        'recent_activities': recent_activities,
    })


@login_required
def profile_edit_view(request):
    """Allow the current user to edit their profile."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


# ---------------------------------------------------------------------------
# Admin – user management views
# ---------------------------------------------------------------------------

@login_required
@admin_required
def user_create_view(request):
    """Create a new user by an admin."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.save()
            UserProfile.objects.get_or_create(user=user)

            log_activity(
                actor=request.user,
                action='USER_CREATED',
                description=f'Admin created user: {user.email}',
                content_type_label='customuser',
                object_id=user.pk,
                object_repr=str(user),
                request=request,
            )

            notify(
                recipient=user,
                title='Account Created',
                message=f'An account has been created for you by {request.user.full_name}. Welcome to LabTrack!',
                level='success',
                link='/',
                category='system',
                send_email=False,
            )
            notify_admins(
                title='New User Created',
                message=f'Admin {request.user.full_name} created user {user.full_name} ({user.email}).',
                level='info',
                link='/accounts/users/',
                category='system',
            )

            messages.success(request, f'User {user.full_name} has been created.')
            return redirect('accounts:user_list')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
@admin_required
def user_edit_view(request, pk):
    """Edit any user as an admin."""
    target_user = get_object_or_404(CustomUser, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=target_user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            log_activity(
                actor=request.user,
                action='USER_UPDATED',
                description=f'Admin updated user: {target_user.email}',
                content_type_label='customuser',
                object_id=target_user.pk,
                object_repr=str(target_user),
                request=request,
            )

            notify(
                recipient=target_user,
                title='Profile Updated',
                message=f'Your profile has been updated by {request.user.full_name}.',
                level='info',
                link=f'/accounts/users/{target_user.pk}/',
                category='system',
                send_email=False,
            )
            notify_admins(
                title='User Updated',
                message=f'Admin {request.user.full_name} updated user {target_user.full_name} ({target_user.email}).',
                level='info',
                link='/accounts/users/',
                category='system',
            )

            messages.success(request, f'{target_user.full_name} has been updated.')
            return redirect('accounts:user_detail', pk=pk)
    else:
        user_form = UserUpdateForm(instance=target_user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/user_form.html', {
        'form': user_form,
        'profile_form': profile_form,
        'target_user': target_user,
        'action': 'Edit',
    })


@login_required
@admin_required
def user_list_view(request):
    """List all registered users with pagination (admin only)."""
    queryset = CustomUser.objects.select_related('profile').order_by('username')

    # Optional search by name / email / username
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            **{'email__icontains': query}
        ) | queryset.filter(
            **{'username__icontains': query}
        ) | queryset.filter(
            **{'first_name__icontains': query}
        ) | queryset.filter(
            **{'last_name__icontains': query}
        )
        queryset = queryset.distinct()

    # Optional role filter
    role = request.GET.get('role', '').strip()
    if role in ('ADMIN', 'MEMBER'):
        queryset = queryset.filter(role=role)

    # Optional status filter
    status = request.GET.get('status', '').strip()
    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status in ('inactive', 'pending'):
        queryset = queryset.filter(is_active=False)

    pending_count = CustomUser.objects.filter(is_active=False).count()

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'query': query,
        'role': role,
        'status': status,
        'pending_count': pending_count,
    })


@login_required
@admin_required
def user_detail_view(request, pk):
    """Show details for a specific user (admin only)."""
    target_user = get_object_or_404(CustomUser, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    # Recent activity for this user
    recent_activities = target_user.activities.order_by('-timestamp')[:20]

    return render(request, 'accounts/user_detail.html', {
        'target_user': target_user,
        'profile': profile,
        'recent_activities': recent_activities,
    })


@login_required
@admin_required
def assign_role_view(request, pk):
    """Change the role of a user (admin only)."""
    target_user = get_object_or_404(CustomUser, pk=pk)
    old_role = target_user.get_role_display()

    if request.method == 'POST':
        form = RoleAssignForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            new_role = target_user.get_role_display()
            log_activity(
                actor=request.user,
                action='USER_ROLE_CHANGED',
                description=(
                    f'Role of {target_user.email} changed from {old_role} to {new_role} '
                    f'by {request.user.email}.'
                ),
                content_type_label='customuser',
                object_id=target_user.pk,
                object_repr=str(target_user),
                request=request,
            )

            notify(
                recipient=target_user,
                title='Role Changed',
                message=f'Your role has been changed from {old_role} to {new_role} by {request.user.full_name}.',
                level='info',
                link='/accounts/profile/',
                category='system',
                send_email=False,
            )
            notify_admins(
                title='User Role Changed',
                message=f'Role of {target_user.full_name} changed from {old_role} to {new_role} by {request.user.full_name}.',
                level='info',
                link='/accounts/users/',
                category='system',
            )

            messages.success(
                request,
                f"Role for {target_user.full_name} updated to {new_role}.",
            )
            return redirect('accounts:user_detail', pk=pk)
    else:
        form = RoleAssignForm(instance=target_user)

    return render(request, 'accounts/assign_role.html', {
        'form': form,
        'target_user': target_user,
    })


@login_required
@admin_required
def toggle_active_view(request, pk):
    """Toggle the active/inactive status of a user (admin only)."""
    target_user = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=['is_active'])
        status = 'activated' if target_user.is_active else 'deactivated'
        log_activity(
            actor=request.user,
            action='USER_STATUS_CHANGED',
            description=f'User {target_user.email} was {status} by {request.user.email}.',
            content_type_label='customuser',
            object_id=target_user.pk,
            object_repr=str(target_user),
            request=request,
        )

        if target_user.is_active:
            notify(
                recipient=target_user,
                title='Account Approved',
                message=f'Your account has been approved by {request.user.full_name}. You can now log in.',
                level='success',
                link='/',
                category='system',
                send_email=False,
            )
        else:
            notify(
                recipient=target_user,
                title='Account Deactivated',
                message=f'Your account has been deactivated by {request.user.full_name}. Contact an administrator for help.',
                level='warning',
                link='/accounts/profile/',
                category='system',
                send_email=False,
            )
        notify_admins(
            title='User Status Changed',
            message=f'User {target_user.full_name} ({target_user.email}) has been {status} by {request.user.full_name}.',
            level='info',
            link='/accounts/users/',
            category='system',
        )

        messages.success(request, f"{target_user.full_name} has been {status}.")

    return redirect('accounts:user_list')


@login_required
@admin_required
def user_delete_view(request, pk):
    """Delete a user account (admin only)."""
    target_user = get_object_or_404(CustomUser, pk=pk)

    if target_user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:user_list')

    if request.method == 'POST':
        name = target_user.full_name or target_user.username
        target_user.delete()
        log_activity(
            actor=request.user,
            action='USER_DELETED',
            description=f'Admin deleted user: {name}.',
            content_type_label='customuser',
            object_id=pk,
            object_repr=name,
            request=request,
        )

        notify_admins(
            title='User Deleted',
            message=f'User "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='/accounts/users/',
            category='system',
        )

        messages.success(request, f'User "{name}" has been deleted.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/user_confirm_delete.html', {
        'target_user': target_user,
    })
