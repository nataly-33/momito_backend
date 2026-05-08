from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.db import transaction
from django.conf import settings
from decimal import Decimal
from django.http import HttpResponse
from django.views import View

from .models import Pedido, DetallePedido, Pago, MetodoPago, HistorialEstadoPedido, Envio, ESTADOS_ENVIO
from .serializers import (
    PedidoListSerializer, PedidoDetailSerializer, MetodoPagoSerializer,
    CheckoutSerializer, CambiarEstadoPedidoSerializer, EnvioListSerializer,
    EnvioDetailSerializer
)
from apps.core.permissions import IsAdminUser, IsEmpleadoOrAdmin
from apps.cart.models import Carrito
from apps.products.models import StockPrenda


class MetodoPagoViewSet(viewsets.ReadOnlyModelViewSet):
    """Listar métodos de pago disponibles"""
    queryset = MetodoPago.objects.filter(activo=True, deleted_at__isnull=True)
    serializer_class = MetodoPagoSerializer
    permission_classes = [IsAuthenticated]


class PedidoViewSet(viewsets.ModelViewSet):
    """CRUD de pedidos"""
    serializer_class = PedidoListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        if hasattr(user, 'rol') and user.rol and user.rol.nombre in ['Admin', 'Empleado']:
            qs = Pedido.objects.filter(deleted_at__isnull=True).select_related(
                'usuario', 'client'
            )
        else:
            qs = Pedido.objects.filter(
                usuario=user, deleted_at__isnull=True
            ).select_related('usuario', 'client')

        # Filtro por estado
        estado = params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        # Filtro por fechas
        fecha_inicio = params.get('fecha_inicio')
        fecha_fin = params.get('fecha_fin')
        if fecha_inicio:
            qs = qs.filter(created_at__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(created_at__date__lte=fecha_fin)

        # Búsqueda por número de pedido o empresa
        search = params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(numero_pedido__icontains=search) |
                Q(client__company_name__icontains=search) |
                Q(usuario__nombre__icontains=search) |
                Q(usuario__apellido__icontains=search)
            )

        return qs.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PedidoDetailSerializer
        return PedidoListSerializer
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Procesar checkout y crear pedido"""
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        usuario = request.user
        direccion_envio = serializer.validated_data.get('direccion_envio_id')  # puede ser None en B2B
        metodo_pago_codigo = serializer.validated_data['metodo_pago']
        notas_cliente = serializer.validated_data.get('notas_cliente', '')
        
        # Obtener carrito del usuario
        try:
            carrito = Carrito.objects.get(usuario=usuario)
        except Carrito.DoesNotExist:
            return Response(
                {'error': 'No tienes items en el carrito'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el carrito tenga items
        items = carrito.items.filter(deleted_at__isnull=True)
        if not items.exists():
            return Response(
                {'error': 'El carrito está vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar stock y calcular totales
        subtotal = Decimal('0.00')
        items_invalidos = []
        
        for item in items:
            # Verificar stock: B2B usa prenda.stock directo; B2C usa StockPrenda por talla
            if item.talla:
                stock_obj = StockPrenda.objects.filter(
                    prenda=item.prenda, talla=item.talla
                ).first()
                disponible = stock_obj.cantidad if stock_obj else 0
            else:
                disponible = item.prenda.stock

            if disponible < item.cantidad:
                items_invalidos.append({
                    'prenda': item.prenda.nombre,
                    'solicitado': item.cantidad,
                    'disponible': disponible,
                })

            subtotal += item.subtotal
        
        if items_invalidos:
            return Response({
                'error': 'Stock insuficiente para algunos productos',
                'items_invalidos': items_invalidos
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular totales
        descuento = Decimal('0.00')  # TODO: Aplicar descuentos
        costo_envio = Decimal('10.00')  # TODO: Calcular costo de envío
        total = subtotal - descuento + costo_envio
        
        # Obtener método de pago
        try:
            metodo_pago = MetodoPago.objects.get(codigo=metodo_pago_codigo, activo=True)
        except MetodoPago.DoesNotExist:
            return Response(
                {'error': 'Método de pago no válido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener perfil B2B del usuario si existe
        client_profile = getattr(usuario, 'client_profile', None)

        # Crear pedido en una transacción
        with transaction.atomic():
            pedido = Pedido.objects.create(
                usuario=usuario,
                client=client_profile,
                direccion_envio=direccion_envio,
                subtotal=subtotal,
                descuento=descuento,
                costo_envio=costo_envio,
                total=total,
                estado='pendiente',
                payment_method=metodo_pago_codigo if metodo_pago_codigo in ['transferencia', 'credito', 'efectivo', 'stripe'] else 'transferencia',
                notas_cliente=notas_cliente,
            )

            # Crear detalles y reducir stock
            for item in items:
                DetallePedido.objects.create(
                    pedido=pedido,
                    prenda=item.prenda,
                    talla=item.talla if item.talla else None,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                )

                # Reducir stock según tipo de producto
                if item.talla:
                    stock_obj = StockPrenda.objects.filter(
                        prenda=item.prenda, talla=item.talla
                    ).first()
                    if stock_obj:
                        stock_obj.reducir_stock(item.cantidad)
                else:
                    # Stock directo en prenda (B2B)
                    item.prenda.stock = max(0, item.prenda.stock - item.cantidad)
                    item.prenda.save(update_fields=['stock'])
            
            # Procesar pago según el método
            pago = Pago.objects.create(
                pedido=pedido,
                metodo_pago=metodo_pago,
                monto=total,
                estado='pendiente'
            )
            
            if metodo_pago_codigo == 'efectivo':
                # Efectivo: pedido queda pendiente de pago
                pass
            
            elif metodo_pago_codigo == 'billetera':
                # Descontar de billetera
                usuario.saldo_billetera -= total
                usuario.save()
                
                pago.estado = 'completado'
                pago.transaction_id = f'WALLET-{pedido.numero_pedido}'
                pago.save()
                
                pedido.cambiar_estado('pago_recibido', usuario, 'Pago con billetera virtual')
            
            elif metodo_pago_codigo == 'tarjeta':
                # Stripe
                from .services.stripe_service import StripeService
                
                payment_method_id = serializer.validated_data.get('payment_method_id')
                
                stripe_result = StripeService.crear_payment_intent(
                    monto=total,
                    moneda='usd',
                    metadata={
                        'pedido_id': str(pedido.id),
                        'numero_pedido': pedido.numero_pedido
                    }
                )
                
                if stripe_result['success']:
                    pago.stripe_payment_intent_id = stripe_result['payment_intent']['id']
                    pago.estado = 'procesando'
                    pago.response_data = {'payment_intent': stripe_result['payment_intent']}
                    pago.save()
                else:
                    raise Exception(f"Error procesando pago: {stripe_result.get('error')}")
            
            elif metodo_pago_codigo == 'paypal':
                # PayPal
                from .services.paypal_service import PayPalService
                
                paypal_order_id = serializer.validated_data.get('paypal_order_id')
                
                paypal_service = PayPalService()
                capture_result = paypal_service.capturar_orden(paypal_order_id)
                
                if capture_result['success'] and capture_result['status'] == 'COMPLETED':
                    pago.paypal_order_id = paypal_order_id
                    pago.transaction_id = paypal_order_id
                    pago.estado = 'completado'
                    pago.response_data = capture_result
                    pago.save()
                    
                    pedido.cambiar_estado('pago_recibido', usuario, 'Pago con PayPal')
                else:
                    raise Exception(f"Error procesando pago PayPal: {capture_result.get('error')}")
            
            # Limpiar carrito
            carrito.limpiar()
        
        # Retornar pedido creado
        pedido_serializer = PedidoDetailSerializer(pedido)
        return Response({
            'message': 'Pedido creado exitosamente',
            'pedido': pedido_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar un pedido"""
        pedido = self.get_object()
        
        # Verificar que el usuario sea el dueño o admin
        if pedido.usuario != request.user and not request.user.tiene_permiso('pedidos.actualizar'):
            return Response(
                {'error': 'No tienes permisos para cancelar este pedido'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verificar que se pueda cancelar
        if not pedido.puede_cancelar:
            return Response(
                {'error': f'No se puede cancelar un pedido en estado "{pedido.get_estado_display()}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Devolver stock
            for detalle in pedido.detalles.all():
                stock = StockPrenda.objects.get(
                    prenda=detalle.prenda,
                    talla=detalle.talla
                )
                stock.aumentar_stock(detalle.cantidad)
            
            # Si el pago fue con billetera, reembolsar
            pago_billetera = pedido.pagos.filter(
                metodo_pago__codigo='billetera',
                estado='completado'
            ).first()
            
            if pago_billetera:
                pedido.usuario.saldo_billetera += pago_billetera.monto
                pedido.usuario.save()
            
            # Cambiar estado
            pedido.cambiar_estado('cancelado', request.user, 'Cancelado por el usuario')
        
        serializer = self.get_serializer(pedido)
        return Response({
            'message': 'Pedido cancelado exitosamente',
            'pedido': serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsEmpleadoOrAdmin])
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado del pedido (Admin/Empleado)"""
        pedido = self.get_object()
        
        serializer = CambiarEstadoPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nuevo_estado = serializer.validated_data['nuevo_estado']
        notas = serializer.validated_data.get('notas', '')
        
        pedido.cambiar_estado(nuevo_estado, request.user, notas)
        
        pedido_serializer = PedidoDetailSerializer(pedido)
        return Response({
            'message': 'Estado actualizado exitosamente',
            'pedido': pedido_serializer.data
        })
    
class StripeWebhookView(View):
    """Webhook para recibir eventos de Stripe"""

    @method_decorator(csrf_exempt, name='dispatch')
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        from .services.stripe_service import StripeService

        result = StripeService.construir_evento_webhook(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )

        if not result['success']:
            return HttpResponse(status=400)

        event = result['event']

        # Manejar diferentes tipos de eventos
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self._handle_payment_success(payment_intent)

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            self._handle_payment_failed(payment_intent)

        return HttpResponse(status=200)

    def _handle_payment_success(self, payment_intent):
        """Manejar pago exitoso"""
        payment_intent_id = payment_intent['id']

        try:
            pago = Pago.objects.get(stripe_payment_intent_id=payment_intent_id)

            with transaction.atomic():
                # Actualizar pago
                pago.estado = 'completado'
                pago.transaction_id = payment_intent_id
                pago.response_data = payment_intent
                pago.save()

                # Actualizar pedido
                pedido = pago.pedido
                if pedido.estado == 'pendiente':
                    pedido.cambiar_estado('pago_recibido', notas='Pago completado via Stripe')

            print(f"✅ Pago exitoso procesado: {pago.id}")

        except Pago.DoesNotExist:
            print(f"⚠️ Pago no encontrado para Payment Intent: {payment_intent_id}")

    def _handle_payment_failed(self, payment_intent):
        """Manejar pago fallido"""
        payment_intent_id = payment_intent['id']

        try:
            pago = Pago.objects.get(stripe_payment_intent_id=payment_intent_id)

            # Actualizar pago
            pago.estado = 'fallido'
            pago.response_data = payment_intent
            pago.notas = payment_intent.get('last_payment_error', {}).get('message', 'Pago fallido')
            pago.save()

            print(f"❌ Pago fallido: {pago.id}")

        except Pago.DoesNotExist:
            print(f"⚠️ Pago no encontrado para Payment Intent: {payment_intent_id}")


class EnvioViewSet(viewsets.ModelViewSet):
    """CRUD de envíos"""
    serializer_class = EnvioListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return Envio.objects.filter(deleted_at__isnull=True).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EnvioDetailSerializer
        return EnvioListSerializer
    
    def perform_create(self, serializer):
        """Crear envío para un pedido"""
        pedido_id = self.request.data.get('pedido_id')
        
        try:
            pedido = Pedido.objects.get(id=pedido_id, deleted_at__isnull=True)
        except Pedido.DoesNotExist:
            raise Response({'error': 'Pedido no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar que el pedido no tenga ya un envío
        if Envio.objects.filter(pedido=pedido, deleted_at__isnull=True).exists():
            raise Response(
                {'error': 'Este pedido ya tiene un envío asignado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(pedido=pedido)
    
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado del envío"""
        envio = self.get_object()
        
        nuevo_estado = request.data.get('nuevo_estado')
        if nuevo_estado not in dict(ESTADOS_ENVIO):
            return Response(
                {'error': 'Estado de envío inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        envio.estado = nuevo_estado
        
        # Actualizar fechas según el estado
        from django.utils import timezone
        
        if nuevo_estado == 'enviado':
            envio.fecha_envio = timezone.now()
        elif nuevo_estado == 'entregado':
            envio.fecha_entrega_real = timezone.now()
            # Actualizar estado del pedido
            envio.pedido.cambiar_estado('entregado', request.user, 'Envío entregado')
        elif nuevo_estado == 'cancelado':
            envio.pedido.cambiar_estado('cancelado', request.user, 'Envío cancelado')
        
        envio.save()
        
        serializer = EnvioDetailSerializer(envio)
        return Response({
            'message': 'Estado del envío actualizado',
            'envio': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def asignar_delivery(self, request, pk=None):
        """Asignar un delivery al envío"""
        envio = self.get_object()
        
        delivery_id = request.data.get('delivery_id')
        if not delivery_id:
            return Response(
                {'error': 'delivery_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import User
            delivery = User.objects.get(
                id=delivery_id,
                rol__nombre='Delivery',
                deleted_at__isnull=True
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'Delivery no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        envio.asignado_a = delivery
        envio.save()
        
        serializer = EnvioDetailSerializer(envio)
        return Response({
            'message': 'Delivery asignado exitosamente',
            'envio': serializer.data
        })
