from django.core.management.base import BaseCommand
from django.db import connection
import os

class Command(BaseCommand):
    help = 'Apply stored procedures from SQL files'

    def handle(self, *args, **kwargs):
        sql_dir = os.path.join(os.path.dirname(__file__), '../../sql')
        for filename in os.listdir(sql_dir):
            if filename.endswith(".sql"):
                with open(os.path.join(sql_dir, filename), 'r') as file:
                    sql = file.read()
                    with connection.cursor() as cursor:
                        cursor.execute(sql)
                self.stdout.write(self.style.SUCCESS(f"Executed {filename}"))