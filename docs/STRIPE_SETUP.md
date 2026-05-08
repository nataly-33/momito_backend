# Configurar Stripe en TUMOMITO ERP

Esta guía explica cómo obtener las credenciales de Stripe y colocarlas correctamente en el proyecto.

---

## 1. Crear cuenta en Stripe

1. Ve a [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Completa el registro con tu email y contraseña
3. Verifica tu email si te lo pide
4. No es necesario activar la cuenta para usar el modo **test** (pruebas)

---

## 2. Obtener las API Keys (claves)

1. Entra al [Dashboard de Stripe](https://dashboard.stripe.com)
2. En el menú lateral izquierdo ve a **Developers → API keys**
   - URL directa: `https://dashboard.stripe.com/test/apikeys`
3. Verás dos claves en modo **Test** (asegúrate que el toggle "Test mode" esté activo):

| Clave | Empieza con | Para qué sirve |
|---|---|---|
| **Publishable key** | `pX_tXXX_...` | Frontend (pública, va en el `.env` del frontend) |
| **Secret key** | `sX_tXXX_...` | Backend (privada, NUNCA en el frontend) |

4. Copia ambas claves

---

## 3. Configurar el Webhook (para recibir confirmaciones de pago)

El webhook permite que Stripe notifique a tu backend cuando un pago se completa.

### En desarrollo local (usando Stripe CLI)

1. Descarga [Stripe CLI](https://stripe.com/docs/stripe-cli#install)
   - Windows: descarga el `.exe` desde la página de releases de GitHub de stripe-cli
2. Autentícate:
   ```bash
   stripe login
   ```
3. Escucha eventos y reenvíalos a tu backend local:
   ```bash
   stripe listen --forward-to http://localhost:8000/api/orders/webhook/stripe/
   ```
4. La CLI te mostrará tu **webhook secret** temporal, algo como:
   ```
   > Ready! Your webhook signing secret is wXXXX_xxxxxxxxxxxxx
   ```
5. Copia ese `wXXXX_xxx...` — es tu `STRIPE_WEBHOOK_SECRET`

### En producción (servidor real)

1. Ve a [Dashboard → Developers → Webhooks](https://dashboard.stripe.com/test/webhooks)
2. Clic en **Add endpoint**
3. URL del endpoint: `https://tu-dominio.com/api/orders/webhook/stripe/`
4. Selecciona los eventos:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Clic en **Add endpoint**
6. Abre el endpoint creado y copia el **Signing secret** (`whsec_xxx...`)

---

## 4. Colocar las credenciales en los archivos .env

### Backend: `tm_backend/.env`

Abre el archivo y llena estas líneas:

```env
# Stripe
STRIPE_PUBLIC_KEY=pX_tXXX_XXXXXXXXXXXXXXXXXXXXXXXX
STRIPE_SECRET_KEY=sX_tXXX_XXXXXXXXXXXXXXXXXXXXXXXX
STRIPE_WEBHOOK_SECRET=wX_XXXXXXXXXXXXXXXXXXXXXXXX
```

### Frontend: `tm_frontend/.env`

```env
VITE_API_URL=http://localhost:8000/api
VITE_STRIPE_PUBLIC_KEY=pXXX_tXXX_XXXXXXXXXXXXXXXXXXXXXXXX
```

> **Importante:** La `VITE_STRIPE_PUBLIC_KEY` es la misma `pX_tXXXX_...` del backend.
> La `sX_tXXXX_...` (secret key) SOLO va en el backend, NUNCA en el frontend.

---

## 5. Tarjetas de prueba (Test mode)

En modo test usa estas tarjetas para probar pagos:

| Tarjeta | Número | Resultado |
|---|---|---|
| Visa (éxito) | `4242 4242 4242 4242` | Pago aprobado |
| Visa (fallo) | `4000 0000 0000 0002` | Pago declinado |
| Requiere 3D Secure | `4000 0025 0000 3155` | Autenticación requerida |

- **Fecha de vencimiento:** cualquier fecha futura (ej. `12/28`)
- **CVC:** cualquier 3 dígitos (ej. `123`)
- **ZIP:** cualquier 5 dígitos (ej. `12345`)

---

## 6. Verificar que funciona

1. Asegúrate que el backend está corriendo:
   ```bash
   cd tm_backend
   python manage.py runserver
   ```
2. Corre el Stripe CLI en otra terminal (modo test):
   ```bash
   stripe listen --forward-to http://localhost:8000/api/orders/webhook/stripe/
   ```
3. Corre el frontend:
   ```bash
   cd tm_frontend
   npm run dev
   ```
4. Ve a `http://localhost:3000`, inicia sesión, agrega un producto al carrito
5. Ve al checkout, selecciona **Tarjeta**, ingresa la tarjeta de prueba `4242 4242 4242 4242`
6. Confirma el pedido — debería procesarse correctamente

---

## Resumen de archivos modificados

```
tm_backend/.env          ← STRIPE_PUBLIC_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
tm_frontend/.env         ← VITE_STRIPE_PUBLIC_KEY
```

Ambos archivos ya tienen las líneas preparadas; solo debes pegar los valores reales.
