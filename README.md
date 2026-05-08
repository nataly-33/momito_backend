# TUMOMITO ERP — Backend

API REST + WebSocket para el sistema ERP B2B de **TUMOMITO S.A.**, importadora mayorista.  
Construido con Django 4.2, Django REST Framework y Django Channels.

---

## Stack

| Capa | Tecnología |
|---|---|
| Framework | Django 4.2 + Django REST Framework 3.14 |
| Autenticación | JWT (SimpleJWT) — access + refresh tokens |
| Base de datos | PostgreSQL |
| WebSockets | Django Channels 4 + Daphne |
| Pagos | Stripe (tarjeta + 3D Secure) |
| Almacenamiento | AWS S3 (imágenes y archivos) |
| Tareas async | Celery + Redis |
| ML | scikit-learn (predicciones de ventas) |
| PDF / Excel | ReportLab + openpyxl |
| Docs API | drf-spectacular (Swagger / ReDoc) |

---

## Requisitos previos

- Python 3.11+
- PostgreSQL 14+
- Virtualenv activado

---

## Instalación local

```bash
# 1. Entrar al directorio
cd tm_backend

# 2. Crear y activar virtualenv
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# → editar .env con tus credenciales locales

# 5. Aplicar migraciones
python manage.py migrate

# 6. Cargar datos de prueba
python manage.py seed_tumomito
python manage.py seed_payment_methods

# 7. Crear superusuario (admin)
python manage.py createsuperuser

# 8. Iniciar servidor con WebSocket support
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

> Usar **`daphne`** en lugar de `runserver` para que los WebSockets de stock en tiempo real funcionen.

---

## Variables de entorno (.env)

```env
# Django
DEBUG=True
SECRET_KEY=cambia-esta-clave-en-produccion
ALLOWED_HOSTS=localhost,127.0.0.1
ENVIRONMENT=development

# Base de datos (PostgreSQL local)
DATABASE_URL=postgresql://usuario:password@localhost:5432/tumomito_db

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60      # minutos
JWT_REFRESH_TOKEN_LIFETIME=1440   # minutos (24 h)

# Stripe (ver STRIPE_SETUP.md)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS S3 — imágenes (en dev se puede dejar en False)
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1
```

---

## Comandos útiles

```bash
# Migraciones
python manage.py makemigrations
python manage.py migrate

# Seeders
python manage.py seed_tumomito           # productos, clientes y pedidos de prueba
python manage.py seed_payment_methods    # crea efectivo + tarjeta en DB

# Calidad de código
black .
flake8 .

# Tests
pytest

# API Docs (servidor corriendo)
# http://localhost:8000/api/docs/    → Swagger UI
# http://localhost:8000/api/redoc/   → ReDoc
# http://localhost:8000/admin/       → Django Admin
```

---

## Endpoints principales

| Grupo | Prefijo URL |
|---|---|
| Autenticación | `/api/auth/` |
| Productos | `/api/products/` |
| Carrito | `/api/cart/` |
| Pedidos y pagos | `/api/orders/` |
| Clientes | `/api/customers/` |
| Cotizaciones | `/api/quotes/` |
| Reportes / Dashboard | `/api/reports/` |
| AI / Predicciones | `/api/ai/` |
| WebSocket stock (tiempo real) | `ws://host/ws/stock/<slug>/` |

---

## Estructura de apps

```
apps/
├── core/         Modelos base, permisos, autenticación silenciosa
├── accounts/     Usuarios, roles, JWT personalizado
├── products/     Catálogo, inventario, WebSocket de stock
├── cart/         Carrito B2B/B2C con validación min_order_qty
├── orders/       Pedidos, Stripe, webhook, historial de estados
├── customers/    Perfiles de cliente, direcciones, favoritos
├── quotes/       Cotizaciones B2B + exportación PDF
├── reports/      Dashboard ERP con filtros de fecha
└── ai/           Predicciones de ventas con scikit-learn
```

---

## Deploy

Ver la guía completa de despliegue en **[../DEPLOY_GUIDE.md](../DEPLOY_GUIDE.md)**.  
Incluye: Supabase (DB), AWS S3 (imágenes), Render (backend + frontend).

---

## Documentación completa

Ver **[DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)** para:
- Descripción detallada de cada app y sus modelos
- Cómo funciona el flujo de Stripe
- Cómo agregar nuevas apps
- Convenciones de código
