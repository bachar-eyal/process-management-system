from itertools import count
import sqlite3
import random
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import json
import re
import base64
from io import BytesIO
# # ---- מספר סידורי ו-SKU ----
# serial_number = "432432"
# sku = "2"

def print_signature_on_image(serial_number, sku, tag_id=None):
    # ---- שליפת נתונים מה-DB ----
    from app import get_team_db_path
    db_path = get_team_db_path()
    if not db_path:
        print("[ERROR] No team database path found")
        return
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    data = {}
    
    # אם יש tag_id ספציפי, שלוף את הנתונים שלו קודם
    if tag_id:
        print(f"[DEBUG] Looking for tag_id: {tag_id}")
        c.execute("SELECT serial_number, sku FROM process_tags WHERE tag_id=?", (tag_id,))
        tag_data = c.fetchone()
        if tag_data:
            tag_serial_number, tag_sku = tag_data
            print(f"[DEBUG] Found tag: serial={tag_serial_number}, sku={tag_sku}")
            # עדכן את המשתנים לפי התג הספציפי
            serial_number = tag_serial_number
            sku = tag_sku
        else:
            print(f"[DEBUG] Tag {tag_id} not found, using original values")
    else:
        print(f"[DEBUG] No tag_id provided, using serial={serial_number}, sku={sku}")

    # products - לפי ה-serial_number וה-SKU הנכונים
    c.execute("SELECT * FROM products WHERE serial_number=? AND sku=?", (serial_number, sku))
    products_result = c.fetchall()
    data["products"] = products_result
    
    # אם לא נמצא מוצר עם ה-SKU הספציפי, נסה לפי serial_number בלבד
    if not products_result:
        c.execute("SELECT * FROM products WHERE serial_number=?", (serial_number,))
        data["products"] = c.fetchall()

    # process_tags - אם יש tag_id ספציפי, הביא רק אותו
    if tag_id:
        c.execute("SELECT * FROM process_tags WHERE tag_id=?", (tag_id,))
        data["process_tags"] = c.fetchall()
    else:
        c.execute("SELECT * FROM process_tags WHERE serial_number=? AND sku=?", (serial_number, sku))
        data["process_tags"] = c.fetchall()

    # approved_skus - לפי ה-SKU הנכון
    c.execute("SELECT * FROM approved_skus WHERE sku_code=?", (sku,))
    approved_skus_result = c.fetchall()
    data["approved_skus"] = approved_skus_result
    
    # אם לא נמצא SKU מאושר, נסה להביא את כל ה-SKUs הפעילים
    if not approved_skus_result:
        c.execute("SELECT * FROM approved_skus WHERE is_active=1 LIMIT 1")
        data["approved_skus"] = c.fetchall()

    # team_members - נביא את כל הצוות
    c.execute("SELECT * FROM team_members")
    data["team_members"] = c.fetchall()

    # spare_parts_usage - צריכת חלפים לתג זה
    if tag_id:
        c.execute("""SELECT spu.usage_id, sp.part_number, sp.description, sp.manufacturer, spu.serial_number, spu.date_used
                     FROM spare_parts_usage spu 
                     JOIN spare_parts sp ON spu.part_id = sp.part_id 
                     WHERE spu.tag_id = ? 
                     ORDER BY spu.date_used DESC""", (tag_id,))
        data["spare_parts_usage"] = c.fetchall()
    else:
        # אם אין tag_id, נסה למצוא לפי serial_number ו-sku
        c.execute("""SELECT spu.usage_id, sp.part_number, sp.description, sp.manufacturer, spu.serial_number, spu.date_used
                     FROM spare_parts_usage spu 
                     JOIN spare_parts sp ON spu.part_id = sp.part_id 
                     JOIN process_tags pt ON spu.tag_id = pt.tag_id
                     WHERE pt.serial_number = ? AND pt.sku = ?
                     ORDER BY spu.date_used DESC""", (serial_number, sku))
        data["spare_parts_usage"] = c.fetchall()

    conn.close()

    # ---- שליפת חתימות פר תג מתוך process_tags (אם קיימות) ----
    performer_signature = None
    checker_signature = None
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # בדוק שקיימות עמודות החתימה, ואז שלוף
    c.execute("PRAGMA table_info(process_tags)")
    process_cols_info = c.fetchall()
    process_cols = [col[1] for col in process_cols_info]
    
    # צור מיפוי של שם עמודה לאינדקס
    process_col_index_map = {col[1]: col[0] for col in process_cols_info}
    
    if 'performer_signature' in process_cols and 'checker_signature' in process_cols:
        if tag_id:
            # אם יש tag_id ספציפי, הביא חתימות מהתג הזה
            c.execute(
                "SELECT performer_signature, checker_signature FROM process_tags WHERE tag_id=?",
                (tag_id,)
            )
        else:
            # אחרת, הביא מהתג העדכני ביותר
            c.execute(
                "SELECT performer_signature, checker_signature FROM process_tags "
                "WHERE serial_number=? AND sku=? ORDER BY date_updated DESC LIMIT 1",
                (serial_number, sku)
            )
        row = c.fetchone()
        if row:
            performer_signature, checker_signature = row[0], row[1]
    conn.close()

    # הפיכת הנתונים לרשימה שטוחה עם תמיכה בשמות עמודות
    all_values = []
    all_values_by_name = {}  # מיפוי לפי שם עמודה
    performer_value = None
    checker_value = None
    
    for table, rows in data.items():
        if table == 'process_tags' and rows:
            # עבור process_tags, צור מיפוי גם לפי שם
            for row in rows:
                for idx, value in enumerate(row):
                    all_values.append((f"{table}.{idx}", str(value) if value is not None else ""))
                    # אם יש לנו את שם העמודה, הוסף גם לפי שם ושמור את הערכים של performer ו-checker
                    if idx < len(process_cols):
                        col_name = process_cols[idx]
                        all_values_by_name[f"{table}.{col_name}"] = str(value) if value is not None else ""
                        # שמור את performer ו-checker בנפרד
                        if col_name == 'performer':
                            performer_value = str(value) if value is not None else ""
                        elif col_name == 'checker':
                            checker_value = str(value) if value is not None else ""
        else:
            # לטבלאות אחרות, השתמש באינדקסים
            for row in rows:
                for idx, value in enumerate(row):
                    all_values.append((f"{table}.{idx}", str(value) if value is not None else ""))

    # זיהוי אינדקסי חתימות בפר-תג כדי לא לצייר אותם כמלל
    skip_signature_varnames = set()
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("PRAGMA table_info(process_tags)")
        cols = c.fetchall()  # (cid, name, type, ...)
        perf_sig_idx = next((col[0] for col in cols if col[1] == 'performer_signature'), None)
        check_sig_idx = next((col[0] for col in cols if col[1] == 'checker_signature'), None)
        if perf_sig_idx is not None:
            skip_signature_varnames.add(f"process_tags.{perf_sig_idx}")
        if check_sig_idx is not None:
            skip_signature_varnames.add(f"process_tags.{check_sig_idx}")
        conn.close()
    except Exception:
        pass

    # ---- מיקומים ----
    positions = [
        (1250, 130),  # מס סידורי
        (1250, 105),  # מסחא
        (0, 0), #תקלה מאומתת כן 905,155
        (0, 0), #ננת לא 960,205
        (0, 0),  # פירוט תקלה 1280,315
        (1280, 250),  # פירוט בר תיקון
        (790, 447), #פירוט הליקוי 790,447
        (0, 0),  # חתימה 1050,450
        (0, 0), #ננש כן 995,230
        (0, 0),  # שם מלא בודק 1250,560
        (136, 150),   # בדיקת קבלה תאריך 
        (0, 0),   # בדיקת קבלה 290,150
        (1430, 448),  # מספר אישי
        (0, 0), #850,447 מס ליקוי
        (1430, 560),  # בודק מספר אישי
        (0, 0), #580,447 פירוט ביצוע העבודה
        (0, 0), #חתימת מבצע 355,447
        (0, 0), #חתימת בודק 250,447
        (0, 0),  # תאריך פירוט ליקוי 150,447
        (0, 0),  # שורה מתחת 850,468
        (0, 0), # תיאור / שם פריט 1250,80
        (0, 0), #תקלה מאומתת לא 870,155
        (1250, 80), #מש כן 1000,180
        (0, 0),#מש לא 960,180
        (0, 0),#ננת כן 995,205
        (0, 0),  # שם מלא 1250,450
        (0, 0),  # חתימה בודק 1050,560
        (0, 0)  # ננש לא 960,230
    ]

    image = Image.open("tag_image.jpg")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 20)

    # פונקציה להצגת חתימה (base64 data URL) על תמונה
    def display_signature_on_image(target_image, signature_data, position_xy, max_width=150):
        if not signature_data:
            return False
        try:
            # תמיכה ב-data URL
            if signature_data.startswith('data:image') and ',' in signature_data:
                signature_data = signature_data.split(',', 1)[1]
            sig_bytes = base64.b64decode(signature_data)
            sig_img = Image.open(BytesIO(sig_bytes))
            # שינוי גודל יחסי עם שמירה על מימדים מינימליים
            if max_width and sig_img.width > 0:
                scale = max_width / float(sig_img.width)
                new_w = int(sig_img.width * scale)
                new_h = int(sig_img.height * scale)
                if new_w < 1:
                    new_w = 1
                if new_h < 1:
                    new_h = 1
                sig_img = sig_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # אם אין אלפא, המר ל-RGBA כדי לאפשר מסכה זהה
            if sig_img.mode != 'RGBA':
                sig_img = sig_img.convert('RGBA')
            target_image.paste(sig_img, position_xy, sig_img)
            return True
        except Exception as e:
            print('שגיאה בהדבקת חתימה:', str(e))
            return False

    placement_map = []


    def split_and_extract_datetime_content(input_string):

        if not input_string.strip():
            return []

        # שיפור הרגקס כדי לתפוס את כל התוכן עד לתאריך הבא או סוף הטקסט
        pattern = r'\d{2}:\d{2}\s+(\d{2}/\d{2}/\d{4}):\s+(.+?)(?=\d{2}:\d{2}\s+\d{2}/\d{2}/\d{4}:|$)'
        
        matches = re.findall(pattern, input_string, re.UNICODE | re.DOTALL)
        
        result = []
        for match in matches:
            new_value = match[0]  # התאריך (למשל, 12/08/2025)
            print('new_value - ', new_value)
            value = match[1].strip()  # התוכן - עכשיו כולל מספרים וסימנים
            
            # אם יש שורות חדשות, נחלק אותן
            if '\n' in value:
                split_value = value.split('\n')
                first = 1
                for index in split_value:
                    if first == 1:
                        result.append({"date": new_value, "content": index.strip()})
                        first = 0
                    else:
                        result.append({"date": '', "content": index.strip()})
                        
            else:
                result.append({"date": new_value, "content": value})
        
        return result

    # הוסף את הערכים לפי שם עמודה גם ל-all_values
    # כך שנוכל לגשת גם לפי שם אם האינדקס לא עובד
    # קבל את האינדקסים של performer ו-checker
    performer_idx = process_col_index_map.get('performer')
    checker_idx = process_col_index_map.get('checker')
    
    for name_key, name_value in all_values_by_name.items():
        if name_key not in [v[0] for v in all_values]:
            # מצא את האינדקס המתאים
            if name_key == "process_tags.performer" and performer_idx is not None:
                all_values.append((f"process_tags.{performer_idx}", name_value))
            elif name_key == "process_tags.checker" and checker_idx is not None:
                all_values.append((f"process_tags.{checker_idx}", name_value))
    
    # עיבוד מיוחד של performer ו-checker לפני הלולאה הראשית
    # כך שנוכל לגשת אליהם לפי שם גם אם האינדקס שונה
    if performer_value and performer_idx is not None:
        # הוסף את performer ל-all_values עם האינדקס הנכון
        performer_var_name = f"process_tags.{performer_idx}"
        if not any(v[0] == performer_var_name for v in all_values):
            # הוסף בנקודה הנכונה (אינדקס 9 או האינדקס האמיתי)
            all_values.insert(min(9, len(all_values)), (performer_var_name, performer_value))
    
    if checker_value and checker_idx is not None:
        # הוסף את checker ל-all_values עם האינדקס הנכון
        checker_var_name = f"process_tags.{checker_idx}"
        if not any(v[0] == checker_var_name for v in all_values):
            # הוסף בנקודה הנכונה (אינדקס 11 או האינדקס האמיתי)
            all_values.insert(min(11, len(all_values)), (checker_var_name, checker_value))
    
    for pos, (var_name, value) in zip(positions, all_values):
        # דלג על שדות חתימה בפר-תג כדי לא לצייר BASE64 כמלל
        if var_name in skip_signature_varnames:
            continue
        
        # הדפס דיבאג לכל השדות החשובים
        if var_name.startswith('process_tags.'):
            print(f"[DEBUG] Processing {var_name}: '{value}'")
        if var_name == 'process_tags.2':
            print(f"[DEBUG] Processing fault_description: '{value}'")
            next_line = 0
            if value and value.strip():  # בדוק שהערך לא ריק
                if '\n' in value:
                    value_split = value.split('\n')
                    for item in value_split:
                        font = ImageFont.truetype("arial.ttf", 20)
                        pos = (1280, 255 + next_line)
                        reshaped_text = arabic_reshaper.reshape(item)
                        bidi_text = get_display(reshaped_text)
                        tbbox = draw.textbbox((0, 0), bidi_text, font=font)
                        text_width = tbbox[2] - tbbox[0]
                        draw.text((pos[0] - text_width, pos[1]), bidi_text, font=font, fill="black")
                        placement_map.append((pos, item, var_name))
                        next_line += 30
                else:
                    # אם אין שורות חדשות, הדפס בשורה אחת
                    font = ImageFont.truetype("arial.ttf", 20)
                    pos = (1280, 255)
                    reshaped_text = arabic_reshaper.reshape(value)
                    bidi_text = get_display(reshaped_text)
                    tbbox = draw.textbbox((0, 0), bidi_text, font=font)
                    text_width = tbbox[2] - tbbox[0]
                    draw.text((pos[0] - text_width, pos[1]), bidi_text, font=font, fill="black")
                    placement_map.append((pos, value, var_name))
            else:
                print(f"[DEBUG] fault_description is empty or None")
            continue
                    

        elif var_name == 'process_tags.3':
            next_line = 0
            result = split_and_extract_datetime_content(value)
            for item in result:
                
                print(f"Date: {item['date']}, Content: {item['content']}")   
                value_split = item
                new_value = value_split['date']
                value = value_split['content']
                new_pos = (150, 447 + next_line)
                reshaped_text = arabic_reshaper.reshape(new_value)
                bidi_text = get_display(reshaped_text)
                tbbox = draw.textbbox((0, 0), bidi_text, font=font)
                text_width = tbbox[2] - tbbox[0]
                draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
                placement_map.append((new_pos, new_value, var_name))

                # המר ל-int כדי למנוע שגיאת float
                y_pos = int(430 + next_line)
                ok2 = display_signature_on_image(image, performer_signature, (250, y_pos), max_width=120)
                if ok2:
                    placement_map.append(((250, y_pos), '[חתימת מבצע]', 'process_tags.performer_signature'))
                ok = display_signature_on_image(image, checker_signature, (140, y_pos), max_width=120)
                if ok:
                    placement_map.append(((140, y_pos), '[חתימת בודק]', 'process_tags.checker_signature'))
                pos = (790, 447 + next_line)
                reshaped_text = arabic_reshaper.reshape(value)
                bidi_text = get_display(reshaped_text)
                tbbox = draw.textbbox((0, 0), bidi_text, font=font)
                text_width = tbbox[2] - tbbox[0]
                draw.text((pos[0] - text_width, pos[1]), bidi_text, font=font, fill="black")
                placement_map.append((pos, value, var_name))
                if '\n' in item['content']:
                    next_line += 23.5
                next_line += 23.5

        elif var_name == 'process_tags.8':
            count = 0
            list_data = json.loads(value)
            if len(list_data) == 10:
                ok = display_signature_on_image(image, performer_signature, (136, 150), max_width=170)
                if ok:
                    placement_map.append(((136, 150), '[חתימת מבצע]', 'process_tags.performer_signature'))

        elif var_name == "process_tags.9" or (performer_idx is not None and var_name == f"process_tags.{performer_idx}"):
            # נסה לקבל את performer לפי שם אם האינדקס לא עובד או שהערך ריק
            if not value or not value.strip():
                value = performer_value if performer_value else all_values_by_name.get("process_tags.performer", "")
            
            # בדוק אם value לא ריק
            if not value or not value.strip():
                continue
            value_split = value.split()
            if len(value_split) == 0:
                continue
            name_value_split = value_split[:-1]
            value = value_split[-1]
            # בדוק אם value ארוך מספיק לפני חיתוך
            if len(value) >= 2:
                value = value[1:-1]
            else:
                value = ""
            name_value = ' '.join(name_value_split)
            new_pos = (1250, 448)
            reshaped_text = arabic_reshaper.reshape(name_value)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
            placement_map.append((new_pos, name_value, var_name))

        elif var_name == "process_tags.11" or (checker_idx is not None and var_name == f"process_tags.{checker_idx}"):
            # נסה לקבל את checker לפי שם אם האינדקס לא עובד או שהערך ריק
            if not value or not value.strip():
                value = checker_value if checker_value else all_values_by_name.get("process_tags.checker", "")
            
            # בדוק אם value לא ריק
            if not value or not value.strip():
                continue
            value_split = value.split()
            if len(value_split) == 0:
                continue
            name_value_split = value_split[:-1]
            value = value_split[-1]
            # בדוק אם value ארוך מספיק לפני חיתוך
            if len(value) >= 2:
                value = value[1:-1]
            else:
                value = ""
            name_value = ' '.join(name_value_split)
            new_pos = (1250, 560)
            reshaped_text = arabic_reshaper.reshape(name_value)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
            placement_map.append((new_pos, name_value, var_name))

        elif var_name == 'process_tags.12':
            try:
                list_value = json.loads(value)
                print('list_value - ', list_value)
                # בדוק אם list_value הוא רשימה או מחרוזת
                if isinstance(list_value, (list, str)):
                    if "מ'ש" in list_value:
                        new_pos = (1000, 174)
                    else:
                        new_pos = (960, 174)
                else:
                    # אם זה לא רשימה או מחרוזת, השתמש במיקום ברירת מחדל
                    new_pos = (960, 174)
            except (json.JSONDecodeError, TypeError):
                # אם יש שגיאה בפרסור JSON או אם הערך לא ניתן לפרסור
                new_pos = (960, 174)
            font = ImageFont.truetype("arial.ttf", 36)
            name_value = 'O'
            reshaped_text = arabic_reshaper.reshape(name_value)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
            placement_map.append((new_pos, name_value, var_name))

            # בדוק אם list_value הוא רשימה או מחרוזת
            if isinstance(list_value, (list, str)) and "ננ'ת" in list_value:
                new_pos = (997, 200)
            else:
                new_pos = (960, 200)
            font = ImageFont.truetype("arial.ttf", 36)
            name_value = 'O'
            reshaped_text = arabic_reshaper.reshape(name_value)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
            placement_map.append((new_pos, name_value, var_name))

            # בדוק אם list_value הוא רשימה או מחרוזת
            if isinstance(list_value, (list, str)) and "ננ'ש" in list_value:
                new_pos = (997, 225)
            else:
                new_pos = (960, 225)
            font = ImageFont.truetype("arial.ttf", 36)
            name_value = 'O'
            reshaped_text = arabic_reshaper.reshape(name_value)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
            placement_map.append((new_pos, name_value, var_name))
            
        elif var_name == 'process_tags.13':
            if 'כן' in value:
                new_pos = (907, 145)
            else:
                new_pos = (870, 145)
            font = ImageFont.truetype("arial.ttf", 36)
            name_value = 'O'
            reshaped_text = arabic_reshaper.reshape(name_value)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((new_pos[0] - text_width, new_pos[1]), bidi_text, font=font, fill="black")
            placement_map.append((new_pos, name_value, var_name))


        elif var_name == 'process_tags.7':
            value_split = value.split()
            value = value_split[0]

        print('pos - ', pos)
        print('var_name - ', var_name)
        print('value - ', value)
        font = ImageFont.truetype("arial.ttf", 20)
        reshaped_text = arabic_reshaper.reshape(value)
        bidi_text = get_display(reshaped_text)
        tbbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = tbbox[2] - tbbox[0]
        draw.text((pos[0] - text_width, pos[1]), bidi_text, font=font, fill="black")
        placement_map.append((pos, value, var_name))

    # הדפסת מידע צריכת חלפים
    if data["spare_parts_usage"]:
        font = ImageFont.truetype("arial.ttf", 16)
        y_pos = 850  
        x_pos = 1340
        
        for usage in data["spare_parts_usage"]:
            usage_id, part_number, description, manufacturer, serial_number, date_used = usage
            
            reshaped_text = arabic_reshaper.reshape(part_number)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((x_pos, y_pos), bidi_text, font=font, fill="black")
            placement_map.append(((x_pos, y_pos), part_number, f'spare_parts_usage.{usage_id}.part'))
            
            reshaped_text = arabic_reshaper.reshape(serial_number)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((x_pos - 265, y_pos), bidi_text, font=font, fill="black")
            placement_map.append(((x_pos + 300, y_pos), serial_number, f'spare_parts_usage.{usage_id}.serial'))
            
            reshaped_text = arabic_reshaper.reshape(manufacturer)
            bidi_text = get_display(reshaped_text)
            tbbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = tbbox[2] - tbbox[0]
            draw.text((x_pos - 162, y_pos), bidi_text, font=font, fill="black")
            placement_map.append(((x_pos - 162, y_pos), manufacturer, f'spare_parts_usage.{usage_id}.serial'))
            
            y_pos += 25

    # הדבק חתימות מהתג (אם קיימות)
    SIGN_PERFORMER_MAIN_W = 120
    SIGN_PERFORMER_TABLE_W = 110
    SIGN_CHECKER_W = 120

    if performer_signature:
        ok = display_signature_on_image(image, performer_signature, (925, 430), max_width=SIGN_PERFORMER_MAIN_W)
        if ok:
            placement_map.append(((1050, 450), '[חתימת מבצע]', 'process_tags.performer_signature'))
        # הדבק גם במיקום נוסף לפי דרישה
    if checker_signature:
        ok = display_signature_on_image(image, checker_signature, (925, 545), max_width=SIGN_CHECKER_W)
        if ok:
            placement_map.append(((1050, 560), '[חתימת בודק]', 'process_tags.checker_signature'))

    # שמירת התמונה החדשה
    image.save("tag_with_random_text.jpg")

    # הדפסות דיבאג מבוקשות
    print("Output image file: tag_with_random_text.jpg")
    print(f"Tag ID: {tag_id if tag_id else 'None (latest tag)'}")
    print(f"Serial Number: {serial_number}")
    print(f"SKU: {sku}")
    
    # הדפסת נתוני התג
    if data["process_tags"]:
        tag_data = data["process_tags"][0]
        print(f"Tag fault_description: {tag_data[2] if len(tag_data) > 2 else 'N/A'}")
        print(f"Tag actions_taken: {tag_data[3] if len(tag_data) > 3 else 'N/A'}")
    
    print(f"Performer signature → DB column: process_tags.performer_signature → position: (1050, 450) → present: {'yes' if performer_signature else 'no'}")
    print(f"Checker signature   → DB column: process_tags.checker_signature   → position: (1050, 560) → present: {'yes' if checker_signature else 'no'}")

    # הדפסת המיפוי
    for pos, value, var_name in placement_map:
        print(f"מיקום {pos} ← '{value}' ← {var_name}")

    image.show()