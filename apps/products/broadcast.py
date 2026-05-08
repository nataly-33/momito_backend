"""
Helper para emitir actualizaciones de stock en tiempo real a todos los
clientes WebSocket que estén viendo ese producto.
"""
import logging

logger = logging.getLogger(__name__)


def broadcast_stock_update(prenda):
    """
    Envía el stock actualizado de 'prenda' a todos los clientes conectados
    al canal ws/stock/<slug>/.
    Falla silenciosamente si channels no está disponible.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            f"stock_{prenda.slug}",
            {
                "type": "stock_update",
                "disponible": prenda.stock,
                "min_order_qty": prenda.min_order_qty,
                "tiene_stock": prenda.stock > 0,
            },
        )
    except Exception as exc:
        logger.warning("broadcast_stock_update error para '%s': %s", prenda.slug, exc)
