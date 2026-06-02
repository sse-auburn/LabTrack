"""Views for the P-Card app."""

import calendar
import io
import mimetypes
from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.accounts.decorators import admin_required
from apps.pcard.forms import PcardFilterForm, PcardItemFormSet, PcardTransactionForm
from apps.pcard.models import PcardDeletionRequest, PcardTransaction
from apps.notifications.utils import notify, notify_admins


def _get_filtered_queryset(request):
    """Return the filtered queryset based on current GET params."""
    queryset = PcardTransaction.objects.prefetch_related('items', 'created_by')

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    search = request.GET.get('q', '').strip()

    if date_from:
        queryset = queryset.filter(transaction_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(transaction_date__lte=date_to)
    if search:
        queryset = queryset.filter(
            Q(notes__icontains=search)
            | Q(items__name__icontains=search)
            | Q(items__description__icontains=search)
        ).distinct()

    return queryset.order_by('-transaction_date', '-created_at')


@login_required
def transaction_list_view(request):
    """List all P-Card transactions with optional date filtering."""
    # Default to current month when no date range has been explicitly set
    if 'date_from' not in request.GET and 'date_to' not in request.GET:
        today = date.today()
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        params = request.GET.copy()
        params['date_from'] = first_day.isoformat()
        params['date_to'] = last_day.isoformat()
        return redirect(f"{request.path}?{params.urlencode()}")

    queryset = _get_filtered_queryset(request)
    total_spent = queryset.aggregate(total=Sum('total_price'))['total']

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pending deletion requests made by current user (for UI badges)
    user_pending_requests = PcardDeletionRequest.objects.filter(
        requested_by=request.user,
        status='PENDING',
    ).values_list('transaction_id', flat=True)

    return render(request, 'pcard/transaction_list.html', {
        'page_obj': page_obj,
        'transaction_list': page_obj,
        'total_count': queryset.count(),
        'total_spent': total_spent,
        'filter_form': PcardFilterForm(request.GET or None),
        'search': request.GET.get('q', ''),
        'user_pending_requests': set(user_pending_requests),
    })


@login_required
def transaction_create_view(request):
    """Create a new P-Card transaction with itemized lines."""
    if request.method == 'POST':
        form = PcardTransactionForm(request.POST, request.FILES)
        formset = PcardItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.save()
            # Save only non-empty items
            for item_form in formset:
                if item_form.cleaned_data and item_form.cleaned_data.get('name'):
                    item = item_form.save(commit=False)
                    item.transaction = transaction
                    item.save()
            messages.success(
                request,
                f'P-Card transaction on {transaction.transaction_date} recorded successfully.'
            )
            return redirect('pcard:detail', pk=transaction.pk)
    else:
        form = PcardTransactionForm(initial={'transaction_date': date.today()})
        formset = PcardItemFormSet()

    return render(request, 'pcard/transaction_form.html', {
        'form': form,
        'formset': formset,
        'action': 'Create',
    })


@login_required
def transaction_detail_view(request, pk):
    """Show full details for a single P-Card transaction."""
    transaction = get_object_or_404(
        PcardTransaction.objects.prefetch_related('items', 'deletion_requests'),
        pk=pk,
    )
    pending_request = transaction.deletion_requests.filter(status='PENDING').first()
    return render(request, 'pcard/transaction_detail.html', {
        'transaction': transaction,
        'pending_request': pending_request,
    })


@login_required
def transaction_edit_view(request, pk):
    """Edit an existing P-Card transaction."""
    transaction = get_object_or_404(PcardTransaction, pk=pk)

    if request.user != transaction.created_by and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to edit this transaction.')
        return redirect('pcard:detail', pk=pk)

    if request.method == 'POST':
        form = PcardTransactionForm(request.POST, request.FILES, instance=transaction)
        formset = PcardItemFormSet(request.POST, instance=transaction)
        if form.is_valid() and formset.is_valid():
            form.save()
            # Save new non-empty items and handle deletions
            for item_form in formset:
                if item_form.cleaned_data:
                    if item_form.cleaned_data.get('DELETE') and item_form.instance.pk:
                        item_form.instance.delete()
                    elif item_form.cleaned_data.get('name'):
                        item = item_form.save(commit=False)
                        item.transaction = transaction
                        item.save()
            messages.success(request, 'P-Card transaction updated successfully.')
            return redirect('pcard:detail', pk=transaction.pk)
    else:
        form = PcardTransactionForm(instance=transaction)
        formset = PcardItemFormSet(instance=transaction)

    return render(request, 'pcard/transaction_form.html', {
        'form': form,
        'formset': formset,
        'transaction': transaction,
        'action': 'Edit',
    })


class DeletionRequestForm(forms.Form):
    """Simple form for members to provide a reason when requesting deletion."""
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Optional reason for deletion request…',
        }),
    )


