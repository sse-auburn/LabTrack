"""
Signal handlers for the borrowing app.

- When a BorrowRequest status changes, send appropriate notifications.
- Log activity for key status transitions.
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse

from apps.borrowing.models import BorrowRequest


@receiver(pre_save, sender=BorrowRequest)
def capture_previous_borrow_status(sender, instance, **kwargs):
    """Store the previous status before a BorrowRequest is updated."""
    if instance.pk:
        try:
            previous = BorrowRequest.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except BorrowRequest.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=BorrowRequest)
def handle_borrow_request_status_change(sender, instance, created, **kwargs):
    """
    After saving a BorrowRequest:
    - Send in-app notifications to the borrower (and admins where relevant).
    - Log an ActivityLog entry for key status changes.
    """
    from apps.notifications.utils import notify, notify_admins
    from apps.activity.utils import log_activity

    item_name = str(instance.equipment or instance.kit or 'Unknown item')

    if created:
        # Notify admins of the new request
        notify_admins(
            title='New Borrow Request',
            message=(
                f"{instance.borrower.full_name} has requested to borrow "
                f"'{item_name}'. Please review."
            ),
            level='info',
            link=reverse('borrowing:detail', args=[instance.pk]),
            category='borrowing',
        )
        log_activity(
            actor=instance.borrower,
            action='BORROW_REQUESTED',
            description=f"{instance.borrower.full_name} requested to borrow '{item_name}'.",
            content_type_label='borrowrequest',
            object_id=instance.pk,
            object_repr=str(instance),
        )
        return

    previous_status = getattr(instance, '_previous_status', None)
    if previous_status is None or previous_status == instance.status:
        return

    if instance.status == 'APPROVED':
        notify(
            recipient=instance.borrower,
            title='Borrow Request Approved',
            message=f"Your request to borrow '{item_name}' has been approved.",
            level='success',
            link=reverse('borrowing:detail', args=[instance.pk]),
            category='borrowing',
        )
        log_activity(
            actor=instance.approved_by,
            action='BORROW_APPROVED',
            description=(
                f"Borrow request for '{item_name}' by "
                f"{instance.borrower.full_name} was approved."
            ),
            content_type_label='borrowrequest',
            object_id=instance.pk,
            object_repr=str(instance),
        )

    elif instance.status == 'REJECTED':
        notify(
            recipient=instance.borrower,
            title='Borrow Request Rejected',
            message=f"Your request to borrow '{item_name}' has been rejected.",
            level='error',
            link=reverse('borrowing:detail', args=[instance.pk]),
            category='borrowing',
        )
        log_activity(
            actor=instance.approved_by,
            action='BORROW_REJECTED',
            description=(
                f"Borrow request for '{item_name}' by "
                f"{instance.borrower.full_name} was rejected."
            ),
            content_type_label='borrowrequest',
            object_id=instance.pk,
            object_repr=str(instance),
        )

    elif instance.status == 'RETURNED':
        notify(
            recipient=instance.borrower,
            title='Item Returned',
            message=f"'{item_name}' has been marked as returned. Thank you!",
            level='success',
            link=reverse('borrowing:detail', args=[instance.pk]),
            category='borrowing',
        )
        log_activity(
            actor=instance.borrower,
            action='BORROW_RETURNED',
            description=f"'{item_name}' returned by {instance.borrower.full_name}.",
            content_type_label='borrowrequest',
            object_id=instance.pk,
            object_repr=str(instance),
        )

    elif instance.status == 'OVERDUE':
        notify(
            recipient=instance.borrower,
            title='Overdue Borrow',
            message=(
                f"Your borrowed item '{item_name}' is overdue. "
                f"Please return it as soon as possible."
            ),
            level='warning',
            link=reverse('borrowing:detail', args=[instance.pk]),
            category='borrowing',
        )
        notify_admins(
            title='Overdue Borrow Alert',
            message=(
                f"{instance.borrower.full_name}'s borrow of '{item_name}' "
                f"is now overdue (due: {instance.due_date})."
            ),
            level='warning',
            link=reverse('borrowing:detail', args=[instance.pk]),
            category='borrowing',
        )
        log_activity(
            actor=instance.borrower,
            action='BORROW_OVERDUE',
            description=(
                f"Borrow of '{item_name}' by {instance.borrower.full_name} "
                f"is overdue (due: {instance.due_date})."
            ),
            content_type_label='borrowrequest',
            object_id=instance.pk,
            object_repr=str(instance),
        )
