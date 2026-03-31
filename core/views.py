from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from .models import Pessoa, Ativo, Familia, Holding, ParticipacaoHolding, AnexoImagem, Imovel, Veiculo, Empresa, Investimento
from .forms import FamiliaForm, HoldingForm, ParticipacaoForm, PessoaForm, AnexoImagemForm, ImovelForm, VeiculoForm, EmpresaForm, InvestimentoForm
from domain.services.partition_engine import PartitionEngine
from decimal import Decimal

# --- Familia CRUD ---
def familia_create(request):
    if request.method == 'POST':
        form = FamiliaForm(request.POST)
        if form.is_valid():
            familia = form.save()
            return redirect('familia_detail', familia_id=familia.id)
    else:
        form = FamiliaForm()
    return render(request, 'crud/familia_form.html', {'form': form, 'title': 'Nova Família'})

def familia_edit(request, familia_id):
    familia = get_object_or_404(Familia, id=familia_id)
    if request.method == 'POST':
        form = FamiliaForm(request.POST, instance=familia)
        if form.is_valid():
            form.save()
            return redirect('familia_detail', familia_id=familia.id)
    else:
        form = FamiliaForm(instance=familia)
    return render(request, 'crud/familia_form.html', {'form': form, 'title': f'Editar {familia.nome}'})

# --- Holding CRUD ---
def holding_create(request, familia_id):
    familia = get_object_or_404(Familia, id=familia_id)
    if request.method == 'POST':
        form = HoldingForm(request.POST)
        if form.is_valid():
            holding = form.save(commit=False)
            holding.familia = familia
            holding.save()
            return redirect('holding_detail', holding_id=holding.id)
    else:
        form = HoldingForm()
    return render(request, 'crud/holding_form.html', {'form': form, 'familia': familia})

def holding_detail(request, holding_id):
    holding = get_object_or_404(Holding, id=holding_id)
    socios = holding.socios.select_related('pessoa').all()
    ativos = Ativo.objects.filter(content_type__model='holding', object_id=holding.id)
    
    # Calculate total participation to validate 100%
    total_participacao = sum(s.percentual for s in socios)
    
    # Add type info to each ativo for template
    ativos_with_type = []
    for ativo in ativos:
        ativo_type = ativo.__class__.__name__.lower()
        ativos_with_type.append({
            'object': ativo,
            'type': ativo_type,
        })
    
    return render(request, 'crud/holding_detail.html', {
        'holding': holding,
        'socios': socios,
        'ativos_with_type': ativos_with_type,
        'total_participacao': total_participacao,
        'familia': holding.familia,
    })

def participacao_add(request, holding_id):
    holding = get_object_or_404(Holding, id=holding_id)
    if request.method == 'POST':
        form = ParticipacaoForm(request.POST, familia_id=holding.familia.id)
        if form.is_valid():
            participacao = form.save(commit=False)
            participacao.holding = holding
            participacao.save()
            return redirect('holding_detail', holding_id=holding.id)
    else:
        form = ParticipacaoForm(familia_id=holding.familia.id)
    return render(request, 'crud/participacao_form.html', {'form': form, 'holding': holding})


# --- Pessoa CRUD ---
def pessoa_create(request, familia_id):
    familia = get_object_or_404(Familia, id=familia_id)
    if request.method == 'POST':
        form = PessoaForm(request.POST, familia_id=familia_id) # custom kwargs if needed, but here simple init
        # Note: form init needs to handle familia_id if we want to filter parents.
        # But for saving, we need to assign manually.
        if form.is_valid():
            pessoa = form.save(commit=False)
            pessoa.familia = familia
            pessoa.save()
            return redirect('familia_detail', familia_id=familia.id)
    else:
        form = PessoaForm(familia_id=familia_id)
    return render(request, 'crud/pessoa_form.html', {'form': form, 'familia': familia})

def pessoa_edit(request, pessoa_id):
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    familia = pessoa.familia
    if request.method == 'POST':
        form = PessoaForm(request.POST, instance=pessoa, familia_id=familia.id if familia else None)
        if form.is_valid():
            form.save()
            return redirect('familia_detail', familia_id=familia.id)
    else:
        form = PessoaForm(instance=pessoa, familia_id=familia.id if familia else None)
    return render(request, 'crud/pessoa_form.html', {'form': form, 'familia': familia})

