import pandas as pd


def import_static_csv():
    df = pd.read_csv('api/list.csv')  # Give the full or relative path
    # StockList.objects.all().delete()
    # for _, row in df.iterrows():
    #     # StockList.objects.create(
    #         Stock_code=row['Stock_code'],
    #         SN=row['SN'],
    #         Lot_size=row['Lot_size'],
    #         Strike_percentage=row['Strike_percentage'],
    #         Expiry_date=row['Expiry_date'],
    #         status=row.get('status', True)
    #     )

    print("CSV data successfully imported.")