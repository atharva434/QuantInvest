from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
# Create your models here.

# class Client(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     name=models.CharField(max_length=100)
#     app_key = models.CharField(max_length=50)
#     secret_key = models.CharField(max_length=100)
#     session_token = models.CharField(max_length=10,blank=True, null=True)

# class OptionChain(models.Model):
#     stock_code = models.CharField(max_length=20)
#     ltp = models.FloatField()
#     strikeprice = models.IntegerField()

# class StockList(models.Model):
#     Stock_code = models.CharField(max_length=100)
#     SN = models.CharField(max_length=150)
#     Lot_size = models.IntegerField()
#     Strike_percentage = models.FloatField()
#     Expiry_date = models.CharField(max_length=50)
#     status = models.BooleanField(default=True)

class Stock(models.Model):
    EXCHANGE_CODE_CHOICES = [
        ('NSE', 'NSE'),
        ('BSE', 'BSE'),
    ]
    STOCK_TYPE_CHOICES = [
        ('equity', 'Equity'),
        ('index', 'Index'),
    ]
    stock_code = models.CharField(max_length=10)
    stock_name = models.CharField(max_length=100)
    lot_size   = models.IntegerField()
    exchange_code = models.CharField(max_length=4, choices=EXCHANGE_CODE_CHOICES)
    stock_type = models.CharField(max_length=10, choices=STOCK_TYPE_CHOICES)
    fno_exchange_code = models.CharField(max_length=5)
    def __str__(self):
        return self.stock_name


class UserAccounts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    acc_name = models.CharField(max_length=50)
    acc_provider = models.CharField(max_length=50)
    app_key = models.CharField(max_length=50)
    secret_key = models.CharField(max_length=100)
    status = models.BooleanField(default=True)


# class StockExpiry(models.Model):
#     stock_code = models.CharField(max_length=10)
#     month = models.CharField(max_length=11)
#     expiry_date = models.DateField(max_length=20)

class Expiry_Stock(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="stockexpiry")
    month = models.CharField(max_length=11)
    expiry_date = models.DateField(max_length=20)

class StockPrice(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="stock_price")
    date = models.CharField(max_length=10)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()
    timestamp = models.DateTimeField()
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['stock', 'date'], name='unique_stock_date')
        ]

class OptionChainSummary(models.Model):
    stock_expiry = models.ForeignKey(Expiry_Stock, on_delete=models.CASCADE, related_name="chain_summary")
    cmp = models.FloatField()
    atm_strike = models.IntegerField()
    atm_strike_pct = models.IntegerField()
    start_of_strike = models.IntegerField()
    margin_per_lot_sos = models.FloatField()
    datetime = models.DateTimeField()
    class Meta:
        unique_together = ('stock_expiry', 'datetime')

class OptionChain(models.Model):
    RIGHT_CHOICES = [
        ('call', 'Call'),
        ('put', 'Put'),
    ]
    option_chain_summary = models.ForeignKey(OptionChainSummary, on_delete=models.CASCADE, related_name='chain')
    right = models.CharField(max_length=4, choices=RIGHT_CHOICES)
    strike_price = models.IntegerField()
    ltp = models.FloatField()
    best_bid_price = models.FloatField()
    best_bid_quantity = models.IntegerField()
    best_offer_price = models.FloatField()
    best_offer_quantity = models.IntegerField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    prev_close = models.FloatField()
    ltp_perc_change = models.FloatField()
    total_quantity_traded = models.IntegerField()
    spot_price = models.FloatField()
    open_interest = models.IntegerField()
    change_in_open_interest = models.FloatField()
    total_buy_quantity = models.IntegerField()
    total_sell_quantity = models.IntegerField()
    datetime = models.DateTimeField()

class Transactions(models.Model):
    ACTION_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    PRODUCT_CHOICES = [
        ('options', 'Options'),
        ('futures', 'Futures'),
    ]
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="transactions")
    stock_expiry = models.ForeignKey(Expiry_Stock,on_delete=models.CASCADE)
    optionchain = models.ForeignKey(OptionChain,on_delete=models.CASCADE, related_name="transactions")
    order_id = models.CharField(max_length=50)
    action = models.CharField(max_length=5, choices=ACTION_CHOICES)
    order_type = models.CharField(max_length=10)
    stop_loss = models.IntegerField()
    quantity = models.IntegerField()
    validity = models.CharField(max_length=50)
    product_type = models.CharField(max_length=10, choices=PRODUCT_CHOICES)


class DailyStockData(models.Model):
    id = models.AutoField(primary_key=True)
    stock_code = models.CharField(max_length=50)
    date = models.DateField()
    open = models.DecimalField(max_digits=20, decimal_places=10)
    high = models.DecimalField(max_digits=20, decimal_places=10)
    low = models.DecimalField(max_digits=20, decimal_places=10)
    close = models.DecimalField(max_digits=20, decimal_places=10)
    volume = models.BigIntegerField()
    expiry = models.DateField(null=True, blank=True)



class Daily_Stock_Data(models.Model):
    date = models.DateField()
    open = models.DecimalField(max_digits=20, decimal_places=10)
    high = models.DecimalField(max_digits=20, decimal_places=10)
    low = models.DecimalField(max_digits=20, decimal_places=10)
    close = models.DecimalField(max_digits=20, decimal_places=10)
    volume = models.BigIntegerField()
    expiry = models.DateField(null=True, blank=True)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)


class Expiry(models.Model):
    EXPIRY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    month = models.DateField()
    expiry_type = models.CharField(max_length=10, choices=EXPIRY_CHOICES)
    expiry_date = models.DateField(max_length=20)



