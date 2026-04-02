from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Familia, Pessoa, Holding, ParticipacaoHolding, Endereco, AnexoImagem, Imovel, Veiculo, Empresa, Investimento, FamiliaAcesso

# --- Mixin para EstilizaÃ§Ã£o Tailwind ---
class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'app-checkbox'
            else:
                field.widget.attrs['class'] = 'app-field'


User = get_user_model()

# --- Forms ---

class FamiliaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Familia
        fields = ['nome', 'inventario_prazo_final', 'itcmd_vencimento', 'itcmd_uf']
        widgets = {
            'inventario_prazo_final': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'itcmd_vencimento': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
        labels = {
            'inventario_prazo_final': 'Prazo final do inventario',
            'itcmd_vencimento': 'Proximo vencimento do ITCMD',
            'itcmd_uf': 'UF de referencia do ITCMD',
        }
        help_texts = {
            'inventario_prazo_final': 'Use para destacar a urgencia do processo no dashboard da familia.',
            'itcmd_vencimento': 'Data mais relevante para recolhimento ou conferencia do ITCMD.',
        }

class HoldingForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Holding
        fields = ['razao_social', 'cnpj', 'tipo_societario', 'data_constituicao']
        widgets = {
            'data_constituicao': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
        labels = {
            'razao_social': 'RazÃ£o Social',
            'cnpj': 'CNPJ',
            'tipo_societario': 'Tipo SocietÃ¡rio',
            'data_constituicao': 'Data de ConstituiÃ§Ã£o',
        }

class ParticipacaoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ParticipacaoHolding
        fields = ['pessoa', 'percentual', 'tipo_quota']
        labels = {
            'pessoa': 'SÃ³cio',
            'percentual': 'Percentual de ParticipaÃ§Ã£o (%)',
            'tipo_quota': 'Tipo de Quota',
        }
        help_texts = {
            'percentual': 'Ex: 50.00 para 50%',
            'tipo_quota': 'ORD (OrdinÃ¡ria): Com direito a voto. PREF (Preferencial): Prioridade em dividendos, sem voto. Use OrdinÃ¡ria em 99% dos casos.',
        }
    
    def __init__(self, *args, **kwargs):
        familia_id = kwargs.pop('familia_id', None)
        super().__init__(*args, **kwargs)
        if familia_id:
            # Filter people to only show members of the same family
            self.fields['pessoa'].queryset = Pessoa.objects.filter(familia_id=familia_id)


class PessoaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = ['nome_completo', 'cpf', 'data_nascimento', 'foto', 'regime_bens', 'pai', 'mae', 'conjuge']
        widgets = {
            'data_nascimento': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        familia_id = kwargs.pop('familia_id', None)
        super().__init__(*args, **kwargs)
        # Se estiver criando dentro de uma famÃ­lia, filtrar opÃ§Ãµes de parentesco se necessÃ¡rio?
        # Por enquanto, deixamos aberto para selecionar qualquer pessoa do sistema ou idealmente da mesma famÃ­lia.
        if familia_id:
            # Filter foreign keys to only show members of the same family to avoid cross-family confusion
            self.fields['pai'].queryset = Pessoa.objects.filter(familia_id=familia_id)
            self.fields['mae'].queryset = Pessoa.objects.filter(familia_id=familia_id)
            self.fields['conjuge'].queryset = Pessoa.objects.filter(familia_id=familia_id)

class ImovelForm(TailwindFormMixin, forms.ModelForm):
    # Campos de endereÃ§o inline
    cep = forms.CharField(max_length=9, label='CEP', widget=forms.TextInput(attrs={'placeholder': '00000-000'}))
    logradouro = forms.CharField(max_length=255, label='Logradouro')
    numero = forms.CharField(max_length=10, label='NÃºmero')
    complemento = forms.CharField(max_length=100, required=False, label='Complemento')
    bairro = forms.CharField(max_length=100, label='Bairro')
    cidade = forms.CharField(max_length=100, label='Cidade')
    uf = forms.ChoiceField(choices=[('', '---------')] + list(Endereco.UF_CHOICES), label='UF')
    
    class Meta:
        model = Imovel
        fields = [
            'descricao',
            'valor_aquisicao',
            'valor_mercado_atual',
            'natureza_bem',
            'matricula',
            'iptu_index',
            'iptu_valor_anual',
            'iptu_vencimento',
        ]
        labels = {
            'descricao': 'Descricao do Imovel',
            'valor_aquisicao': 'Valor de Aquisicao (R$)',
            'valor_mercado_atual': 'Valor de Mercado Atual (R$)',
            'natureza_bem': 'Natureza do Bem',
            'matricula': 'Matricula do Imovel',
            'iptu_index': 'Inscricao do IPTU',
            'iptu_valor_anual': 'Valor anual do IPTU (R$)',
            'iptu_vencimento': 'Proximo vencimento do IPTU',
        }
        help_texts = {
            'valor_mercado_atual': 'Valor estimado de venda hoje (usado na partilha)',
            'iptu_index': 'Codigo de referencia do cadastro municipal.',
            'iptu_valor_anual': 'Valor esperado para a obrigacao tributaria anual deste imovel.',
            'iptu_vencimento': 'Data usada para alertas operacionais e agenda fiscal.',
        }
        widgets = {
            'iptu_vencimento': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se editando, preenche campos de endereÃ§o
        if self.instance.pk and self.instance.endereco:
            self.fields['cep'].initial = self.instance.endereco.cep
            self.fields['logradouro'].initial = self.instance.endereco.logradouro
            self.fields['numero'].initial = self.instance.endereco.numero
            self.fields['complemento'].initial = self.instance.endereco.complemento
            self.fields['bairro'].initial = self.instance.endereco.bairro
            self.fields['cidade'].initial = self.instance.endereco.cidade
            self.fields['uf'].initial = self.instance.endereco.uf
    
    def save(self, commit=True):
        imovel = super().save(commit=False)
        
        # Cria ou atualiza endereÃ§o
        if imovel.endereco:
            endereco = imovel.endereco
        else:
            endereco = Endereco()
        
        endereco.cep = self.cleaned_data['cep']
        endereco.logradouro = self.cleaned_data['logradouro']
        endereco.numero = self.cleaned_data['numero']
        endereco.complemento = self.cleaned_data['complemento']
        endereco.bairro = self.cleaned_data['bairro']
        endereco.cidade = self.cleaned_data['cidade']
        endereco.uf = self.cleaned_data['uf']
        
        if commit:
            endereco.save()
            imovel.endereco = endereco
            imovel.save()
        
        return imovel


class VeiculoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ['descricao', 'tipo', 'marca', 'modelo', 'ano_fabricacao', 'ano_modelo', 'placa', 'renavam_enc', 'valor_mercado_atual', 'natureza_bem', 'codigo_fipe']
        labels = {
            'descricao': 'DescriÃ§Ã£o/Apelido',
            'valor_mercado_atual': 'Valor de Mercado (FIPE)',
            'renavam_enc': 'Renavam',
            'natureza_bem': 'Natureza do Bem',
        }
        widgets = {
            'tipo': forms.Select(choices=[('carros', 'Carros'), ('motos', 'Motos'), ('caminhoes', 'CaminhÃµes')]),
            'marca': forms.Select(attrs={'class': 'form-select block w-full mt-1'}),
            'modelo': forms.Select(attrs={'class': 'form-select block w-full mt-1'}),
            'ano_modelo': forms.Select(attrs={'class': 'form-select block w-full mt-1'}),
            'ano_fabricacao': forms.NumberInput(attrs={'placeholder': 'Ano Fab.'}),
        }

        help_texts = {
            'valor_mercado_atual': 'Consulte a Tabela FIPE para precisÃ£o',
        }

class EmpresaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['descricao', 'valor_aquisicao', 'valor_mercado_atual', 'natureza_bem', 'cnpj_enc', 'razao_social', 'percentual_participacao']
        labels = {
            'descricao': 'DescriÃ§Ã£o da ParticipaÃ§Ã£o',
            'valor_aquisicao': 'Valor Investido (R$)',
            'valor_mercado_atual': 'Valor Patrimonial da Quota (R$)',
            'natureza_bem': 'Natureza do Bem',
            'percentual_participacao': 'Percentual de ParticipaÃ§Ã£o (%)',
        }
        help_texts = {
            'valor_mercado_atual': 'Valor proporcional ao % de participaÃ§Ã£o',
            'percentual_participacao': 'Ex: 50 para 50% das quotas',
        }

class InvestimentoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Investimento
        fields = ['descricao', 'valor_aquisicao', 'valor_mercado_atual', 'natureza_bem', 'tipo', 'custodiante', 'ticker']
        labels = {
            'descricao': 'DescriÃ§Ã£o do Investimento',
            'valor_aquisicao': 'Valor Original (R$)',
            'valor_mercado_atual': 'Valor Atual de Mercado (R$)',
            'natureza_bem': 'Natureza do Bem',
        }
        help_texts = {
            'valor_aquisicao': 'Quanto foi pago na aquisiÃ§Ã£o original',
            'valor_mercado_atual': 'Valor atual de venda/liquidaÃ§Ã£o',
        }

class AnexoImagemForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = AnexoImagem
        fields = ['imagem', 'descricao', 'tipo']
        labels = {
            'imagem': 'Arquivo',
            'descricao': 'DescriÃ§Ã£o',
            'tipo': 'Tipo de Documento',
        }
        widgets = {
            'imagem': forms.FileInput(attrs={'accept': 'image/*'}),
        }


class FamilyAccessCreateForm(TailwindFormMixin, forms.Form):
    username = forms.CharField(label='Usuario', max_length=150)
    first_name = forms.CharField(label='Nome', max_length=150, required=False)
    last_name = forms.CharField(label='Sobrenome', max_length=150, required=False)
    email = forms.EmailField(label='Email', required=False)
    familia = forms.ModelChoiceField(queryset=Familia.objects.none(), label='Familia')
    password1 = forms.CharField(label='Senha', widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput(render_value=False))
    is_active = forms.BooleanField(label='Acesso ativo', required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['familia'].queryset = Familia.objects.order_by('nome')
        self.fields['username'].help_text = 'Login usado pela familia para entrar no sistema.'
        self.fields['familia'].help_text = 'Cada usuario comum acessa apenas uma familia.'
        self.fields['email'].help_text = 'Opcional, util para contato ou recuperacao futura.'

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Ja existe um usuario com este login.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 != password2:
            self.add_error('password2', 'As senhas nao coincidem.')

        if password1:
            try:
                validate_password(password1)
            except ValidationError as exc:
                self.add_error('password1', exc)

        return cleaned_data

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data.get('email', ''),
            password=self.cleaned_data['password1'],
        )
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_active = self.cleaned_data.get('is_active', True)
        user.is_staff = False
        user.is_superuser = False
        user.save()

        FamiliaAcesso.objects.update_or_create(
            user=user,
            defaults={'familia': self.cleaned_data['familia']},
        )
        return user


class FamilyAccessUpdateForm(TailwindFormMixin, forms.Form):
    username = forms.CharField(label='Usuario', max_length=150)
    first_name = forms.CharField(label='Nome', max_length=150, required=False)
    last_name = forms.CharField(label='Sobrenome', max_length=150, required=False)
    email = forms.EmailField(label='Email', required=False)
    familia = forms.ModelChoiceField(queryset=Familia.objects.none(), label='Familia')
    password1 = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(render_value=False),
        required=False,
    )
    password2 = forms.CharField(
        label='Confirmar nova senha',
        widget=forms.PasswordInput(render_value=False),
        required=False,
    )
    is_active = forms.BooleanField(label='Acesso ativo', required=False)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['familia'].queryset = Familia.objects.order_by('nome')
        access = getattr(user, 'familia_access', None)
        self.initial.update({
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'familia': access.familia if access else None,
            'is_active': user.is_active,
        })
        self.fields['password1'].help_text = 'Preencha apenas se quiser trocar a senha.'
        self.fields['familia'].help_text = 'O usuario continuara limitado a esta familia.'

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        existing = User.objects.filter(username__iexact=username).exclude(pk=self.user.pk)
        if existing.exists():
            raise forms.ValidationError('Ja existe um usuario com este login.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', 'As senhas nao coincidem.')

            if password1:
                try:
                    validate_password(password1, self.user)
                except ValidationError as exc:
                    self.add_error('password1', exc)

        return cleaned_data

    @transaction.atomic
    def save(self):
        self.user.username = self.cleaned_data['username']
        self.user.first_name = self.cleaned_data.get('first_name', '')
        self.user.last_name = self.cleaned_data.get('last_name', '')
        self.user.email = self.cleaned_data.get('email', '')
        self.user.is_active = self.cleaned_data.get('is_active', False)
        self.user.is_staff = False
        self.user.is_superuser = False

        password = self.cleaned_data.get('password1')
        if password:
            self.user.set_password(password)

        self.user.save()

        FamiliaAcesso.objects.update_or_create(
            user=self.user,
            defaults={'familia': self.cleaned_data['familia']},
        )
        return self.user


