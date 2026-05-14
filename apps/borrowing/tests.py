"""Unit tests for the borrowing app."""

import datetime

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.borrowing.forms import BorrowRequestForm
from apps.borrowing.models import BorrowRequest, KitItemReturnApproval
from apps.equipment.models import Category, Equipment, Location
from apps.kits.models import Kit, KitItem
from apps.notifications.models import Notification
from apps.reservations.models import Reservation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_admin(username='admin', email='admin@lab.test'):
    return CustomUser.objects.create_user(
        email=email, username=username, password='testpass123', role='ADMIN'
    )


def make_member(username='member', email='member@lab.test'):
    return CustomUser.objects.create_user(
        email=email, username=username, password='testpass123', role='MEMBER'
    )


def make_equipment(name='Oscilloscope', owner=None, status='AVAILABLE'):
    cat, _ = Category.objects.get_or_create(name='Electronics')
    loc, _ = Location.objects.get_or_create(name='Lab A')
    return Equipment.objects.create(
        name=name,
        category=cat,
        location=loc,
        owner=owner,
        status=status,
        is_active=True,
    )


def make_kit(name='Lab Kit', created_by=None):
    return Kit.objects.create(name=name, is_active=True, created_by=created_by)


def make_borrow(borrower, equipment=None, kit=None, status='APPROVED', days_ahead=7):
    return BorrowRequest.objects.create(
        borrower=borrower,
        equipment=equipment,
        kit=kit,
        purpose='Test purpose',
        due_date=datetime.date.today() + datetime.timedelta(days=days_ahead),
        status=status,
    )


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------

class BorrowRequestFormTests(TestCase):

    def setUp(self):
        self.owner = make_member(username='owner', email='owner@lab.test')
        self.equipment = make_equipment(owner=self.owner)

    def _form_data(self, **overrides):
        data = {
            'equipment': self.equipment.pk,
            'kit': '',
            'purpose': 'Research experiment',
            'due_date': (datetime.date.today() + datetime.timedelta(days=5)).isoformat(),
        }
        data.update(overrides)
        return data

    # Test 1 – due_date in the past is rejected
    def test_past_due_date_is_invalid(self):
        data = self._form_data(due_date=(datetime.date.today() - datetime.timedelta(days=1)).isoformat())
        form = BorrowRequestForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('Due date must be today or a future date.', str(form.errors))

    # Test 2 – conflicting CONFIRMED reservation is rejected
    def test_conflicting_confirmed_reservation_is_invalid(self):
        requester = make_member(username='res_user', email='resuser@lab.test')
        today = datetime.date.today()
        Reservation.objects.create(
            requester=requester,
            equipment=self.equipment,
            status='CONFIRMED',
            start_date=today + datetime.timedelta(days=2),
            end_date=today + datetime.timedelta(days=10),
        )
        # due_date falls within the reservation window
        data = self._form_data(due_date=(today + datetime.timedelta(days=5)).isoformat())
        form = BorrowRequestForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('confirmed reservation', str(form.errors))

    # Test 3 – valid form with no conflicts
    def test_valid_form_no_conflicts(self):
        data = self._form_data()
        form = BorrowRequestForm(data=data)
        self.assertTrue(form.is_valid(), msg=str(form.errors))


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

class BorrowCreateViewTests(TestCase):

    def setUp(self):
        self.member = make_member()
        self.equipment = make_equipment(owner=self.member)
        self.url = reverse('borrowing:create')

    # Test 4 – anonymous GET redirects to login
    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    # Test 5 – POST creates BorrowRequest with status APPROVED and correct borrower
    def test_post_creates_borrow_request(self):
        self.client.force_login(self.member)
        due_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        response = self.client.post(self.url, {
            'equipment': self.equipment.pk,
            'kit': '',
            'purpose': 'Lab work',
            'due_date': due_date,
        })
        self.assertEqual(BorrowRequest.objects.count(), 1)
        borrow = BorrowRequest.objects.first()
        self.assertEqual(borrow.status, 'APPROVED')
        self.assertEqual(borrow.borrower, self.member)


