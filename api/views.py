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
      # Limpiar sesión SOLO si NO viene de "agregar más productos"
    if not request.GET.get('agregar'):
        request.session.pop('productos_caja', None)
        request.session.pop('total_caja', None)
        print("=" * 80)
        print("🧹 SESIÓN LIMPIADA - Nueva detección")
        print("=" * 80)
    else:
        print("=" * 80)
        print("➕ Modo AGREGAR MÁS - Manteniendo productos anteriores")
        print("=" * 80)
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
                    'error': 'Error, no se han identificado productos en la imagen'
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
def limpiar_sesion_caja(request):
    """
    Limpia todos los datos de sesión relacionados con la caja
    """
    if request.method == 'POST':
        try:
            # Limpiar todos los datos de la sesión de caja
            request.session.pop('productos_caja', None)
            request.session.pop('total_caja', None)
            request.session.pop('imagen_caja', None)
            request.session.pop('clientDNI', None)
            request.session.pop('clientNombre', None)
            request.session.pop('clientTelefono', None)
            
            print("=" * 80)
            print("🧹 SESIÓN LIMPIADA COMPLETAMENTE")
            print("=" * 80)
            
            return JsonResponse({
                'success': True,
                'message': 'Sesión limpiada correctamente'
            })
            
        except Exception as e:
            print(f"❌ ERROR al limpiar sesión: {e}")
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
    # Obtener depósitos seleccionados desde la sesión
    deposito_origen = request.session.get('deposito_origen', {'id': 1, 'nombre': 'Deposito 1'})
    deposito_destino = request.session.get('deposito_destino', {'id': 2, 'nombre': 'Deposito 2'})
    
    context = {
        'deposito_origen': deposito_origen,
        'deposito_destino': deposito_destino
    }
    return render(request, 'api/foto_deposito.html', context)


def resumen_deposito_page(request):
    # Obtener productos desde la sesión si existen
    productos = request.session.get('productos_deposito', [])
    
    # Obtener depósitos seleccionados (ahora son objetos con id y nombre)
    deposito_origen = request.session.get('deposito_origen', {'id': 1, 'nombre': 'Deposito 1'})
    deposito_destino = request.session.get('deposito_destino', {'id': 2, 'nombre': 'Deposito 2'})
    
    context = {
        'productos': productos,
        'deposito_origen': deposito_origen,
        'deposito_destino': deposito_destino,
        'deposito_origen_json': json.dumps(deposito_origen),
        'deposito_destino_json': json.dumps(deposito_destino)
    }
    return render(request, 'api/resumen_deposito.html', context)

def deposito_confirmada_page(request):
    return render(request, 'api/deposito_confirmada.html')

