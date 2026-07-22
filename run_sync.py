# -*- coding: utf-8 -*-
import sys
import os

# שנה לתיקייה הנכונה
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# הרץ את הסקריפט
exec(open('sync_db_structure.py', encoding='utf-8').read())

