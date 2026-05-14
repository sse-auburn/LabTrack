"""Views for the P-Card app."""

import io
import mimetypes
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from openpyxl import Workbook
from openpyxl.styles import Font, NamedStyle
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.pcard.forms import PcardFilterForm, PcardItemFormSet, PcardTransactionForm
from apps.pcard.models import PcardTransaction


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
    queryset = _get_filtered_queryset(request)
    total_spent = queryset.aggregate(total=Sum('total_price'))['total']

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pcard/transaction_list.html', {
        'page_obj': page_obj,
        'transaction_list': page_obj,
        'total_count': queryset.count(),
        'total_spent': total_spent,
        'filter_form': PcardFilterForm(request.GET or None),
        'search': request.GET.get('q', ''),
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
            formset.instance = transaction
            formset.save()
            messages.success(
                request,
                f'P-Card transaction on {transaction.transaction_date} recorded successfully.'
            )
            return redirect('pcard:detail', pk=transaction.pk)
    else:
        form = PcardTransactionForm()
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
        PcardTransaction.objects.prefetch_related('items'),
        pk=pk,
    )
    return render(request, 'pcard/transaction_detail.html', {
        'transaction': transaction,
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
            formset.save()
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


@login_required
def transaction_delete_view(request, pk):
    """Delete a P-Card transaction."""
    transaction = get_object_or_404(PcardTransaction, pk=pk)

    if request.user != transaction.created_by and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to delete this transaction.')
        return redirect('pcard:detail', pk=pk)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'P-Card transaction deleted successfully.')
        return redirect('pcard:list')

    return render(request, 'pcard/transaction_confirm_delete.html', {
        'transaction': transaction,
    })


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

def _make_header_page(tx):
    """Return a single-page PDF (bytes) with transaction header info."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75 * inch, height - 1 * inch, "P-Card Receipt")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, height - 1.4 * inch, f"Transaction #{tx.pk}")

    c.setFont("Helvetica", 10)
    y = height - 1.8 * inch
    line_height = 14

    c.drawString(0.75 * inch, y, f"Date: {tx.transaction_date}")
    y -= line_height
    c.drawString(0.75 * inch, y, f"Total: ${tx.total_price}")
    y -= line_height
    c.drawString(0.75 * inch, y, f"Recorded by: {tx.created_by.full_name if tx.created_by else 'Unknown'}")
    y -= line_height * 1.5

    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75 * inch, y, "Items:")
    y -= line_height
    c.setFont("Helvetica", 9)
    for item in tx.items.all():
        line = f"  • {item.name}"
        if item.description:
            line += f" — {item.description}"
        line += f" (x{item.quantity})"
        if item.unit_price:
            line += f" @ ${item.unit_price}"
        c.drawString(0.75 * inch, y, line)
        y -= line_height
        if y < 0.75 * inch:
            break

    if tx.notes:
        y -= line_height * 0.5
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.75 * inch, y, "Notes:")
        y -= line_height
        c.setFont("Helvetica", 9)
        for note_line in tx.notes.splitlines()[:5]:
            c.drawString(0.75 * inch, y, note_line)
            y -= line_height

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _make_image_page(tx, image_bytes):
    """Return a single-page PDF (bytes) with the receipt image centered."""
    from PIL import Image as PILImage

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    margin = 0.75 * inch

    # Header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, height - margin, f"Receipt — Transaction #{tx.pk} ({tx.transaction_date})")

    # Image area
    img_buf = io.BytesIO(image_bytes)
    pil_img = PILImage.open(img_buf)
    img_w, img_h = pil_img.size

    # Fit inside available area while keeping aspect ratio
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin - 0.5 * inch
    ratio = min(avail_w / img_w, avail_h / img_h)
    draw_w = img_w * ratio
    draw_h = img_h * ratio
    x = (width - draw_w) / 2
    y = (height - draw_h) / 2 - 0.25 * inch

    c.drawImage(img_buf, x, y, width=draw_w, height=draw_h)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


@login_required
def export_pdf_view(request):
    """Export a compiled PDF of all receipts for the filtered transactions."""
    queryset = _get_filtered_queryset(request)
    transactions = list(queryset.prefetch_related('items'))

    writer = PdfWriter()

    # Cover page
    cover_buf = io.BytesIO()
    c = canvas.Canvas(cover_buf, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 2 * inch, "P-Card Receipt Compilation")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 2.5 * inch, f"Generated: {date.today().isoformat()}")
    c.drawCentredString(width / 2, height - 2.9 * inch, f"Transactions: {len(transactions)}")
    c.showPage()
    c.save()
    cover_buf.seek(0)
    writer.append(PdfReader(cover_buf))

    for tx in transactions:
        if not tx.receipt_file:
            continue

        # Header page
        header_pdf = _make_header_page(tx)
        writer.append(PdfReader(io.BytesIO(header_pdf)))

        # Receipt content
        receipt_name = tx.receipt_file.name
        receipt_mime, _ = mimetypes.guess_type(receipt_name)
        if receipt_mime is None:
            receipt_mime = 'application/octet-stream'

        try:
            tx.receipt_file.seek(0)
            receipt_data = tx.receipt_file.read()
        except Exception:
            continue

        if receipt_mime.startswith('image/'):
            try:
                img_pdf = _make_image_page(tx, receipt_data)
                writer.append(PdfReader(io.BytesIO(img_pdf)))
            except Exception:
                pass
        elif receipt_mime == 'application/pdf':
            try:
                writer.append(PdfReader(io.BytesIO(receipt_data)))
            except Exception:
                pass

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    filename = f"pcard_receipts_{date.today().isoformat()}.pdf"
    response = HttpResponse(output.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
