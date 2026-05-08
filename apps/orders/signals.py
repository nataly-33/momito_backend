from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pedido, Pago


@receiver(post_save, sender=Pedido)
def pedido_creado(sender, instance, created, **kwargs):
    """Signal cuando se crea un pedido"""
    if created:
        print(f"[Pedido] Creado: {instance.numero_pedido} - Total: {instance.total}")


@receiver(post_save, sender=Pago)
def pago_procesado(sender, instance, created, **kwargs):
    """Signal cuando se procesa un pago"""
    if created:
        print(f"[Pago] Registrado: {instance.id} - Metodo: {instance.metodo_pago.nombre}")