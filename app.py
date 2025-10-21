from flask import Flask, request, jsonify, render_template, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import os
import time

# กำหนดพาธพื้นฐานของโปรเจกต์
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

# ตั้งค่า Flask App
app = Flask(__name__)

# --- ค่าคงที่ที่ต้องปรับเปลี่ยน ---
TEMPLATE_IMAGE_PATH = os.path.join(BASE_DIR, 'template.png')
OUTPUT_DIR_NAME = 'generated_images'
OUTPUT_DIR = os.path.join(BASE_DIR, OUTPUT_DIR_NAME)

# ตรวจสอบและสร้างโฟลเดอร์ผลลัพธ์
if not os.path.exists(OUTPUT_DIR): 
    os.makedirs(OUTPUT_DIR, exist_ok=True) 

# 🚨 การแก้ไข: กำหนดให้ใช้ฟอนต์ THSarabunNew.ttf ที่จะถูกอัปโหลดไปในโฟลเดอร์ 'templates'
# ตรวจสอบให้แน่ใจว่าได้อัปโหลดไฟล์ 'thsarabunnew.ttf' ไปยังโฟลเดอร์ 'templates' ใน GitHub แล้ว
FONT_NAME = 'thsarabunnew.ttf'
DEFAULT_FONT_PATH = os.path.join(BASE_DIR, 'templates', FONT_NAME) 

DEFAULT_FONT_SIZE = 60
# -----------------------------------

@app.route('/')
def index():
    return render_template('index.html') 


# ฟังก์ชันช่วยเหลือ: แปลงรหัสสี #RRGGBB เป็น Tuple (R, G, B)
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


@app.route('/generate-image', methods=['POST'])
def generate_image():
    # 1. รับข้อมูลทั้งหมดจาก Front-end
    try:
        data = request.get_json()
        user_text = data.get('user_text', 'ข้อความว่างเปล่า')
        font_size = int(data.get('font_size', DEFAULT_FONT_SIZE))
        text_align = data.get('text_align', 'left')
        bg_color_hex = data.get('bg_color', 'template')
        text_color_hex = data.get('text_color', '#000000')

    except Exception as e:
        return jsonify({"error": f"รูปแบบข้อมูล (JSON) ไม่ถูกต้อง: {str(e)}"}), 400
    
    # 2. โหลดภาพพื้นหลัง หรือ สร้างภาพสีพื้น
    try:
        if bg_color_hex == 'template':
            img = Image.open(TEMPLATE_IMAGE_PATH).convert("RGBA")
            width, height = img.size
        else:
            width, height = 1000, 600 
            img = Image.new('RGBA', (width, height), hex_to_rgb(bg_color_hex) + (255,))
    except FileNotFoundError:
        return jsonify({"error": f"ไม่พบไฟล์ Template: template.png. โปรดตรวจสอบ!"}), 500
    except Exception as e:
        return jsonify({"error": f"เกิดข้อผิดพลาดในการโหลดหรือสร้างภาพ: {str(e)}"}), 500

    draw = ImageDraw.Draw(img)
    
    # 3. โหลดฟอนต์ (ใช้ฟอนต์ที่อัปโหลดเอง)
    try:
        if DEFAULT_FONT_PATH and os.path.exists(DEFAULT_FONT_PATH):
            FONT = ImageFont.truetype(DEFAULT_FONT_PATH, size=font_size) 
        else:
            # Fallback หากไม่พบฟอนต์ที่อัปโหลด (ซึ่งไม่ควรเกิดขึ้นหากอัปโหลดถูกต้อง)
            FONT = ImageFont.load_default() 
            print(f"Warning: Custom font not found at {DEFAULT_FONT_PATH}. Using default font.")
            
    except IOError as e:
        # กรณีเกิด IOError (เช่น ไฟล์ฟอนต์เสีย)
        FONT = ImageFont.load_default() 
        print(f"Error loading custom font: {e}. Using default font.")
        
    text_color_rgb = hex_to_rgb(text_color_hex)
    
    # 4. คำนวณขนาดและตำแหน่ง
    # ใช้ font.getbbox() เพื่อคำนวณขนาดข้อความอย่างถูกต้อง
    try:
        bbox = draw.textbbox((0, 0), user_text, font=FONT)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

    except Exception:
        # Fallback สำหรับฟอนต์ load_default() หากเกิดปัญหาในการคำนวณ bbox
        text_width, text_height = draw.textsize(user_text, font=FONT)
        print("Warning: Using fallback for text size calculation.")

    
    # คำนวณ X ตามการจัดตำแหน่ง
    margin = 50 
    if text_align == 'center':
        position_x = (width - text_width) / 2
    elif text_align == 'right':
        position_x = width - text_width - margin
    else: 
        position_x = margin
    
    # กำหนด Y ให้อยู่กึ่งกลางของภาพ 
    position_y = (height - text_height) / 2
    
    # 5. วาดข้อความลงบนภาพ
    draw.text((position_x, position_y), user_text, font=FONT, fill=text_color_rgb)
    
    # 6. บันทึกภาพผลลัพธ์
    output_filename = f"result_{int(time.time())}_{os.getpid()}.png"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    try:
        img.save(output_path)
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถบันทึกภาพผลลัพธ์ได้: {str(e)}"}), 500
    
    # 7. ส่ง URL ของภาพผลลัพธ์กลับไป
    image_url = f"/images/{output_filename}" 
    return jsonify({"image_url": image_url})


# Route สำหรับให้ Front-end ดึงภาพที่ถูกสร้างขึ้นมาแสดงผล
@app.route('/images/<filename>')
def serve_generated_image(filename):
    # สำหรับ Cloud, เราต้องส่งไฟล์จากโฟลเดอร์ generated_images
    return send_from_directory(OUTPUT_DIR, filename)
