from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid
from infrastructure.db.fields import EncryptedDataField
from .validators import validate_cpf, validate_cnpj

# --- Mixin para Auditoria ---
class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True

# --- Endereços Estruturados ---
class Endereco(models.Model):
    """Endereço estruturado para imóveis com integração ViaCEP e geocoding"""
    UF_CHOICES = [
        ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
        ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
        ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'),
        ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
        ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
        ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
        ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cep = models.CharField(max_length=9, verbose_name='CEP', help_text='Formato: 00000-000')
    logradouro = models.CharField(max_length=255, verbose_name='Logradouro')
    numero = models.CharField(max_length=10, verbose_name='Número')
    complemento = models.CharField(max_length=100, blank=True, verbose_name='Complemento')
    bairro = models.CharField(max_length=100, verbose_name='Bairro')
    cidade = models.CharField(max_length=100, verbose_name='Cidade')
    uf = models.CharField(max_length=2, choices=UF_CHOICES, verbose_name='UF')
    
    # Geocoding (para futura plotagem em mapas)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
    
    def __str__(self):
        return f"{self.logradouro}, {self.numero} - {self.bairro}, {self.cidade}/{self.uf}"

# --- Anexos e Documentos ---
class AnexoImagem(AuditModel):
    """Imagens e documentos anexados a qualquer entidade (Pessoa, Imovel, Veiculo, etc.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # GenericForeignKey para anexar a qualquer modelo
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    entidade = GenericForeignKey('content_type', 'object_id')
    
    # Dados do anexo
    imagem = models.ImageField(upload_to='anexos/%Y/%m/', verbose_name='Imagem')
    descricao = models.CharField(max_length=255, verbose_name='Descrição')
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('FOTO', 'Fotografia'),
            ('DOC', 'Documento'),
            ('ESCRIT', 'Escritura'),
            ('RG', 'RG/CPF'),
            ('MATRICULA', 'Matrícula'),
            ('IPTU', 'IPTU'),
            ('RENAVAM', 'Renavam'),
            ('OUTRO', 'Outro'),
        ],
        default='FOTO'
    )
    
    class Meta:
        verbose_name = 'Anexo/Imagem'
        verbose_name_plural = 'Anexos/Imagens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.descricao} ({self.get_tipo_display()})"

# --- Gestão de Pessoas ---
class Familia(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255, verbose_name="Nome da Família/Caso")
    
    def __str__(self):
        return self.nome

class FamiliaAcesso(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='familia_access')
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='acessos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Acesso de FamÃ­lia'
        verbose_name_plural = 'Acessos de FamÃ­lia'

    def __str__(self):
        return f"{self.user} -> {self.familia}"


class Pessoa(AuditModel):
    REGIMES_BENS = [
        ('CP', 'Comunhão Parcial'),
        ('CU', 'Comunhão Universal'),
        ('SB', 'Separação de Bens'),
        ('PF', 'Participação Final nos Questos'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='membros', null=True, blank=True)
    nome_completo = models.CharField(max_length=255)
    # Campo sensível que será tratado pelo Service Layer ou Custom Field
    cpf = EncryptedDataField(verbose_name="CPF", validators=[validate_cpf]) 
    data_nascimento = models.DateField()
    regime_bens = models.CharField(max_length=2, choices=REGIMES_BENS, null=True, blank=True)
    foto = models.ImageField(upload_to='membros/', null=True, blank=True, verbose_name='Foto do Perfil')
    
    # Auto-relacionamento para Árvore Genealógica
    pai = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='filhos_pai', blank=True)
    mae = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='filhos_mae', blank=True)
    conjuge = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nome_completo

# --- Holdings Patrimoniais ---
class Holding(AuditModel):
    """Entidade jurídica para proteção patrimonial e planejamento sucessório"""
    TIPOS_SOCIETARIOS = [
        ('LTDA', 'Sociedade Limitada'),
        ('SA', 'Sociedade Anônima'),
        ('EIRELI', 'Empresa Individual de Responsabilidade Limitada'),
        ('SLU', 'Sociedade Limitada Unipessoal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, related_name='holdings')
    razao_social = models.CharField(max_length=255, verbose_name='Razão Social')
    cnpj = EncryptedDataField(verbose_name='CNPJ', validators=[validate_cnpj])
    tipo_societario = models.CharField(max_length=10, choices=TIPOS_SOCIETARIOS, default='LTDA')
    data_constituicao = models.DateField(verbose_name='Data de Constituição')
    
    class Meta:
        verbose_name = 'Holding'
        verbose_name_plural = 'Holdings'
    
    def __str__(self):
        return self.razao_social

class ParticipacaoHolding(AuditModel):
    """Registro de participação societária de uma pessoa em uma holding"""
    TIPOS_QUOTA = [
        ('ORD', 'Ordinária'),
        ('PREF', 'Preferencial'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='participacoes')
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE, related_name='socios')
    percentual = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)],
        help_text='Percentual de participação (ex: 50.00 para 50%)'
    )
    tipo_quota = models.CharField(max_length=4, choices=TIPOS_QUOTA, default='ORD')
    
    class Meta:
        verbose_name = 'Participação em Holding'
        verbose_name_plural = 'Participações em Holdings'
        unique_together = ['pessoa', 'holding']  # Pessoa não pode ter duplicidade na mesma holding
    
    def __str__(self):
        return f"{self.pessoa.nome_completo} - {self.percentual}% em {self.holding.razao_social}"


# --- Base Polimórfica de Ativos ---
class Ativo(AuditModel):
    TITULARIDADE_CHOICES = [('P', 'Particular'), ('C', 'Comum')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Generic Foreign Key para suportar Pessoa OU Holding como proprietário
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    proprietario = GenericForeignKey('content_type', 'object_id')
    
    descricao = models.CharField(max_length=255)
    valor_aquisicao = models.DecimalField(max_digits=15, decimal_places=2)
    valor_mercado_atual = models.DecimalField(max_digits=15, decimal_places=2)
    moeda_origem = models.CharField(max_length=3, default='BRL')
    natureza_bem = models.CharField(
        max_length=1, 
        choices=TITULARIDADE_CHOICES,
        help_text='COMUM: Adquirido durante o casamento (sofre meação). PARTICULAR: Anterior ao casamento, herança ou doação (não sofre meação).'
    )
    
    class Meta:
        verbose_name = "Ativo"
    
    def __str__(self):
        return self.descricao

# --- Especializações ---
# Note: For true polymorphism we might want django-polymorphic, but standard inheritance (OneToOne implicit) works too for basic cases.
# Assuming Multi-table inheritance here as per user class structure.

class Imovel(Ativo):
    matricula = models.CharField(max_length=100)
    iptu_index = models.CharField(max_length=100)
    
    # Endereço estruturado (novo)
    endereco = models.ForeignKey(Endereco, on_delete=models.CASCADE, null=True, blank=True, related_name='imoveis')
    
    # Mantido temporariamente para migração
    endereco_completo = models.TextField(blank=True, verbose_name='Endereço (legado)')


class Veiculo(Ativo):
    tipo = models.CharField(max_length=50, verbose_name='Tipo (Carro/Moto)', default='Carros')
    marca = models.CharField(max_length=100, verbose_name='Marca', blank=True)
    modelo = models.CharField(max_length=100, verbose_name='Modelo', blank=True)
    ano_fabricacao = models.IntegerField(verbose_name='Ano Fabricação', default=2024)
    ano_modelo = models.IntegerField(verbose_name='Ano Modelo', null=True, blank=True)
    placa = models.CharField(max_length=10, blank=True, null=True, verbose_name='Placa')
    codigo_fipe = models.CharField(max_length=20, blank=True, null=True, verbose_name='Código FIPE')
    renavam_enc = models.CharField(max_length=500, blank=True, verbose_name='Renavam')
    
    class Meta:
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'

class Investimento(Ativo):
    tipo = models.CharField(max_length=50) # Ações, FIIs, CDB
    ticker = models.CharField(max_length=20, null=True, blank=True)
    custodiante = models.CharField(max_length=100) # Corretora/Banco

class Empresa(Ativo):
    cnpj_enc = models.CharField(max_length=500)
    razao_social = models.CharField(max_length=255)
    percentual_participacao = models.DecimalField(max_digits=5, decimal_places=2)

# --- Sistema de Logs de Operação ---
class OperacaoLog(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    acao = models.CharField(max_length=10) # CREATE, UPDATE, DELETE, VIEW
    tabela = models.CharField(max_length=50)
    objeto_id = models.CharField(max_length=100)
    payload_antes = models.JSONField(null=True)
    payload_depois = models.JSONField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
