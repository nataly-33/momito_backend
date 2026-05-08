"""
Crea los MetodoPago necesarios para TUMOMITO: efectivo y tarjeta (Stripe).
Desactiva cualquier otro método que pueda existir (transferencia, credito, paypal, etc.).

Uso:
    python manage.py seed_payment_methods
"""
from django.core.management.base import BaseCommand
from apps.orders.models import MetodoPago

ACTIVE_METHODS = [
    {
        "codigo": "efectivo",
        "nombre": "Efectivo",
        "descripcion": "Pago en efectivo al recibir el pedido.",
        "activo": True,
        "requiere_procesador": False,
    },
    {
        "codigo": "tarjeta",
        "nombre": "Tarjeta de crédito / débito",
        "descripcion": "Pago seguro con tarjeta vía Stripe.",
        "activo": True,
        "requiere_procesador": True,
    },
]

INACTIVE_CODES = ["transferencia", "credito", "paypal", "billetera"]


class Command(BaseCommand):
    help = "Configura los métodos de pago activos (efectivo + tarjeta) y desactiva los demás."

    def handle(self, *args, **kwargs):
        # Crear / activar los métodos necesarios
        for m in ACTIVE_METHODS:
            obj, created = MetodoPago.objects.get_or_create(
                codigo=m["codigo"],
                defaults={k: v for k, v in m.items() if k != "codigo"},
            )
            if not created:
                # Actualizar en caso de que estuviera desactivado
                obj.nombre = m["nombre"]
                obj.descripcion = m["descripcion"]
                obj.activo = True
                obj.requiere_procesador = m["requiere_procesador"]
                obj.save()
            label = self.style.SUCCESS("✔ Creado  ") if created else "  Actualizado"
            self.stdout.write(f"{label}: {m['nombre']}")

        # Desactivar métodos no usados
        deactivated = MetodoPago.objects.filter(
            codigo__in=INACTIVE_CODES, activo=True
        ).update(activo=False)
        if deactivated:
            self.stdout.write(
                self.style.WARNING(f"  Desactivados {deactivated} método(s): {', '.join(INACTIVE_CODES)}")
            )

        self.stdout.write(self.style.SUCCESS("\nMétodos de pago configurados correctamente."))
