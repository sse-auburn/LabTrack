"""Views for the projects app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render

from apps.activity.utils import log_activity
from apps.projects.forms import ProjectForm, ProjectMemberForm
from apps.projects.models import Project, ProjectMember
from apps.notifications.utils import notify_admins


def _is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


@login_required
def project_list_view(request):
    """List projects.

    Admins see all projects. Members see projects they are a part of (either as
    lead or as a project member).
    Supports ?status= filter and ?q= search.
    """
    if _is_admin(request.user):
        qs = Project.objects.select_related('lead').prefetch_related('project_members')
    else:
        qs = Project.objects.filter(
            models.Q(project_members__user=request.user) | models.Q(lead=request.user)
        ).select_related('lead').prefetch_related('project_members').distinct()

    status_filter = request.GET.get('status', '').strip()
    search = request.GET.get('q', '').strip()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            models.Q(name__icontains=search) | models.Q(description__icontains=search)
        )

    paginator = Paginator(qs.order_by('-created_at'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'projects/project_list.html', {
        'projects': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'search': search,
    })


@login_required
def project_detail_view(request, pk):
    """Show project details including members and linked borrow requests."""
    project = get_object_or_404(
        Project.objects.select_related('lead').prefetch_related(
            'project_members__user',
        ),
        pk=pk,
    )

    # Members can only view projects they belong to (or lead).
    if not _is_admin(request.user):
        is_member = project.project_members.filter(user=request.user).exists()
        if not is_member and project.lead != request.user:
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')

    borrow_requests = project.borrow_requests.select_related(
        'borrower', 'equipment', 'kit'
    ).order_by('-requested_date')

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'borrow_requests': borrow_requests,
    })


@login_required
def project_create_view(request):
    """Create a new project."""
    if request.method == 'POST':
        form = ProjectForm(request.POST, current_user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.lead = request.user
            project.save()
            form.save_m2m()

            # Automatically add the creator as a LEAD member.
            ProjectMember.objects.create(
                project=project,
                user=request.user,
                role='LEAD',
            )

            # Add any additionally selected members as MEMBER.
            for user in form.cleaned_data.get('initial_members', []):
                ProjectMember.objects.get_or_create(
                    project=project,
                    user=user,
                    defaults={'role': 'MEMBER'},
                )

            log_activity(
                actor=request.user,
                action='PROJECT_CREATED',
                description=f'{request.user.full_name or request.user.username} created project "{project.name}"',
                content_type_label='project',
                object_id=project.pk,
                object_repr=str(project),
                request=request,
            )

            notify_admins(
                title='Project Created',
                message=f'Project "{project.name}" was created by {request.user.full_name or request.user.username}.',
                level='info',
                link=f'/projects/{project.pk}/',
                category='projects',
            )

            messages.success(request, f'Project "{project.name}" created successfully.')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm(current_user=request.user)

    return render(request, 'projects/project_form.html', {
        'form': form,
        'action': 'Create',
        'selected_equipment_ids': set(),
        'selected_kit_ids': set(),
        'selected_member_ids': set(),
    })


@login_required
def project_edit_view(request, pk):
    """Edit a project (project lead or admin only)."""
    project = get_object_or_404(Project, pk=pk)

    is_lead = project.lead == request.user or project.project_members.filter(
        user=request.user, role='LEAD'
    ).exists()

    if not _is_admin(request.user) and not is_lead:
        messages.error(request, 'Only the project lead or an admin can edit this project.')
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project, current_user=request.user)
        if form.is_valid():
            form.save()

            # Add any newly selected members (skips duplicates).
            for user in form.cleaned_data.get('initial_members', []):
                ProjectMember.objects.get_or_create(
                    project=project,
                    user=user,
                    defaults={'role': 'MEMBER'},
                )

            log_activity(
                actor=request.user,
                action='PROJECT_UPDATED',
                description=f'{request.user.full_name or request.user.username} updated project "{project.name}"',
                content_type_label='project',
                object_id=project.pk,
                object_repr=str(project),
                request=request,
            )

            notify_admins(
                title='Project Updated',
                message=f'Project "{project.name}" was updated by {request.user.full_name or request.user.username}.',
                level='info',
                link=f'/projects/{project.pk}/',
                category='projects',
            )

            messages.success(request, f'Project "{project.name}" updated successfully.')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project, current_user=request.user)

    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project,
        'action': 'Edit',
        'selected_equipment_ids': set(project.equipment.values_list('pk', flat=True)),
        'selected_kit_ids': set(project.kits.values_list('pk', flat=True)),
        'selected_member_ids': set(project.project_members.values_list('user_id', flat=True)),
    })


@login_required
def project_delete_view(request, pk):
    """Delete a project (project lead or admin)."""
    project = get_object_or_404(Project, pk=pk)

    is_lead = project.lead == request.user or project.project_members.filter(
        user=request.user, role='LEAD'
    ).exists()

    if not _is_admin(request.user) and not is_lead:
        messages.error(request, 'Only the project lead or an admin can delete this project.')
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        project_name = project.name
        project.delete()

        log_activity(
            actor=request.user,
            action='PROJECT_DELETED',
            description=f'{request.user.full_name or request.user.username} deleted project "{project_name}"',
            content_type_label='project',
            object_id=pk,
            object_repr=project_name,
            request=request,
        )

        notify_admins(
            title='Project Deleted',
            message=f'Project "{project_name}" was deleted by {request.user.full_name or request.user.username}.',
            level='warning',
            link='/projects/',
            category='projects',
        )

        messages.success(request, f'Project "{project_name}" deleted.')
        return redirect('projects:list')

    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@login_required
def project_member_add_view(request, pk):
    """Add a member to a project (project lead or admin)."""
    project = get_object_or_404(Project, pk=pk)

    is_lead = project.lead == request.user or project.project_members.filter(
        user=request.user, role='LEAD'
    ).exists()

    if not _is_admin(request.user) and not is_lead:
        messages.error(request, 'Only the project lead or an admin can add members.')
        return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        form = ProjectMemberForm(request.POST, project=project)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.project = project
            membership.save()

            log_activity(
                actor=request.user,
                action='PROJECT_UPDATED',
                description=(
                    f'{request.user.full_name or request.user.username} added {membership.user.full_name} '
                    f'to project "{project.name}" as {membership.get_role_display()}'
                ),
                content_type_label='project',
                object_id=project.pk,
                object_repr=str(project),
                request=request,
            )

            notify_admins(
                title='Project Member Added',
                message=(
                    f'{request.user.full_name or request.user.username} added '
                    f'{membership.user.full_name} to project "{project.name}".'
                ),
                level='info',
                link=f'/projects/{project.pk}/',
                category='projects',
            )

            messages.success(
                request,
                f'{membership.user.full_name} added to project "{project.name}".'
            )
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectMemberForm(project=project)

    return render(request, 'projects/project_member_form.html', {
        'form': form,
        'project': project,
    })


@login_required
def project_member_remove_view(request, pk, mem_pk):
    """Remove a member from a project (project lead or admin)."""
    project = get_object_or_404(Project, pk=pk)
    membership = get_object_or_404(ProjectMember, pk=mem_pk, project=project)

    is_lead = project.lead == request.user or project.project_members.filter(
        user=request.user, role='LEAD'
    ).exists()

    if not _is_admin(request.user) and not is_lead:
        messages.error(request, 'Only the project lead or an admin can remove members.')
        return redirect('projects:detail', pk=project.pk)

    # Prevent removing the sole lead.
    if membership.role == 'LEAD':
        lead_count = project.project_members.filter(role='LEAD').count()
        if lead_count <= 1:
            messages.error(
                request,
                'Cannot remove the only lead from the project. '
                'Assign another lead first.'
            )
            return redirect('projects:detail', pk=project.pk)

    if request.method == 'POST':
        username = membership.user.full_name
        membership.delete()

        log_activity(
            actor=request.user,
            action='PROJECT_UPDATED',
            description=(
                f'{request.user.full_name or request.user.username} removed {username} '
                f'from project "{project.name}"'
            ),
            content_type_label='project',
            object_id=project.pk,
            object_repr=str(project),
            request=request,
        )

        notify_admins(
            title='Project Member Removed',
            message=(
                f'{request.user.full_name or request.user.username} removed '
                f'{username} from project "{project.name}".'
            ),
            level='warning',
            link=f'/projects/{project.pk}/',
            category='projects',
        )

        messages.success(request, f'{username} removed from project "{project.name}".')
        return redirect('projects:detail', pk=project.pk)

    return render(request, 'projects/project_member_confirm_remove.html', {
        'project': project,
        'membership': membership,
    })
