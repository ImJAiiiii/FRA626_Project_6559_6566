import cv2
import numpy as np

# ค่าเริ่มต้น (Mask จะยังกว้างๆ จนกว่าเราจะคลิก)
lower = np.array([0, 0, 0])
upper = np.array([179, 255, 255])

# ฟังก์ชันทำงานเมื่อใช้เมาส์คลิกบนจอ
def pick_color(event, x, y, flags, param):
    global lower, upper
    if event == cv2.EVENT_LBUTTONDOWN:
        # ดึงค่าสี BGR จากพิกเซลที่เราคลิก
        bgr_pixel = frame[y, x]
        
        # แปลงเป็น HSV 
        hsv_pixel = cv2.cvtColor(np.uint8([[bgr_pixel]]), cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = hsv_pixel
        
        # คำนวณช่วงสี (Range) ให้ครอบคลุมแสงที่แกว่งนิดหน่อย
        # ค่า H (Hue) เอา +- 15 (เพราะสีมักจะไม่เพี้ยนไปจากเดิมมาก)
        # ค่า S, V (ความสด/ความสว่าง) เอา +- 50 (เผื่อจังหวะขยับไปตรงที่มืดลง/สว่างขึ้น)
        lower = np.array([max(0, h - 15), max(50, s - 50), max(50, v - 50)])
        upper = np.array([min(179, h + 15), 255, 255])
        
        print("\n" + "="*30)
        print("🎯 สีที่ดูดมาได้ (HSV):", hsv_pixel)
        print(f"👉 ก๊อปปี้ค่านี้ไปใส่ในโค้ดหลัก:")
        print(f"lower = np.array([{lower[0]}, {lower[1]}, {lower[2]}])")
        print(f"upper = np.array([{upper[0]}, {upper[1]}, {upper[2]}])")
        print("="*30 + "\n")

# เปิดกล้อง
cap = cv2.VideoCapture(0)
cv2.namedWindow("Magic Color Picker")
# ผูกเมาส์เข้ากับหน้าต่าง
cv2.setMouseCallback("Magic Color Picker", pick_color)

print("📝 วิธีใช้:")
print("1. เอาไม้กายสิทธิ์มาโชว์หน้ากล้อง")
print("2. ใช้เมาส์คลิกที่ 'ปลายไม้' ในหน้าต่าง Magic Color Picker")
print("3. ดูผลลัพธ์ในหน้าต่าง Mask (ต้องดำสนิท และมีสีขาวเฉพาะที่ปลายไม้)")
print("4. ก๊อปปี้ค่าที่โชว์ใน Terminal ไปใช้ในโค้ดจริง!")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 360))
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # สร้าง Mask ตามค่าที่ดูดมา
    mask = cv2.inRange(hsv, lower, upper)
    # ลด Noise นิดหน่อยเพื่อให้เห็นภาพชัดเจนขึ้น
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    
    # วาดเป้าเล็งตรงกลางจอให้รู้ว่ากล้องพร้อม
    cv2.circle(frame, (320, 180), 5, (255, 255, 255), 1)

    cv2.imshow("Magic Color Picker", frame)
    cv2.imshow("Mask Test", mask)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()