@login_required
def transaction_delete_view(request, pk):
    """
    Delete a P-Card transaction.
    Admins delete immediately. Members create a deletion request for admin approval.
    """
    transaction = get_object_or_404(PcardTransaction, pk=pk)

    # Only the creator or an admin can initiate deletion
    if request.user != transaction.created_by and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to delete this transaction.')
        return redirect('pcard:detail', pk=pk)

    is_admin = request.user.role == 'ADMIN'

    if request.method == 'POST':
        if is_admin:
            transaction.delete()
            messages.success(request, 'P-Card transaction deleted successfully.')
            return redirect('pcard:list')
        else:
            # Member: create a deletion request
            reason = request.POST.get('reason', '').strip()

            # Check for existing pending request
            if PcardDeletionRequest.objects.filter(
                transaction=transaction,
                requested_by=request.user,
                status='PENDING',
            ).exists():
                messages.warning(request, 'You already have a pending deletion request for this transaction.')
                return redirect('pcard:detail', pk=pk)

            PcardDeletionRequest.objects.create(
                transaction=transaction,
                requested_by=request.user,
                reason=reason,
            )

            notify_admins(
                title='P-Card Deletion Requested',
                message=(
                    f'{request.user.full_name} requested deletion of P-Card transaction '
                    f'#{transaction.pk} ({transaction.transaction_date}, ${transaction.total_price}).'
                ),
                level='warning',
                link='/pcard/deletion-requests/',
                category='system',
                send_email=True,
            )

            messages.success(
                request,
                'Deletion request submitted. An admin will review it shortly.'
            )
            return redirect('pcard:detail', pk=pk)

    form = DeletionRequestForm()
    return render(request, 'pcard/transaction_confirm_delete.html', {
        'transaction': transaction,
        'is_admin': is_admin,
        'form': form,
    })


# ---------------------------------------------------------------------------
# Deletion request admin views
# ---------------------------------------------------------------------------

@login_required
@admin_required
def deletion_request_list_view(request):
    """List all pending P-Card deletion requests (admin only)."""
    pending = PcardDeletionRequest.objects.filter(
        status='PENDING',
    ).select_related('transaction', 'requested_by').order_by('-created_at')

    resolved = PcardDeletionRequest.objects.exclude(
        status='PENDING',
    ).select_related('transaction', 'requested_by', 'resolved_by').order_by('-resolved_at')[:20]

    return render(request, 'pcard/deletion_request_list.html', {
        'pending_requests': pending,
        'resolved_requests': resolved,
    })


@login_required
@admin_required
def deletion_request_approve_view(request, pk):
    """Approve a deletion request and delete the transaction (admin only)."""
    del_request = get_object_or_404(
        PcardDeletionRequest.objects.select_related('transaction', 'requested_by'),
        pk=pk,
        status='PENDING',
    )

    transaction = del_request.transaction
    requester = del_request.requested_by

    # Update request status BEFORE deleting the transaction
    # so Django doesn't complain about an unsaved related object
    del_request.status = 'APPROVED'
    del_request.resolved_by = request.user
    del_request.resolved_at = timezone.now()
    del_request.save()

    # Now delete the transaction
    transaction.delete()

    # Notify requester
    if requester:
        notify(
            recipient=requester,
            title='P-Card Deletion Approved',
            message=(
                f'Your request to delete P-Card transaction '
                f'#{transaction.pk} ({transaction.transaction_date}) was approved by '
                f'{request.user.full_name}.'
            ),
            level='success',
            link='/pcard/',
            category='system',
            send_email=False,
        )

    messages.success(request, 'Deletion request approved and transaction removed.')
    return redirect('pcard:deletion_requests')


