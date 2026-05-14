"""Views for the incidents app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.activity.utils import log_activity
from apps.incidents.forms import (
    CalibrationLogForm,
    IncidentAssignForm,
    IncidentReportForm,
    IncidentUpdateForm,
    MaintenanceCompleteForm,
    MaintenanceLogForm,
)
from apps.incidents.models import CalibrationLog, IncidentReport, MaintenanceLog
from apps.notifications.utils import notify, notify_admins


# ---------------------------------------------------------------------------
# Incident views
# ---------------------------------------------------------------------------

@login_required
def incident_list_view(request):
    """All members can see all incidents."""
    qs = IncidentReport.objects.select_related('equipment', 'reported_by', 'assigned_to')

    severity = request.GET.get('severity', '').strip()
    status = request.GET.get('status', '').strip()
    if severity:
        qs = qs.filter(severity=severity)
    if status:
        qs = qs.filter(status=status)

    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'incidents/list.html', {
        'page_obj': page_obj,
        'incidents': page_obj,
        'severity_filter': severity,
        'status_filter': status,
    })


@login_required
def incident_detail_view(request, pk):
    """All members can view any incident."""
    incident = get_object_or_404(
        IncidentReport.objects.select_related(
            'equipment', 'reported_by', 'assigned_to', 'resolved_by'
        ),
        pk=pk,
    )
    return render(request, 'incidents/detail.html', {'incident': incident})


@login_required
def incident_create_view(request):
    """Any logged-in user can report a new incident."""
    if request.method == 'POST':
        form = IncidentReportForm(request.POST, request.FILES)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.reported_by = request.user
            incident.save()

            log_activity(
                actor=request.user,
                action='INCIDENT_REPORTED',
                description=(
                    f'{request.user.username} reported incident "{incident.title}" '
                    f'on {incident.equipment.name} (severity: {incident.severity}).'
                ),
                content_type_label='incidentreport',
                object_id=incident.pk,
                object_repr=str(incident),
                request=request,
            )

            notify_admins(
                title=f'New Incident Reported: {incident.title}',
                message=(
                    f'{request.user.username} reported a {incident.get_severity_display()} '
                    f'incident on "{incident.equipment.name}": {incident.title}.'
                ),
                level='warning' if incident.severity in ('HIGH', 'CRITICAL') else 'info',
                link=f'/incidents/{incident.pk}/',
                category='incidents',
            )

            messages.success(request, 'Incident reported successfully.')
            return redirect('incidents:detail', pk=incident.pk)
    else:
        equipment_id = request.GET.get('equipment')
        initial = {'equipment': equipment_id} if equipment_id else {}
        form = IncidentReportForm(initial=initial)

    return render(request, 'incidents/form.html', {
        'form': form,
        'title': 'Report Incident',
        'submit_label': 'Submit Report',
    })


def _can_manage_incident(user, incident):
    """Reporter, equipment owner, assignee, or admin can edit/resolve."""
    return (
        user.role == 'ADMIN'
        or incident.reported_by == user
        or incident.equipment.owner == user
        or incident.assigned_to == user
    )


@login_required
def incident_edit_view(request, pk):
    """Reporter, equipment owner, assignee, or admin can edit."""
    incident = get_object_or_404(IncidentReport, pk=pk)

    if not _can_manage_incident(request.user, incident):
        messages.error(request, 'You do not have permission to edit this incident.')
        return redirect('incidents:detail', pk=pk)

    if request.method == 'POST':
        form = IncidentReportForm(request.POST, request.FILES, instance=incident)
        if form.is_valid():
            incident = form.save()
            log_activity(
                actor=request.user,
                action='INCIDENT_REPORTED',
                description=f'Incident "{incident.title}" updated by {request.user.username}.',
                content_type_label='incidentreport',
                object_id=incident.pk,
                object_repr=str(incident),
                request=request,
            )

            notify_admins(
                title='Incident Updated',
                message=f'Incident "{incident.title}" was updated by {request.user.full_name or request.user.username}.',
                level='info',
                link=f'/incidents/{incident.pk}/',
                category='incidents',
            )

            messages.success(request, 'Incident updated successfully.')
            return redirect('incidents:detail', pk=incident.pk)
    else:
        form = IncidentReportForm(instance=incident)

    return render(request, 'incidents/form.html', {
        'form': form,
        'incident': incident,
        'title': f'Edit Incident: {incident.title}',
        'submit_label': 'Save Changes',
    })


@login_required
def incident_resolve_view(request, pk):
    """Reporter, equipment owner, assignee, or admin can resolve an incident."""
    incident = get_object_or_404(IncidentReport, pk=pk)

    if not _can_manage_incident(request.user, incident):
        messages.error(request, 'You do not have permission to resolve this incident.')
        return redirect('incidents:detail', pk=pk)

    if request.method == 'POST':
        form = IncidentUpdateForm(request.POST, instance=incident)
        if form.is_valid():
            incident = form.save(commit=False)
            if incident.status == 'RESOLVED':
                incident.resolved_by = request.user
                incident.resolved_at = timezone.now()

                # Update equipment condition if incident was critical
                if incident.severity == 'CRITICAL':
                    equipment = incident.equipment
                    equipment.condition = 'POOR'
                    equipment.save(update_fields=['condition', 'updated_at'])
            incident.save()

            log_activity(
                actor=request.user,
                action='INCIDENT_RESOLVED',
                description=(
                    f'Incident "{incident.title}" marked as {incident.get_status_display()} '
                    f'by {request.user.username}.'
                ),
                content_type_label='incidentreport',
                object_id=incident.pk,
                object_repr=str(incident),
                request=request,
            )

            if incident.reported_by:
                notify(
                    recipient=incident.reported_by,
                    title=f'Incident Update: {incident.title}',
                    message=(
                        f'Your incident report "{incident.title}" has been marked as '
                        f'{incident.get_status_display()}.'
                    ),
                    level='success' if incident.status == 'RESOLVED' else 'info',
                    link=f'/incidents/{incident.pk}/',
                    category='incidents',
                )

            messages.success(request, f'Incident updated to "{incident.get_status_display()}".')
            return redirect('incidents:detail', pk=incident.pk)
    else:
        form = IncidentUpdateForm(instance=incident)

    return render(request, 'incidents/resolve.html', {
        'form': form,
        'incident': incident,
    })


@login_required
def incident_assign_view(request, pk):
    """Reporter or equipment owner can assign someone to investigate an incident."""
    incident = get_object_or_404(IncidentReport, pk=pk)

    if not _can_manage_incident(request.user, incident):
        messages.error(request, 'You do not have permission to assign this incident.')
        return redirect('incidents:detail', pk=pk)

    if request.method == 'POST':
        form = IncidentAssignForm(request.POST, instance=incident)
        if form.is_valid():
            prev_assignee = incident.assigned_to
            incident = form.save()

            log_activity(
                actor=request.user,
                action='OTHER',
                description=(
                    f'Incident "{incident.title}" assigned to '
                    f'{incident.assigned_to.full_name if incident.assigned_to else "nobody"} '
                    f'by {request.user.username}.'
                ),
                content_type_label='incidentreport',
                object_id=incident.pk,
                object_repr=str(incident),
                request=request,
            )

            if incident.assigned_to and incident.assigned_to != request.user:
                notify(
                    recipient=incident.assigned_to,
                    title=f'Incident Assigned to You: {incident.title}',
                    message=(
                        f'{request.user.full_name or request.user.username} assigned you to '
                        f'investigate incident "{incident.title}" on {incident.equipment.name}.'
                    ),
                    level='info',
                    link=f'/incidents/{incident.pk}/',
                    category='incidents',
                )

            # Auto-set status to INVESTIGATING if it was OPEN
            if incident.status == 'OPEN' and incident.assigned_to:
                incident.status = 'INVESTIGATING'
                incident.save(update_fields=['status'])

            messages.success(request, 'Incident assignment updated.')
            return redirect('incidents:detail', pk=incident.pk)
    else:
        form = IncidentAssignForm(instance=incident)

    return render(request, 'incidents/assign.html', {
        'form': form,
        'incident': incident,
    })


# ---------------------------------------------------------------------------
# Maintenance views
# ---------------------------------------------------------------------------

@login_required
def maintenance_list_view(request):
    """Members see maintenance logs for equipment they own or currently borrow; admins see all."""
    if request.user.role == 'ADMIN':
        logs = MaintenanceLog.objects.select_related(
            'equipment', 'performed_by'
        ).order_by('-scheduled_date')
    else:
        owned_ids = request.user.owned_equipment.values_list('pk', flat=True)
        borrowed_ids = (
            request.user.borrow_requests
            .filter(status__in=['APPROVED', 'ACTIVE'])
            .exclude(equipment__isnull=True)
            .values_list('equipment__pk', flat=True)
        )
        logs = MaintenanceLog.objects.filter(
            equipment__pk__in=list(owned_ids) + list(borrowed_ids)
        ).select_related('equipment', 'performed_by').order_by('-scheduled_date')

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'incidents/maintenance_list.html', {'page_obj': page_obj})


@login_required
def maintenance_detail_view(request, pk):
    """Show details of a single maintenance log entry."""
    log = get_object_or_404(MaintenanceLog, pk=pk)
    return render(request, 'incidents/maintenance_detail.html', {'log': log})


@login_required
def maintenance_create_view(request):
    """Schedule a new maintenance activity (any logged-in user)."""
    if request.method == 'POST':
        form = MaintenanceLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.performed_by = request.user
            log.save()

            log_activity(
                actor=request.user,
                action='MAINTENANCE_SCHEDULED',
                description=(
                    f'Maintenance scheduled for "{log.equipment.name}" '
                    f'({log.get_maintenance_type_display()}) on {log.scheduled_date}.'
                ),
                content_type_label='maintenancelog',
                object_id=log.pk,
                object_repr=str(log),
                request=request,
            )

            notify_admins(
                title=f'Maintenance Scheduled: {log.equipment.name}',
                message=(
                    f'{log.get_maintenance_type_display()} maintenance scheduled for '
                    f'"{log.equipment.name}" on {log.scheduled_date}.'
                ),
                level='info',
                link=f'/incidents/maintenance/{log.pk}/',
                category='incidents',
            )

            messages.success(request, 'Maintenance log created successfully.')
            return redirect('incidents:maintenance_detail', pk=log.pk)
    else:
        equipment_id = request.GET.get('equipment')
        initial = {'equipment': equipment_id} if equipment_id else {}
        form = MaintenanceLogForm(initial=initial)

    return render(request, 'incidents/maintenance_form.html', {
        'form': form,
        'title': 'Schedule Maintenance',
        'submit_label': 'Create',
    })


@login_required
def maintenance_complete_view(request, pk):
    """Mark a maintenance log as completed — equipment owner or admin."""
    log = get_object_or_404(MaintenanceLog, pk=pk)

    if request.user.role != 'ADMIN' and log.equipment.owner != request.user:
        messages.error(request, 'Only the equipment owner can complete this maintenance.')
        return redirect('incidents:maintenance_detail', pk=pk)

    if request.method == 'POST':
        form = MaintenanceCompleteForm(request.POST, instance=log)
        if form.is_valid():
            log = form.save(commit=False)
            if log.status == 'COMPLETED':
                # Set equipment back to available
                equipment = log.equipment
                if equipment.status == 'MAINTENANCE':
                    equipment.status = 'AVAILABLE'
                    equipment.save(update_fields=['status', 'updated_at'])
            log.save()

            log_activity(
                actor=request.user,
                action='MAINTENANCE_COMPLETED',
                description=(
                    f'Maintenance for "{log.equipment.name}" marked as '
                    f'{log.get_status_display()} by {request.user.username}.'
                ),
                content_type_label='maintenancelog',
                object_id=log.pk,
                object_repr=str(log),
                request=request,
            )

            notify_admins(
                title='Maintenance Updated',
                message=(
                    f'Maintenance for "{log.equipment.name}" marked as '
                    f'{log.get_status_display()} by {request.user.full_name or request.user.username}.'
                ),
                level='info',
                link=f'/incidents/maintenance/{log.pk}/',
                category='incidents',
            )

            messages.success(request, f'Maintenance log updated to "{log.get_status_display()}".')
            return redirect('incidents:maintenance_detail', pk=log.pk)
    else:
        form = MaintenanceCompleteForm(instance=log)

    return render(request, 'incidents/maintenance_complete.html', {
        'form': form,
        'log': log,
    })


# ---------------------------------------------------------------------------
# Calibration views
# ---------------------------------------------------------------------------

@login_required
def calibration_list_view(request):
    """List calibration logs; admins see all, members see their owned equipment."""
    if request.user.role == 'ADMIN':
        logs = CalibrationLog.objects.select_related(
            'equipment', 'calibrated_by'
        ).order_by('-calibration_date')
    else:
        logs = CalibrationLog.objects.filter(
            equipment__owner=request.user
        ).select_related('equipment', 'calibrated_by').order_by('-calibration_date')

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'incidents/calibration_list.html', {'page_obj': page_obj})


@login_required
def calibration_create_view(request):
    """Record a new calibration log (any logged-in user)."""
    if request.method == 'POST':
        form = CalibrationLogForm(request.POST)
        if form.is_valid():
            calibration = form.save(commit=False)
            calibration.calibrated_by = request.user
            calibration.save()

            log_activity(
                actor=request.user,
                action='OTHER',
                description=(
                    f'Calibration logged for "{calibration.equipment.name}" '
                    f'on {calibration.calibration_date} — status: {calibration.get_status_display()}.'
                ),
                content_type_label='calibrationlog',
                object_id=calibration.pk,
                object_repr=str(calibration),
                request=request,
            )

            notify_admins(
                title=f'Calibration Logged: {calibration.equipment.name}',
                message=(
                    f'Calibration for "{calibration.equipment.name}" recorded on '
                    f'{calibration.calibration_date}. Status: {calibration.get_status_display()}.'
                ),
                level='success' if calibration.status == 'PASS' else 'warning',
                link=f'/incidents/calibration/',
                category='incidents',
            )

            messages.success(request, 'Calibration log created successfully.')
            return redirect('incidents:calibration_list')
    else:
        form = CalibrationLogForm()

    return render(request, 'incidents/calibration_form.html', {
        'form': form,
        'title': 'Record Calibration',
        'submit_label': 'Save',
    })


@login_required
def incident_delete_view(request, pk):
    """Delete an incident report (admin or reporter only)."""
    incident = get_object_or_404(IncidentReport, pk=pk)

    if request.user.role != 'ADMIN' and incident.reported_by != request.user:
        messages.error(request, 'You do not have permission to delete this incident.')
        return redirect('incidents:detail', pk=pk)

    if request.method == 'POST':
        title = incident.title
        incident.delete()
        log_activity(
            actor=request.user,
            action='INCIDENT_DELETED',
            description=f'{request.user.username} deleted incident "{title}"',
            content_type_label='incidentreport',
            object_id=pk,
            object_repr=title,
            request=request,
        )

        notify_admins(
            title='Incident Deleted',
            message=f'Incident "{title}" was deleted by {request.user.full_name or request.user.username}.',
            level='warning',
            link='/incidents/',
            category='incidents',
        )

        messages.success(request, f'Incident "{title}" has been deleted.')
        return redirect('incidents:list')

    return render(request, 'incidents/incident_confirm_delete.html', {'incident': incident})


@login_required
def maintenance_delete_view(request, pk):
    """Delete a maintenance log (admin or the performer only)."""
    log = get_object_or_404(MaintenanceLog, pk=pk)

    if request.user.role != 'ADMIN' and log.performed_by != request.user:
        messages.error(request, 'You do not have permission to delete this maintenance log.')
        return redirect('incidents:maintenance_detail', pk=pk)

    if request.method == 'POST':
        equipment_name = log.equipment.name
        log.delete()
        log_activity(
            actor=request.user,
            action='MAINTENANCE_DELETED',
            description=f'{request.user.username} deleted maintenance log for "{equipment_name}"',
            content_type_label='maintenancelog',
            object_id=pk,
            object_repr=equipment_name,
            request=request,
        )

        notify_admins(
            title='Maintenance Deleted',
            message=f'Maintenance log for "{equipment_name}" was deleted by {request.user.full_name or request.user.username}.',
            level='warning',
            link='/incidents/maintenance/',
            category='incidents',
        )

        messages.success(request, f'Maintenance log for "{equipment_name}" has been deleted.')
        return redirect('incidents:maintenance_list')

    return render(request, 'incidents/maintenance_confirm_delete.html', {'log': log})


@login_required
def calibration_delete_view(request, pk):
    """Delete a calibration log (admin or the performer only)."""
    calibration = get_object_or_404(CalibrationLog, pk=pk)

    if request.user.role != 'ADMIN' and calibration.calibrated_by != request.user:
        messages.error(request, 'You do not have permission to delete this calibration log.')
        return redirect('incidents:calibration_list')

    if request.method == 'POST':
        equipment_name = calibration.equipment.name
        calibration.delete()
        log_activity(
            actor=request.user,
            action='OTHER',
            description=f'{request.user.username} deleted calibration log for "{equipment_name}"',
            content_type_label='calibrationlog',
            object_id=pk,
            object_repr=equipment_name,
            request=request,
        )

        notify_admins(
            title='Calibration Deleted',
            message=f'Calibration log for "{equipment_name}" was deleted by {request.user.full_name or request.user.username}.',
            level='warning',
            link='/incidents/calibration/',
            category='incidents',
        )

        messages.success(request, f'Calibration log for "{equipment_name}" has been deleted.')
        return redirect('incidents:calibration_list')

    return render(request, 'incidents/calibration_confirm_delete.html', {'calibration': calibration})
