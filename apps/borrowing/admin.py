from django.contrib import admin

from .models import BorrowRequest, KitItemReturnApproval


@admin.register(BorrowRequest)
class BorrowRequestAdmin(admin.ModelAdmin):
    list_display = ('borrower', 'equipment', 'kit', 'status', 'due_date', 'requested_date', 'approved_by')
    list_filter = ('status',)
    search_fields = ('borrower__email', 'borrower__username', 'equipment__name')
    readonly_fields = ('requested_date', 'approved_date', 'returned_date')
    date_hierarchy = 'requested_date'
    raw_id_fields = ('borrower', 'equipment', 'kit', 'project', 'approved_by')


@admin.register(KitItemReturnApproval)
class KitItemReturnApprovalAdmin(admin.ModelAdmin):
    list_display = ('borrow_request', 'equipment', 'owner', 'confirmed_by', 'confirmed_at')
    list_filter = ('confirmed_at',)
    search_fields = ('borrow_request__borrower__email', 'equipment__name')
    raw_id_fields = ('borrow_request', 'equipment', 'owner', 'confirmed_by')
