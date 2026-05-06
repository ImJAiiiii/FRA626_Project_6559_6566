import cv2
import numpy as np
from collections import deque
import pickle

# 1. โหลดโมเดล AI ที่เทรนมาได้ 90%
try:
    with open('magic_wand_model.pkl', 'rb') as f:
        ai_model = pickle.load(f)
    print("AI Model Loaded Successfully!")
except:
    print("Error: ไม่พบไฟล์ magic_wand_model.pkl กรุณาเทรนโมเดลก่อน")
    exit()

# 2. ฟังก์ชัน Preprocess (ต้องเหมือนกับตอนเก็บข้อมูล)
def preprocess_for_ai(points, num_points=30):
    if len(points) < 15: return None # สั้นไปไม่ทาย
    
    # Resample ให้เหลือ 30 จุด
    indices = np.linspace(0, len(points) - 1, num_points)
    resampled = []
    for i in indices:
        idx1, idx2 = int(np.floor(i)), int(np.ceil(i))
        weight = i - idx1
        if idx1 == idx2: resampled.append(points[idx1])
        else:
            x = points[idx1][0] * (1 - weight) + points[idx2][0] * weight
            y = points[idx1][1] * (1 - weight) + points[idx2][1] * weight
            resampled.append((x, y))
            
    # Normalize (0.0 - 1.0)
    xs, ys = [p[0] for p in resampled], [p[1] for p in resampled]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    scale = max(max_x - min_x, max_y - min_y, 1e-5)
    
    normalized_flat = []
    for x, y in resampled:
        normalized_flat.extend([(x - min_x) / scale, (y - min_y) / scale])
    return normalized_flat

# 3. ตั้งค่ากล้องและการตรวจจับสี (ค่าที่คุณจูนล่าสุด)
cap = cv2.VideoCapture(0)
pts = deque(maxlen=64)
history = deque(maxlen=5)
prev = None

# สีเขียวปลายไม้
lower = np.array([40, 80, 80])
upper = np.array([89, 255, 255])

state = "IDLE"
hold_counter = 0
msg = "WAITING..."
spell_effect = ""

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 360))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Masking & Tracking
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)
    
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tip = None

    if cnts:
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) > 200: # ปรับขนาดขั้นต่ำตามที่แก้รอบที่แล้ว
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
                pts_c = c.reshape(-1,2)
                dist = np.linalg.norm(pts_c - np.array([cx,cy]), axis=1)
                tip = tuple(pts_c[np.argmax(dist)])

    # Smoothing Logic
    if tip:
        history.append(tip)
        mx, my = int(np.median([p[0] for p in history])), int(np.median([p[1] for p in history]))
        if prev is None: px, py = mx, my
        else:
            alpha = 0.6
            px, py = int(alpha*prev[0] + (1-alpha)*mx), int(alpha*prev[1] + (1-alpha)*my)
        prev = (px, py)
        pts.append((px, py))
    else:
        px, py = None, None
        prev = None

    # State Machine Logic
    valid_pts = list(pts)
    if len(valid_pts) > 10:
        xs, ys = [p[0] for p in valid_pts[-10:]], [p[1] for p in valid_pts[-10:]]
        is_holding = (max(xs)-min(xs) < 15 and max(ys)-min(ys) < 15)
    else: is_holding = False

    if state == "IDLE":
        if is_holding: hold_counter += 1
        else: hold_counter = 0
        if hold_counter > 15:
            state = "READY"
            pts.clear()
            msg = "READY TO CAST!"
            spell_effect = ""

    elif state == "READY":
            if not is_holding:
                state = "DRAW"
                pts.clear()
                has_moved_enough = False # ตัวแปรใหม่: เช็คว่าขยับไกลพอหรือยัง
                msg = "START DRAWING..."

    elif state == "DRAW":
        # 1. คำนวณระยะห่างจากจุดเริ่มต้น
        if len(valid_pts) > 2:
            dist_from_start = np.linalg.norm(np.array(valid_pts[-1]) - np.array(valid_pts[0]))
        else:
            dist_from_start = 0

        # 2. ถ้าลากมือเกิน 40 พิกเซลแล้ว ให้ปลดล็อคว่า "นี่คือการวาดจริงๆ"
        if dist_from_start > 40:
            has_moved_enough = True

        # 3. เงื่อนไขการทำนาย: ต้องนิ่ง (is_holding) และ ต้องเคยขยับมาไกลพอแล้ว (has_moved_enough)
        if is_holding:
            if has_moved_enough and len(valid_pts) > 20:
                # --- ส่วนประมวลผล AI เหมือนเดิม ---
                input_ai = preprocess_for_ai(valid_pts)
                if input_ai:
                    input_array = np.array([input_ai])
                    prediction = ai_model.predict(input_array)[0]
                    probs = ai_model.predict_proba(input_array)[0]
                    confidence = np.max(probs)
                    
                    if confidence > 0.5: 
                        spell_effect = f"MAGIC: {prediction.upper()}!"
                        msg = f"SUCCESS ({confidence*100:.0f}%)"
                    else:
                        msg = "UNCLEAR GESTURE"
                    
                    state = "IDLE"
                    hold_counter = 0
                    pts.clear()
            
            elif not has_moved_enough:
                # ถ้ามือนิ่งแต่ยังไม่เคยขยับไปไหนเลย ให้ประคองสถานะ DRAW ไว้ก่อน
                # (ห้ามดีดไป TOO SHORT ทันที)
                pass 
            
            else:
                # ถ้าเคยขยับแล้ว แต่นิ่งเร็วไป หรือจุดน้อยไป ค่อยขึ้น TOO SHORT
                state = "IDLE"
                pts.clear()
                msg = "TOO SHORT! TRY AGAIN"

    # --- การแสดงผล (Visuals) ---
    # วาดเส้นเวทมนตร์ (ใช้สีต่างกันตามสถานะ)
    line_color = (0, 255, 255) if state == "DRAW" else (255, 0, 255)
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i-1], pts[i], line_color, 3)

    # UI
    cv2.putText(frame, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    if spell_effect:
        cv2.putText(frame, spell_effect, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

    cv2.imshow("AI Magic Wand", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()