from django.urls import path
from api import views

urlpatterns = [
    # === AUTENTICACIÓN ===
    path('login/', views.login_page, name='login'),
    path('login-process/', views.login_process, name='login_process'),
    
    # === HOME ===
    path('home/', views.home_page, name='home'),
    
    # === CAJA ===
    path('caja/', views.caja_page, name='caja'),
    path('caja/foto/', views.foto_caja_page, name='foto_caja'),
    path('caja/resumen/', views.resumen_caja_page, name='resumen_caja'),
    path('caja/procesar-imagen/', views.procesar_imagen_caja, name='procesar_imagen_caja'),
    path('caja/guardar-temporales/', views.guardar_productos_temporales, name='guardar_productos_temporales'),    
    path('caja/confirmar/', views.confirmar_orden_caja, name='confirmar_orden_caja'),
    path('caja/compra-confirmada/', views.compra_confirmada_page, name='compra_confirmada'),
    path('caja/registro-cliente/', views.registro_cliente_page, name='registro_cliente'),
    
    # === DEPÓSITO ===
    path('deposito/', views.deposito_page, name='deposito'),
    path('deposito/foto/', views.foto_deposito_page, name='foto_deposito'),
    path('deposito/resumen/', views.resumen_deposito_page, name='resumen_deposito'),
    path('deposito/confirmada/', views.deposito_confirmada_page, name='deposito_confirmada'),
    path('deposito/historial/', views.historial_deposito_page, name='historial_deposito'),
]

