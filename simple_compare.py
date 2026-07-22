# -*- coding: utf-8 -*-
import sqlite3

db1 = r'teams_databases\צוות בדיקה_20250826_162719.db'
db2 = r'teams_databases\eyal_20251105_104247.db'

def get_cols(db):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('PRAGMA table_info(process_tags)')
    cols = [(col[0], col[1], col[2]) for col in c.fetchall()]
    conn.close()
    return cols

try:
    cols1 = get_cols(db1)
    cols2 = get_cols(db2)
    
    print('צוות בדיקה:')
    for idx, name, typ in cols1:
        print(f'  [{idx}] {name} ({typ})')
    
    print('\neyal:')
    for idx, name, typ in cols2:
        print(f'  [{idx}] {name} ({typ})')
    
    print('\nהבדלים:')
    names1 = {name: (idx, typ) for idx, name, typ in cols1}
    names2 = {name: (idx, typ) for idx, name, typ in cols2}
    
    all_names = set(names1.keys()) | set(names2.keys())
    for name in sorted(all_names):
        if name in names1 and name in names2:
            idx1, typ1 = names1[name]
            idx2, typ2 = names2[name]
            if idx1 != idx2 or typ1 != typ2:
                print(f'  {name}: בדיקה[idx={idx1}, type={typ1}] vs eyal[idx={idx2}, type={typ2}]')
        elif name in names1:
            print(f'  {name}: רק ב-בדיקה')
        else:
            print(f'  {name}: רק ב-eyal')
            
except Exception as e:
    print(f'Error: {e}')

