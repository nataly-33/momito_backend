from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_sql_views'),
    ]

    operations = [
        # Categoria.imagen: URLField → ImageField
        migrations.AlterField(
            model_name='categoria',
            name='imagen',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='images/categorias/',
                verbose_name='Imagen',
            ),
        ),
        # Prenda: nuevo campo imagen
        migrations.AddField(
            model_name='prenda',
            name='imagen',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='images/productos/',
                verbose_name='Imagen principal',
            ),
        ),
    ]
