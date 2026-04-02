import datetime
import random
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from core.models import (
    AnexoImagem,
    Ativo,
    Empresa,
    Endereco,
    Familia,
    Holding,
    Imovel,
    Investimento,
    ParticipacaoHolding,
    Pessoa,
    Veiculo,
)


DEMO_FAMILY_PREFIX = "Família Seed"

ADULT_MALE_NAMES = [
    "João",
    "Carlos",
    "Ricardo",
    "Eduardo",
    "Marcelo",
    "André",
    "Paulo",
    "Roberto",
    "Fernando",
    "Gustavo",
]

ADULT_FEMALE_NAMES = [
    "Maria",
    "Ana",
    "Patrícia",
    "Fernanda",
    "Juliana",
    "Carla",
    "Renata",
    "Aline",
    "Beatriz",
    "Camila",
]

CHILD_MALE_NAMES = [
    "Pedro",
    "Lucas",
    "Gabriel",
    "Mateus",
    "Rafael",
    "Thiago",
    "Bruno",
    "Vinícius",
    "Henrique",
    "Daniel",
]

CHILD_FEMALE_NAMES = [
    "Laura",
    "Sofia",
    "Mariana",
    "Helena",
    "Clara",
    "Isabela",
    "Luiza",
    "Valentina",
    "Bianca",
    "Manuela",
]

FAMILY_SURNAMES = [
    "Almeida",
    "Souza",
    "Oliveira",
    "Ferreira",
    "Costa",
    "Rodrigues",
    "Martins",
    "Barbosa",
    "Pereira",
    "Nascimento",
]

ADDRESS_TEMPLATES = [
    {
        "cidade": "Fortaleza",
        "uf": "CE",
        "bairro": "Aldeota",
        "logradouro": "Rua das Carnaúbas",
        "cep_prefix": "601",
        "latitude": Decimal("-3.731862"),
        "longitude": Decimal("-38.526669"),
    },
    {
        "cidade": "Recife",
        "uf": "PE",
        "bairro": "Boa Viagem",
        "logradouro": "Avenida dos Navegantes",
        "cep_prefix": "510",
        "latitude": Decimal("-8.118210"),
        "longitude": Decimal("-34.894093"),
    },
    {
        "cidade": "Salvador",
        "uf": "BA",
        "bairro": "Pituba",
        "logradouro": "Rua das Gaivotas",
        "cep_prefix": "418",
        "latitude": Decimal("-12.979434"),
        "longitude": Decimal("-38.454308"),
    },
    {
        "cidade": "São Paulo",
        "uf": "SP",
        "bairro": "Moema",
        "logradouro": "Alameda dos Bem-te-vis",
        "cep_prefix": "045",
        "latitude": Decimal("-23.600520"),
        "longitude": Decimal("-46.662113"),
    },
    {
        "cidade": "Belo Horizonte",
        "uf": "MG",
        "bairro": "Lourdes",
        "logradouro": "Rua dos Timbiras",
        "cep_prefix": "301",
        "latitude": Decimal("-19.924501"),
        "longitude": Decimal("-43.940119"),
    },
]

HOLDING_SUFFIXES = [
    "Patrimonial",
    "Participações",
    "Investimentos",
    "Administração de Bens",
]

BANKS = ["Itaú", "BTG Pactual", "XP Investimentos", "Santander", "Bradesco"]
INVESTMENT_TYPES = ["CDB", "Tesouro Selic", "FII", "Ações", "Previdência"]
VEHICLE_BRANDS = [
    ("Toyota", "Corolla"),
    ("Jeep", "Compass"),
    ("Volkswagen", "T-Cross"),
    ("Honda", "Civic"),
    ("BMW", "320i"),
]
COMPANY_SECTORS = [
    "Logística",
    "Tecnologia",
    "Agro",
    "Serviços Médicos",
    "Educação",
]