@csrf_exempt
def guardar_seleccion_depositos(request):
    """
    Guarda la selección de depósito origen y destino en la sesión
    Ahora recibe objetos con {id, nombre}
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            deposito_origen = data.get('depositoOrigen')
            deposito_destino = data.get('depositoDestino')
            
            if not deposito_origen or not deposito_destino:
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan datos de depósito origen o destino'
                }, status=400)
            
            # Validar que sean objetos con id y nombre
            if not isinstance(deposito_origen, dict) or not isinstance(deposito_destino, dict):
                return JsonResponse({
                    'success': False,
                    'error': 'Los depósitos deben ser objetos con id y nombre'
                }, status=400)
            
            if 'id' not in deposito_origen or 'nombre' not in deposito_origen:
                return JsonResponse({
                    'success': False,
                    'error': 'El depósito origen debe tener id y nombre'
                }, status=400)
                
            if 'id' not in deposito_destino or 'nombre' not in deposito_destino:
                return JsonResponse({
                    'success': False,
                    'error': 'El depósito destino debe tener id y nombre'
                }, status=400)
            
            # Guardar en sesión como objetos completos
            request.session['deposito_origen'] = deposito_origen
            request.session['deposito_destino'] = deposito_destino
            
            print("=" * 80)
            print("🏢 DEPÓSITOS SELECCIONADOS:")
            print(f"   Origen: {deposito_origen['nombre']} (ID: {deposito_origen['id']})")
            print(f"   Destino: {deposito_destino['nombre']} (ID: {deposito_destino['id']})")
            print("=" * 80)
            
            return JsonResponse({
                'success': True,
                'message': 'Selección guardada correctamente'
            })
            
        except Exception as e:
            print(f"❌ ERROR al guardar selección de depósitos: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

@csrf_exempt
def limpiar_sesion_deposito(request):
    """
    Limpia todos los datos de sesión relacionados con el depósito
    """
    if request.method == 'POST':
        try:
            # Limpiar todos los datos de la sesión de depósito
            request.session.pop('productos_deposito', None)
            request.session.pop('total_deposito', None)
            request.session.pop('imagen_deposito', None)
            request.session.pop('deposito_origen', None)
            request.session.pop('deposito_destino', None)
            
            print("=" * 80)
            print("🧹 DEPÓSITO - SESIÓN LIMPIADA COMPLETAMENTE")
            print("=" * 80)
            
            return JsonResponse({
                'success': True,
                'message': 'Sesión de depósito limpiada correctamente'
            })
            
        except Exception as e:
            print(f"❌ ERROR al limpiar sesión de depósito: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

@csrf_exempt
def guardar_productos_temporales_deposito(request):
    """
    Guarda los productos actuales de depósito antes de tomar otra foto
    Permite acumular productos en múltiples capturas
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            productos = data.get('productos', [])
            
            # Guardar en sesión
            request.session['productos_deposito'] = productos
            
            # Calcular total de cantidades
            total_cantidad = sum(p.get('cantidad', 0) for p in productos)
            request.session['total_deposito'] = total_cantidad
            
            print("=" * 80)
            print("💾 DEPÓSITO - PRODUCTOS GUARDADOS TEMPORALMENTE:")
            print(f"Cantidad de productos: {len(productos)}")
            print(f"Total cantidad: {total_cantidad}")
            for p in productos:
                print(f"  - {p.get('nombre')}: {p.get('cantidad')} unidades")
            print("=" * 80)
            
            return JsonResponse({
                'success': True,
                'message': 'Productos guardados'
            })
            
        except Exception as e:
            print(f"❌ ERROR al guardar productos de depósito: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

@csrf_exempt
def procesar_imagen_deposito(request):
    """
    API para procesar la imagen de depósito y detectar productos
    Recibe una imagen como archivo multipart/form-data y retorna los productos detectados
    NO acumula productos (a diferencia de caja)
    """
    if request.method == 'POST':
        try:
            imagen_file = request.FILES.get('image')
            
            if not imagen_file:
                return JsonResponse({
                    'success': False,
                    'error': 'No se proporcionó ninguna imagen'
                }, status=400)
            
            print("=" * 80)
            print("📸 DEPÓSITO - Procesando imagen")
            print(f"Nombre del archivo: {imagen_file.name}")
            print(f"Content-Type: {imagen_file.content_type}")
            print(f"Tamaño: {imagen_file.size} bytes")
            
            # URL del backend FastAPI
            BACKEND_URL = getattr(settings, 'BACKEND_URL', 'http://localhost:8000')
            
            # Preparar la imagen para el backend
            files = {
                'image': (imagen_file.name, imagen_file.read(), imagen_file.content_type)
            }
            
            # Enviar al backend FastAPI
            print(f"🚀 Enviando imagen al backend: {BACKEND_URL}/api/caja/detectarobjetos/")
            response = requests.post(
                f'{BACKEND_URL}/api/caja/detectarobjetos/',
                files=files,
                timeout=30
            )
            
            print(f"📥 Respuesta del backend: Status {response.status_code}")
            
            if response.status_code != 200:
                return JsonResponse({
                    'success': False,
                    'error': 'Error al procesar la imagen en el backend'
                }, status=500)
            
            response_json = response.json()
            productos_nuevos = response_json.get('productos', [])
            
            print(f"✅ Productos detectados en imagen: {len(productos_nuevos)}")
            
            # ✅ ACUMULAR productos si hay productos anteriores en la sesión
            productos_anteriores = request.session.get('productos_deposito', [])
            print(f"📦 Productos anteriores en sesión: {len(productos_anteriores)}")
            
            # Combinar productos (acumulación)
            productos_acumulados = productos_anteriores + productos_nuevos
            
            # Guardar productos acumulados en sesión
            request.session['productos_deposito'] = productos_acumulados
            
            # Calcular total de cantidades (no precio en depósito)
            total_cantidad = sum(p.get('cantidad', 0) for p in productos_acumulados)
            request.session['total_deposito'] = total_cantidad
            
            print(f"💾 Total productos en sesión: {len(productos_acumulados)} (anteriores: {len(productos_anteriores)} + nuevos: {len(productos_nuevos)})")
            print(f"📊 Total cantidad: {total_cantidad}")
            print("=" * 80)
            
            return JsonResponse({
                'success': True,
                'productos': productos_acumulados,
                'total_cantidad': total_cantidad
            })
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión con backend: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error al conectar con el backend: {str(e)}'
            }, status=500)
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")
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