# --- Ativo CRUD ---
def ativo_select_type(request, pessoa_id):
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    return render(request, 'crud/ativo_select_type.html', {'pessoa': pessoa})

def ativo_select_type_holding(request, holding_id):
    holding = get_object_or_404(Holding, id=holding_id)
    return render(request, 'crud/ativo_select_type_holding.html', {'holding': holding})


def ativo_create(request, pessoa_id, tipo):
    from django.contrib.contenttypes.models import ContentType
    
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    
    # Map type to form and model
    config = {
        'imovel': ImovelForm,
        'veiculo': VeiculoForm,
        'empresa': EmpresaForm,
        'investimento': InvestimentoForm,
    }
    
    FormClass = config.get(tipo)
    if not FormClass:
        return redirect('ativo_select_type', pessoa_id=pessoa_id)
        
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            ativo = form.save(commit=False)
            # Set proprietario using GenericForeignKey (defaulting to Pessoa for now)
            ativo.proprietario = pessoa
            ativo.save()
            return redirect('simular_inventario', familia_id=pessoa.id)
    else:
        form = FormClass()
        
    return render(request, 'crud/ativo_form.html', {'form': form, 'pessoa': pessoa, 'tipo': tipo})

def ativo_create_holding(request, holding_id, tipo):
    """Create asset owned by a Holding"""
    from django.contrib.contenttypes.models import ContentType
    
    holding = get_object_or_404(Holding, id=holding_id)
    
    config = {
        'imovel': ImovelForm,
        'veiculo': VeiculoForm,
        'empresa': EmpresaForm,
        'investimento': InvestimentoForm,
    }
    
    FormClass = config.get(tipo)
    if not FormClass:
        return redirect('ativo_select_type_holding', holding_id=holding_id)
        
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            ativo = form.save(commit=False)
            # Set proprietario to Holding using GenericForeignKey
            ativo.proprietario = holding
            ativo.save()
            return redirect('holding_detail', holding_id=holding.id)
    else:
        form = FormClass()
        
    return render(request, 'crud/ativo_form_holding.html', {'form': form, 'holding': holding, 'tipo': tipo})


