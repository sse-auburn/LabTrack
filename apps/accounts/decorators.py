"""Custom decorators for the accounts app."""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def admin_required(view_func):
    """
    Allow access only to users whose role is 'ADMIN'.

    Unauthenticated visitors are sent to the login page.
    Authenticated non-admins are redirected to the dashboard with an error
    message.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'ADMIN' and not getattr(request.user, 'is_superuser', False):
            messages.error(
                request,
                'You do not have permission to access that page. Admin access is required.',
            )
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)

    return _wrapped


def member_required(view_func):
    """
    Allow access only to authenticated users (any role).

    Unauthenticated visitors are redirected to the login page.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)

    return _wrapped
