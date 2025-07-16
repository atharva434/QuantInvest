from datetime import datetime, timedelta
import json, os
from django.conf import settings
from decouple import config

def get_date_range(num_days):
    to_date = datetime.now()
    from_date = to_date - timedelta(days=num_days)
    return from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")




PROGRESS_PATH = os.path.join(settings.BASE_DIR, 'batch_progress.json')

def update_progress(batch, total, done=False):
    data = {
        'batch': batch,
        'total': total,
        'done': done
    }
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(data, f)

def get_progress():
    if not os.path.exists(PROGRESS_PATH):
        return {'batch': 0, 'total': 0, 'done': False}
    with open(PROGRESS_PATH, 'r') as f:
        return json.load(f)
    

def get_atm_per(stock_code, stock_type, right):
    atm_key = "ATM_PER_EQ" if stock_type == 'equity' else "ATM_PER_IND"
    atm_per = config(atm_key, cast=int, default=5)
    if right.upper() == "PUT":
        atm_per = -atm_per
    return atm_per
    