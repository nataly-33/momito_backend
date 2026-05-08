from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pedido, Pago


@receiver(post_save, sender=Pedido)
def pedido_creado(sender, instance, created, **kwargs):
    pass  # log eliminado (demasiado verbose en seeder)


@receiver(post_save, sender=Pago)
def pago_procesado(sender, instance, created, **kwargs):
    """Signal cuando se procesa un pago"""
    if created:
        print(f"[Pago] Registrado: {instance.id} - Metodo: {instance.metodo_pago.nombre}")