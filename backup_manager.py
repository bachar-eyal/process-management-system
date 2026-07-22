#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import shutil
from datetime import datetime
import zipfile
import json

class BackupManager:
    def __init__(self):
        self.backup_dir = 'backups'
        self.teams_db_path = 'teams.db'
        self.teams_dir = 'teams_databases'
        
        # צור תיקיית גיבויים אם לא קיימת
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_backup(self, backup_name=None):
        """יוצר גיבוי מלא של כל המערכת"""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        # צור תיקיית גיבוי
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        
        print(f"🔄 יוצר גיבוי: {backup_name}")
        
        # גבה את מסד הנתונים הראשי
        if os.path.exists(self.teams_db_path):
            shutil.copy2(self.teams_db_path, os.path.join(backup_path, 'teams.db'))
            print(f"✅ נגבה: {self.teams_db_path}")
        
        # גבה את כל מסדי הנתונים של הצוותים
        if os.path.exists(self.teams_dir):
            teams_backup_dir = os.path.join(backup_path, 'teams_databases')
            os.makedirs(teams_backup_dir, exist_ok=True)
            
            for filename in os.listdir(self.teams_dir):
                if filename.endswith('.db'):
                    src_path = os.path.join(self.teams_dir, filename)
                    dst_path = os.path.join(teams_backup_dir, filename)
                    shutil.copy2(src_path, dst_path)
                    print(f"✅ נגבה: {filename}")
        
        # צור קובץ מידע על הגיבוי
        backup_info = {
            'backup_name': backup_name,
            'created_at': datetime.now().isoformat(),
            'teams_count': len([f for f in os.listdir(self.teams_dir) if f.endswith('.db')]) if os.path.exists(self.teams_dir) else 0,
            'total_size_mb': self.get_backup_size(backup_path)
        }
        
        with open(os.path.join(backup_path, 'backup_info.json'), 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        print(f"✅ גיבוי הושלם: {backup_name}")
        print(f"📁 מיקום: {backup_path}")
        print(f"📊 גודל: {backup_info['total_size_mb']:.2f} MB")
        
        return backup_path
    
    def create_compressed_backup(self, backup_name=None):
        """יוצר גיבוי דחוס"""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # צור גיבוי רגיל
        backup_path = self.create_backup(backup_name)
        
        # דחוס את הגיבוי
        zip_path = f"{backup_path}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_path)
                    zipf.write(file_path, arcname)
        
        # מחק את התיקייה הלא דחוסה
        shutil.rmtree(backup_path)
        
        print(f"🗜️  גיבוי דחוס נוצר: {zip_path}")
        return zip_path
    
    def restore_backup(self, backup_path):
        """משחזר גיבוי"""
        print(f"🔄 משחזר גיבוי: {backup_path}")
        
        # בדוק אם זה קובץ ZIP
        if backup_path.endswith('.zip'):
            # חלץ את הקובץ
            extract_path = backup_path[:-4]
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(extract_path)
            backup_path = extract_path
        
        # שחזר את מסד הנתונים הראשי
        teams_backup = os.path.join(backup_path, 'teams.db')
        if os.path.exists(teams_backup):
            shutil.copy2(teams_backup, self.teams_db_path)
            print(f"✅ שוחזר: teams.db")
        
        # שחזר את מסדי הנתונים של הצוותים
        teams_backup_dir = os.path.join(backup_path, 'teams_databases')
        if os.path.exists(teams_backup_dir):
            # מחק את התיקייה הקיימת
            if os.path.exists(self.teams_dir):
                shutil.rmtree(self.teams_dir)
            
            # העתק את התיקייה החדשה
            shutil.copytree(teams_backup_dir, self.teams_dir)
            print(f"✅ שוחזרו מסדי נתונים של צוותים")
        
        print(f"✅ שחזור הושלם!")
    
    def list_backups(self):
        """מציג את כל הגיבויים הזמינים"""
        backups = []
        
        for item in os.listdir(self.backup_dir):
            item_path = os.path.join(self.backup_dir, item)
            
            if os.path.isdir(item_path):
                # גיבוי רגיל
                info_file = os.path.join(item_path, 'backup_info.json')
                if os.path.exists(info_file):
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    backups.append({
                        'name': item,
                        'type': 'folder',
                        'info': info
                    })
            
            elif item.endswith('.zip'):
                # גיבוי דחוס
                size = os.path.getsize(item_path) / (1024 * 1024)  # MB
                backups.append({
                    'name': item,
                    'type': 'zip',
                    'size_mb': size
                })
        
        return backups
    
    def get_backup_size(self, backup_path):
        """מחשב את גודל הגיבוי ב-MB"""
        total_size = 0
        for root, dirs, files in os.walk(backup_path):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)  # MB
    
    def cleanup_old_backups(self, keep_count=5):
        """מנקה גיבויים ישנים, שומר רק על האחרונים"""
        backups = self.list_backups()
        
        # מיין לפי תאריך יצירה
        backups.sort(key=lambda x: x['info']['created_at'] if 'info' in x else '0', reverse=True)
        
        # מחק גיבויים ישנים
        for backup in backups[keep_count:]:
            backup_path = os.path.join(self.backup_dir, backup['name'])
            if os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            elif os.path.isfile(backup_path):
                os.remove(backup_path)
            print(f"🗑️  נמחק גיבוי ישן: {backup['name']}")
        
        print(f"✅ ניקוי גיבויים הושלם. נשארו {min(keep_count, len(backups))} גיבויים")

def main():
    """פונקציה ראשית לבדיקת המערכת"""
    backup_mgr = BackupManager()
    
    print("🔄 מערכת גיבויים מתקדמת")
    print("=" * 50)
    
    # צור גיבוי
    backup_mgr.create_backup()
    
    # הצג גיבויים קיימים
    print("\n📋 גיבויים קיימים:")
    backups = backup_mgr.list_backups()
    for backup in backups:
        if 'info' in backup:
            print(f"📁 {backup['name']} - {backup['info']['teams_count']} צוותים, {backup['info']['total_size_mb']:.2f} MB")
        else:
            print(f"🗜️  {backup['name']} - {backup['size_mb']:.2f} MB")

if __name__ == "__main__":
    main()
