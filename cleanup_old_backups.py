#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

def cleanup_old_backup_system():
    """מנקה את מערכת הגיבויים הישנה"""
    
    print("🧹 מנקה מערכת גיבויים ישנה...")
    
    # בדוק אם התיקייה קיימת
    if os.path.exists('db_backups'):
        # מנה את הקבצים לפני המחיקה
        files_count = len([f for f in os.listdir('db_backups') if f.endswith('.db')])
        total_size_mb = sum(os.path.getsize(os.path.join('db_backups', f)) 
                           for f in os.listdir('db_backups') if f.endswith('.db')) / (1024 * 1024)
        
        print(f"📊 נמצאו {files_count} קבצי גיבוי ישנים")
        print(f"📊 גודל כולל: {total_size_mb:.2f} MB")
        
        # מחק את התיקייה
        shutil.rmtree('db_backups')
        print("✅ תיקיית db_backups נמחקה בהצלחה!")
        
        print(f"🗑️  שוחררו {total_size_mb:.2f} MB של מקום")
    else:
        print("❌ תיקיית db_backups לא נמצאה")
    
    print("\n✅ ניקוי מערכת הגיבויים הישנה הושלם!")
    print("📁 מערכת הגיבויים החדשה נמצאת ב: backups/")

if __name__ == "__main__":
    cleanup_old_backup_system()
