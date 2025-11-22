from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings 
import json

# ==================== AUTENTICACIÓN ====================

def login_page(request):
    """Renderiza el formulario de login"""
    return render(request, 'api/login.html')


def home_page(request):
    """Renderiza la página de inicio después del login"""
    return render(request, 'api/home.html')


@csrf_exempt
def login_process(request):
    """Maneja el proceso de autenticación"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dni = data.get('dni')
            password = data.get('password')
            
            if dni and password:
                # Simulación de autenticación exitosa
                if dni == "555555" and password == "password":
                    return JsonResponse({
                        'success': True,
                        'message': '¡Login exitoso! Redirigiendo...',
                        'redirect_url': '/api/home/'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'DNI o contraseña incorrectos'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor complete todos los campos'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Error en los datos enviados'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    })


# ==================== CAJA ====================

def caja_page(request):
    """Redirige a la página de captura de foto de caja"""
    return redirect('foto_caja')


def foto_caja_page(request):
    """Renderiza la página para capturar/subir foto en caja"""
    return render(request, 'api/foto_caja.html')


def resumen_caja_page(request):
    """Renderiza la página de resumen de caja con productos detectados"""
    # Obtener productos desde la sesión si existen
    productos = request.session.get('productos_caja', [
        {'id': 1, 'cantidad': 2, 'nombre': 'Item 1', 'precio': 30, 'total': 60},
        {'id': 2, 'cantidad': 5, 'nombre': 'Item 2', 'precio': 20, 'total': 100},
        {'id': 3, 'cantidad': 3, 'nombre': 'Item 3', 'precio': 5.25, 'total': 15.75},
        {'id': 4, 'cantidad': 6, 'nombre': 'Item 4', 'precio': 7, 'total': 42},
    ])
    
    context = {
        'productos': productos
    }
    return render(request, 'api/resumen_caja.html', context)


def compra_confirmada_page(request):
    """Renderiza la página de compra confirmada"""
    return render(request, 'api/compra_confirmada.html')

def registro_cliente_page(request):
    """Renderiza la página de registro de cliente"""
    return render(request, 'api/registro_cliente.html')

@csrf_exempt
def procesar_imagen_caja(request):
    """
    API para procesar la imagen de caja y detectar productos
    Recibe una imagen en base64 y retorna los productos detectados
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            imagen_base64 = data.get('imagen')
            
            if not imagen_base64:
                return JsonResponse({
                    'success': False,
                    'error': 'No se proporcionó ninguna imagen'
                }, status=400)
            
            # TODO: Aquí implementarías tu lógica de reconocimiento de imágenes
            # Por ahora retornamos datos de ejemplo
            productos_detectados = [
                {'id': 1, 'cantidad': 2, 'nombre': 'Item 1', 'precio': 30, 'total': 60},
                {'id': 2, 'cantidad': 5, 'nombre': 'Item 2', 'precio': 20, 'total': 100},
                {'id': 3, 'cantidad': 3, 'nombre': 'Item 3', 'precio': 5.25, 'total': 15.75},
                {'id': 4, 'cantidad': 6, 'nombre': 'Item 4', 'precio': 7, 'total': 42},
            ]
            
            # Guardar productos en la sesión
            request.session['productos_caja'] = productos_detectados
            request.session['imagen_caja'] = imagen_base64
            
            return JsonResponse({
                'success': True,
                'productos': productos_detectados,
                'total': sum(p['total'] for p in productos_detectados)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Error al procesar los datos'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


@csrf_exempt
def confirmar_orden_caja(request):
    """
    API para confirmar la orden de caja
    Recibe los productos finales y procesa la orden
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            productos = data.get('productos', [])
            total = data.get('total', 0)
            
            if not productos:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay productos para confirmar'
                }, status=400)
            
            # TODO: Aquí guardarías la orden en la base de datos
            # Por ahora solo limpiamos la sesión
            request.session.pop('productos_caja', None)
            request.session.pop('imagen_caja', None)
            
            return JsonResponse({
                'success': True,
                'message': 'Orden confirmada exitosamente',
                'orden_id': 12345,  # ID de ejemplo
                'total': total
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Error al procesar los datos'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


# ==================== DEPÓSITO ====================

def deposito_page(request):
    """Página principal de depósito (placeholder)"""
    return HttpResponse("Página de Depósito - En desarrollo")


def foto_deposito_page(request):
    """Página para capturar foto en depósito (placeholder)"""
    return HttpResponse("Página de Foto Depósito - En desarrollo")


def resumen_deposito_page(request):
    """Página de resumen de depósito (placeholder)"""
    return HttpResponse("Página de Resumen Depósito - En desarrollo")


@csrf_exempt
def procesar_imagen_deposito(request):
    """API para procesar imagen de depósito (placeholder)"""
    return JsonResponse({
        'success': False,
        'message': 'Funcionalidad en desarrollo'
    })


@csrf_exempt
def confirmar_inventario_deposito(request):
    """API para confirmar inventario de depósito (placeholder)"""
    return JsonResponse({
        'success': False,
        'message': 'Funcionalidad en desarrollo'
    })
