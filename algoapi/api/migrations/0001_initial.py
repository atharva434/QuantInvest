# Generated by Django 4.2.20 on 2025-05-19 06:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Daily_Stock_Data',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_code', models.CharField(max_length=50)),
                ('date', models.DateField()),
                ('open', models.DecimalField(decimal_places=10, max_digits=20)),
                ('high', models.DecimalField(decimal_places=10, max_digits=20)),
                ('low', models.DecimalField(decimal_places=10, max_digits=20)),
                ('close', models.DecimalField(decimal_places=10, max_digits=20)),
                ('volume', models.BigIntegerField()),
                ('expiry', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DailyStockData',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('stock_code', models.CharField(max_length=50)),
                ('date', models.DateField()),
                ('open', models.DecimalField(decimal_places=10, max_digits=20)),
                ('high', models.DecimalField(decimal_places=10, max_digits=20)),
                ('low', models.DecimalField(decimal_places=10, max_digits=20)),
                ('close', models.DecimalField(decimal_places=10, max_digits=20)),
                ('volume', models.BigIntegerField()),
                ('expiry', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Expiry_Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.CharField(max_length=11)),
                ('expiry_date', models.DateField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='OptionChain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('right', models.CharField(choices=[('call', 'Call'), ('put', 'Put')], max_length=4)),
                ('strike_price', models.IntegerField()),
                ('ltp', models.FloatField()),
                ('best_bid_price', models.FloatField()),
                ('best_bid_quantity', models.IntegerField()),
                ('best_offer_price', models.FloatField()),
                ('best_offer_quantity', models.IntegerField()),
                ('open', models.FloatField()),
                ('high', models.FloatField()),
                ('low', models.FloatField()),
                ('prev_close', models.FloatField()),
                ('ltp_perc_change', models.FloatField()),
                ('total_quantity_traded', models.IntegerField()),
                ('spot_price', models.FloatField()),
                ('open_interest', models.IntegerField()),
                ('change_in_open_interest', models.FloatField()),
                ('total_buy_quantity', models.IntegerField()),
                ('total_sell_quantity', models.IntegerField()),
                ('datetime', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_code', models.CharField(max_length=10)),
                ('stock_name', models.CharField(max_length=100)),
                ('lot_size', models.IntegerField()),
                ('exchange_code', models.CharField(choices=[('NSE', 'NSE'), ('BSE', 'BSE')], max_length=4)),
                ('stock_type', models.CharField(choices=[('equity', 'Equity'), ('index', 'Index')], max_length=10)),
                ('fno_exchange_code', models.CharField(max_length=5)),
            ],
        ),
        migrations.CreateModel(
            name='UserAccounts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acc_name', models.CharField(max_length=50)),
                ('acc_provider', models.CharField(max_length=50)),
                ('app_key', models.CharField(max_length=50)),
                ('secret_key', models.CharField(max_length=100)),
                ('status', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clients', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Transactions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.CharField(max_length=50)),
                ('action', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=5)),
                ('order_type', models.CharField(max_length=10)),
                ('stop_loss', models.IntegerField()),
                ('quantity', models.IntegerField()),
                ('validity', models.CharField(max_length=50)),
                ('product_type', models.CharField(choices=[('options', 'Options'), ('futures', 'Futures')], max_length=10)),
                ('optionchain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='api.optionchain')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='api.stock')),
                ('stock_expiry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.expiry_stock')),
            ],
        ),
        migrations.CreateModel(
            name='StockPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.CharField(max_length=10)),
                ('open', models.FloatField()),
                ('high', models.FloatField()),
                ('low', models.FloatField()),
                ('close', models.FloatField()),
                ('volume', models.FloatField()),
                ('timestamp', models.DateTimeField()),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_price', to='api.stock')),
            ],
        ),
        migrations.CreateModel(
            name='OptionChainSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cmp', models.FloatField()),
                ('atm_strike', models.IntegerField()),
                ('atm_strike_pct', models.IntegerField()),
                ('start_of_strike', models.IntegerField()),
                ('margin_per_lot_sos', models.FloatField()),
                ('datetime', models.DateTimeField()),
                ('stock_expiry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chain_summary', to='api.expiry_stock')),
            ],
        ),
        migrations.AddField(
            model_name='optionchain',
            name='option_chain_summary',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chain', to='api.optionchainsummary'),
        ),
        migrations.AddField(
            model_name='expiry_stock',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stockexpiry', to='api.stock'),
        ),
        migrations.AddConstraint(
            model_name='stockprice',
            constraint=models.UniqueConstraint(fields=('stock', 'date'), name='unique_stock_date'),
        ),
        migrations.AlterUniqueTogether(
            name='optionchainsummary',
            unique_together={('stock_expiry', 'datetime')},
        ),
    ]
