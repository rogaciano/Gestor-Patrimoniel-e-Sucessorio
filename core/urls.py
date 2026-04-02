from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('acessos/', views.acesso_list, name='acesso_list'),
    path('acessos/novo/', views.acesso_create, name='acesso_create'),
    path('acessos/<int:user_id>/editar/', views.acesso_edit, name='acesso_edit'),
    path('familia/nova/', views.familia_create, name='familia_create'),
    path('familia/<uuid:familia_id>/', views.familia_detail, name='familia_detail'),
    path('familia/<uuid:familia_id>/dashboard/', views.familia_dashboard, name='familia_dashboard'),
    path('familia/<uuid:familia_id>/editar/', views.familia_edit, name='familia_edit'),

    
    path('familia/<uuid:familia_id>/holding/nova/', views.holding_create, name='holding_create'),
    path('holding/<uuid:holding_id>/', views.holding_detail, name='holding_detail'),
    path('holding/<uuid:holding_id>/socio/novo/', views.participacao_add, name='participacao_add'),
    path('holding/<uuid:holding_id>/ativo/novo/', views.ativo_select_type_holding, name='ativo_select_type_holding'),
    path('holding/<uuid:holding_id>/ativo/novo/<str:tipo>/', views.ativo_create_holding, name='ativo_create_holding'),

    
    path('familia/<uuid:familia_id>/pessoa/nova/', views.pessoa_create, name='pessoa_create'),
    path('pessoa/<uuid:pessoa_id>/editar/', views.pessoa_edit, name='pessoa_edit'),
    
    path('pessoa/<uuid:pessoa_id>/ativo/novo/', views.ativo_select_type, name='ativo_select_type'),
    path('pessoa/<uuid:pessoa_id>/ativo/novo/<str:tipo>/', views.ativo_create, name='ativo_create'),
    path('ativo/<uuid:ativo_id>/editar/', views.ativo_edit, name='ativo_edit'),
    path('imovel/<uuid:imovel_id>/', views.imovel_detail, name='imovel_detail'),
    
    # Anexos/Imagens
    path('anexo/<str:model_name>/<uuid:object_id>/adicionar/', views.anexo_adicionar, name='anexo_adicionar'),
    path('anexo/<str:model_name>/<uuid:object_id>/listar/', views.anexo_listar, name='anexo_listar'),
    
    path('simulacao/<uuid:pessoa_id>/', views.simular_inventario_view, name='simular_inventario'),
]
