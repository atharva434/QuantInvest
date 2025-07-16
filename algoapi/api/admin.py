from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(UserAccounts)
admin.site.register(Expiry_Stock)
admin.site.register(Stock)
admin.site.register(StockPrice)
admin.site.register(OptionChainSummary)
admin.site.register(OptionChain)
admin.site.register(Transactions)
admin.site.register(DailyStockData)
admin.site.register(Daily_Stock_Data)
admin.site.register(Expiry)