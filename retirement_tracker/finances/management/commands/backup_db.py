#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import shutil
import datetime
import subprocess as sp
import shlex
import json

# Other Imports
from django.core.management.base import BaseCommand, CommandError
from retirement_tracker.settings import DATABASES

# Defined Functions:
#   backup_db - copies the database to the input directory


class Command(BaseCommand):
    help = 'Creates a backup of the database at the called point in time to a specified directory'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=Path, help='Directory to store backup copy.')
        parser.add_argument('--dump_name', type=str, default='dump.json',
                            help='Filename for old db. Defaults to dump.json')
        parser.add_argument('--new_name',
                            type=str,
                            help='Optional new name for copy of database.\
                                  If not entered, name is bu_<month>_<day>_<year>.json')

    def handle(self, *args, **options):
        if 'dump_name' in options:
            dump_name = options['dump_name']
        else:
            dump_name = 'dump.json'

        bu_time = datetime.datetime.now()
        cmd = shlex.split(f'python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2')
        output = sp.check_output(cmd)
        output_json = json.loads(output)

        with open(dump_name, 'w', encoding='utf-8') as fileobj:
            json.dump(output_json, fileobj, ensure_ascii=False, indent=4, sort_keys=True)

        if options['new_name'] is not None:
            dump_name_new = options['new_name']
        else:
            dump_name_new = f'bu_{bu_time.month}_{bu_time.day}_{bu_time.year}.json'
        dir_name = options['directory']

        backup_dir = os.path.join(dir_name, bu_time.strftime('%Y'), bu_time.strftime('%B'))
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except Exception as e:
            print(f"Could not create directory: {e}. \nExiting.")
            return

        try:
            shutil.move(dump_name, os.path.join(backup_dir, dump_name_new))
        except Exception as e:
            print(f"Could not copy database: {e}")
            return

        self.stdout.write(self.style.SUCCESS(f'Successfully copied database at {bu_time}'))
