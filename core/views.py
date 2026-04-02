from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect

from .models import Pessoa, Ativo, Familia, FamiliaAcesso, Holding, ParticipacaoHolding, AnexoImagem, Imovel, Veiculo, Empresa, Investimento
from .forms import FamiliaForm, HoldingForm, ParticipacaoForm, PessoaForm, AnexoImagemForm, ImovelForm, VeiculoForm, EmpresaForm, InvestimentoForm, FamilyAccessCreateForm, FamilyAccessUpdateForm
from domain.services.partition_engine import PartitionEngine
from decimal import Decimal


User = get_user_model()


def _user_is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _manageable_by_user(user):
    return _user_is_admin(user)


def _get_user_accessible_familias(user):
    if _user_is_admin(user):
        return Familia.objects.all()

    access = getattr(user, 'familia_access', None)
    if access:
        return Familia.objects.filter(id=access.familia_id)

    return Familia.objects.none()


def _require_family_access(user, familia):
    if _user_is_admin(user):
        return

    access = getattr(user, 'familia_access', None)
    if not access or access.familia_id != familia.id:
        raise PermissionDenied("VocÃª nÃ£o tem acesso a esta famÃ­lia.")


def _require_management_access(user):
    if not _manageable_by_user(user):
        raise PermissionDenied("Somente administradores podem alterar os dados.")


def _resolve_related_familia(instance):
    if isinstance(instance, Familia):
        return instance
    if isinstance(instance, Pessoa):
        return instance.familia
    if isinstance(instance, Holding):
        return instance.familia
    if isinstance(instance, Ativo):
        owner = instance.proprietario
        return _resolve_related_familia(owner) if owner else None

    familia = getattr(instance, 'familia', None)
    if familia is not None:
        return familia

    owner = getattr(instance, 'proprietario', None)
    if owner is not None:
        return _resolve_related_familia(owner)

    return None


def management_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        _require_management_access(request.user)
        return view_func(request, *args, **kwargs)

    return wrapped


def _get_family_user_or_404(user_id):
    return get_object_or_404(
        User.objects.filter(is_staff=False, is_superuser=False),
        pk=user_id,
    )


def _person_sort_key(person):
    return (person.data_nascimento, person.nome_completo)


def _collect_tree_member_ids(node):
    collected = {node['person'].id}
    if node['spouse']:
        collected.add(node['spouse'].id)
    for child in node['children']:
        collected.update(_collect_tree_member_ids(child))
    return collected


def _build_tree_node(person, member_ids, children_index, spouse_map, branch_seen=None):
    branch_seen = branch_seen or set()
    if person.id in branch_seen:
        return None

    spouse = spouse_map.get(person.id)
    current_ids = {person.id}
    if spouse:
        current_ids.add(spouse.id)

    next_seen = branch_seen | current_ids
    child_candidates = {}
    for parent_id in current_ids:
        for child in children_index.get(parent_id, []):
            child_candidates[child.id] = child

    children = []
    for child in sorted(child_candidates.values(), key=_person_sort_key):
        if child.id in next_seen:
            continue
        child_node = _build_tree_node(child, member_ids, children_index, spouse_map, next_seen)
        if child_node:
            children.append(child_node)

    return {
        'person': person,
        'spouse': spouse,
        'children': children,
    }


