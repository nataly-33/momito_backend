# TUMOMITO Backend — Guía de desarrollo

Esta guía explica la arquitectura, la estructura de directorios, los módulos disponibles y cómo extender el proyecto.

---

## Tabla de contenidos

1. [Estructura de directorios](#1-estructura-de-directorios)
2. [Configuración del proyecto](#2-configuración-del-proyecto)
3. [Apps de Django](#3-apps-de-django)
4. [WebSockets](#4-websockets)
5. [API endpoints completos](#5-api-endpoints-completos)
6. [Autenticación y permisos](#6-autenticación-y-permisos)
7. [Seeders y datos de prueba](#7-seeders-y-datos-de-prueba)
8. [Cómo agregar una nueva app](#8-cómo-agregar-una-nueva-app)
9. [Convenciones de código](#9-convenciones-de-código)

---

## 1. Estructura de directorios

```
tm_backend/
├── apps/                       # Aplicaciones Django
│   ├── accounts/               # Auth, usuarios, roles
│   ├── ai/                     # ML / predicciones de ventas
│   ├── cart/                   # Carrito de compras
│   ├── core/                   # Utilidades compartidas
│   ├── customers/              # Clientes, direcciones, favoritos
│   ├── orders/                 # Pedidos, pagos, envíos
│   ├── products/               # Catálogo, inventario, WebSocket
│   ├── quotes/                 # Cotizaciones B2B
│   └── reports/                # Dashboard ERP, analytics
├── config/                     # Configuración Django
│   ├── settings/
│   │   ├── base.py             # Settings comunes
│   │   ├── development.py      # Overrides para dev
│   │   └── production.py       # Overrides para prod
│   ├── urls.py                 # Routing raíz
│   ├── asgi.py                 # ASGI + Channels (WebSocket)
│   └── wsgi.py                 # WSGI (legacy)
├── models/                     # Modelos ML entrenados (.pkl)
├── static/                     # Archivos estáticos
├── manage.py
├── requirements.txt
└── .env
```

---

## 2. Configuración del proyecto

### Settings

El proyecto usa tres capas de settings:

| Archivo | Cuándo se usa |
|---|---|
| `config/settings/base.py` | Siempre (configuración base) |
| `config/settings/development.py` | `ENVIRONMENT=development` |
| `config/settings/production.py` | `ENVIRONMENT=production` |

### Módulo de entrada ASGI

`config/asgi.py` define `ProtocolTypeRouter` que enruta:
- `http` → Django estándar
- `websocket` → `AuthMiddlewareStack` + `URLRouter` de `apps/products/routing.py`

### Variable de entorno clave

```python
DJANGO_SETTINGS_MODULE = 'config.settings'
```

---

## 3. Apps de Django

### `apps/core`

Utilidades compartidas por todas las demás apps.

| Archivo | Contenido |
|---|---|
| `models.py` | `BaseModel` — abstract con `id (UUID)`, `created_at`, `updated_at`, `deleted_at` (soft-delete), método `soft_delete()` |
| `permissions.py` | `IsAdminUser`, `IsEmpleadoOrAdmin`, `IsOwnerOrAdmin` |
| `authentication.py` | `SilentJWTAuthentication` — ignora tokens expirados en endpoints públicos en vez de devolver 401 |
| `constants.py` | Listas de estados, métodos de pago, tallas, colores |

**Herencia:** todos los modelos del proyecto extienden `BaseModel`.

---

### `apps/accounts`

Autenticación, usuarios y roles.

**Modelos:**
- `Role` — Admin, Empleado, Cliente, Delivery
- `Permission` — permisos por módulo (CRUD)
- `User` — usuario custom (extiende `AbstractBaseUser`); campos extras: `nombre`, `apellido`, `telefono`, `rol`, `codigo_empleado`, `saldo_billetera`
- `LoginAudit` — registro de inicios de sesión

**Endpoints (`/api/auth/`):**
```
POST   /login/           → devuelve access + refresh token
POST   /refresh/         → renueva access token
POST   /register/        → crea usuario + perfil de empresa opcional
GET    /users/me/         → perfil del usuario autenticado
PUT    /users/me/         → actualizar perfil
GET    /users/            → listar usuarios (Admin/Empleado)
GET    /roles/            → listar roles
GET    /permissions/      → listar permisos
```

**Notas:**
- `CustomTokenObtainPairView` extiende el login de SimpleJWT y agrega `rol`, `nombre`, `permisos` en el payload del token.
- El endpoint `/register/` acepta `company_data` para crear un `Client` junto con el usuario en un solo paso.

---

### `apps/products`

Catálogo de productos mayoristas + inventario + WebSocket de stock.

**Modelos:**
- `Categoria`, `Marca` — clasificación de productos
- `Talla` — opcional (solo para B2C con ropa)
- `Prenda` — producto principal; campos B2B: `code`, `unit`, `min_order_qty`, `price_wholesale`, `price_retail`, `stock`, `stock_min`
- `StockPrenda` — stock por talla (B2C)
- `ImagenPrendaURL` — imágenes del producto
- `InventoryMovement` — entradas/salidas/ajustes de inventario

**Endpoints (`/api/products/`):**
```
GET    /prendas/                    → listar (AllowAny, con filtros)
GET    /prendas/<slug>/             → detalle producto
POST   /prendas/                    → crear (staff)
PUT    /prendas/<id>/               → actualizar (staff)
GET    /prendas/<id>/stock/         → ver stock
PUT    /prendas/<id>/stock/         → actualizar stock
GET    /categorias/                 → listar categorías
GET    /marcas/                     → listar marcas
GET    /inventory-movements/        → movimientos de inventario
POST   /inventory-movements/        → registrar movimiento
```

**Filtros disponibles en `/prendas/`:**
`?categorias=id&marca=id&precio_min=N&precio_max=N&destacada=true&es_novedad=true&con_stock=true&search=texto`

**WebSocket:**
```python
# apps/products/consumers.py
ws://host/ws/stock/<slug>/
# Al conectarse devuelve: { type: "stock_update", disponible: N, min_order_qty: N, tiene_stock: bool }
# Recibe broadcast cuando el stock cambia (checkout, movimiento de inventario)
```

```python
# apps/products/broadcast.py — llamar cuando el stock cambia
from apps.products.broadcast import broadcast_stock_update
broadcast_stock_update(prenda_instance)
```

---

### `apps/cart`

Carrito de compras. Soporta flujo B2C (con talla) y B2B (sin talla).

**Modelos:**
- `Carrito` — un carrito por usuario
- `ItemCarrito` — `prenda` + `talla (opcional)` + `cantidad` + `precio_unitario`

**Endpoints (`/api/cart/`):**
```
GET    /mi_carrito/                  → carrito del usuario
POST   /agregar/                     → { prenda, talla?, cantidad }
PUT    /items/<id>/actualizar/       → { cantidad }
DELETE /items/<id>/eliminar/
POST   /limpiar/                     → vacía el carrito
```

**Validaciones:**
- `min_order_qty`: si el producto tiene pedido mínimo mayorista, valida que `cantidad >= min_order_qty`
- Stock B2C: valida contra `StockPrenda.cantidad`
- Stock B2B: valida contra `Prenda.stock`

---

### `apps/orders`

Pedidos, pagos (Stripe), historial de estados, envíos.

**Modelos:**
- `MetodoPago` — efectivo, tarjeta (activos)
- `Pedido` — pedido completo; campos B2B: `client (FK)`, `payment_method`, `metadata (JSON)`
- `DetallePedido` — línea de pedido con snapshot del producto
- `Pago` — registro del pago; campos Stripe: `stripe_payment_intent_id`
- `HistorialEstadoPedido` — log de cambios de estado
- `Envio` — información de envío

**Endpoints (`/api/orders/`):**
```
GET    /pedidos/                    → mis pedidos (admin ve todos)
POST   /pedidos/checkout/           → crear pedido + procesar pago
GET    /pedidos/<id>/               → detalle
POST   /pedidos/<id>/cancelar/      → cancelar pedido
POST   /pedidos/<id>/cambiar_estado/ → cambiar estado (staff)
GET    /metodos-pago/               → listar métodos activos
POST   /webhooks/stripe/            → webhook de Stripe (CSRF exempt)
```

**Flujo checkout con Stripe:**
1. Frontend crea `PaymentMethod` con `stripe.createPaymentMethod()` → `pm_xxx`
2. POST `/checkout/` con `{ metodo_pago: 'tarjeta', payment_method_id: 'pm_xxx', ... }`
3. Backend llama `StripeService.crear_y_confirmar(monto, pm_xxx)` — crea y confirma el PI en un paso
4. Si `pi.status == 'succeeded'` → pedido confirmado inmediatamente
5. Si `pi.status == 'requires_action'` → respuesta incluye `stripe_client_secret` para 3D Secure
6. Frontend llama `stripe.handleCardAction(client_secret)` si es necesario

**Servicio Stripe (`apps/orders/services/stripe_service.py`):**
```python
StripeService.crear_y_confirmar(monto, payment_method_id, moneda='usd', metadata=None)
StripeService.crear_payment_intent(monto, moneda, metadata)
StripeService.crear_refund(payment_intent_id, monto=None)
StripeService.construir_evento_webhook(payload, sig_header, webhook_secret)
```

---

### `apps/customers`

Perfiles de cliente B2B y direcciones.

**Modelos:**
- `Direccion` — dirección de envío guardada del usuario
- `Client` — perfil de empresa (vinculado 1:1 a `User`); campos: `company_name`, `ruc_nit`, `city`, `client_type (vip|regular|nuevo)`
- `Favoritos` — productos favoritos del usuario

**Endpoints (`/api/customers/`):**
```
GET/PUT  /profile/         → perfil del usuario autenticado
GET      /clients/         → listar clientes (staff)
GET/PUT  /clients/<id>/    → perfil empresa del cliente
GET/POST /addresses/       → direcciones del usuario
PUT/DEL  /addresses/<id>/  → actualizar / eliminar dirección
GET/POST /favorites/       → favoritos
```

---

### `apps/quotes`

Cotizaciones B2B generadas por el equipo de ventas de TUMOMITO.

**Modelos:**
- `Quote` — cotización con `numero_cotizacion`, `client`, `seller (FK User)`, `estado (borrador|enviada|aceptada|rechazada|expirada)`, `total`
- `QuoteItem` — línea de cotización con `prenda`, `cantidad`, `precio_unitario`

**Endpoints (`/api/quotes/`):**
```
GET/POST   /quotes/           → listar / crear (staff)
GET/PUT    /quotes/<id>/      → ver / editar
POST       /quotes/<id>/pdf/  → generar PDF (ReportLab)
```

> Las cotizaciones son de uso **interno** para el equipo de TUMOMITO. Los clientes B2B hacen pedidos directamente desde el portal.

---

### `apps/reports`

Dashboard ERP, analytics y reportes. Todos los endpoints aceptan filtros de fecha opcionales.

**Endpoints (`/api/reports/`):**
```
GET /dashboard/         → KPIs: ingresos, pedidos pendientes, stock bajo
GET /sales/             → top 50 productos por ingresos
GET /monthly/           → ventas agrupadas por mes
GET /top-clients/       → top 10 clientes
GET /orders-status/     → distribución por estado
GET /low-stock/         → productos con stock <= stock_min
GET /brands/            → ventas por marca
GET /categories/        → ventas por categoría
GET /recent-activity/   → feed de actividad reciente
```

**Filtros de fecha (todos los endpoints salvo `low-stock`):**
```
?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD
```

---

### `apps/ai`

Predicciones de ventas con scikit-learn.

**Modelos:**
- `MLModel` — registro de modelos entrenados (path al `.pkl`, métricas)
- `PrediccionVentas` — resultado de predicciones guardadas

Los modelos entrenados se almacenan en `models/*.pkl`.

---

## 4. WebSockets

### Configuración

```python
# config/settings/base.py
ASGI_APPLICATION = 'config.asgi.application'
CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
}
# En producción: cambiar a RedisChannelLayer
```

### Consumer de stock

```python
# Conectar: ws://host/ws/stock/<product-slug>/
# Mensajes recibidos por el cliente:
{ "type": "stock_update", "disponible": 45, "min_order_qty": 6, "tiene_stock": true }
```

### Emitir broadcast desde views

```python
from apps.products.broadcast import broadcast_stock_update
# Llamar después de modificar stock (checkout, movimiento de inventario)
broadcast_stock_update(prenda_instance)
```

---

## 5. API endpoints completos

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/api/auth/login/` | No | Login |
| POST | `/api/auth/refresh/` | No | Refresh token |
| POST | `/api/auth/register/` | No | Registro |
| GET | `/api/auth/users/me/` | Sí | Mi perfil |
| GET | `/api/products/prendas/` | No | Catálogo |
| GET | `/api/products/prendas/<slug>/` | No | Detalle producto |
| POST | `/api/products/prendas/` | Staff | Crear producto |
| GET | `/api/cart/mi_carrito/` | Sí | Mi carrito |
| POST | `/api/cart/agregar/` | Sí | Agregar al carrito |
| POST | `/api/orders/pedidos/checkout/` | Sí | Finalizar compra |
| GET | `/api/orders/pedidos/` | Sí | Mis pedidos |
| GET | `/api/orders/metodos-pago/` | Sí | Métodos de pago |
| POST | `/api/orders/webhooks/stripe/` | No* | Webhook Stripe |
| GET | `/api/reports/dashboard/` | Sí | Dashboard KPIs |
| GET | `/api/quotes/quotes/` | Staff | Cotizaciones |
| GET | `/api/docs/` | No | Swagger UI |

*El webhook Stripe está exento de CSRF pero verifica la firma de Stripe.

---

## 6. Autenticación y permisos

### Token JWT

El frontend envía el token en cada request:
```http
Authorization: Bearer <access_token>
```

### Clases de permiso disponibles

```python
from apps.core.permissions import IsAdminUser, IsEmpleadoOrAdmin, IsOwnerOrAdmin
from rest_framework.permissions import IsAuthenticated, AllowAny
```

### Autenticación silenciosa

`SilentJWTAuthentication` (configurada globalmente) devuelve `None` (usuario anónimo) cuando el token es inválido o expirado, en lugar de lanzar 401. Esto permite que los endpoints `AllowAny` funcionen aunque el navegador envíe un token vencido.

---

## 7. Seeders y datos de prueba

```bash
# Datos completos de TUMOMITO (ejecutar una sola vez)
python manage.py seed_tumomito
# → 6 categorías, 3 marcas, 50 productos
# → 30 clientes empresa
# → ~12.000 pedidos (2021-2024)

# Métodos de pago (efectivo + tarjeta)
python manage.py seed_payment_methods
# → Desactiva transferencia, crédito, paypal si existen
```

**Ubicación de los seeders:**
- `apps/products/management/commands/seed_tumomito.py`
- `apps/orders/management/commands/seed_payment_methods.py`

---

## 8. Cómo agregar una nueva app

```bash
# 1. Crear la app dentro de apps/
cd apps
mkdir nueva_app
cd nueva_app
django-admin startapp . 
```

```python
# 2. Registrar en config/settings/base.py
LOCAL_APPS = [
    ...
    'apps.nueva_app',
]
```

```python
# 3. Estructura mínima recomendada
apps/nueva_app/
├── models.py       # extiende BaseModel
├── serializers.py  # DRF serializers
├── views.py        # ViewSets
├── urls.py         # router.register(...)
├── admin.py        # registro en Django admin
└── apps.py
```

```python
# 4. Registrar URLs en config/urls.py
from apps.nueva_app.urls import urlpatterns as nueva_app_urls
urlpatterns += [path('api/nueva_app/', include('apps.nueva_app.urls'))]
```

```bash
# 5. Crear y aplicar migración
python manage.py makemigrations nueva_app
python manage.py migrate
```

---

## 9. Convenciones de código

### Modelos
- Todos extienden `BaseModel` (UUID pk + timestamps + soft-delete)
- Usar `soft_delete()` en lugar de `.delete()` donde sea posible
- Nombres en español para `verbose_name`

### Serializers
- `ListSerializer` (campos mínimos para listados) y `DetailSerializer` (campos completos)
- `CreateUpdateSerializer` para escritura

### Views
- Usar `ViewSet` con `get_permissions()` para permisos por acción
- Usar `get_serializer_class()` para serializer por acción

### Reportes con filtro de fecha
- Usar `_parse_dates(request)` y `_date_filter(start, end, field)` de `apps/reports/tumomito_views.py`

### Errores
- Devolver `Response({'error': str(e)}, status=400)` para errores de usuario
- Dejar que DRF maneje errores de validación (400 automático)
- Loguear errores internos con `logger.error(..., exc_info=True)`
