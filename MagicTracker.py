import cv2
import numpy as np
from collections import deque
import pickle
import time

# ==========================================
# PART 1: ฟังก์ชันสำหรับ EFFECTS
# ให้เขียนโค้ดวาดเอฟเฟกต์ในฟังก์ชันเหล่านี้
# ==========================================

def draw_magic_effect(frame, gesture_name, center_pt):
    """ฟังก์ชันหลักที่เพื่อนต้องมาใส่ความเมพ"""
    if gesture_name == "Circle":
        # ตัวอย่าง: วาดวงกลมซ้อนหลายชั้นสีฟ้า
        cv2.circle(frame, center_pt, 50, (255, 255, 0), 5)
        cv2.putText(frame, "ICE STORM!", (center_pt[0]-60, center_pt[1]+80), 
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 255, 0), 2)
        
    elif gesture_name == "Triangle":
        # ตัวอย่าง: วาดสามเหลี่ยมสีแดง
        pts = np.array([ [center_pt[0], center_pt[1]-50], 
                         [center_pt[0]-50, center_pt[1]+50], 
                         [center_pt[0]+50, center_pt[1]+50] ], np.int32)
        cv2.polylines(frame, [pts], True, (0, 0, 255), 5)
        cv2.putText(frame, "FIRE BLAST!", (center_pt[0]-60, center_pt[1]+80), 
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 0, 255), 2)
        
    elif gesture_name == "Slash":
        # ตัวอย่าง: วาดเส้นสายฟ้าสีเหลือง
        cv2.line(frame, (center_pt[0]-60, center_pt[1]-60), (center_pt[0]+60, center_pt[1]+60), (0, 255, 255), 8)
        cv2.putText(frame, "THUNDERBOLT!", (center_pt[0]-80, center_pt[1]+80), 
                    cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 2)

# ==========================================
# PART 2: CORE SYSTEM
# ==========================================

# โหลดโมเดล
try:
    with open('magic_wand_model.pkl', 'rb') as f:
        ai_model = pickle.load(f)
    print("AI Model Loaded!")
except:
    print("Error: Model file not found!")
    exit()

def preprocess_for_ai(points, num_points=30):
    if len(points) < 15: return None
    indices = np.linspace(0, len(points) - 1, num_points)
    resampled = [points[int(i)] for i in indices]
    xs, ys = [p[0] for p in resampled], [p[1] for p in resampled]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    scale = max(max_x - min_x, max_y - min_y, 1e-5)
    normalized = []
    for x, y in resampled:
        normalized.extend([(x - min_x) / scale, (y - min_y) / scale])
    return normalized

cap = cv2.VideoCapture(0)
pts = deque(maxlen=64)
history = deque(maxlen=5)
prev = None

# ค่าสี HSV
lower = np.array([40, 80, 80])
upper = np.array([89, 255, 255])

state = "IDLE"
hold_counter = 0
msg = "WAITING..."
last_gesture = None
last_pt = (0,0)
effect_start_time = 0

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 360))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)
    
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tip = None

    if cnts:
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) > 200:
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
                pts_c = c.reshape(-1,2)
                dist = np.linalg.norm(pts_c - np.array([cx,cy]), axis=1)
                tip = tuple(pts_c[np.argmax(dist)])

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

    valid_pts = list(pts)
    if len(valid_pts) > 10:
        xs, ys = [p[0] for p in valid_pts[-10:]], [p[1] for p in valid_pts[-10:]]
        is_holding = (max(xs)-min(xs) < 15 and max(ys)-min(ys) < 15)
    else: is_holding = False

    # STATE MACHINE
    if state == "IDLE":
        if is_holding: hold_counter += 1
        else: hold_counter = 0
        if hold_counter > 15:
            state = "READY"
            pts.clear()
            msg = "READY TO CAST!"

    elif state == "READY":
        if not is_holding:
            state = "DRAW"
            pts.clear()
            has_moved_enough = False
            msg = "CASTING..."

    elif state == "DRAW":
        dist_from_start = np.linalg.norm(np.array(valid_pts[-1]) - np.array(valid_pts[0])) if len(valid_pts) > 1 else 0
        if dist_from_start > 40: has_moved_enough = True

        if is_holding:
            if has_moved_enough and len(valid_pts) > 20:
                input_ai = preprocess_for_ai(valid_pts)
                if input_ai:
                    prediction = ai_model.predict(np.array([input_ai]))[0]
                    confidence = np.max(ai_model.predict_proba(np.array([input_ai]))[0])
                    
                    if confidence > 0.5: 
                        last_gesture = prediction
                        last_pt = valid_pts[-1]
                        effect_start_time = time.time() # เริ่มจับเวลาแสดงเอฟเฟกต์
                        msg = f"SUCCESS: {prediction}!"
                    else:
                        msg = "UNCLEAR GESTURE"
                    
                    state = "IDLE"
                    hold_counter = 0
                    pts.clear()
            elif not has_moved_enough: pass 
            else:
                state = "IDLE"
                pts.clear()
                msg = "TOO SHORT!"

    # --- แสดงผลเอฟเฟกต์ (ค้างไว้ 2 วินาที) ---
    if last_gesture and (time.time() - effect_start_time < 2.0):
        draw_magic_effect(frame, last_gesture, last_pt)
    else:
        last_gesture = None

    # วาดเส้นที่กำลังวาด
    line_color = (0, 255, 255) if state == "DRAW" else (255, 0, 255)
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i-1], pts[i], line_color, 3)

    cv2.putText(frame, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("AI Magic Wand Project", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()