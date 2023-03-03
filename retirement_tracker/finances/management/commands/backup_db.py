#!/usr/bin/env python3

# Python Library Imports
from pathlib import Path
import os
import shutil
import datetime
import subprocess as sp
import shlex

# Other Imports
from django.core.management.base import BaseCommand, CommandError
from retirement_tracker.settings import DATABASES

# Defined Functions:
#   backup_db - copies the database to the input directory


class Command(BaseCommand):
    help = 'Copies the database file to a specified directory'

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
        try:
            os.makedirs(options['directory'], exist_ok=True)
        except Exception as e:
            print(f"Could not create directory: {e}. \nExiting.")
            return

        cmd = shlex.split('python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e '
                          f'auth.Permission --indent 2 > {dump_name}')
        output = sp.check_output(cmd, shell=True)

        dir_name = options['directory']

        bu_time = datetime.datetime.now()
        if options['new_name'] is not None:
            dump_name_new = options['new_name']
        else:
            dump_name_new = f'bu_{bu_time.month}_{bu_time.day}_{bu_time.year}.json'

        print(f"dump_name: {dump_name}")
        print(f"dump_name_new: {dump_name_new}")
        try:
            shutil.move(dump_name, os.path.join(dir_name, dump_name_new))
        except Exception as e:
            print(f"Could not copy database: {e}")
            return

        self.stdout.write(self.style.SUCCESS(f'Successfully copied database at {bu_time}'))