def _build_family_tree(members):
    members = list(members)
    if not members:
        return []

    member_by_id = {member.id: member for member in members}
    member_ids = set(member_by_id)
    children_index = {member_id: [] for member_id in member_ids}
    spouse_map = {}

    for member in members:
        for parent_id in (member.pai_id, member.mae_id):
            if parent_id in member_ids:
                children_index[parent_id].append(member)
        if member.conjuge_id in member_ids:
            spouse = member_by_id[member.conjuge_id]
            spouse_map[member.id] = spouse
            spouse_map[spouse.id] = member

    for parent_id, children in children_index.items():
        deduped_children = {child.id: child for child in children}
        children_index[parent_id] = sorted(deduped_children.values(), key=_person_sort_key)

    roots = sorted(
        [member for member in members if member.pai_id not in member_ids and member.mae_id not in member_ids],
        key=_person_sort_key,
    )

    branches = []
    covered_ids = set()

    for root in roots:
        if root.id in covered_ids:
            continue
        node = _build_tree_node(root, member_ids, children_index, spouse_map)
        if not node:
            continue
        branches.append(node)
        covered_ids.update(_collect_tree_member_ids(node))

    for member in sorted(members, key=_person_sort_key):
        if member.id in covered_ids:
            continue
        node = _build_tree_node(member, member_ids, children_index, spouse_map)
        if not node:
            continue
        branches.append(node)
        covered_ids.update(_collect_tree_member_ids(node))

    return branches


@management_required
def acesso_list(request):
    acessos = FamiliaAcesso.objects.select_related('user', 'familia').order_by('familia__nome', 'user__username')
    stats = {
        'usuarios': acessos.count(),
        'ativos': acessos.filter(user__is_active=True).count(),
        'familias': acessos.values('familia_id').distinct().count(),
    }
    return render(request, 'acessos/list.html', {
        'acessos': acessos,
        'stats': stats,
    })


@management_required
def acesso_create(request):
    if request.method == 'POST':
        form = FamilyAccessCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Acesso criado para {user.username}.')
            return redirect('acesso_list')
    else:
        form = FamilyAccessCreateForm()

    return render(request, 'acessos/form.html', {
        'form': form,
        'title': 'Novo acesso de familia',
        'subtitle': 'Crie o login, defina a senha e vincule o usuario a familia correta em um unico fluxo.',
        'submit_label': 'Criar acesso',
    })


@management_required
def acesso_edit(request, user_id):
    user = _get_family_user_or_404(user_id)
    if request.method == 'POST':
        form = FamilyAccessUpdateForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Acesso atualizado para {user.username}.')
            return redirect('acesso_list')
    else:
        form = FamilyAccessUpdateForm(user=user)

    return render(request, 'acessos/form.html', {
        'form': form,
        'title': f'Editar acesso de {user.username}',
        'subtitle': 'Ajuste dados de login, senha, status e familia vinculada sem usar o admin tecnico.',
        'submit_label': 'Salvar alteracoes',
        'managed_user': user,
    })

# --- Familia CRUD ---
@management_required
def familia_create(request):
    if request.method == 'POST':
        form = FamiliaForm(request.POST)
        if form.is_valid():
            familia = form.save()
            return redirect('familia_detail', familia_id=familia.id)
    else:
        form = FamiliaForm()
    return render(request, 'crud/familia_form.html', {'form': form, 'title': 'Nova Família'})

@management_required
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
@management_required
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

@login_required
def holding_detail(request, holding_id):
    holding = get_object_or_404(Holding, id=holding_id)
    _require_family_access(request.user, holding.familia)
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

    holding_stats = {
        'socios': socios.count(),
        'ativos': len(ativos_with_type),
        'valor_total': sum((ativo.valor_mercado_atual for ativo in ativos), Decimal('0')),
    }
    
    return render(request, 'crud/holding_detail.html', {
        'holding': holding,
        'socios': socios,
        'ativos_with_type': ativos_with_type,
        'total_participacao': total_participacao,
        'holding_stats': holding_stats,
        'familia': holding.familia,
    })

@management_required
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
@management_required
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

@management_required
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
@management_required
def ativo_select_type(request, pessoa_id):
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    return render(request, 'crud/ativo_select_type.html', {'pessoa': pessoa})

@management_required
def ativo_select_type_holding(request, holding_id):
    holding = get_object_or_404(Holding, id=holding_id)
    return render(request, 'crud/ativo_select_type_holding.html', {'holding': holding})


@management_required
def ativo_create(request, pessoa_id, tipo):
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
            return redirect('simular_inventario', pessoa_id=pessoa.id)
    else:
        form = FormClass()
        
    return render(request, 'crud/ativo_form.html', {'form': form, 'pessoa': pessoa, 'tipo': tipo})

