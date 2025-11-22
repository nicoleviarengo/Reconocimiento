from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings 
import json
import requests

# ==================== URL Backend ====================
BACKEND_URL = getattr(settings, 'BACKEND_API_URL', 'http://localhost:8000')

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
            
            if not dni or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor complete todos los campos'
                })
            
            # ✅ LLAMAR AL BACKEND para autenticación
            response = requests.post(
                f'{BACKEND_URL}/api/home/login/',
                json={'username': dni, 'password': password},
                timeout=10
            )

            if response.status_code == 200:
                backend_data = response.json()
                
                # ✅ Guardar DNI y nombre en sesión
                request.session['user_dni'] = dni
                request.session['user_nombre'] = backend_data.get('usuario', {}).get('nombre', '')
                
                return JsonResponse({
                    'success': True,
                    'message': '¡Login exitoso! Redirigiendo...',
                    'redirect_url': '/api/home/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'DNI o clave incorrectos'
                })
                
        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'success': False,
                'message': f'Error conectando con el servidor: {str(e)}'
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
            user_dni = request.session.get('user_dni', '12345678')
            
            if not imagen_base64:
                return JsonResponse({
                    'success': False,
                    'error': 'No se proporcionó ninguna imagen'
                }, status=400)
            
            # ✅ LLAMAR AL BACKEND - Detectar objetos
            response = requests.post(
                f'{BACKEND_URL}/api/caja/detectarobjetos/',
                files={'image': imagen_base64},
                timeout=30
            )

            if response.status_code == 200:
                productos_detectados = response.json().get('productos', [])
                
                # Guardar productos en la sesión
                request.session['productos_caja'] = productos_detectados
                request.session['imagen_caja'] = imagen_base64
            
                return JsonResponse({
                    'success': True,
                    'productos': productos_detectados,
                    'total': sum(p.get('subtotal', 0) for p in productos_detectados)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al procesar la imagen en el servidor'
                }, status=500)
            
        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'success': False,
                'error': f'Error conectando con el servidor: {str(e)}'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

def historial_deposito_page(request):
    """Renderiza la página de historial de depósito"""
    # Obtener el historial de la sesión
    productos = request.session.get('historial_deposito', [])
    
    # Calcular el total de cantidades
    total_cantidad = sum(p['cantidad'] for p in productos)
    
    context = {
        'productos': productos,
        'total_cantidad': total_cantidad
    }
    
    return render(request, 'api/historial_deposito.html', context)

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
            cliente_dni = data.get('cliente_dni', None)
            user_dni = request.session.get('user_dni', '12345678')
            
            if not productos:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay productos para confirmar'
                }, status=400)
            
            # ✅ LLAMAR AL BACKEND - Confirmar compra
            backend_data = {
                'usuarioDNI': user_dni,
                'productos': productos
            }
            
            if cliente_dni:
                backend_data['clienteDNI'] = cliente_dni
                endpoint = f'{BACKEND_URL}/api/caja/confirmarcompra/'
            else:
                endpoint = f'{BACKEND_URL}/api/caja/confirmarsincliente/'
            
            response = requests.post(
                endpoint,
                json=backend_data,
                timeout=10
            )
            
            if response.status_code == 200:
                # Limpiar sesión
                request.session.pop('productos_caja', None)
                request.session.pop('imagen_caja', None)
                
                backend_response = response.json()
                return JsonResponse({
                    'success': True,
                    'message': 'Orden confirmada exitosamente',
                    'orden_id': backend_response.get('venta_id'),
                    'total': backend_response.get('total')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al confirmar la orden en el servidor'
                }, status=500)
            
        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'success': False,
                'error': f'Error conectando con el servidor: {str(e)}'
            }, status=500)
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
    return render(request, 'api/deposito.html')


def foto_deposito_page(request):
    return render(request, 'api/foto_deposito.html')


def resumen_deposito_page(request):
    # Obtener productos desde la sesión si existen
    productos = request.session.get('productos_deposito', [
        {'id': 1, 'cantidad': 12, 'nombre': 'Item 1'},
        {'id': 2, 'cantidad': 25, 'nombre': 'Item 2'},
        {'id': 3, 'cantidad': 33, 'nombre': 'Item 3'},
        {'id': 4, 'cantidad': 9, 'nombre': 'Item 4'},
    ])
    
    context = {
        'productos': productos
    }
    return render(request, 'api/resumen_deposito.html', context)

def deposito_confirmada_page(request):
    return render(request, 'api/deposito_confirmada.html')

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

