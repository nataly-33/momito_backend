"""
Migración: crea vistas SQL para el dashboard TUMOMITO
Tablas reales:
  - prenda (productos)
  - categoria (categorías)
  - pedido (pedidos)
  - detalle_pedido (items de pedidos)
  - client (clientes empresa)
"""
from django.db import migrations


SQL_CREATE_VIEWS = """
CREATE OR REPLACE VIEW vw_sales_by_product AS
SELECT
    p.id AS product_id,
    p.code,
    p.nombre AS product_name,
    m.nombre AS brand,
    c.nombre AS category,
    p.stock AS current_stock,
    p.stock_min,
    CASE WHEN p.stock <= p.stock_min THEN 'Bajo' ELSE 'Normal' END AS stock_status,
    COUNT(DISTINCT o.id) AS total_orders,
    COALESCE(SUM(oi.cantidad), 0) AS total_units_sold,
    COALESCE(SUM(oi.subtotal), 0) AS total_revenue
FROM prenda p
LEFT JOIN marca m ON p.marca_id = m.id
LEFT JOIN prenda_categorias pc ON p.id = pc.prenda_id
LEFT JOIN categoria c ON pc.categoria_id = c.id
LEFT JOIN detalle_pedido oi ON oi.prenda_id = p.id
LEFT JOIN pedido o ON oi.pedido_id = o.id
    AND o.estado NOT IN ('cancelado', 'pendiente')
    AND o.deleted_at IS NULL
WHERE p.activa = TRUE AND p.deleted_at IS NULL
GROUP BY p.id, p.code, p.nombre, m.nombre, c.nombre, p.stock, p.stock_min;

CREATE OR REPLACE VIEW vw_orders_by_month AS
SELECT
    DATE_TRUNC('month', created_at) AS month,
    estado AS status,
    COUNT(id) AS total_orders,
    COALESCE(SUM(total), 0) AS total_revenue
FROM pedido
WHERE deleted_at IS NULL
GROUP BY DATE_TRUNC('month', created_at), estado
ORDER BY month DESC;

CREATE OR REPLACE VIEW vw_top_clients AS
SELECT
    cl.id,
    cl.company_name,
    cl.city,
    cl.client_type,
    COUNT(DISTINCT o.id) AS total_orders,
    COALESCE(SUM(o.total), 0) AS total_spent
FROM client cl
LEFT JOIN pedido o ON o.client_id = cl.id
    AND o.estado NOT IN ('cancelado')
    AND o.deleted_at IS NULL
WHERE cl.deleted_at IS NULL
GROUP BY cl.id, cl.company_name, cl.city, cl.client_type
ORDER BY total_spent DESC;
"""

SQL_DROP_VIEWS = """
DROP VIEW IF EXISTS vw_sales_by_product;
DROP VIEW IF EXISTS vw_orders_by_month;
DROP VIEW IF EXISTS vw_top_clients;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_tumomito_b2b_fields'),
        ('orders', '0002_tumomito_b2b_orders'),
        ('customers', '0002_client_model'),
    ]

    operations = [
        migrations.RunSQL(SQL_CREATE_VIEWS, SQL_DROP_VIEWS),
    ]
