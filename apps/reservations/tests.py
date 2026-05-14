"""Unit tests for the reservations app."""

import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.equipment.models import Category, Equipment, Location
from apps.kits.models import Kit
from apps.notifications.models import Notification
from apps.reservations.models import Reservation, WaitlistEntry


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


def make_equipment(name='Microscope', owner=None, status='AVAILABLE'):
    cat, _ = Category.objects.get_or_create(name='Optics')
    loc, _ = Location.objects.get_or_create(name='Lab B')
    return Equipment.objects.create(
        name=name,
        category=cat,
        location=loc,
        owner=owner,
        status=status,
        is_active=True,
    )


def make_kit(name='Research Kit', created_by=None):
    return Kit.objects.create(name=name, is_active=True, created_by=created_by)


def make_reservation(requester, equipment=None, kit=None, status='CONFIRMED', days_ahead=3, duration=5):
    today = datetime.date.today()
    return Reservation.objects.create(
        requester=requester,
        equipment=equipment,
        kit=kit,
        status=status,
        start_date=today + datetime.timedelta(days=days_ahead),
        end_date=today + datetime.timedelta(days=days_ahead + duration),
        purpose='Test reservation',
    )


# ---------------------------------------------------------------------------
# reservation_create_view
# ---------------------------------------------------------------------------

class ReservationCreateViewTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.equipment = make_equipment(owner=self.admin)
        self.url = reverse('reservations:create')
        self.today = datetime.date.today()

    def _post_data(self, **overrides):
        data = {
            'equipment': self.equipment.pk,
            'kit': '',
            'start_date': (self.today + datetime.timedelta(days=2)).isoformat(),
            'end_date': (self.today + datetime.timedelta(days=7)).isoformat(),
            'purpose': 'Experiment',
        }
        data.update(overrides)
        return data

    # Test 1 – POST creates reservation with status=PENDING (requires owner confirmation)
    def test_post_creates_pending_reservation(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url, self._post_data())
        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.status, 'PENDING')
        self.assertEqual(reservation.requester, self.member)

    # Test 2 – anonymous GET redirects to login
    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


# ---------------------------------------------------------------------------
# reservation_detail_view
# ---------------------------------------------------------------------------

class ReservationDetailViewTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.other = make_member(username='other', email='other@lab.test')
        self.equipment = make_equipment(owner=self.admin)
        self.reservation = make_reservation(requester=self.member, equipment=self.equipment)
        self.url = reverse('reservations:detail', kwargs={'pk': self.reservation.pk})

    # Test 3 – requester can access their own reservation detail
    def test_requester_can_view_detail(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    # Test 4 – different member is redirected with an error
    def test_other_member_cannot_view_detail(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('reservations:list'))

    # Test 5 – admin can access any reservation detail
    def test_admin_can_view_detail(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# reservation_cancel_view
# ---------------------------------------------------------------------------

class ReservationCancelViewTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.equipment = make_equipment(owner=self.admin)
        self.reservation = make_reservation(requester=self.member, equipment=self.equipment)
        self.url = reverse('reservations:cancel', kwargs={'pk': self.reservation.pk})

    # Test 6 – POST cancels a CONFIRMED reservation
    def test_post_cancels_confirmed_reservation(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'CANCELLED')

    # Test 7 – POST notifies next person on waitlist when one exists
    def test_cancel_notifies_next_waitlist_member(self):
        waitlist_user = make_member(username='waiter', email='waiter@lab.test')
        WaitlistEntry.objects.create(
            user=waitlist_user,
            equipment=self.equipment,
            position=1,
            notified=False,
        )
        self.client.force_login(self.member)
        self.client.post(self.url)

        notified = Notification.objects.filter(recipient=waitlist_user)
        self.assertTrue(notified.exists())

        entry = WaitlistEntry.objects.get(user=waitlist_user)
        self.assertTrue(entry.notified)


# ---------------------------------------------------------------------------
# reservation_return_view
# ---------------------------------------------------------------------------

class ReservationReturnViewTests(TestCase):

    def setUp(self):
        self.owner = make_member(username='owner', email='owner@lab.test')
        self.member = make_member()
        self.equipment = make_equipment(owner=self.owner)
        self.reservation = make_reservation(requester=self.member, equipment=self.equipment, status='CONFIRMED')
        self.url = reverse('reservations:return', kwargs={'pk': self.reservation.pk})

    # Test 8 – POST sets status=RETURN_PENDING and records returned_date
    def test_post_sets_return_pending(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url, {
            'return_condition': 'GOOD',
            'notes': 'Works fine',
        })
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'RETURN_PENDING')
        self.assertIsNotNone(self.reservation.returned_date)
        self.assertEqual(self.reservation.return_condition, 'GOOD')

    # Test 9 – rejects return if status is not CONFIRMED
    def test_return_rejected_when_not_confirmed(self):
        self.reservation.status = 'CANCELLED'
        self.reservation.save()
        self.client.force_login(self.member)
        response = self.client.post(self.url, {
            'return_condition': 'GOOD',
            'notes': '',
        })
        self.reservation.refresh_from_db()
        # Status must remain CANCELLED; the view redirects without processing
        self.assertEqual(self.reservation.status, 'CANCELLED')


# ---------------------------------------------------------------------------
# reservation_return_confirm_view
# ---------------------------------------------------------------------------

class ReservationReturnConfirmViewTests(TestCase):

    def setUp(self):
        self.owner = make_member(username='owner', email='owner@lab.test')
        self.member = make_member()
        self.other = make_member(username='other', email='other@lab.test')
        self.equipment = make_equipment(owner=self.owner)
        self.reservation = make_reservation(
            requester=self.member,
            equipment=self.equipment,
            status='RETURN_PENDING',
        )
        self.url = reverse('reservations:return_confirm', kwargs={'pk': self.reservation.pk})

    # Test 10 – equipment owner POST sets status=RETURNED
    def test_owner_post_sets_returned(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'RETURNED')

    # Test 11 – non-owner is redirected (cannot confirm return)
    def test_non_owner_cannot_confirm_return(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.reservation.refresh_from_db()
        # Status must remain RETURN_PENDING
        self.assertEqual(self.reservation.status, 'RETURN_PENDING')
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# waitlist_create_view / waitlist_leave_view
# ---------------------------------------------------------------------------

class WaitlistViewTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.equipment = make_equipment(owner=self.admin)
        self.create_url = reverse('reservations:waitlist_create')
        self.today = datetime.date.today()

    def _post_data(self):
        return {
            'equipment': self.equipment.pk,
            'kit': '',
            'notes': '',
        }

    # Test 12 – duplicate waitlist entry for same user+equipment is prevented
    def test_duplicate_waitlist_entry_prevented(self):
        # Create an initial entry
        WaitlistEntry.objects.create(
            user=self.member,
            equipment=self.equipment,
            position=1,
        )
        self.client.force_login(self.member)
        response = self.client.post(self.create_url, self._post_data())
        # Still only one entry
        self.assertEqual(
            WaitlistEntry.objects.filter(user=self.member, equipment=self.equipment).count(),
            1,
        )
        # Should redirect (view sends warning and redirects on duplicate)
        self.assertEqual(response.status_code, 302)

    # Test 13 – waitlist_leave_view deletes the entry
    def test_leave_waitlist_deletes_entry(self):
        entry = WaitlistEntry.objects.create(
            user=self.member,
            equipment=self.equipment,
            position=1,
        )
        self.client.force_login(self.member)
        leave_url = reverse('reservations:waitlist_leave', kwargs={'pk': entry.pk})
        response = self.client.post(leave_url)
        self.assertFalse(WaitlistEntry.objects.filter(pk=entry.pk).exists())
        self.assertEqual(response.status_code, 302)
