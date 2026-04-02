from decimal import Decimal
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase

from core.models import AnexoImagem, Empresa, Endereco, Familia, FamiliaAcesso, Holding, Imovel, Investimento, ParticipacaoHolding, Pessoa, Veiculo
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

    def test_family_user_cannot_access_access_control_screen(self):
        self.client.login(username='familia-a', password='senha-forte-123')

        response = self.client.get('/acessos/')

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_family_access_through_internal_screen(self):
        self.client.login(username='admin', password='senha-forte-123')

        response = self.client.post('/acessos/novo/', {
            'username': 'familia-b',
            'first_name': 'Familia',
            'last_name': 'Barbosa',
            'email': 'barbosa@example.com',
            'familia': str(self.family_b.id),
            'password1': 'SenhaSegura#2026',
            'password2': 'SenhaSegura#2026',
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username='familia-b')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.familia_access.familia, self.family_b)

    def test_admin_can_edit_family_access_through_internal_screen(self):
        self.client.login(username='admin', password='senha-forte-123')

        response = self.client.post(f'/acessos/{self.user.id}/editar/', {
            'username': 'familia-a',
            'first_name': 'Responsavel',
            'last_name': 'Atualizado',
            'email': 'novo-email@example.com',
            'familia': str(self.family_b.id),
            'password1': '',
            'password2': '',
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Responsavel')
        self.assertEqual(self.user.last_name, 'Atualizado')
        self.assertEqual(self.user.email, 'novo-email@example.com')
        self.assertEqual(self.user.familia_access.familia, self.family_b)

    def test_dashboard_renders_geographic_map_for_georeferenced_properties(self):
        self.family_a.inventario_prazo_final = '2026-05-10'
        self.family_a.itcmd_vencimento = '2026-05-20'
        self.family_a.itcmd_uf = 'CE'
        self.family_a.save()

        endereco = Endereco.objects.create(
            cep='60000-000',
            logradouro='Av. Beira Mar',
            numero='100',
            complemento='Apto 1201',
            bairro='Meireles',
            cidade='Fortaleza',
            uf='CE',
            latitude=Decimal('-3.73186200'),
            longitude=Decimal('-38.49648300'),
        )
        imovel = Imovel.objects.create(
            content_type=ContentType.objects.get_for_model(Pessoa),
            object_id=self.person_a.id,
            descricao='Apartamento Beira Mar',
            valor_aquisicao=Decimal('850000'),
            valor_mercado_atual=Decimal('1250000'),
            natureza_bem='P',
            matricula='MAT-001',
            iptu_index='IPTU-001',
            iptu_valor_anual=Decimal('9800'),
            iptu_vencimento='2026-04-30',
            endereco=endereco,
        )
        AnexoImagem.objects.create(
            content_type=ContentType.objects.get_for_model(Imovel),
            object_id=imovel.id,
            imagem=SimpleUploadedFile(
                'fachada.gif',
                b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;',
                content_type='image/gif',
            ),
            descricao='Fachada principal',
            tipo='FOTO',
        )

        self.client.login(username='admin', password='senha-forte-123')

        response = self.client.get(f'/familia/{self.family_a.id}/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'family-geo-map')
        self.assertContains(response, 'Apartamento Beira Mar')
        self.assertContains(response, 'Fortaleza')
        self.assertContains(response, 'Obrigacoes mapeadas para a proxima fase')
        self.assertContains(response, 'Ver imagens')
        self.assertContains(response, '30/04/2026')

    def test_family_user_can_open_property_show_page(self):
        endereco = Endereco.objects.create(
            cep='70000-000',
            logradouro='Rua das Flores',
            numero='22',
            complemento='Casa',
            bairro='Centro',
            cidade='Recife',
            uf='PE',
            latitude=Decimal('-8.04756200'),
            longitude=Decimal('-34.87700200'),
        )
        imovel = Imovel.objects.create(
            content_type=ContentType.objects.get_for_model(Pessoa),
            object_id=self.person_a.id,
            descricao='Casa Recife',
            valor_aquisicao=Decimal('420000'),
            valor_mercado_atual=Decimal('650000'),
            natureza_bem='P',
            matricula='MAT-REC-1',
            iptu_index='IPTU-REC-1',
            iptu_vencimento='2026-06-15',
            endereco=endereco,
        )

        self.client.login(username='familia-a', password='senha-forte-123')

        response = self.client.get(f'/imovel/{imovel.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Casa Recife')
        self.assertContains(response, 'Show do Imovel')
        self.assertContains(response, 'Rua das Flores')

    def test_family_user_cannot_open_property_from_other_family(self):
        endereco = Endereco.objects.create(
            cep='40000-000',
            logradouro='Avenida Atlantica',
            numero='500',
            complemento='Sala 8',
            bairro='Barra',
            cidade='Salvador',
            uf='BA',
        )
        imovel = Imovel.objects.create(
            content_type=ContentType.objects.get_for_model(Pessoa),
            object_id=self.person_b.id,
            descricao='Sala Salvador',
            valor_aquisicao=Decimal('300000'),
            valor_mercado_atual=Decimal('470000'),
            natureza_bem='P',
            matricula='MAT-SSA-1',
            iptu_index='IPTU-SSA-1',
            endereco=endereco,
        )

        self.client.login(username='familia-a', password='senha-forte-123')

        response = self.client.get(f'/imovel/{imovel.id}/')

        self.assertEqual(response.status_code, 403)
