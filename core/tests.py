from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase

from core.models import Empresa, Familia, FamiliaAcesso, Holding, Imovel, Investimento, ParticipacaoHolding, Pessoa, Veiculo
from core.seeders.demo_data import DEMO_FAMILY_PREFIX


User = get_user_model()


class SeedDataCommandTests(TestCase):
    def test_seed_command_creates_expected_demo_dataset(self):
        call_command(
            "seed_data",
            families=5,
            min_members=3,
            max_members=3,
            seed=123,
            stdout=StringIO(),
        )

        families = Familia.objects.filter(nome__startswith=DEMO_FAMILY_PREFIX).order_by("nome")
        self.assertEqual(families.count(), 5)
        self.assertEqual(Pessoa.objects.filter(familia__in=families).count(), 15)
        self.assertTrue(all(family.membros.count() == 3 for family in families))
        self.assertGreaterEqual(Holding.objects.filter(familia__in=families).count(), 5)
        self.assertTrue(Imovel.objects.exists())
        self.assertTrue(Veiculo.objects.exists())
        self.assertTrue(Investimento.objects.exists())
        self.assertTrue(Empresa.objects.exists())

        for holding in Holding.objects.filter(familia__in=families):
            total = ParticipacaoHolding.objects.filter(holding=holding).aggregate(total=Sum("percentual"))["total"]
            self.assertEqual(total, Decimal("100"))

    def test_seed_command_replaces_previous_demo_data_without_duplication(self):
        call_command(
            "seed_data",
            families=5,
            min_members=4,
            max_members=4,
            seed=1,
            stdout=StringIO(),
        )
        call_command(
            "seed_data",
            families=5,
            min_members=4,
            max_members=4,
            seed=2,
            stdout=StringIO(),
        )

        families = Familia.objects.filter(nome__startswith=DEMO_FAMILY_PREFIX)
        self.assertEqual(families.count(), 5)
        self.assertEqual(Pessoa.objects.filter(familia__in=families).count(), 20)


class AccessControlTests(TestCase):
    def setUp(self):
        self.family_a = Familia.objects.create(nome='Familia A')
        self.family_b = Familia.objects.create(nome='Familia B')

        self.person_a = Pessoa.objects.create(
            familia=self.family_a,
            nome_completo='Pessoa A',
            cpf='123.456.789-09',
            data_nascimento='1985-01-01',
        )
        self.person_b = Pessoa.objects.create(
            familia=self.family_b,
            nome_completo='Pessoa B',
            cpf='987.654.321-00',
            data_nascimento='1986-01-01',
        )

        self.user = User.objects.create_user(username='familia-a', password='senha-forte-123')
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='senha-forte-123')
        FamiliaAcesso.objects.create(user=self.user, familia=self.family_a)

    def test_home_requires_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_family_user_sees_only_assigned_family_on_home(self):
        self.client.login(username='familia-a', password='senha-forte-123')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Familia A')
        self.assertNotContains(response, 'Familia B')

    def test_family_user_cannot_open_other_family(self):
        self.client.login(username='familia-a', password='senha-forte-123')

        response = self.client.get(f'/familia/{self.family_b.id}/')

        self.assertEqual(response.status_code, 403)

    def test_family_user_cannot_access_management_routes(self):
        self.client.login(username='familia-a', password='senha-forte-123')

        response = self.client.get('/familia/nova/')

        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_management_routes(self):
        self.client.login(username='admin', password='senha-forte-123')

        response = self.client.get('/familia/nova/')

        self.assertEqual(response.status_code, 200)