def ativo_edit(request, ativo_id):
    # Need to check specific type to bind correct form
    # Try getting the specific instance. Since we don't know the type easily without a polimorphic manager or extra query.
    # We can try to fetch from base Ativo and check instance attributes if we had `django-polymorphic`.
    # Without it, we do a simple check.
    
    # Quick hack: try to find in each table.
    # In production, use `django-polymorphic` or store type in base model better.
    # We have `ativo.imovel` etc due to OneToOne implicit inheritance.
    
    ativo = get_object_or_404(Ativo, id=ativo_id)
    instance = None
    FormClass = None
    
    if hasattr(ativo, 'imovel'):
        instance = ativo.imovel
        FormClass = ImovelForm
    elif hasattr(ativo, 'veiculo'):
        instance = ativo.veiculo
        FormClass = VeiculoForm
    elif hasattr(ativo, 'empresa'):
        instance = ativo.empresa
        FormClass = EmpresaForm
    elif hasattr(ativo, 'investimento'):
        instance = ativo.investimento
        FormClass = InvestimentoForm
        
    if request.method == 'POST':
        form = FormClass(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            # Redirect based on owner type
            if ativo.content_type.model == 'holding':
                return redirect('holding_detail', holding_id=ativo.proprietario.id)
            else:
                return redirect('simular_inventario', pessoa_id=ativo.proprietario.id)
    else:
        form = FormClass(instance=instance)
        
    return render(request, 'crud/ativo_form.html', {'form': form, 'pessoa': ativo.proprietario, 'tipo': 'Ativo'})


def simular_inventario_view(request, pessoa_id):
    """
    Simula inventário considerando:
    - Ativos diretos da pessoa
    - Ativos indiretos via Holdings (baseado no % de participação)
    """
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    
    # Ativos diretos (proprietário = pessoa)
    ativos_diretos = Ativo.objects.filter(
        content_type__model='pessoa',
        object_id=pessoa.id
    )
    
    comuns_diretos = [{"valor": a.valor_mercado_atual} for a in ativos_diretos if a.natureza_bem == 'C']
    particulares_diretos = [{"valor": a.valor_mercado_atual} for a in ativos_diretos if a.natureza_bem == 'P']
    
    # Ativos indiretos (via Holdings)
    comuns_indiretos = []
    particulares_indiretos = []
    
    participacoes = pessoa.participacoes.select_related('holding').all()
    for participacao in participacoes:
        holding = participacao.holding
        percentual = participacao.percentual / Decimal('100')  # Converte % para decimal
        
        # Busca ativos da holding
        ativos_holding = Ativo.objects.filter(
            content_type__model='holding',
            object_id=holding.id
        )
        
        for ativo in ativos_holding:
            valor_indireto = ativo.valor_mercado_atual * percentual
            
            if ativo.natureza_bem == 'C':
                comuns_indiretos.append({"valor": valor_indireto, "holding": holding.razao_social})
            else:
                particulares_indiretos.append({"valor": valor_indireto, "holding": holding.razao_social})
    
    resultado = PartitionEngine.calculate_partition(
        regime_bens=pessoa.regime_bens,
        ativos_comuns=comuns_diretos,
        ativos_particulares=particulares_diretos,
        ativos_comuns_indiretos=comuns_indiretos,
        ativos_particulares_indiretos=particulares_indiretos,
        numero_herdeiros=pessoa.filhos_pai.count() + pessoa.filhos_mae.count(),
        tem_conjuge=True if pessoa.conjuge else False
    )
    
    resultado['itcmd_estimado'] = resultado['heranca_total'] * Decimal('0.04')
    
    # Adiciona detalhamento de ativos indiretos para exibição
    resultado['ativos_indiretos'] = {
        'comuns': comuns_indiretos,
        'particulares': particulares_indiretos,
    }
    
    return render(request, 'simulacao.html', {'resumo': resultado, 'pessoa': pessoa})

def home(request):
    # List Families
    familias = Familia.objects.all()
    return render(request, 'index.html', {'familias': familias})

def familia_detail(request, familia_id):
    familia = get_object_or_404(Familia, id=familia_id)
    membros = familia.membros.all()
    return render(request, 'familia_detail.html', {'familia': familia, 'membros': membros})

def familia_dashboard(request, familia_id):
    """Dashboard visual com estatísticas e resumos da família"""
    from django.db.models import Sum, Count, Q
    from collections import defaultdict
    
    familia = get_object_or_404(Familia, id=familia_id)
    
    # Estatísticas gerais
    stats = {
        'total_membros': familia.membros.count(),
        'total_holdings': familia.holdings.count(),
    }
    
    # Ativos por tipo (diretos das pessoas)
    ativos_pessoas = Ativo.objects.filter(
        content_type__model='pessoa',
        object_id__in=familia.membros.values_list('id', flat=True)
    )
    
    # Ativos por tipo (via holdings)
    ativos_holdings = Ativo.objects.filter(
        content_type__model='holding',
        object_id__in=familia.holdings.values_list('id', flat=True)
    )
    
    # Valores por tipo
    imoveis = Imovel.objects.filter(id__in=ativos_pessoas.values_list('id', flat=True)) | \
              Imovel.objects.filter(id__in=ativos_holdings.values_list('id', flat=True))
    veiculos = Veiculo.objects.filter(id__in=ativos_pessoas.values_list('id', flat=True)) | \
               Veiculo.objects.filter(id__in=ativos_holdings.values_list('id', flat=True))
    empresas = Empresa.objects.filter(id__in=ativos_pessoas.values_list('id', flat=True)) | \
               Empresa.objects.filter(id__in=ativos_holdings.values_list('id', flat=True))
    investimentos = Investimento.objects.filter(id__in=ativos_pessoas.values_list('id', flat=True)) | \
                    Investimento.objects.filter(id__in=ativos_holdings.values_list('id', flat=True))
    
    stats['imoveis_count'] = imoveis.count()
    stats['veiculos_count'] = veiculos.count()
    stats['empresas_count'] = empresas.count()
    stats['investimentos_count'] = investimentos.count()
    
    stats['imoveis_valor'] = imoveis.aggregate(Sum('valor_mercado_atual'))['valor_mercado_atual__sum'] or Decimal('0')
    stats['veiculos_valor'] = veiculos.aggregate(Sum('valor_mercado_atual'))['valor_mercado_atual__sum'] or Decimal('0')
    stats['empresas_valor'] = empresas.aggregate(Sum('valor_mercado_atual'))['valor_mercado_atual__sum'] or Decimal('0')
    stats['investimentos_valor'] = investimentos.aggregate(Sum('valor_mercado_atual'))['valor_mercado_atual__sum'] or Decimal('0')
    
    stats['patrimonio_total'] = stats['imoveis_valor'] + stats['veiculos_valor'] + stats['empresas_valor'] + stats['investimentos_valor']
    
    # Distribuição geográfica dos imóveis
    distribuicao_geo = defaultdict(int)
    for imovel in imoveis:
        if imovel.endereco:
            distribuicao_geo[imovel.endereco.uf] += 1
    
    # Imóveis com coordenadas para mapa
    imoveis_mapa = [
        {
            'descricao': i.descricao,
            'endereco': str(i.endereco) if i.endereco else 'N/A',
            'lat': float(i.endereco.latitude) if i.endereco and i.endereco.latitude else None,
            'lng': float(i.endereco.longitude) if i.endereco and i.endereco.longitude else None,
            'valor': float(i.valor_mercado_atual),
        }
        for i in imoveis if i.endereco
    ]
    
    context = {
        'familia': familia,
        'stats': stats,
        'distribuicao_geo': dict(distribuicao_geo),
        'imoveis_mapa': imoveis_mapa,
    }
    
    return render(request, 'dashboard.html', context)


# --- Anexos/Imagens ---
def anexo_adicionar(request, model_name, object_id):
    """Adiciona anexo/imagem a qualquer entidade"""
    # Mapeia model_name para o ContentType
    model_map = {
        'pessoa': Pessoa,
        'imovel': Imovel,
        'veiculo': Veiculo,
        'empresa': Empresa,
        'investimento': Investimento,
        'ativo': Ativo,
    }
    
    model_class = model_map.get(model_name)
    if not model_class:
        # Try to find the actual model dynamically
        from django.apps import apps
        try:
            model_class = apps.get_model('core', model_name.capitalize())
        except LookupError:
            return redirect('home')
    
    entidade = get_object_or_404(model_class, id=object_id)
    
    if request.method == 'POST':
        form = AnexoImagemForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.entidade = entidade
            if request.user.is_authenticated:
                anexo.created_by = request.user
            anexo.save()
            
            # Redirect back to entity detail/edit
            return redirect(request.META.get('HTTP_REFERER', 'home'))
    else:
        form = AnexoImagemForm()
    
    return render(request, 'crud/anexo_form.html', {
        'form': form,
        'entidade': entidade,
        'model_name': model_name,
    })

def anexo_listar(request, model_name, object_id):
    """Lista anexos de uma entidade"""
    model_map = {
        'pessoa': Pessoa,
        'imovel': Imovel,
        'veiculo': Veiculo,
        'empresa': Empresa,
        'investimento': Investimento,
        'ativo': Ativo,  # Generic Ativo
    }
    
    model_class = model_map.get(model_name)
    if not model_class:
        # Try to find the actual model dynamically
        from django.apps import apps
        try:
            model_class = apps.get_model('core', model_name.capitalize())
        except LookupError:
            return redirect('home')
    
    entidade = get_object_or_404(model_class, id=object_id)
    content_type = ContentType.objects.get_for_model(model_class)
    
    anexos = AnexoImagem.objects.filter(
        content_type=content_type,
        object_id=object_id
    )
    
    return render(request, 'crud/anexo_listar.html', {
        'entidade': entidade,
        'anexos': anexos,
        'model_name': model_name,
        'object_id': object_id,
    })