@login_required
@admin_required
def deletion_request_reject_view(request, pk):
    """Reject a deletion request (admin only)."""
    del_request = get_object_or_404(
        PcardDeletionRequest.objects.select_related('transaction', 'requested_by'),
        pk=pk,
        status='PENDING',
    )

    transaction = del_request.transaction
    requester = del_request.requested_by

    del_request.status = 'REJECTED'
    del_request.resolved_by = request.user
    del_request.resolved_at = timezone.now()
    del_request.save()

    # Notify requester
    if requester:
        notify(
            recipient=requester,
            title='P-Card Deletion Rejected',
            message=(
                f'Your request to delete P-Card transaction '
                f'#{transaction.pk} ({transaction.transaction_date}) was rejected by '
                f'{request.user.full_name}.'
            ),
            level='error',
            link=f'/pcard/{transaction.pk}/',
            category='system',
            send_email=False,
        )

    messages.success(request, 'Deletion request rejected.')
    return redirect('pcard:deletion_requests')


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

@login_required
def export_excel_view(request):
    """Export filtered transactions to an Excel workbook."""
    queryset = _get_filtered_queryset(request)

    wb = Workbook()

    # ---- Transactions sheet ----
    ws_tx = wb.active
    ws_tx.title = 'Transactions'

    headers_tx = [
        'ID', 'Transaction Date', 'Total Price', 'Item Count',
        'Notes', 'Created By', 'Created At',
    ]
    ws_tx.append(headers_tx)
    for cell in ws_tx[1]:
        cell.font = Font(bold=True)

    for tx in queryset:
        ws_tx.append([
            tx.pk,
            tx.transaction_date,
            float(tx.total_price) if tx.total_price else 0,
            tx.item_count,
            tx.notes or '',
            tx.created_by.full_name if tx.created_by else 'Unknown',
            tx.created_at.replace(tzinfo=None) if tx.created_at else '',
        ])

    # ---- Items sheet ----
    ws_items = wb.create_sheet(title='Items')
    headers_items = [
        'Transaction ID', 'Transaction Date', 'Item Name',
        'Description', 'Quantity', 'Unit Price', 'Line Total',
    ]
    ws_items.append(headers_items)
    for cell in ws_items[1]:
        cell.font = Font(bold=True)

    for tx in queryset.prefetch_related('items'):
        for item in tx.items.all():
            ws_items.append([
                tx.pk,
                tx.transaction_date,
                item.name,
                item.description or '',
                item.quantity,
                float(item.unit_price) if item.unit_price else '',
                float(item.line_total) if item.line_total else '',
            ])

    # ---- Response ----
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"pcard_transactions_{date.today().isoformat()}.xlsx"
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# PDF receipt compilation
# ---------------------------------------------------------------------------

def _make_receipt_image_page(image_bytes):
    """Return a single-page PDF (bytes) with just the receipt image fitted to the page."""
    from PIL import Image as PILImage
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    margin = 0.5 * inch

    pil_img = PILImage.open(io.BytesIO(image_bytes))
    img_w, img_h = pil_img.size

    # Fit inside page while keeping aspect ratio
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    ratio = min(avail_w / img_w, avail_h / img_h)
    draw_w = img_w * ratio
    draw_h = img_h * ratio
    x = (width - draw_w) / 2
    y = (height - draw_h) / 2

    # Use ImageReader so reportlab reads from the PIL object directly,
    # avoiding a seek issue on a previously-consumed BytesIO.
    c.drawImage(ImageReader(pil_img), x, y, width=draw_w, height=draw_h)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


@login_required
def export_pdf_view(request):
    """Export a compiled PDF containing only the receipt images/PDFs."""
    from apps.files.models import StoredFile

    queryset = _get_filtered_queryset(request)
    writer = PdfWriter()

    for tx in queryset:
        if not tx.receipt_file:
            continue

        try:
            stored = StoredFile.objects.get(pk=int(tx.receipt_file.name))
        except (ValueError, TypeError, StoredFile.DoesNotExist):
            continue

        receipt_data = bytes(stored.data)
        receipt_mime = stored.mimetype or mimetypes.guess_type(stored.filename)[0] or ''

        if receipt_mime.startswith('image/'):
            try:
                img_pdf = _make_receipt_image_page(receipt_data)
                writer.append(PdfReader(io.BytesIO(img_pdf)))
            except Exception:
                pass
        elif receipt_mime == 'application/pdf':
            try:
                writer.append(PdfReader(io.BytesIO(receipt_data)))
            except Exception:
                pass

    if not writer.pages:
        # No receipts found — return a single-page empty PDF
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.setFont("Helvetica", 14)
        c.drawCentredString(letter[0] / 2, letter[1] / 2, "No receipts found for the selected transactions.")
        c.showPage()
        c.save()
        buf.seek(0)
        writer.append(PdfReader(buf))

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    filename = f"pcard_receipts_{date.today().isoformat()}.pdf"
    response = HttpResponse(output.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
