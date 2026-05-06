import cv2
import numpy as np
from collections import deque
import csv
import os

# ===== สร้างไฟล์ CSV สำหรับเก็บข้อมูล =====
csv_filename = "gesture_data.csv"
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        # สร้าง Header: label, x0, y0, x1, y1, ... x29, y29
        header = ["label"] + [f"{axis}{i}" for i in range(30) for axis in ('x', 'y')]
        writer.writerow(header)

# ===== ฟังก์ชันแปลงข้อมูลให้พร้อมสำหรับ AI =====
def preprocess_points(points, num_points=30):
    """ฟังก์ชันบังคับให้เส้นมี 30 จุดเท่ากัน และย่อส่วนให้อยู่ในกรอบ 0 ถึง 1"""
    if len(points) < 10: 
        return None # ถ้ายาวไม่พอก็ไม่เซฟ
    
    # 1. Resample: เกลี่ยให้เหลือ/เพิ่มให้ครบ 30 จุด
    indices = np.linspace(0, len(points) - 1, num_points)
    resampled = []
    for i in indices:
        idx1, idx2 = int(np.floor(i)), int(np.ceil(i))
        weight = i - idx1
        if idx1 == idx2:
            resampled.append(points[idx1])
        else:
            x = points[idx1][0] * (1 - weight) + points[idx2][0] * weight
            y = points[idx1][1] * (1 - weight) + points[idx2][1] * weight
            resampled.append((x, y))
            
    # 2. Normalize: เลื่อนมาจุดกำเนิดและปรับขนาด (Scale) เป็น 0.0 - 1.0
    xs = [p[0] for p in resampled]
    ys = [p[1] for p in resampled]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    scale = max(max_x - min_x, max_y - min_y, 1e-5) # ป้องกันหารด้วย 0
    
    normalized_flat = []
    for x, y in resampled:
        nx = (x - min_x) / scale
        ny = (y - min_y) / scale
        normalized_flat.extend([nx, ny]) # จับยัดใส่ List ยาวๆ 60 ตัว
        
    return normalized_flat

def save_to_csv(label, points):
    data = preprocess_points(points)
    if data:
        with open(csv_filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([label] + data)
        return True
    return False

# ===== การตั้งค่ากล้องและตัวแปรเดิม =====
cap = cv2.VideoCapture(0)
history = deque(maxlen=5)
prev = None
pts = deque(maxlen=150) # เพิ่ม maxlen ให้วาดได้ยาวขึ้นตอนเก็บข้อมูล

state = "IDLE"
hold_counter = 0
HOLD_THRESHOLD = 10
msg = "Ready to collect data!"
counts = {"Circle": 0, "Triangle": 0, "Slash": 0}

while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 360))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # สีเขียวที่คุณจูนไว้ (แก้เป็นค่าปัจจุบันของคุณได้เลย)
    lower = np.array([59, 179, 77])
    upper = np.array([89, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tip = None

    if cnts:
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) > 300:
            M = cv2.moments(c)
            if M["m00"] > 0:
                cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
                pts_c = c.reshape(-1,2)
                dist = np.linalg.norm(pts_c - np.array([cx,cy]), axis=1)
                tip = tuple(pts_c[np.argmax(dist)])

    # Smoothing
    if tip is not None:
        history.append(tip)
        mx, my = int(np.median([p[0] for p in history])), int(np.median([p[1] for p in history]))
        if prev is None:
            px, py = mx, my
        else:
            alpha = 0.6
            px, py = int(alpha*prev[0] + (1-alpha)*mx), int(alpha*prev[1] + (1-alpha)*my)
        prev = (px, py)
    else:
        px, py = None, None

    if px is not None:
        pts.append((px, py))

    valid_pts = list(pts)

    # State Machine (เอาไว้ควบคุมจังหวะวาด)
    if len(valid_pts) > 10:
        xs, ys = [p[0] for p in valid_pts[-10:]], [p[1] for p in valid_pts[-10:]]
        is_holding = (max(xs)-min(xs) < 15 and max(ys)-min(ys) < 15)
    else:
        is_holding = False

    if state == "IDLE":
        if is_holding: hold_counter += 1
        else: hold_counter = 0
        if hold_counter > HOLD_THRESHOLD:
            state = "READY"
            pts.clear()
            msg = "HOLDING... START DRAWING!"

    elif state == "READY":
        if not is_holding:
            state = "DRAW"
            pts.clear()
            msg = "DRAWING... (Press 1/2/3 to save, R to retry)"

    elif state == "DRAW":
        # ระบบจะรอให้เรากดปุ่มบันทึก
        pass

    # วาดเส้น
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i-1], pts[i], (255, 0, 255), 2)
    if px is not None:
        cv2.circle(frame, (px, py), 6, (0, 255, 0), -1)

    # แสดงข้อความ
    cv2.putText(frame, msg, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    stat_str = f"Circle:{counts['Circle']}  Triangle:{counts['Triangle']}  Slash:{counts['Slash']}"
    cv2.putText(frame, stat_str, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    cv2.imshow("Data Collector", frame)
    cv2.imshow("Mask", mask)

    # จัดการปุ่มกด (Keyboard Input)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): 
        break
    elif state == "DRAW":
        if key == ord('1'):
            if save_to_csv("Circle", valid_pts): counts["Circle"] += 1
            state, msg, hold_counter = "IDLE", "SAVED: CIRCLE!", 0
            pts.clear()
        elif key == ord('2'):
            if save_to_csv("Triangle", valid_pts): counts["Triangle"] += 1
            state, msg, hold_counter = "IDLE", "SAVED: TRIANGLE!", 0
            pts.clear()
        elif key == ord('3'):
            if save_to_csv("Slash", valid_pts): counts["Slash"] += 1
            state, msg, hold_counter = "IDLE", "SAVED: SLASH!", 0
            pts.clear()
        elif key == ord('r'):
            state, msg, hold_counter = "IDLE", "CLEARED! TRY AGAIN", 0
            pts.clear()

cap.release()
cv2.destroyAllWindows()