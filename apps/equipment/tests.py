"""Unit tests for the equipment app."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser, UserProfile
from apps.equipment.models import Category, Equipment, Location


def _minimal_gif():
    """Return a minimal valid 1×1 GIF as a SimpleUploadedFile."""
    gif_bytes = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00'
        b'!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01'
        b'\x00\x00\x02\x02D\x01\x00;'
    )
    return SimpleUploadedFile('test.gif', gif_bytes, content_type='image/gif')


class EquipmentModelTest(TestCase):
    """Tests for the Equipment model."""

    def setUp(self):
        self.equipment = Equipment.objects.create(
            name='Oscilloscope X200',
            is_active=True,
        )

    def test_equipment_str_returns_name(self):
        """Equipment.__str__ should return the equipment name."""
        self.assertEqual(str(self.equipment), 'Oscilloscope X200')


class CategoryModelTest(TestCase):
    """Tests for the Category model."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Measurement Instruments',
            description='Tools used for measurement.',
        )

    def test_category_str_returns_name(self):
        """Category.__str__ should return the category name."""
        self.assertEqual(str(self.category), 'Measurement Instruments')


class LocationModelTest(TestCase):
    """Tests for the Location model."""

    def setUp(self):
        self.location_plain = Location.objects.create(name='Storage Room A')
        self.location_with_detail = Location.objects.create(
            name='Cabinet B',
            building='Engineering Block',
            room='Room 201',
        )

    def test_location_str_returns_name_when_no_building_or_room(self):
        """Location.__str__ returns just the name when building/room are blank."""
        self.assertEqual(str(self.location_plain), 'Storage Room A')

    def test_location_str_includes_building_and_room(self):
        """Location.__str__ appends building and room when provided."""
        result = str(self.location_with_detail)
        self.assertIn('Cabinet B', result)
        self.assertIn('Engineering Block', result)
        self.assertIn('Room 201', result)


class EquipmentListViewTest(TestCase):
    """Tests for equipment_list_view."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='member@lab.test',
            username='member',
            password='testpass123',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.client.force_login(self.user)
        self.url = reverse('equipment:list')

    def test_accessible_to_logged_in_member(self):
        """Any logged-in member should get a 200 from the equipment list view."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_redirects_anonymous_user(self):
        """An anonymous user should be redirected to the login page."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)


class EquipmentCreateViewTest(TestCase):
    """Tests for equipment_create_view."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='member@lab.test',
            username='member',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.location = Location.objects.create(name='Test Location')
        self.client.force_login(self.user)
        self.url = reverse('equipment:create')

    def test_any_member_can_reach_create_form(self):
        """Any logged-in member should get a 200 on the equipment create page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_creates_equipment_with_owner_as_request_user(self):
        """A valid POST with owner=self sets approval_status=APPROVED immediately."""
        response = self.client.post(self.url, {
            'name': 'New Multimeter',
            'description': 'A digital multimeter.',
            'status': 'AVAILABLE',
            'condition': 'GOOD',
            'owner': self.user.pk,
            'category': self.category.pk,
            'location': self.location.pk,
            'image': _minimal_gif(),
        })
        self.assertEqual(Equipment.objects.count(), 1)
        equipment = Equipment.objects.first()
        self.assertEqual(equipment.owner, self.user)
        self.assertEqual(equipment.name, 'New Multimeter')
        self.assertRedirects(response, reverse('equipment:detail', kwargs={'pk': equipment.pk}))


class EquipmentDetailViewTest(TestCase):
    """Tests for equipment_detail_view."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='member@lab.test',
            username='member',
            password='testpass123',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.equipment = Equipment.objects.create(
            name='Spectrum Analyser',
            is_active=True,
        )
        self.client.force_login(self.user)
        self.url = reverse('equipment:detail', kwargs={'pk': self.equipment.pk})

    def test_accessible_to_any_logged_in_member(self):
        """Any logged-in member should be able to view the equipment detail page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['equipment'], self.equipment)


class EquipmentEditViewTest(TestCase):
    """Tests for equipment_edit_view."""

    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            email='owner@lab.test',
            username='owner',
            password='testpass123',
            first_name='Owner',
            last_name='User',
        )
        UserProfile.objects.get_or_create(user=self.owner)

        self.non_owner = CustomUser.objects.create_user(
            email='nonowner@lab.test',
            username='nonowner',
            password='testpass123',
        )
        UserProfile.objects.get_or_create(user=self.non_owner)

        self.category = Category.objects.create(name='Edit Test Category')
        self.location = Location.objects.create(name='Edit Test Location')

        self.equipment = Equipment.objects.create(
            name='Power Supply Unit',
            owner=self.owner,
            category=self.category,
            location=self.location,
            is_active=True,
            status='AVAILABLE',
            condition='GOOD',
        )
        self.url = reverse('equipment:edit', kwargs={'pk': self.equipment.pk})

    def test_owner_can_edit_equipment(self):
        """The equipment owner should be able to successfully POST an update."""
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {
            'name': 'Power Supply Unit Updated',
            'description': 'Updated description.',
            'status': 'AVAILABLE',
            'condition': 'EXCELLENT',
            'owner': self.owner.pk,
            'category': self.category.pk,
            'location': self.location.pk,
            'image': _minimal_gif(),
        })
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.name, 'Power Supply Unit Updated')
        self.assertRedirects(response, reverse('equipment:detail', kwargs={'pk': self.equipment.pk}))

    def test_non_owner_cannot_edit_equipment(self):
        """A non-owner should be redirected with an error and changes must not be saved."""
        self.client.force_login(self.non_owner)
        response = self.client.post(self.url, {
            'name': 'Hijacked Name',
            'description': '',
            'status': 'AVAILABLE',
            'condition': 'GOOD',
            'owner': self.non_owner.pk,
            'category': self.category.pk,
            'location': self.location.pk,
        })
        self.assertRedirects(response, reverse('equipment:detail', kwargs={'pk': self.equipment.pk}))
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.name, 'Power Supply Unit')
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('permission' in str(m).lower() for m in messages))
