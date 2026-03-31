from django.core.management.base import BaseCommand
from core.models import Pessoa, Imovel, Veiculo, Investimento, Empresa, Familia
from decimal import Decimal
import datetime

class Command(BaseCommand):
    help = 'Cria dados de exemplo para teste'

    def handle(self, *args, **kwargs):
        self.stdout.write('Criando dados de exemplo...')
        
        # 0. Create Family
        familia_silva = Familia.objects.create(nome="Família Silva")
        
        # 1. Create People
        joao = Pessoa.objects.create(
            familia=familia_silva,
            nome_completo="João Silva",
            cpf="123.456.789-00", # Will be encrypted
            data_nascimento=datetime.date(1960, 5, 15),
            regime_bens="CP" # Comunhão Parcial
        )
        
        maria = Pessoa.objects.create(
            familia=familia_silva,
            nome_completo="Maria Silva",
            cpf="987.654.321-00",
            data_nascimento=datetime.date(1965, 8, 20),
            conjuge=joao
        )
        # Update Joao's spouse
        joao.conjuge = maria
        joao.save()
        
        filho1 = Pessoa.objects.create(
            familia=familia_silva,
            nome_completo="Pedro Silva",
            cpf="111.222.333-44",
            data_nascimento=datetime.date(1990, 1, 10),
            pai=joao,
            mae=maria
        )
        
        filho2 = Pessoa.objects.create(
            familia=familia_silva,
            nome_completo="Ana Silva",
            cpf="555.666.777-88",
            data_nascimento=datetime.date(1995, 3, 25),
            pai=joao,
            mae=maria
        )
        
        # 2. Create Assets
        # Bem Comum - Casa
        Imovel.objects.create(
            proprietario=joao,
            descricao="Casa na Praia",
            valor_aquisicao=Decimal("500000.00"),
            valor_mercado_atual=Decimal("1200000.00"),
            natureza_bem='C', # Comum
            matricula="12345",
            endereco_completo="Rua da Praia, 100"
        )
        
        # Bem Particular (João) - Herança anterior
        Imovel.objects.create(
            proprietario=joao,
            descricao="Apartamento Antigo",
            valor_aquisicao=Decimal("200000.00"),
            valor_mercado_atual=Decimal("450000.00"),
            natureza_bem='P', # Particular
            matricula="67890",
            endereco_completo="Rua Centro, 50"
        )
        
        # Bem Comum - Carro
        Veiculo.objects.create(
            proprietario=joao, # Could be Maria too, but technically listed under one, nature determines split
            descricao="SUV de Luxo",
            valor_aquisicao=Decimal("150000.00"),
            valor_mercado_atual=Decimal("120000.00"),
            natureza_bem='C',
            renavam_enc="999999999",
            placa="ABC-1234",
            modelo_ano="2022"
        )
        
        # Investimento (Comum)
        Investimento.objects.create(
            proprietario=joao,
            descricao="CDB Banco X",
            valor_aquisicao=Decimal("50000.00"),
            valor_mercado_atual=Decimal("65000.00"),
            natureza_bem='C',
            tipo="CDB",
            custodiante="Banco X"
        )
        
        self.stdout.write(self.style.SUCCESS(f'Dados criados! ID do João: {joao.id}'))
