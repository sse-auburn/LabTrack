"""Unit tests for the consumables app."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser, UserProfile
from apps.consumables.models import Consumable


class ConsumableModelTest(TestCase):
    """Tests for the Consumable model."""

    def setUp(self):
        self.consumable = Consumable.objects.create(
            name='Isopropyl Alcohol',
            quantity=Decimal('50.00'),
            unit='BOTTLE',
            low_stock_threshold=Decimal('10.00'),
            is_active=True,
        )

    def test_consumable_str_returns_name(self):
        """Consumable.__str__ should include the consumable name."""
        result = str(self.consumable)
        self.assertIn('Isopropyl Alcohol', result)

    def test_is_low_stock_true_when_quantity_at_threshold(self):
        """is_low_stock should return True when quantity equals the threshold."""
        self.consumable.quantity = Decimal('10.00')  # exactly at threshold
        self.consumable.save()
        self.assertTrue(self.consumable.is_low_stock)

    def test_is_low_stock_true_when_quantity_below_threshold(self):
        """is_low_stock should return True when quantity is below the threshold."""
        self.consumable.quantity = Decimal('5.00')
        self.consumable.save()
        self.assertTrue(self.consumable.is_low_stock)

    def test_is_low_stock_false_when_quantity_above_threshold(self):
        """is_low_stock should return False when quantity is above the threshold."""
        self.consumable.quantity = Decimal('50.00')
        self.consumable.save()
        self.assertFalse(self.consumable.is_low_stock)


class ConsumableListViewTest(TestCase):
    """Tests for consumable_list_view."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='member@lab.test',
            username='member',
            password='testpass123',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.client.force_login(self.user)
        self.url = reverse('consumables:list')

    def test_accessible_to_any_logged_in_member(self):
        """Any logged-in member should receive a 200 from the consumable list view."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_redirects_anonymous_user(self):
        """An anonymous user should not get a 200."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)


class ConsumableCreateViewTest(TestCase):
    """Tests for consumable_create_view (admin-only)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='admin@lab.test',
            username='admin',
            password='testpass123',
            role='ADMIN',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.client.force_login(self.user)
        self.url = reverse('consumables:create')

    def test_admin_can_create_consumable(self):
        """An admin should be able to POST and create a consumable."""
        response = self.client.post(self.url, {
            'name': 'Latex Gloves',
            'description': 'Disposable latex gloves, size M.',
            'quantity': '100.00',
            'unit': 'BOX',
            'low_stock_threshold': '10.00',
        })
        self.assertEqual(Consumable.objects.count(), 1)
        consumable = Consumable.objects.first()
        self.assertEqual(consumable.name, 'Latex Gloves')
        self.assertRedirects(response, reverse('consumables:detail', kwargs={'pk': consumable.pk}))


class ConsumableUseViewTest(TestCase):
    """Tests for log_usage_view (consumable use)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='member@lab.test',
            username='member',
            password='testpass123',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.consumable = Consumable.objects.create(
            name='Ethanol',
            quantity=Decimal('100.00'),
            unit='LITER',
            low_stock_threshold=Decimal('10.00'),
            is_active=True,
        )
        self.client.force_login(self.user)
        self.url = reverse('consumables:log_usage', kwargs={'pk': self.consumable.pk})

    def test_post_deducts_quantity_from_stock(self):
        """A valid usage POST should deduct the quantity_used from the consumable's stock."""
        self.client.post(self.url, {
            'quantity_used': '25.00',
            'purpose': 'Experiment cleanup',
        })
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('75.00'))

    def test_post_rejects_usage_exceeding_available_stock(self):
        """A POST requesting more than available stock should fail form validation."""
        response = self.client.post(self.url, {
            'quantity_used': '999.00',  # far more than the 100 in stock
            'purpose': 'Over-use attempt',
        })
        # The view should re-render the form (200), not redirect
        self.assertEqual(response.status_code, 200)
        # Stock must remain unchanged
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('100.00'))


class ConsumableRestockViewTest(TestCase):
    """Tests for restock_view (admin-only)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='admin@lab.test',
            username='admin',
            password='testpass123',
            role='ADMIN',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.consumable = Consumable.objects.create(
            name='Nitrogen Gas',
            quantity=Decimal('20.00'),
            unit='BOTTLE',
            low_stock_threshold=Decimal('5.00'),
            is_active=True,
        )
        self.client.force_login(self.user)
        self.url = reverse('consumables:restock', kwargs={'pk': self.consumable.pk})

    def test_post_adds_quantity_to_stock(self):
        """A valid restock POST should increase the consumable's quantity by quantity_to_add."""
        self.client.post(self.url, {
            'quantity_to_add': '30.00',
            'notes': 'New delivery arrived.',
        })
        self.consumable.refresh_from_db()
        self.assertEqual(self.consumable.quantity, Decimal('50.00'))


class LowStockListViewTest(TestCase):
    """Tests for low_stock_list_view (admin-only)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='admin@lab.test',
            username='admin',
            password='testpass123',
            role='ADMIN',
        )
        UserProfile.objects.get_or_create(user=self.user)

        # Low-stock consumable (quantity <= threshold)
        self.low = Consumable.objects.create(
            name='Low Stock Item',
            quantity=Decimal('3.00'),
            unit='PIECE',
            low_stock_threshold=Decimal('10.00'),
            is_active=True,
        )

        # Well-stocked consumable (quantity > threshold)
        self.ample = Consumable.objects.create(
            name='Ample Stock Item',
            quantity=Decimal('100.00'),
            unit='PIECE',
            low_stock_threshold=Decimal('10.00'),
            is_active=True,
        )

        self.client.force_login(self.user)
        self.url = reverse('consumables:low_stock')

    def test_low_stock_list_shows_only_low_stock_consumables(self):
        """The low_stock_list_view should include only consumables at or below their threshold."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        consumables_in_context = list(response.context['consumables'])
        self.assertIn(self.low, consumables_in_context)
        self.assertNotIn(self.ample, consumables_in_context)
