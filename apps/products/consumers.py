import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class StockConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer que transmite el stock en tiempo real de un producto.
    URL: ws://host/ws/stock/<slug>/
    """

    async def connect(self):
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        self.group_name = f"stock_{self.slug}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Enviar stock actual al conectarse
        data = await self.get_stock(self.slug)
        await self.send(json.dumps({"type": "stock_update", **data}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # El cliente puede pedir un refresh enviando cualquier mensaje
        data = await self.get_stock(self.slug)
        await self.send(json.dumps({"type": "stock_update", **data}))

    # --- Handler para mensajes del channel layer (broadcast desde views) ---
    async def stock_update(self, event):
        await self.send(json.dumps({
            "type": "stock_update",
            "disponible": event["disponible"],
            "min_order_qty": event["min_order_qty"],
            "tiene_stock": event["tiene_stock"],
        }))

    @database_sync_to_async
    def get_stock(self, slug):
        from apps.products.models import Prenda
        try:
            p = Prenda.objects.get(slug=slug, activa=True, deleted_at__isnull=True)
            return {
                "disponible": p.stock,
                "min_order_qty": p.min_order_qty,
                "tiene_stock": p.stock > 0,
            }
        except Prenda.DoesNotExist:
            return {"disponible": 0, "min_order_qty": 1, "tiene_stock": False}