class DemoSeeder:
    def __init__(self, families=5, min_members=3, max_members=8, seed=20260331):
        self.families = families
        self.min_members = min_members
        self.max_members = max_members
        self.seed = seed
        self.random = random.Random(seed)
        self.today = datetime.date.today()
        self._cpf_counter = 0
        self._cnpj_counter = 0
        self._matricula_counter = 1000
        self._plate_counter = 0
        self._renavam_counter = 10000000000
        self._used_family_surnames = set()
        self.summary = {
            "familias": 0,
            "pessoas": 0,
            "holdings": 0,
            "participacoes": 0,
            "imoveis": 0,
            "veiculos": 0,
            "investimentos": 0,
            "empresas": 0,
            "familias_removidas": 0,
            "pessoas_removidas": 0,
            "holdings_removidas": 0,
            "ativos_removidos": 0,
        }

    @transaction.atomic
    def run(self):
        self.summary.update(self._cleanup_existing_demo_data())

        for index in range(1, self.families + 1):
            self._create_family_batch(index)

        return self.summary

    def _cleanup_existing_demo_data(self):
        families = list(Familia.objects.filter(nome__startswith=DEMO_FAMILY_PREFIX))
        if not families:
            return {
                "familias_removidas": 0,
                "pessoas_removidas": 0,
                "holdings_removidas": 0,
                "ativos_removidos": 0,
            }

        family_ids = [family.id for family in families]
        person_ids = list(Pessoa.objects.filter(familia_id__in=family_ids).values_list("id", flat=True))
        holding_ids = list(Holding.objects.filter(familia_id__in=family_ids).values_list("id", flat=True))

        ownership_filter = Q(pk__isnull=True)
        if person_ids:
            ownership_filter |= Q(content_type__model="pessoa", object_id__in=person_ids)
        if holding_ids:
            ownership_filter |= Q(content_type__model="holding", object_id__in=holding_ids)

        matching_imoveis = Imovel.objects.filter(ownership_filter)
        address_ids = list(matching_imoveis.exclude(endereco_id__isnull=True).values_list("endereco_id", flat=True))

        ativos_removidos = 0
        for model in (Imovel, Veiculo, Investimento, Empresa):
            queryset = model.objects.filter(ownership_filter)
            ativos_removidos += queryset.count()
            queryset.delete()

        orphan_assets = Ativo.objects.filter(ownership_filter)
        ativos_removidos += orphan_assets.count()
        orphan_assets.delete()

        AnexoImagem.objects.filter(object_id__in=person_ids + holding_ids).delete()

        if address_ids:
            Endereco.objects.filter(id__in=address_ids).delete()

        ParticipacaoHolding.objects.filter(holding_id__in=holding_ids).delete()

        people_count = len(person_ids)
        holdings_count = len(holding_ids)
        families_count = len(family_ids)

        Familia.objects.filter(id__in=family_ids).delete()

        return {
            "familias_removidas": families_count,
            "pessoas_removidas": people_count,
            "holdings_removidas": holdings_count,
            "ativos_removidos": ativos_removidos,
        }

    def _create_family_batch(self, index):
        surname = self._next_family_surname()
        family = Familia.objects.create(nome=f"{DEMO_FAMILY_PREFIX} {index:02d} - {surname}")
        self.summary["familias"] += 1

        member_count = self.random.randint(self.min_members, self.max_members)
        regime = self.random.choice(["CP", "CU", "SB"])

        spouse_a = Pessoa.objects.create(
            familia=family,
            nome_completo=f"{self.random.choice(ADULT_MALE_NAMES)} {surname}",
            cpf=self._generate_cpf(),
            data_nascimento=self._random_birthdate(44, 68),
            regime_bens=regime,
        )
        spouse_b = Pessoa.objects.create(
            familia=family,
            nome_completo=f"{self.random.choice(ADULT_FEMALE_NAMES)} {surname}",
            cpf=self._generate_cpf(),
            data_nascimento=self._random_birthdate(40, 64),
            regime_bens=regime,
            conjuge=spouse_a,
        )
        spouse_a.conjuge = spouse_b
        spouse_a.save(update_fields=["conjuge"])
        self.summary["pessoas"] += 2

        members = [spouse_a, spouse_b]
        for child_index in range(member_count - 2):
            first_name = self.random.choice(CHILD_FEMALE_NAMES if child_index % 2 == 0 else CHILD_MALE_NAMES)
            child = Pessoa.objects.create(
                familia=family,
                nome_completo=f"{first_name} {surname}",
                cpf=self._generate_cpf(),
                data_nascimento=self._random_birthdate(8, 30),
                pai=spouse_a,
                mae=spouse_b,
            )
            members.append(child)
            self.summary["pessoas"] += 1

        self._create_direct_assets(family, members)
        self._create_holdings(family, members)

    def _create_direct_assets(self, family, members):
        home_owner = members[0]
        second_owner = members[1]
        family_label = family.nome.replace(DEMO_FAMILY_PREFIX, "").strip(" -")

        self._create_imovel(
            owner=home_owner,
            descricao=f"Residência Principal {family_label}",
            natureza="C",
            valor_aquisicao=Decimal("650000.00"),
            valor_mercado=Decimal("980000.00"),
            address_suffix="Residencial",
        )
        self._create_imovel(
            owner=second_owner,
            descricao=f"Apartamento de Renda {family_label}",
            natureza="P",
            valor_aquisicao=Decimal("280000.00"),
            valor_mercado=Decimal("420000.00"),
            address_suffix="Business",
        )

        self._create_veiculo(
            owner=home_owner,
            descricao=f"SUV Familiar {family_label}",
            natureza="C",
            valor_aquisicao=Decimal("180000.00"),
            valor_mercado=Decimal("155000.00"),
        )
        self._create_veiculo(
            owner=second_owner,
            descricao=f"Sedan Executivo {family_label}",
            natureza="P",
            valor_aquisicao=Decimal("120000.00"),
            valor_mercado=Decimal("98000.00"),
        )

        self._create_investimento(
            owner=home_owner,
            descricao=f"Carteira Conservadora {family_label}",
            natureza="C",
            valor_aquisicao=Decimal("250000.00"),
            valor_mercado=Decimal("291000.00"),
        )
        self._create_investimento(
            owner=second_owner,
            descricao=f"Carteira de Longo Prazo {family_label}",
            natureza="P",
            valor_aquisicao=Decimal("180000.00"),
            valor_mercado=Decimal("224000.00"),
        )

        self._create_empresa(
            owner=home_owner,
            descricao=f"Participação societária {family_label}",
            natureza="P",
            valor_aquisicao=Decimal("350000.00"),
            valor_mercado=Decimal("510000.00"),
        )

    def _create_holdings(self, family, members):
        adults = [member for member in members if self._age(member.data_nascimento) >= 18]
        holding_count = 2 if len(members) >= 5 else 1

        for index in range(1, holding_count + 1):
            holding = Holding.objects.create(
                familia=family,
                razao_social=f"{family.nome} {self.random.choice(HOLDING_SUFFIXES)} {index}",
                cnpj=self._generate_cnpj(),
                tipo_societario=self.random.choice(["LTDA", "SLU"]),
                data_constituicao=self._random_past_date(6, 20),
            )
            self.summary["holdings"] += 1

            participants = adults[:]
            self.random.shuffle(participants)
            participants = participants[: min(len(participants), 3)]
            percentages = self._distribution_for(len(participants))

            for pessoa, percentual in zip(participants, percentages):
                ParticipacaoHolding.objects.create(
                    pessoa=pessoa,
                    holding=holding,
                    percentual=percentual,
                    tipo_quota="ORD",
                )
                self.summary["participacoes"] += 1

            holding_label = f"{family.nome.split('-')[-1].strip()} {index}"
            self._create_imovel(
                owner=holding,
                descricao=f"Imóvel Comercial {holding_label}",
                natureza="P",
                valor_aquisicao=Decimal("900000.00"),
                valor_mercado=Decimal("1280000.00"),
                address_suffix="Corporate",
            )
            self._create_investimento(
                owner=holding,
                descricao=f"Caixa Aplicado {holding_label}",
                natureza="C",
                valor_aquisicao=Decimal("420000.00"),
                valor_mercado=Decimal("463000.00"),
            )
            self._create_empresa(
                owner=holding,
                descricao=f"Participação operacional {holding_label}",
                natureza="P",
                valor_aquisicao=Decimal("500000.00"),
                valor_mercado=Decimal("740000.00"),
            )

    def _create_imovel(self, owner, descricao, natureza, valor_aquisicao, valor_mercado, address_suffix):
        endereco = self._build_address(address_suffix)
        Imovel.objects.create(
            proprietario=owner,
            descricao=descricao,
            valor_aquisicao=valor_aquisicao,
            valor_mercado_atual=valor_mercado,
            natureza_bem=natureza,
            matricula=self._next_matricula(),
            iptu_index=f"IPTU-{self.random.randint(100000, 999999)}",
            endereco=endereco,
            endereco_completo=str(endereco),
        )
        self.summary["imoveis"] += 1

    def _create_veiculo(self, owner, descricao, natureza, valor_aquisicao, valor_mercado):
        marca, modelo = self.random.choice(VEHICLE_BRANDS)
        ano_modelo = self.random.randint(2020, self.today.year)
        Veiculo.objects.create(
            proprietario=owner,
            descricao=descricao,
            valor_aquisicao=valor_aquisicao,
            valor_mercado_atual=valor_mercado,
            natureza_bem=natureza,
            tipo="carros",
            marca=marca,
            modelo=modelo,
            ano_fabricacao=max(ano_modelo - 1, 2018),
            ano_modelo=ano_modelo,
            placa=self._next_plate(),
            codigo_fipe=f"{self.random.randint(1000000, 9999999)}-{self.random.randint(0, 9)}",
            renavam_enc=str(self._next_renavam()),
        )
        self.summary["veiculos"] += 1

    def _create_investimento(self, owner, descricao, natureza, valor_aquisicao, valor_mercado):
        Investimento.objects.create(
            proprietario=owner,
            descricao=descricao,
            valor_aquisicao=valor_aquisicao,
            valor_mercado_atual=valor_mercado,
            natureza_bem=natureza,
            tipo=self.random.choice(INVESTMENT_TYPES),
            ticker=self.random.choice(["ITSA4", "HGLG11", "TESOURO", "BBDC4", "XPML11"]),
            custodiante=self.random.choice(BANKS),
        )
        self.summary["investimentos"] += 1

    def _create_empresa(self, owner, descricao, natureza, valor_aquisicao, valor_mercado):
        sector = self.random.choice(COMPANY_SECTORS)
        Empresa.objects.create(
            proprietario=owner,
            descricao=descricao,
            valor_aquisicao=valor_aquisicao,
            valor_mercado_atual=valor_mercado,
            natureza_bem=natureza,
            cnpj_enc=self._generate_cnpj(),
            razao_social=f"{sector} {self.random.choice(['Alpha', 'Prime', 'Nexus', 'Aurora'])} Ltda",
            percentual_participacao=Decimal(str(self.random.choice([15, 20, 25, 30, 40]))),
        )
        self.summary["empresas"] += 1

    def _build_address(self, address_suffix):
        template = self.random.choice(ADDRESS_TEMPLATES)
        cep = f"{template['cep_prefix']}{self.random.randint(10, 99):02d}-{self.random.randint(100, 999):03d}"
        latitude = template["latitude"] + Decimal(f"0.00{self.random.randint(1, 8)}")
        longitude = template["longitude"] - Decimal(f"0.00{self.random.randint(1, 8)}")
        return Endereco.objects.create(
            cep=cep,
            logradouro=f"{template['logradouro']} {address_suffix}",
            numero=str(self.random.randint(10, 999)),
            complemento=self.random.choice(["", "Sala 201", "Bloco B", "Cobertura", "Casa 02"]),
            bairro=template["bairro"],
            cidade=template["cidade"],
            uf=template["uf"],
            latitude=latitude,
            longitude=longitude,
        )

    def _next_family_surname(self):
        available = [surname for surname in FAMILY_SURNAMES if surname not in self._used_family_surnames]
        surname = self.random.choice(available)
        self._used_family_surnames.add(surname)
        return surname

    def _distribution_for(self, count):
        if count <= 1:
            return [Decimal("100.00")]
        if count == 2:
            return [Decimal("60.00"), Decimal("40.00")]
        if count == 3:
            return [Decimal("50.00"), Decimal("30.00"), Decimal("20.00")]
        return [Decimal("40.00"), Decimal("25.00"), Decimal("20.00"), Decimal("15.00")]

    def _random_birthdate(self, min_age, max_age):
        age = self.random.randint(min_age, max_age)
        year = self.today.year - age
        return datetime.date(year, self.random.randint(1, 12), self.random.randint(1, 28))

    def _random_past_date(self, min_years_ago, max_years_ago):
        years_ago = self.random.randint(min_years_ago, max_years_ago)
        year = self.today.year - years_ago
        return datetime.date(year, self.random.randint(1, 12), self.random.randint(1, 28))

    def _age(self, birthdate):
        years = self.today.year - birthdate.year
        if (self.today.month, self.today.day) < (birthdate.month, birthdate.day):
            years -= 1
        return years

    def _next_matricula(self):
        self._matricula_counter += 1
        return f"MAT-{self._matricula_counter}"

    def _next_plate(self):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        index = self._plate_counter
        self._plate_counter += 1
        first = letters[(index // (26 * 26)) % 26]
        second = letters[(index // 26) % 26]
        third = letters[index % 26]
        return f"{first}{second}{third}{self.random.randint(0, 9)}{self.random.choice(letters)}{self.random.randint(0, 9)}{self.random.randint(0, 9)}"

    def _next_renavam(self):
        self._renavam_counter += 1
        return self._renavam_counter

    def _generate_cpf(self):
        self._cpf_counter += 1
        base_number = f"{self.seed % 1000:03d}{self._cpf_counter:06d}"[:9]
        if len(set(base_number)) == 1:
            base_number = "123456789"
        digits = [int(char) for char in base_number]
        total_1 = sum(number * multiplier for number, multiplier in zip(digits, range(10, 1, -1)))
        remainder_1 = total_1 % 11
        digit_1 = 0 if remainder_1 < 2 else 11 - remainder_1
        total_2 = sum(number * multiplier for number, multiplier in zip(digits + [digit_1], range(11, 1, -1)))
        remainder_2 = total_2 % 11
        digit_2 = 0 if remainder_2 < 2 else 11 - remainder_2
        cpf = f"{base_number}{digit_1}{digit_2}"
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def _generate_cnpj(self):
        self._cnpj_counter += 1
        base_number = f"{self.seed % 10000:04d}{self._cnpj_counter:08d}"[:12]
        if len(set(base_number)) == 1:
            base_number = "123456780001"
        digits = [int(char) for char in base_number]
        multipliers_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total_1 = sum(number * multiplier for number, multiplier in zip(digits, multipliers_1))
        remainder_1 = total_1 % 11
        digit_1 = 0 if remainder_1 < 2 else 11 - remainder_1
        multipliers_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total_2 = sum(number * multiplier for number, multiplier in zip(digits + [digit_1], multipliers_2))
        remainder_2 = total_2 % 11
        digit_2 = 0 if remainder_2 < 2 else 11 - remainder_2
        cnpj = f"{base_number}{digit_1}{digit_2}"
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
