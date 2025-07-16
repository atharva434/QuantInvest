from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_expiry'),  # Update with actual app name
    ]

    operations = [
        migrations.AddField(
            model_name='daily_stock_data',
            name='stock',
            field=models.ForeignKey(
                to='api.stock',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                null=True,  # Use null=True for now; you can clean up and make it required later
            ),
        ),
    ]