class BorrowApproveViewTests(TestCase):
    """
    The borrow_request_create_view auto-approves on creation.
    Tests 6 & 7 validate that the detail/return flow enforces ownership:
    only the borrower (or admin) can view/act on a borrow request.
    """

    def setUp(self):
        self.admin = make_admin()
        self.owner = make_member(username='owner', email='owner@lab.test')
        self.other = make_member(username='other', email='other@lab.test')
        self.equipment = make_equipment(owner=self.owner)
        self.borrow = make_borrow(borrower=self.owner, equipment=self.equipment)

    # Test 6 – equipment owner can view borrow detail
    def test_owner_can_view_borrow_detail(self):
        self.client.force_login(self.owner)
        url = reverse('borrowing:detail', kwargs={'pk': self.borrow.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # Test 7 – non-owner/non-admin is redirected with an error message
    def test_non_owner_cannot_view_borrow_detail(self):
        self.client.force_login(self.other)
        url = reverse('borrowing:detail', kwargs={'pk': self.borrow.pk})
        response = self.client.get(url)
        # Should redirect away from the detail page
        self.assertEqual(response.status_code, 302)


class BorrowRejectViewTests(TestCase):
    """
    The project uses status='APPROVED' on auto-create. A PENDING→REJECTED
    transition would be driven by direct model manipulation (no separate
    reject view exists in urls.py). We verify the status field works correctly.
    """

    def setUp(self):
        self.member = make_member()
        self.equipment = make_equipment(owner=self.member)
        self.borrow = make_borrow(borrower=self.member, equipment=self.equipment)

    # Test 8 – status can be set to REJECTED
    def test_set_status_to_rejected(self):
        self.borrow.status = 'REJECTED'
        self.borrow.save()
        self.borrow.refresh_from_db()
        self.assertEqual(self.borrow.status, 'REJECTED')


class BorrowReturnViewTests(TestCase):

    def setUp(self):
        self.owner = make_member(username='owner', email='owner@lab.test')
        self.equipment = make_equipment(owner=self.owner)
        self.borrow = make_borrow(borrower=self.owner, equipment=self.equipment, status='APPROVED')
        self.url = reverse('borrowing:return', kwargs={'pk': self.borrow.pk})

    # Test 9 – POST sets status to RETURN_PENDING and records return_condition
    def test_post_sets_return_pending(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {
            'return_condition': 'GOOD',
            'notes': 'All fine',
        })
        self.borrow.refresh_from_db()
        self.assertEqual(self.borrow.status, 'RETURN_PENDING')
        self.assertEqual(self.borrow.return_condition, 'GOOD')
        self.assertIsNotNone(self.borrow.returned_date)


class KitBorrowReturnTests(TestCase):

    def setUp(self):
        self.borrower = make_member(username='borrower', email='borrower@lab.test')
        self.owner1 = make_member(username='kitowner1', email='kitowner1@lab.test')
        self.owner2 = make_member(username='kitowner2', email='kitowner2@lab.test')

        self.kit = make_kit(created_by=self.owner1)
        self.eq1 = make_equipment(name='EQ1', owner=self.owner1)
        self.eq2 = make_equipment(name='EQ2', owner=self.owner2)
        KitItem.objects.create(kit=self.kit, equipment=self.eq1)
        KitItem.objects.create(kit=self.kit, equipment=self.eq2)

        self.borrow = make_borrow(borrower=self.borrower, kit=self.kit, status='APPROVED')

    # Test 10 – borrow_return_view POST creates KitItemReturnApproval for each owner
    def test_return_creates_kit_item_approvals(self):
        self.client.force_login(self.borrower)
        url = reverse('borrowing:return', kwargs={'pk': self.borrow.pk})
        self.client.post(url, {
            'return_condition': 'GOOD',
            'notes': '',
        })
        self.borrow.refresh_from_db()
        self.assertEqual(self.borrow.status, 'RETURN_PENDING')
        approvals = KitItemReturnApproval.objects.filter(borrow_request=self.borrow)
        self.assertEqual(approvals.count(), 2)
        approval_equipment = set(approvals.values_list('equipment_id', flat=True))
        self.assertIn(self.eq1.pk, approval_equipment)
        self.assertIn(self.eq2.pk, approval_equipment)

    # Test 11 – confirming one item leaves borrow as RETURN_PENDING
    def test_partial_kit_confirm_stays_return_pending(self):
        self.client.force_login(self.borrower)
        url = reverse('borrowing:return', kwargs={'pk': self.borrow.pk})
        self.client.post(url, {'return_condition': 'GOOD', 'notes': ''})

        # Owner1 confirms their item only
        approval1 = KitItemReturnApproval.objects.get(borrow_request=self.borrow, equipment=self.eq1)
        self.client.force_login(self.owner1)
        confirm_url = reverse('borrowing:kit_item_confirm', kwargs={'approval_pk': approval1.pk})
        self.client.post(confirm_url)

        self.borrow.refresh_from_db()
        self.assertEqual(self.borrow.status, 'RETURN_PENDING')

    # Test 12 – confirming the last item sets borrow to RETURNED
    def test_all_kit_items_confirmed_sets_returned(self):
        self.client.force_login(self.borrower)
        url = reverse('borrowing:return', kwargs={'pk': self.borrow.pk})
        self.client.post(url, {'return_condition': 'GOOD', 'notes': ''})

        approval1 = KitItemReturnApproval.objects.get(borrow_request=self.borrow, equipment=self.eq1)
        approval2 = KitItemReturnApproval.objects.get(borrow_request=self.borrow, equipment=self.eq2)

        self.client.force_login(self.owner1)
        self.client.post(reverse('borrowing:kit_item_confirm', kwargs={'approval_pk': approval1.pk}))

        self.client.force_login(self.owner2)
        self.client.post(reverse('borrowing:kit_item_confirm', kwargs={'approval_pk': approval2.pk}))

        self.borrow.refresh_from_db()
        self.assertEqual(self.borrow.status, 'RETURNED')


# ---------------------------------------------------------------------------
# Signal tests
# ---------------------------------------------------------------------------

class BorrowSignalTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.equipment = make_equipment(owner=self.member)

    # Test 13 – creating a BorrowRequest sends notify_admins (Notification count increases)
    def test_create_borrow_notifies_admins(self):
        initial_count = Notification.objects.filter(recipient=self.admin).count()
        BorrowRequest.objects.create(
            borrower=self.member,
            equipment=self.equipment,
            purpose='Signal test',
            due_date=datetime.date.today() + datetime.timedelta(days=3),
            status='APPROVED',
        )
        new_count = Notification.objects.filter(recipient=self.admin).count()
        self.assertGreater(new_count, initial_count)

    # Test 13b – OVERDUE transition notifies the borrower
    def test_overdue_status_notifies_borrower(self):
        borrow = BorrowRequest.objects.create(
            borrower=self.member,
            equipment=self.equipment,
            purpose='Overdue signal test',
            due_date=datetime.date.today() - datetime.timedelta(days=1),
            status='APPROVED',
        )
        initial_count = Notification.objects.filter(recipient=self.member).count()

        borrow.status = 'OVERDUE'
        borrow.save()

        new_count = Notification.objects.filter(recipient=self.member).count()
        self.assertGreater(new_count, initial_count)

    # Test 14 – transitioning status to APPROVED notifies the borrower
    def test_approve_status_notifies_borrower(self):
        borrow = BorrowRequest.objects.create(
            borrower=self.member,
            equipment=self.equipment,
            purpose='Signal test',
            due_date=datetime.date.today() + datetime.timedelta(days=3),
            status='PENDING',
        )
        initial_count = Notification.objects.filter(recipient=self.member).count()

        borrow.status = 'APPROVED'
        borrow.approved_by = self.admin
        borrow.save()

        new_count = Notification.objects.filter(recipient=self.member).count()
        self.assertGreater(new_count, initial_count)
