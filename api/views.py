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
    productos = request.session.get('productos_caja', [])
    total = request.session.get('total_caja', 0)
    
    print("=" * 80)
    print("📦 RESUMEN CAJA - Productos en sesión:")
    print(json.dumps(productos, indent=2, ensure_ascii=False))
    print("=" * 80)
    if not productos:
        print("⚠️ No se han detectado productos")
    
    context = {
        'productos': productos,
        'total': total,
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
    Recibe una imagen como archivo multipart/form-data y retorna los productos detectados
    """
    if request.method == 'POST':
        try:
            # ✅ Obtener archivo de imagen desde FormData
            imagen_file = request.FILES.get('image')
            
            if not imagen_file:
                return JsonResponse({
                    'success': False,
                    'error': 'No se proporcionó ninguna imagen'
                }, status=400)
            
            user_dni = request.session.get('user_dni', '12345678')
            
            # ✅ LLAMAR AL BACKEND - Detectar objetos enviando el archivo
            files = {'image': (imagen_file.name, imagen_file.read(), imagen_file.content_type)}
            
            response = requests.post(
                f'{BACKEND_URL}/api/caja/detectarobjetos/',
                files=files,
                timeout=30
            )

            if response.status_code == 200:
                response_json = response.json()

                print("✅ JSON RECIBIDO:")
                print(json.dumps(response_json, indent=2, ensure_ascii=False))
                print("=" * 80)

                productos_nuevos = response_json.get('productos', [])
                total_nuevos = response_json.get('total', 0)

                # Acumular productos anteriores y nuevos
                productos_anteriores = request.session.get('productos_caja', [])
                total_anterior = request.session.get('total_caja', 0)
                
                # Combinar productos
                productos_acumulados = productos_anteriores + productos_nuevos
                
                total_acumulado = 0
                for p in productos_acumulados:
                    subtotal = p.get('subtotal', 0)
                    # Convertir a float si es string
                    if isinstance(subtotal, str):
                        subtotal = float(subtotal)
                    total_acumulado += subtotal 

                # Guardar productos en la sesión
                request.session['productos_caja'] = productos_acumulados
                request.session['total_caja'] = total_acumulado
            
                return JsonResponse({
                    'success': True,
                    'productos': productos_acumulados,
                    'total': round(total_acumulado, 2)  # Redondear a 2 decimales
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

@csrf_exempt
def guardar_productos_temporales(request):
    """
    Guarda los productos actuales antes de tomar otra foto
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            productos = data.get('productos', [])
            
            # Guardar en sesión
            request.session['productos_caja'] = productos
            
            # Calcular total
            total = 0
            for p in productos:
                subtotal = p.get('subtotal', 0)
                if isinstance(subtotal, str):
                    subtotal = float(subtotal)
                total += subtotal
            
            request.session['total_caja'] = total
            
            print("=" * 80)
            print("💾 PRODUCTOS GUARDADOS TEMPORALMENTE:")
            print(f"Cantidad: {len(productos)}")
            print(f"Total: ${total}")
            print("=" * 80)
            
            return JsonResponse({
                'success': True,
                'message': 'Productos guardados'
            })
            
        except Exception as e:
            print(f"❌ ERROR al guardar: {e}")
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
    """
    API para procesar la imagen de depósito y detectar productos
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
            
            # Decodificar la imagen base64
            import base64
            from io import BytesIO
            
            # Remover el prefijo 'data:image/jpeg;base64,' si existe
            if ',' in imagen_base64:
                imagen_base64 = imagen_base64.split(',')[1]
            
            imagen_bytes = base64.b64decode(imagen_base64)
            
            # URL del microservicio (ajusta según tu configuración)
            MICROSERVICIO_URL = getattr(settings, 'MICROSERVICIO_URL', 'http://localhost:5000')
            
            # Enviar la imagen al microservicio
            files = {'image': ('image.jpg', BytesIO(imagen_bytes), 'image/jpeg')}
            response = requests.post(
                f'{MICROSERVICIO_URL}/predict',
                files=files,
                data={'conf_threshold': 0.25},
                timeout=30
            )
            
            if response.status_code != 200:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al procesar la imagen en el microservicio'
                }, status=500)
            
            resultado = response.json()
            productos_detectados = []
            
            # Convertir el formato del microservicio al formato esperado por el frontend
            for idx, obj in enumerate(resultado.get('objects', []), start=1):
                productos_detectados.append({
                    'id': idx,
                    'cantidad': obj['cantidad'],
                    'nombre': obj['nombre']
                })
            
            # Guardar productos en la sesión
            request.session['productos_deposito'] = productos_detectados
            request.session['imagen_deposito'] = imagen_base64
            
            return JsonResponse({
                'success': True,
                'productos': productos_detectados
            })
            
        except requests.exceptions.RequestException as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al conectar con el microservicio: {str(e)}'
            }, status=500)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Error al procesar los datos'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


@csrf_exempt
def confirmar_inventario_deposito(request):
    """
    API para confirmar inventario de depósito
    Recibe los productos finales y procesa la transferencia
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            productos = data.get('productos', [])
            almacen_origen = data.get('almacen_origen', '')
            almacen_destino = data.get('almacen_destino', '')
            
            if not productos:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay productos para confirmar'
                }, status=400)
            
            # Calcular total de cantidades
            total_cantidad = sum(p['cantidad'] for p in productos)
            
            # Guardar en historial de depósito
            historial = request.session.get('historial_deposito', [])
            
            # Agregar nuevos productos al historial
            for producto in productos:
                historial.append({
                    'id': len(historial) + 1,
                    'cantidad': producto['cantidad'],
                    'nombre': producto['nombre']
                })
            
            request.session['historial_deposito'] = historial
            
            # TODO: Aquí guardarías la transferencia en la base de datos
            # Por ahora solo limpiamos los datos temporales
            request.session.pop('productos_deposito', None)
            request.session.pop('imagen_deposito', None)
            
            return JsonResponse({
                'success': True,
                'message': 'Transferencia confirmada exitosamente',
                'transferencia_id': 12345,  # ID de ejemplo
                'total_productos': len(productos),
                'total_cantidad': total_cantidad
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