@management_required
def ativo_create_holding(request, holding_id, tipo):
    """Create asset owned by a Holding"""
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


@management_required
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


@login_required
def simular_inventario_view(request, pessoa_id):
    """
    Simula inventário considerando:
    - Ativos diretos da pessoa
    - Ativos indiretos via Holdings (baseado no % de participação)
    """
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    _require_family_access(request.user, pessoa.familia)
    
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

@login_required
def home(request):
    familias = _get_user_accessible_familias(request.user).order_by('nome')
    familia_ids = list(familias.values_list('id', flat=True))
    membros = Pessoa.objects.filter(familia_id__in=familia_ids)
    holdings = Holding.objects.filter(familia_id__in=familia_ids)
    ativos = Ativo.objects.filter(content_type__model='pessoa', object_id__in=membros.values_list('id', flat=True)) | Ativo.objects.filter(
        content_type__model='holding',
        object_id__in=holdings.values_list('id', flat=True),
    )
    stats = {
        'familias': familias.count(),
        'membros': membros.count(),
        'holdings': holdings.count(),
        'ativos': ativos.count(),
    }
    return render(request, 'index.html', {'familias': familias, 'stats': stats})

@login_required
def familia_detail(request, familia_id):
    familia = get_object_or_404(Familia, id=familia_id)
    _require_family_access(request.user, familia)
    membros = list(familia.membros.all())
    member_ids = [membro.id for membro in membros]
    holding_ids = list(familia.holdings.values_list('id', flat=True))
    ativos_pessoais = Ativo.objects.filter(content_type__model='pessoa', object_id__in=member_ids).count() if member_ids else 0
    ativos_holdings = Ativo.objects.filter(content_type__model='holding', object_id__in=holding_ids).count() if holding_ids else 0
    stats = {
        'membros': len(membros),
        'holdings': len(holding_ids),
        'ativos': ativos_pessoais + ativos_holdings,
    }
    tree_branches = _build_family_tree(membros)
    membros_ordenados = sorted(membros, key=_person_sort_key)
    stats['ramos'] = len(tree_branches)
    return render(request, 'familia_detail.html', {
        'familia': familia,
        'membros': membros_ordenados,
        'stats': stats,
        'tree_branches': tree_branches,
    })

@login_required
def familia_dashboard(request, familia_id):
    """Dashboard visual com estatísticas e resumos da família"""
    from django.db.models import Sum, Count, Q
    from collections import defaultdict
    
    familia = get_object_or_404(Familia, id=familia_id)
    _require_family_access(request.user, familia)
    
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
    asset_mix = [
        {
            'label': 'Imóveis',
            'count': stats['imoveis_count'],
            'value': stats['imoveis_valor'],
            'tone': 'warm',
        },
        {
            'label': 'Veículos',
            'count': stats['veiculos_count'],
            'value': stats['veiculos_valor'],
            'tone': 'ink',
        },
        {
            'label': 'Empresas',
            'count': stats['empresas_count'],
            'value': stats['empresas_valor'],
            'tone': 'soft',
        },
        {
            'label': 'Investimentos',
            'count': stats['investimentos_count'],
            'value': stats['investimentos_valor'],
            'tone': 'soft',
        },
    ]
    for item in asset_mix:
        if stats['patrimonio_total'] > 0:
            item['share'] = ((item['value'] / stats['patrimonio_total']) * Decimal('100')).quantize(Decimal('0.1'))
        else:
            item['share'] = Decimal('0.0')
    
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
        'asset_mix': asset_mix,
        'distribuicao_geo': dict(distribuicao_geo),
        'imoveis_mapa': imoveis_mapa,
    }
    
    return render(request, 'dashboard.html', context)


# --- Anexos/Imagens ---
@management_required
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
    familia = _resolve_related_familia(entidade)
    if familia:
        _require_family_access(request.user, familia)
    
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

@login_required
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
    familia = _resolve_related_familia(entidade)
    if familia:
        _require_family_access(request.user, familia)
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


