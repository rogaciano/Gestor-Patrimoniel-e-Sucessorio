from django.contrib import admin

from .models import (
    AnexoImagem,
    Empresa,
    Endereco,
    Familia,
    FamiliaAcesso,
    Holding,
    Imovel,
    Investimento,
    OperacaoLog,
    ParticipacaoHolding,
    Pessoa,
    Veiculo,
)


@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'created_at', 'updated_at')
    search_fields = ('nome',)


@admin.register(FamiliaAcesso)
class FamiliaAcessoAdmin(admin.ModelAdmin):
    list_display = ('user', 'familia', 'created_at')
    search_fields = ('user__username', 'user__email', 'familia__nome')
    autocomplete_fields = ('user', 'familia')


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'familia', 'data_nascimento', 'regime_bens')
    list_filter = ('familia', 'regime_bens')
    search_fields = ('nome_completo',)
    autocomplete_fields = ('familia', 'pai', 'mae', 'conjuge')


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'familia', 'tipo_societario', 'data_constituicao')
    list_filter = ('tipo_societario', 'familia')
    search_fields = ('razao_social',)
    autocomplete_fields = ('familia',)


@admin.register(ParticipacaoHolding)
class ParticipacaoHoldingAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'holding', 'percentual', 'tipo_quota')
    list_filter = ('tipo_quota',)
    autocomplete_fields = ('pessoa', 'holding')


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor_mercado_atual', 'natureza_bem')
    search_fields = ('descricao', 'matricula')


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'marca', 'modelo', 'placa', 'valor_mercado_atual')
    search_fields = ('descricao', 'placa', 'marca', 'modelo')


@admin.register(Investimento)
class InvestimentoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'tipo', 'custodiante', 'valor_mercado_atual')
    search_fields = ('descricao', 'ticker', 'custodiante')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'razao_social', 'percentual_participacao', 'valor_mercado_atual')
    search_fields = ('descricao', 'razao_social')


@admin.register(AnexoImagem)
class AnexoImagemAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'tipo', 'created_at', 'created_by')
    list_filter = ('tipo',)
    search_fields = ('descricao',)


@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = ('logradouro', 'numero', 'bairro', 'cidade', 'uf')
    list_filter = ('uf', 'cidade')
    search_fields = ('logradouro', 'bairro', 'cidade', 'cep')


@admin.register(OperacaoLog)
class OperacaoLogAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'acao', 'tabela', 'timestamp', 'ip_address')
    list_filter = ('acao', 'timestamp')
    search_fields = ('usuario__username', 'tabela', 'objeto_id', 'ip_address')
    readonly_fields = ('usuario', 'acao', 'tabela', 'objeto_id', 'payload_antes', 'payload_depois', 'timestamp', 'ip_address')
