from django import forms
from .models import Familia, Pessoa, Holding, ParticipacaoHolding, Endereco, AnexoImagem, Imovel, Veiculo, Empresa, Investimento

# --- Mixin para Estilização Tailwind ---
class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'
            else:
                # Added 'border', 'border-gray-400', 'px-3', 'py-2' for better visibility
                field.widget.attrs['class'] = 'mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border border-gray-400 rounded-md px-3 py-2'

# --- Forms ---

class FamiliaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Familia
        fields = ['nome']

class HoldingForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Holding
        fields = ['razao_social', 'cnpj', 'tipo_societario', 'data_constituicao']
        widgets = {
            'data_constituicao': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }
        labels = {
            'razao_social': 'Razão Social',
            'cnpj': 'CNPJ',
            'tipo_societario': 'Tipo Societário',
            'data_constituicao': 'Data de Constituição',
        }

class ParticipacaoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ParticipacaoHolding
        fields = ['pessoa', 'percentual', 'tipo_quota']
        labels = {
            'pessoa': 'Sócio',
            'percentual': 'Percentual de Participação (%)',
            'tipo_quota': 'Tipo de Quota',
        }
        help_texts = {
            'percentual': 'Ex: 50.00 para 50%',
            'tipo_quota': 'ORD (Ordinária): Com direito a voto. PREF (Preferencial): Prioridade em dividendos, sem voto. Use Ordinária em 99% dos casos.',
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
        # Se estiver criando dentro de uma família, filtrar opções de parentesco se necessário?
        # Por enquanto, deixamos aberto para selecionar qualquer pessoa do sistema ou idealmente da mesma família.
        if familia_id:
            # Filter foreign keys to only show members of the same family to avoid cross-family confusion
            self.fields['pai'].queryset = Pessoa.objects.filter(familia_id=familia_id)
            self.fields['mae'].queryset = Pessoa.objects.filter(familia_id=familia_id)
            self.fields['conjuge'].queryset = Pessoa.objects.filter(familia_id=familia_id)

class ImovelForm(TailwindFormMixin, forms.ModelForm):
    # Campos de endereço inline
    cep = forms.CharField(max_length=9, label='CEP', widget=forms.TextInput(attrs={'placeholder': '00000-000'}))
    logradouro = forms.CharField(max_length=255, label='Logradouro')
    numero = forms.CharField(max_length=10, label='Número')
    complemento = forms.CharField(max_length=100, required=False, label='Complemento')
    bairro = forms.CharField(max_length=100, label='Bairro')
    cidade = forms.CharField(max_length=100, label='Cidade')
    uf = forms.ChoiceField(choices=[('', '---------')] + list(Endereco.UF_CHOICES), label='UF')
    
    class Meta:
        model = Imovel
        fields = ['descricao', 'valor_aquisicao', 'valor_mercado_atual', 'natureza_bem', 'matricula']
        labels = {
            'descricao': 'Descrição do Imóvel',
            'valor_aquisicao': 'Valor de Aquisição (R$)',
            'valor_mercado_atual': 'Valor de Mercado Atual (R$)',
            'natureza_bem': 'Natureza do Bem',
            'matricula': 'Matrícula do Imóvel',
        }
        help_texts = {
            'valor_mercado_atual': 'Valor estimado de venda hoje (usado na partilha)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se editando, preenche campos de endereço
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
        
        # Cria ou atualiza endereço
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
            'descricao': 'Descrição/Apelido',
            'valor_mercado_atual': 'Valor de Mercado (FIPE)',
            'renavam_enc': 'Renavam',
            'natureza_bem': 'Natureza do Bem',
        }
        widgets = {
            'tipo': forms.Select(choices=[('carros', 'Carros'), ('motos', 'Motos'), ('caminhoes', 'Caminhões')]),
            'marca': forms.Select(attrs={'class': 'form-select block w-full mt-1'}),
            'modelo': forms.Select(attrs={'class': 'form-select block w-full mt-1'}),
            'ano_modelo': forms.Select(attrs={'class': 'form-select block w-full mt-1'}),
            'ano_fabricacao': forms.NumberInput(attrs={'placeholder': 'Ano Fab.'}),
        }

        help_texts = {
            'valor_mercado_atual': 'Consulte a Tabela FIPE para precisão',
        }

class EmpresaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['descricao', 'valor_aquisicao', 'valor_mercado_atual', 'natureza_bem', 'cnpj_enc', 'razao_social', 'percentual_participacao']
        labels = {
            'descricao': 'Descrição da Participação',
            'valor_aquisicao': 'Valor Investido (R$)',
            'valor_mercado_atual': 'Valor Patrimonial da Quota (R$)',
            'natureza_bem': 'Natureza do Bem',
            'percentual_participacao': 'Percentual de Participação (%)',
        }
        help_texts = {
            'valor_mercado_atual': 'Valor proporcional ao % de participação',
            'percentual_participacao': 'Ex: 50 para 50% das quotas',
        }

class InvestimentoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Investimento
        fields = ['descricao', 'valor_aquisicao', 'valor_mercado_atual', 'natureza_bem', 'tipo', 'custodiante', 'ticker']
        labels = {
            'descricao': 'Descrição do Investimento',
            'valor_aquisicao': 'Valor Original (R$)',
            'valor_mercado_atual': 'Valor Atual de Mercado (R$)',
            'natureza_bem': 'Natureza do Bem',
        }
        help_texts = {
            'valor_aquisicao': 'Quanto foi pago na aquisição original',
            'valor_mercado_atual': 'Valor atual de venda/liquidação',
        }

class AnexoImagemForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = AnexoImagem
        fields = ['imagem', 'descricao', 'tipo']
        labels = {
            'imagem': 'Arquivo',
            'descricao': 'Descrição',
            'tipo': 'Tipo de Documento',
        }
        widgets = {
            'imagem': forms.FileInput(attrs={'accept': 'image/*'}),
        }

