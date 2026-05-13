"""Views for the accounts app."""

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


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

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

            log_activity(
                actor=user,
                action='USER_REGISTERED',
                description=f'New user registered: {user.email}',
                content_type_label='customuser',
                object_id=user.pk,
                object_repr=str(user),
                request=request,
            )

            login(request, user)
            messages.success(request, f'Welcome, {user.full_name}! Your account has been created.')
            return redirect('dashboard:index')
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
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            user = authenticate(request, username=email, password=password)
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
                    messages.error(request, 'Your account has been disabled. Please contact an administrator.')
            else:
                messages.error(request, 'Invalid email address or password. Please try again.')
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
def profile_view(request):
    """Display the current user's profile."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'profile_user': request.user,
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
            messages.success(request, f'{target_user.full_name} has been updated.')
            return redirect('accounts:user_detail', pk=pk)
    else:
        user_form = UserUpdateForm(instance=target_user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'accounts/user_form.html', {
        'user_form': user_form,
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

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'query': query,
        'role': role,
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
        messages.success(request, f'User "{name}" has been deleted.')
        return redirect('accounts:user_list')

    return render(request, 'accounts/user_confirm_delete.html', {
        'target_user': target_user,
    })
