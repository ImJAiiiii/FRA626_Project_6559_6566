import cv2
import numpy as np
from collections import deque
import csv
import os

# ===== CSV =====
csv_filename = "gesture_data.csv"
if not os.path.exists(csv_filename):
    with open(csv_filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        header = ["label"] + [f"{axis}{i}" for i in range(100) for axis in ('x', 'y')]
        writer.writerow(header)

def preprocess_points(points, num_points=100):
    if len(points) < 10:
        return None

    indices = np.linspace(0, len(points) - 1, num_points)
    resampled = []

    for i in indices:
        i1, i2 = int(np.floor(i)), int(np.ceil(i))
        w = i - i1
        if i1 == i2:
            resampled.append(points[i1])
        else:
            x = points[i1][0]*(1-w) + points[i2][0]*w
            y = points[i1][1]*(1-w) + points[i2][1]*w
            resampled.append((x,y))

    xs = [p[0] for p in resampled]
    ys = [p[1] for p in resampled]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    scale = max(max_x-min_x, max_y-min_y, 1e-5)

    out = []
    for x,y in resampled:
        out.extend([(x-min_x)/scale, (y-min_y)/scale])

    return out

def save_to_csv(label, pts):
    # รายชื่อจำนวนจุดที่เราต้องการทดลอง
    test_points_list = [10, 20, 30, 50, 80, 100]
    
    for n in test_points_list:
        data = preprocess_points(pts, num_points=n)
        if data:
            filename = f"gesture_data_{n}.csv"
            file_exists = os.path.exists(filename)
            
            with open(filename, mode='a', newline='') as f:
                writer = csv.writer(f)
                # ถ้ายังไม่มีไฟล์ ให้เขียน Header ก่อน (x0, y0, x1, y1...)
                if not file_exists:
                    header = ["label"] + [f"{axis}{i}" for i in range(n) for axis in ('x', 'y')]
                    writer.writerow(header)
                
                # บันทึกข้อมูลลงไฟล์
                writer.writerow([label] + data)
    
    print(f"Saved {label} to all {len(test_points_list)} files.")
    return True


# ===== CAMERA =====
cap = cv2.VideoCapture(0)

history = deque(maxlen=5)
pts = deque(maxlen=200)

state = "IDLE"
hold_counter = 0
HOLD_THRESHOLD = 10

msg = "Ready"
counts = {"Circle":0,"Triangle":0,"Slash":0}

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame,1)
    frame = cv2.resize(frame,(640,360))

    # ===== เพิ่มความสว่าง =====
    frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=20)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ===== HSV ใหม่ (กว้างขึ้น) =====
    lower = np.array([40, 80, 80])
    upper = np.array([90, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)

    # ===== Clean noise =====
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.medianBlur(mask,5)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

    cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    tip = None

    if cnts:
        c = max(cnts, key=cv2.contourArea)

        if cv2.contourArea(c) > 200:
            pts_c = c.reshape(-1,2)

            # ===== หา "ปลายไม้" ด้วยจุดบนสุด =====
            tip = tuple(pts_c[np.argmin(pts_c[:,1])])

            cv2.drawContours(frame, [c], -1, (0,255,0), 2)

    # ===== smoothing =====
    if tip is not None:
        history.append(tip)

        mx = int(np.median([p[0] for p in history]))
        my = int(np.median([p[1] for p in history]))

        if len(pts) == 0:
            px, py = mx, my
        else:
            prev = pts[-1]
            px = int(0.7*prev[0] + 0.3*mx)
            py = int(0.7*prev[1] + 0.3*my)

        pts.append((px,py))
    else:
        px, py = None, None

    valid_pts = list(pts)

    # ===== HOLD DETECT =====
    if len(valid_pts) > 10:
        xs = [p[0] for p in valid_pts[-10:]]
        ys = [p[1] for p in valid_pts[-10:]]
        is_holding = (max(xs)-min(xs) < 15 and max(ys)-min(ys) < 15)
    else:
        is_holding = False

    if state == "IDLE":
        hold_counter = hold_counter+1 if is_holding else 0
        if hold_counter > HOLD_THRESHOLD:
            state = "READY"
            pts.clear()
            msg = "START DRAW"

    elif state == "READY":
        if not is_holding:
            state = "DRAW"
            pts.clear()
            msg = "DRAWING (1/2/3 save)"

    # ===== DRAW =====
    for i in range(1,len(pts)):
        cv2.line(frame, pts[i-1], pts[i], (255,0,255),2)

    if px is not None:
        cv2.circle(frame, (px,py), 6, (0,255,255), -1)

    # ===== UI =====
    cv2.putText(frame, msg, (20,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255),2)

    stat = f"C:{counts['Circle']} T:{counts['Triangle']} S:{counts['Slash']}"
    cv2.putText(frame, stat, (20,60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0),2)

    cv2.imshow("Data Collector", frame)
    cv2.imshow("Mask", mask)

    # ===== KEY =====
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break

    elif state == "DRAW":
        if key == ord('1'):
            if save_to_csv("Circle", valid_pts):
                counts["Circle"] += 1
            state, msg, hold_counter = "IDLE", "Saved Circle", 0
            pts.clear()

        elif key == ord('2'):
            if save_to_csv("Triangle", valid_pts):
                counts["Triangle"] += 1
            state, msg, hold_counter = "IDLE", "Saved Triangle", 0
            pts.clear()

        elif key == ord('3'):
            if save_to_csv("Slash", valid_pts):
                counts["Slash"] += 1
            state, msg, hold_counter = "IDLE", "Saved Slash", 0
            pts.clear()

        elif key == ord('r'):
            state, msg, hold_counter = "IDLE", "Retry", 0
            pts.clear()

cap.release()
cv2.destroyAllWindows()