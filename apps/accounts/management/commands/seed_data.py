from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.utils import OperationalError
from django.contrib.auth import get_user_model
from apps.equipment.models import Category, Location, Equipment
from apps.equipment.utils import generate_unique_color
from apps.kits.models import Kit, KitItem
from apps.projects.models import Project, ProjectMember
from apps.consumables.models import Consumable

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with sample data for development (auto-runs migrations if needed)'

    def _ensure_migrated(self):
        """Check if the User table exists; if not, run migrate first."""
        try:
            User.objects.exists()
        except OperationalError:
            self.stdout.write(
                self.style.WARNING('Database tables missing. Running migrations first...')
            )
            call_command('migrate', interactive=False)
            self.stdout.write(self.style.SUCCESS('Migrations complete.'))

    def handle(self, *args, **options):
        self._ensure_migrated()
        self.stdout.write('Creating sample data...')

        # ── Admin user ──────────────────────────────────────────────
        admin, created = User.objects.get_or_create(
            username='tur0001',
            defaults={
                'email': 'tur0001@auburn.edu',
                'first_name': 'Dr. Tanzeel',
                'last_name': 'Rehman',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(f'  Created admin: tur0001@auburn.edu / admin123')
        else:
            self.stdout.write(f'  Using existing admin: {admin.email}')

        # ── Admin users ─────────────────────────────────────────────
        admin_data = [
            ('mzr0134@auburn.edu', 'mzr0134', 'Md Hasibur', 'Rahman'),
            ('mzr0167@auburn.edu', 'mzr0167', 'Mohtasim Hadi', 'Rafi'),
        ]
        extra_admins = []
        for email, username, first, last in admin_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email, 'first_name': first, 'last_name': last,
                    'role': 'ADMIN', 'is_staff': True,
                }
            )
            if created:
                user.set_password('admin123')
                user.save()
            else:
                user.role = 'ADMIN'
                user.is_staff = True
                user.save(update_fields=['role', 'is_staff'])
            extra_admins.append(user)
        self.stdout.write(f'  Created/updated {len(extra_admins)} extra admins (password: admin123)')

        # ── Member users ────────────────────────────────────────────
        member_data = [
            ('hhs0015@auburn.edu', 'hhs0015', 'Hamid Habib', 'Syed'),
            ('mzw0147@auburn.edu', 'mzw0147', 'Mohammad', 'Waseem'),
            ('fza0070@auburn.edu', 'fza0070', 'Faraz', 'Ahmad'),
            ('mzm0411@auburn.edu', 'mzm0411', 'Md Mesbahul', 'Maruf'),
            ('mza0291@auburn.edu', 'mza0291', 'Rohan', 'Afzal'),
        ]
        members = []
        for email, username, first, last in member_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': first, 'last_name': last, 'role': 'MEMBER'}
            )
            if created:
                user.set_password('member123')
                user.save()
            members.append(user)
        self.stdout.write(f'  Created/updated {len(members)} member users (password: member123)')

        # ── Categories ──────────────────────────────────────────────
        categories_data = [
            'Jetson',
            'Desktop Computer',
            'Laptop Computer',
            'Edge Device',
            'Router',
            'Drone',
            'Camera',
            'Storage Device',
        ]
        categories = []
        for name in categories_data:
            cat, created = Category.objects.get_or_create(name=name)
            if created:
                # save() auto-generates a unique color when blank
                cat.save()
            categories.append(cat)
        self.stdout.write(f'  Created {len(categories)} categories')

        # ── Locations ───────────────────────────────────────────────
        locations_data = [
            ('Main Lab', 'Engineering Building', 'Room 101'),
            ('Storage Room', 'Engineering Building', 'Room 105'),
            ('Electronics Bench', 'Engineering Building', 'Room 102'),
            ('Clean Room', 'Science Center', 'Room 201'),
            ('Workshop', 'Engineering Building', 'Room 110'),
        ]
        locations = []
        for name, building, room in locations_data:
            loc, _ = Location.objects.get_or_create(name=name, defaults={'building': building, 'room': room})
            locations.append(loc)
        self.stdout.write(f'  Created {len(locations)} locations')

        # ── Equipment ───────────────────────────────────────────────
        equipment_data = [
            ('Oscilloscope Tektronix MSO44', 'Digital oscilloscope with 4 channels, 200MHz bandwidth', 'SN-OSC-001', 'Tektronix', categories[0], locations[2], 'EXCELLENT'),
            ('Multimeter Fluke 87V', 'Professional industrial multimeter', 'SN-MMT-001', 'Fluke', categories[2], locations[2], 'GOOD'),
            ('Arduino Mega 2560', 'Microcontroller development board', 'SN-ARD-001', 'Arduino', categories[0], locations[0], 'GOOD'),
            ('Raspberry Pi 4 (8GB)', 'Single-board computer', 'SN-RPI-001', 'Raspberry Pi Foundation', categories[3], locations[0], 'EXCELLENT'),
            ('3D Printer - Prusa MK4', 'FDM 3D printer', 'SN-3DP-001', 'Prusa Research', categories[6], locations[4], 'GOOD'),
            ('Laser Cutter 60W', 'CO2 laser cutter/engraver', 'SN-LC-001', 'xTool', categories[6], locations[4], 'GOOD'),
            ('Signal Generator', 'Function/arbitrary waveform generator', 'SN-SIG-001', 'Rigol', categories[0], locations[2], 'GOOD'),
            ('Spectrum Analyzer', 'RF spectrum analyzer 9kHz-3GHz', 'SN-SPA-001', 'Rigol', categories[0], locations[2], 'EXCELLENT'),
            ('Soldering Station', 'Temperature-controlled soldering station', 'SN-SOL-001', 'Hakko', categories[0], locations[2], 'GOOD'),
            ('Logic Analyzer', '16-channel logic analyzer', 'SN-LA-001', 'Saleae', categories[0], locations[2], 'GOOD'),
            ('Digital Microscope', 'USB digital microscope 1000x', 'SN-MIC-001', 'AmScope', categories[1], locations[0], 'GOOD'),
            ('Power Supply (Bench)', 'Programmable DC power supply 0-30V/5A', 'SN-PSU-001', 'Rigol', categories[0], locations[2], 'GOOD'),
        ]
        equipment_list = []
        for i, item in enumerate(equipment_data):
            name, desc, serial, manufacturer, cat, loc, condition = item[0], item[1], item[2], item[3], item[4], item[5], item[6]
            eq, created = Equipment.objects.get_or_create(
                serial_number=serial,
                defaults={
                    'name': name, 'description': desc,
                    'manufacturer': manufacturer, 'category': cat,
                    'location': loc, 'condition': condition,
                    'owner': admin, 'status': 'AVAILABLE',
                }
            )
            equipment_list.append(eq)
        self.stdout.write(f'  Created {len(equipment_list)} equipment items')

        # ── Kit ─────────────────────────────────────────────────────
        kit, created = Kit.objects.get_or_create(
            name='Electronics Starter Kit',
            defaults={'description': 'Complete kit for electronics prototyping', 'created_by': admin}
        )
        if created and len(equipment_list) >= 3:
            from apps.kits.models import KitItem
            KitItem.objects.get_or_create(kit=kit, equipment=equipment_list[0], defaults={'quantity': 1})
            KitItem.objects.get_or_create(kit=kit, equipment=equipment_list[1], defaults={'quantity': 1})
            KitItem.objects.get_or_create(kit=kit, equipment=equipment_list[8], defaults={'quantity': 1})
        self.stdout.write(f'  Created kit: {kit.name}')

        # ── Project ─────────────────────────────────────────────────
        project, created = Project.objects.get_or_create(
            name='Smart Sensor Network',
            defaults={
                'description': 'IoT sensor network for environmental monitoring',
                'lead': members[0], 'status': 'ACTIVE'
            }
        )
        if created:
            ProjectMember.objects.get_or_create(project=project, user=members[0], defaults={'role': 'LEAD'})
            ProjectMember.objects.get_or_create(project=project, user=members[1], defaults={'role': 'MEMBER'})

        # ── Consumables ─────────────────────────────────────────────
        consumables_data = [
            ('Resistor Kit 1/4W', 600, 50, 'PIECE', 'Electronics', 0.01),
            ('Capacitor Kit (ceramic)', 400, 30, 'PIECE', 'Electronics', 0.02),
            ('Jumper Wires (M-M)', 100, 20, 'PIECE', 'Electronics', 0.05),
            ('Solder Wire 60/40 500g', 8, 2, 'ROLL', 'Electronics', 5.00),
            ('Isopropyl Alcohol 99%', 5, 1, 'BOTTLE', 'Chemistry', 8.00),
            ('Safety Gloves (box)', 3, 1, 'BOX', 'Safety', 12.00),
            ('Thermal Paste', 4, 1, 'PIECE', 'Electronics', 6.50),
            ('PCB Prototype Boards', 25, 5, 'PIECE', 'Electronics', 1.50),
        ]
        for name, qty, threshold, unit, cat_name, cost in consumables_data:
            cat = Category.objects.filter(name=cat_name).first() or categories[0]
            Consumable.objects.get_or_create(
                name=name,
                defaults={
                    'quantity': qty, 'low_stock_threshold': threshold,
                    'unit': unit, 'category': cat, 'unit_cost': cost,
                    'location': locations[1],
                }
            )
        self.stdout.write(f'  Created consumables')

        self.stdout.write(self.style.SUCCESS('\nSample data created successfully!'))
        self.stdout.write('\nTest accounts:')
        self.stdout.write('  Admin:    tur0001@auburn.edu / admin123')
        self.stdout.write('  Members:  hhs0015@auburn.edu, mzw0147@auburn.edu, ... / member123')
