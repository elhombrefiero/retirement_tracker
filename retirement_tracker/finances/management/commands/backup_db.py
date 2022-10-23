#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import shutil
import datetime

# Other Imports
from django.core.management.base import BaseCommand, CommandError
from retirement_tracker.settings import DATABASES

# Defined Functions:
#   backup_db - copies the database to the input directory


class Command(BaseCommand):
    help = 'Copies the database file to a specified directory'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=Path)

    def handle(self, *args, **options):
        db_full_path = DATABASES['default']['NAME']
        try:
            os.makedirs(options['directory'], exist_ok=True)
        except Exception as e:
            print(f"Could not create directory: {e}. \nExiting.")
            return

        db_name = os.path.basename(db_full_path)
        dir_name = options['directory']

        bu_time = datetime.datetime.now()

        # Append the timestamp onto the endof the file
        timestamp_for_db = bu_time.strftime('%Y-%m-%d')
        db_name = db_name + '_' + timestamp_for_db

        try:
            shutil.copy(db_full_path, os.path.join(dir_name, db_name))
        except Exception as e:
            print(f"Could not copy database: {e}")
            return

        self.stdout.write(self.style.SUCCESS(f'Successfully copied database at {bu_time}'))
