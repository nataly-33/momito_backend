"""
Comando idempotente: crea permisos, roles y usuarios demo de TUMOMITO S.A.
Puede correrse varias veces sin duplicar datos.

Uso:
    python manage.py setup_demo
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

# ── Permisos del sistema ───────────────────────────────────────────────────
PERMISSIONS_DEF = {
    'usuarios':   ['crear', 'leer', 'actualizar', 'eliminar'],
    'roles':      ['crear', 'leer', 'actualizar', 'eliminar'],
    'productos':  ['crear', 'leer', 'actualizar', 'eliminar'],
    'categorias': ['crear', 'leer', 'actualizar', 'eliminar'],
    'marcas':     ['crear', 'leer', 'actualizar', 'eliminar'],
    'pedidos':    ['crear', 'leer', 'actualizar', 'eliminar', 'aprobar'],
    'ventas':     ['crear', 'leer', 'cancelar'],
    'clientes':   ['crear', 'leer', 'actualizar'],
    'envios':     ['crear', 'leer', 'actualizar', 'entregar'],
    'reportes':   ['crear', 'leer', 'exportar'],
    'descuentos': ['crear', 'leer', 'actualizar', 'eliminar'],
    'dashboard':  ['leer'],
}

# ── Permisos por rol ───────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    'Admin': None,   # None = todos los permisos

    'Empleado': [
        'productos.crear', 'productos.leer', 'productos.actualizar', 'productos.eliminar',
        'categorias.crear', 'categorias.leer', 'categorias.actualizar', 'categorias.eliminar',
        'marcas.crear', 'marcas.leer', 'marcas.actualizar', 'marcas.eliminar',
        'pedidos.crear', 'pedidos.leer', 'pedidos.actualizar', 'pedidos.aprobar',
        'ventas.crear', 'ventas.leer', 'ventas.cancelar',
        'clientes.crear', 'clientes.leer', 'clientes.actualizar',
        'envios.crear', 'envios.leer', 'envios.actualizar', 'envios.entregar',
        'reportes.leer', 'reportes.exportar',
        'dashboard.leer',
    ],

    'Cliente': [
        'pedidos.crear', 'pedidos.leer',
        'ventas.crear', 'ventas.leer',
        'clientes.leer',
        'dashboard.leer',
    ],

    'Delivery': [
        'envios.leer', 'envios.actualizar', 'envios.entregar',
        'pedidos.leer',
    ],
}

# ── Usuarios demo ──────────────────────────────────────────────────────────
DEMO_USERS = [
    {
        'email':    'naty@gmail.com',
        'password': 'naty123',
        'nombre':   'Nataly',
        'apellido': 'Admin',
        'rol':      'Admin',
        'is_staff': True,
        'is_superuser': True,
        'client':   None,
    },
    {
        'email':    'empleado@tumomito.com',
        'password': 'emp123456',
        'nombre':   'Carlos',
        'apellido': 'Empleado',
        'rol':      'Empleado',
        'is_staff': False,
        'is_superuser': False,
        'client':   None,
    },
    {
        'email':    'cliente@supermercado.com',
        'password': 'cli123456',
        'nombre':   'Ana',
        'apellido': 'Cliente',
        'rol':      'Cliente',
        'is_staff': False,
        'is_superuser': False,
        'client': {
            'company_name': 'Supermercado El Sol S.A.',
            'nit':          None,   # None para evitar UniqueViolation con el seeder
            'city':         'Santa Cruz',
            'credit_limit': 50000,
            'client_type':  'vip',
        },
    },
    {
        'email':    'delivery@tumomito.com',
        'password': 'del123456',
        'nombre':   'Pedro',
        'apellido': 'Delivery',
        'rol':      'Delivery',
        'is_staff': False,
        'is_superuser': False,
        'client':   None,
    },
]


class Command(BaseCommand):
    help = 'Crea permisos, roles y usuarios demo de TUMOMITO S.A. (idempotente)'

    def handle(self, *args, **options):
        from apps.accounts.models import Permission, Role

        verbosity = options.get('verbosity', 1)

        def log(msg):
            if verbosity > 0:
                self.stdout.write(msg)

        log('=== TUMOMITO S.A. - Setup inicial ===\n')

        # ── 1. Crear permisos ─────────────────────────────────────────────
        all_perms = {}
        new_perm_count = 0
        for modulo, acciones in PERMISSIONS_DEF.items():
            for accion in acciones:
                codigo = f'{modulo}.{accion}'
                perm, created = Permission.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        'nombre':      f'{accion.capitalize()} {modulo}',
                        'descripcion': f'Permite {accion} en el módulo {modulo}',
                        'modulo':      modulo,
                    },
                )
                all_perms[codigo] = perm
                if created:
                    new_perm_count += 1

        total_perms = len(all_perms)
        log(f'  OK {total_perms} permisos disponibles ({new_perm_count} nuevos creados)')

        # ── 2. Crear roles y asignar permisos ────────────────────────────
        for rol_nombre, codigos in ROLE_PERMISSIONS.items():
            role, created = Role.objects.get_or_create(
                nombre=rol_nombre,
                defaults={
                    'descripcion':   f'Rol {rol_nombre} del sistema TUMOMITO',
                    'es_rol_sistema': True,
                },
            )
            tag = 'nuevo' if created else 'existente'

            if codigos is None:
                # Admin: todos los permisos
                perms_to_assign = list(all_perms.values())
            else:
                perms_to_assign = [all_perms[c] for c in codigos if c in all_perms]

            role.permisos.set(perms_to_assign)
            log(f'  OK Rol "{rol_nombre}" ({tag}) - {len(perms_to_assign)} permisos asignados')

        # ── 3. Crear usuarios demo ────────────────────────────────────────
        log('\n  Usuarios de demostración:')
        log('  ' + '-' * 64)

        for ud in DEMO_USERS:
            role = Role.objects.get(nombre=ud['rol'])

            user, created = User.objects.get_or_create(
                email=ud['email'],
                defaults={
                    'nombre':       ud['nombre'],
                    'apellido':     ud['apellido'],
                    'activo':       True,
                    'is_staff':     ud['is_staff'],
                    'is_superuser': ud['is_superuser'],
                    'rol':          role,
                },
            )

            # Actualizar siempre: contraseña, rol y flags
            user.set_password(ud['password'])
            user.rol          = role
            user.is_staff     = ud['is_staff']
            user.is_superuser = ud['is_superuser']
            user.activo       = True
            user.save()

            # Crear perfil de cliente si corresponde
            if ud['client']:
                from apps.customers.models import Client
                if not Client.objects.filter(user=user).exists():
                    Client.objects.create(
                        user=user,
                        company_name=ud['client']['company_name'],
                        nit=ud['client']['nit'],
                        city=ud['client']['city'],
                        credit_limit=ud['client']['credit_limit'],
                        client_type=ud['client']['client_type'],
                    )
                    empresa_info = f"\n                 empresa: {ud['client']['company_name']}"
                else:
                    empresa_info = ''
            else:
                empresa_info = ''

            tag = 'creado' if created else 'actualizado'
            log(
                f'  [OK] {tag:<10} {ud["email"]:<35} password: {ud["password"]:<12} rol: {ud["rol"]}'
                + empresa_info
            )

        log('  ' + '-' * 64)
        log('\nSetup completado exitosamente.')
