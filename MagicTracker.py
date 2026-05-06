import cv2
import numpy as np
from collections import deque
import pickle
import time
import os
import random

# ==========================================
# PART 1: โหลด Sprite Frames
# ==========================================

def load_frames(folder_path, prefix, total):
    frames = []
    for i in range(total):
        filename = f"{prefix}_{str(i).zfill(5)}.png"
        path = os.path.join(folder_path, filename)
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            frames.append(img)
    return frames

def load_fireball_frames(folder_path, total):
    frames = []
    for i in range(total):
        path = os.path.join(folder_path, f"img_{i}.png")
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            frames.append(img)
    return frames

def load_potion_frames(folder_path, prefix, total):
    frames = []
    for i in range(total):
        filename = f"{prefix} - {str(i).zfill(4)}.png"
        path = os.path.join(folder_path, filename)
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            frames.append(img)
    return frames

print("Loading assets...")
BASE = "effects"

frames_A1     = load_frames(os.path.join(BASE, "animal", "Normal", "A1"), "A0", 20)
frames_A2     = load_frames(os.path.join(BASE, "animal", "Normal", "A2"), "A2", 20)
frames_A3     = load_frames(os.path.join(BASE, "animal", "Normal", "A3"), "A3", 20)
frames_A4     = load_frames(os.path.join(BASE, "animal", "Normal", "A4"), "A4", 20)
frames_A5     = load_frames(os.path.join(BASE, "animal", "Normal", "A5"), "A5", 20)
frames_A6     = load_frames(os.path.join(BASE, "animal", "Normal", "A6"), "A6", 20)
frames_A7     = load_frames(os.path.join(BASE, "animal", "Normal", "A7"), "A7", 20)
frames_A8     = load_frames(os.path.join(BASE, "animal", "Normal", "A8"), "A8", 20)
frames_A9     = load_frames(os.path.join(BASE, "animal", "Normal", "A9"), "A9", 20)
frames_fire         = load_fireball_frames(os.path.join(BASE, "fireball", "imgs_explode"), 35)
frames_fire_explode = load_fireball_frames(os.path.join(BASE, "fireball", "explode"), 33)
frames_potion = load_potion_frames(os.path.join(BASE, "Potion", "Sprites"), "Large Bottle - PURPLE", 14)
all_butterfly_frames = [frames_A1, frames_A2, frames_A3, frames_A4, frames_A5,
                        frames_A6, frames_A7, frames_A8, frames_A9]
print(f"Loaded: A1:{len(frames_A1)} A2:{len(frames_A2)} A3:{len(frames_A3)} A4:{len(frames_A4)} "
      f"A5:{len(frames_A5)} A6:{len(frames_A6)} A7:{len(frames_A7)} A8:{len(frames_A8)} "
      f"A9:{len(frames_A9)} Fire:{len(frames_fire)} FireExplode:{len(frames_fire_explode)} Potion:{len(frames_potion)}")

# ==========================================
# PART 2: Overlay Helper
# ==========================================

def overlay_png(background, sprite, x, y, scale=1.0, alpha_mul=1.0):
    if sprite is None:
        return background
    h_s, w_s = sprite.shape[:2]
    new_w = int(w_s * scale)
    new_h = int(h_s * scale)
    if new_w <= 0 or new_h <= 0:
        return background
    sprite = cv2.resize(sprite, (new_w, new_h), interpolation=cv2.INTER_AREA)
    x1 = x - new_w // 2;  y1 = y - new_h // 2
    x2 = x1 + new_w;      y2 = y1 + new_h
    bh, bw = background.shape[:2]
    sx1 = max(0, -x1);  sy1 = max(0, -y1)
    sx2 = new_w - max(0, x2 - bw)
    sy2 = new_h - max(0, y2 - bh)
    x1 = max(0, x1);  y1 = max(0, y1)
    x2 = min(bw, x2);  y2 = min(bh, y2)
    if x2 <= x1 or y2 <= y1 or sx2 <= sx1 or sy2 <= sy1:
        return background
    roi  = background[y1:y2, x1:x2]
    crop = sprite[sy1:sy2, sx1:sx2]
    if crop.shape[2] == 4:
        alpha = crop[:, :, 3:4].astype(np.float32) / 255.0 * alpha_mul
        rgb   = crop[:, :, :3].astype(np.float32)
        blended = (rgb * alpha + roi.astype(np.float32) * (1 - alpha)).astype(np.uint8)
        background[y1:y2, x1:x2] = blended
    else:
        background[y1:y2, x1:x2] = crop
    return background

# ==========================================
# PART 3: Effect Classes
# ==========================================

class Sparkle:
    """อนุภาควิงซ์ๆ ระยิบระยับ"""
    def __init__(self, x, y):
        self.x = x + random.randint(-5, 5)
        self.y = y + random.randint(-5, 5)
        self.size = random.uniform(1, 3)
        self.color = (random.randint(200, 255), random.randint(200, 255), 255) # สีขาว-ฟ้าสว่าง
        self.life = 1.0  # อายุขัย
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.05 # หายไปใน 20 เฟรม

    def draw(self, frame):
        alpha = self.life
        s = int(self.size * alpha * 2)
        if s > 0:
            # วาดเป็นรูปกากบาทเล็กๆ ให้ดูวิงซ์
            cv2.line(frame, (int(self.x-s), int(self.y)), (int(self.x+s), int(self.y)), self.color, 1)
            cv2.line(frame, (int(self.x), int(self.y-s)), (int(self.x), int(self.y+s)), self.color, 1)

class WandTrail:
    """Glow trail + วิ้งค์ระยิบระยับ"""
    def __init__(self):
        self.trail = deque(maxlen=45)
        self.sparkles = [] # เก็บรายการวิงซ์ๆ

    def update(self, px, py):
        # อัพเดท Trail หลัก
        for p in self.trail:
            p['life'] -= 0.035
        while self.trail and self.trail[0]['life'] <= 0:
            self.trail.popleft()
        
        if px is not None:
            self.trail.append({'x': px, 'y': py, 'life': 1.0})
            # สุ่มสร้างวิงซ์ๆ ออกมาเมื่อขยับไม้
            if random.random() > 0.3: # ไม่ต้องออกทุกเฟรมเดี๋ยวรก
                self.sparkles.append(Sparkle(px, py))

        # อัพเดทวิงซ์ๆ
        for s in self.sparkles:
            s.update()
        self.sparkles = [s for s in self.sparkles if s.life > 0]

    def draw(self, frame):
        # 1. วาดเส้น Trail (เหมือนเดิม)
        pts_list = list(self.trail)
        if len(pts_list) >= 2:
            overlay = frame.copy()
            for i in range(1, len(pts_list)):
                p, pp = pts_list[i], pts_list[i-1]
                alpha = p['life']
                color = (255, int(150 * alpha), 200) # ปรับสีให้ชมพู-ม่วงสว่างขึ้น
                cv2.line(overlay, (pp['x'], pp['y']), (p['x'], p['y']), color, max(1, int(alpha * 5)), cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # 2. วาดวิงซ์ๆ (Sparkles)
        for s in self.sparkles:
            s.draw(frame)

        # 3. วาดหัวไม้กายสิทธิ์ (Glow)
        if pts_list:
            head = pts_list[-1]
            if head['life'] > 0.5:
                cv2.circle(frame, (head['x'], head['y']), 5, (255, 255, 255), -1, cv2.LINE_AA)
                # เพิ่มวงแหวนรอบหัวไม้
                cv2.circle(frame, (head['x'], head['y']), 8, (255, 200, 255), 1, cv2.LINE_AA)
        
        return frame


class FireflyParticle:
    """หิ่งห้อยตัวเดียว — กระจายเต็มจอ ลอยช้าๆ กระพริบ มีหางสั้น"""
    def __init__(self, duration):
        angle       = random.uniform(0, 2 * np.pi)
        speed       = random.uniform(0.4, 1.4)
        # spawn กระจายทั่วจอ
        self.x      = random.uniform(20, 620)
        self.y      = random.uniform(20, 340)
        self.vx     = np.cos(angle) * speed
        self.vy     = np.sin(angle) * speed
        self.life   = 1.0
        self.decay  = 1.0 / (duration * 30)
        self.blink  = random.uniform(0, 2 * np.pi)
        self.blink_speed  = random.uniform(0.08, 0.18)
        self.wobble = random.uniform(0, 2 * np.pi)
        self.size   = random.uniform(2.0, 4.0)
        self.trail  = deque(maxlen=10)
        # สี: เขียว-เหลือง หิ่งห้อย (BGR)
        self.color  = (
            random.randint(80, 140),   # B
            random.randint(200, 255),  # G
            random.randint(100, 200),  # R
        )

    def update(self):
        self.blink   += self.blink_speed
        self.wobble  += 0.05
        self.vx      += np.sin(self.wobble * 0.7) * 0.04
        self.vy      += np.cos(self.wobble * 0.5) * 0.04
        self.vx      *= 0.97
        self.vy      *= 0.97
        self.x       += self.vx
        self.y       += self.vy
        self.trail.append((int(self.x), int(self.y)))
        self.life    -= self.decay
        # กระเด้งขอบเต็มจอ
        if self.x < 5 or self.x > 635:  self.vx *= -1
        if self.y < 5 or self.y > 355:  self.vy *= -1
        self.x = max(5, min(635, self.x))
        self.y = max(5, min(355, self.y))

    def draw(self, frame):
        glow_val   = (np.sin(self.blink) * 0.5 + 0.5)
        fade = self.life ** 3
        brightness = glow_val * fade
        if brightness < 0.05:
            return frame

        # วาด trail
        trail_pts = list(self.trail)
        for i in range(1, len(trail_pts)):
            t = i / len(trail_pts)
            a = t * brightness * 0.4
            overlay = frame.copy()
            cv2.line(overlay, trail_pts[i-1], trail_pts[i],
                     self.color, max(1, int(self.size * t * 0.5)), cv2.LINE_AA)
            cv2.addWeighted(overlay, a, frame, 1 - a, 0, frame)

        # glow รัศมีรอบตัว
        glow_r = int(self.size * 4)
        if glow_r > 1:
            glow_overlay = frame.copy()
            cv2.circle(glow_overlay, (int(self.x), int(self.y)),
                       glow_r, self.color, -1, cv2.LINE_AA)
            cv2.addWeighted(glow_overlay, brightness * 0.3,
                            frame, 1 - brightness * 0.3, 0, frame)

        # จุดสว่างตรงกลาง
        dot_overlay = frame.copy()
        cv2.circle(dot_overlay, (int(self.x), int(self.y)),
                   max(1, int(self.size * (0.5 + glow_val * 0.5))),
                   self.color, -1, cv2.LINE_AA)
        cv2.addWeighted(dot_overlay, brightness, frame, 1 - brightness, 0, frame)

        return frame

    def is_done(self):
        return self.life <= 0


class ButterflyEffect:
    def __init__(self, center, all_frames=None):
        self.butterflies = []
        frame_sets   = all_butterfly_frames
        stagger_step = 0.35
        total_valid  = sum(1 for f in frame_sets if f)

        idx = 0
        for fset in frame_sets:
            if not fset:
                continue
            sx = random.randint(50, 590)
            sy = random.randint(50, 310)
            vx = random.uniform(-3, 3)
            vy = random.uniform(-3, 3)
            self.butterflies.append({
                "frames":      fset,
                "frame_idx":   random.randint(0, len(fset)-1),
                "x":           float(sx),
                "y":           float(sy),
                "vx":          vx,
                "vy":          vy,
                "scale":       random.uniform(0.8, 1.5),
                "wobble":      random.uniform(0, 2 * np.pi),
                "fade_offset": idx * stagger_step,
            })
            idx += 1

        offsets = [i * stagger_step for i in range(total_valid)]
        random.shuffle(offsets)
        for i, b in enumerate(self.butterflies):
            b["fade_offset"] = offsets[i]

        self.start_time    = time.time()
        self.base_duration = 4.0
        self.duration      = self.base_duration + (total_valid - 1) * stagger_step + 1.0
        self.fade_duration = 1.0
        self.anim_timer    = time.time()
        self.fps_interval  = 0.06

        # ===== หิ่งห้อย กระจายเต็มจอ =====
        firefly_duration = self.duration
        self.fireflies = [
            FireflyParticle(firefly_duration)
            for _ in range(60)
        ]

    def draw(self, frame):
        now     = time.time()
        elapsed = now - self.start_time
        step    = (now - self.anim_timer) > self.fps_interval
        if step:
            self.anim_timer = now

        # อัพเดทและวาดหิ่งห้อย (วาดก่อน ให้อยู่ใต้ผีเสื้อ)
        for f in self.fireflies:
            f.update()
            frame = f.draw(frame)
        self.fireflies = [f for f in self.fireflies if not f.is_done()]

        # วาดผีเสื้อ
        for b in self.butterflies:
            fade_start = self.base_duration + b["fade_offset"]
            if elapsed >= fade_start + self.fade_duration:
                continue
            elif elapsed >= fade_start:
                t = (elapsed - fade_start) / self.fade_duration
                alpha_global = max(0.0, 1.0 - (t * t))
            else:
                alpha_global = 1.0

            b["wobble"] += 0.08
            b["x"] += b["vx"] + np.sin(b["wobble"]) * 1.5
            b["y"] += b["vy"] + np.cos(b["wobble"]) * 1.0

            if b["x"] < 20 or b["x"] > 620: b["vx"] *= -1
            if b["y"] < 20 or b["y"] > 340: b["vy"] *= -1
            b["x"] = max(20, min(620, b["x"]))
            b["y"] = max(20, min(340, b["y"]))

            if step:
                b["frame_idx"] = (b["frame_idx"] + 1) % len(b["frames"])

            frame = overlay_png(frame, b["frames"][b["frame_idx"]],
                                int(b["x"]), int(b["y"]),
                                scale=b["scale"], alpha_mul=alpha_global)
        return frame

    def is_done(self):
        return time.time() - self.start_time > self.duration


class FireballEffect:
    def __init__(self, wand_pos):
        self.center     = wand_pos if wand_pos is not None else (320, 180)
        self.start_time = time.time()
        self.anim_timer = time.time()
        self.frame_idx  = 0
        self.phase      = "charge"

        self.charge_fps  = 0.05
        self.explode_fps = 0.045

        total = len(frames_fire) * self.charge_fps + len(frames_fire_explode) * self.explode_fps
        self.duration = total

    def draw(self, frame):
        now    = time.time()
        cx, cy = self.center

        if self.phase == "charge":
            if now - self.anim_timer > self.charge_fps:
                self.frame_idx += 1
                self.anim_timer = now
                if self.frame_idx >= len(frames_fire):
                    self.phase     = "explode"
                    self.frame_idx = 0

            if self.phase == "charge" and frames_fire:
                t     = self.frame_idx / max(len(frames_fire) - 1, 1)
                scale = 0.4 + t * 1.8
                frame = overlay_png(frame, frames_fire[self.frame_idx], cx, cy, scale=scale)

        if self.phase == "explode" and frames_fire_explode:
            if now - self.anim_timer > self.explode_fps:
                self.frame_idx  = min(self.frame_idx + 1, len(frames_fire_explode) - 1)
                self.anim_timer = now
            t     = self.frame_idx / max(len(frames_fire_explode) - 1, 1)
            scale = 2.2 + t * 0.5
            frame = overlay_png(frame, frames_fire_explode[self.frame_idx], cx, cy, scale=scale)

        return frame

    def is_done(self):
        return time.time() - self.start_time > self.duration


class PotionEffect:
    def __init__(self, center):
        self.x            = float(center[0])
        self.y            = float(center[1])
        self.target_x     = float(center[0])
        self.target_y     = float(center[1]) - 60
        self.frame_idx    = 0
        self.start_time   = time.time()
        self.duration     = 6.0
        self.anim_timer   = time.time()
        self.fps_interval = 0.08
        self.time_offset  = random.uniform(0, 2 * np.pi)
        self.fade_start   = 5.0
        self.fade_dur     = 1.0

    def update_wand(self, wand_pos):
        if wand_pos is not None:
            self.target_x = float(wand_pos[0])
            self.target_y = float(wand_pos[1]) - 60

    def draw(self, frame):
        if not frames_potion:
            return frame

        now     = time.time()
        elapsed = now - self.start_time

        if now - self.anim_timer > self.fps_interval:
            self.frame_idx = (self.frame_idx + 1) % len(frames_potion)
            self.anim_timer = now

        lerp = 0.10
        self.x += (self.target_x - self.x) * lerp
        self.y += (self.target_y - self.y) * lerp

        sway   = np.sin((elapsed + self.time_offset) * 2.5) * 6.0
        draw_x = max(30, min(610, int(self.x + sway)))
        draw_y = max(30, min(330, int(self.y)))

        breathe = 1.0 + np.sin(elapsed * 3.0) * 0.04
        scale   = 2.5 * breathe

        if elapsed >= self.fade_start:
            t     = (elapsed - self.fade_start) / self.fade_dur
            alpha = max(0.0, 1.0 - (t * t))
        else:
            alpha = 1.0

        frame = overlay_png(frame, frames_potion[self.frame_idx],
                            draw_x, draw_y, scale=scale, alpha_mul=alpha)
        return frame

    def is_done(self):
        return time.time() - self.start_time > self.duration


# ==========================================
# PART 4: CORE SYSTEM
# ==========================================

try:
    with open('magic_wand_model.pkl', 'rb') as f:
        ai_model = pickle.load(f)
    print("AI Model Loaded!")
except:
    print("Error: Model file not found!")
    exit()

def preprocess_for_ai(points, num_points=30):
    if len(points) < 15: return None
    indices   = np.linspace(0, len(points) - 1, num_points)
    resampled = [points[int(i)] for i in indices]
    xs, ys    = [p[0] for p in resampled], [p[1] for p in resampled]
    scale     = max(max(xs)-min(xs), max(ys)-min(ys), 1e-5)
    normalized = []
    for x, y in resampled:
        normalized.extend([(x-min(xs))/scale, (y-min(ys))/scale])
    return normalized

cap = cv2.VideoCapture(0)
pts     = deque(maxlen=64)
history = deque(maxlen=5)
prev    = None

lower = np.array([40, 80, 80])
upper = np.array([89, 255, 255])

state            = "IDLE"
hold_counter     = 0
msg              = "WAITING..."
has_moved_enough = False
active_effects   = []
draw_start_time  = 0

# ===== Wand Trail =====
wand_trail = WandTrail()

# ===== เปลี่ยน True/False ตรงนี้ =====
TEST_MODE = True   # True = กด 1/2/3 เพื่อ test | False = โหมดจริง

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 360))
    hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

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
                pts_c  = c.reshape(-1,2)
                dist   = np.linalg.norm(pts_c - np.array([cx,cy]), axis=1)
                tip    = tuple(pts_c[np.argmax(dist)])

    if tip:
        history.append(tip)
        mx = int(np.median([p[0] for p in history]))
        my = int(np.median([p[1] for p in history]))
        if prev is None: px, py = mx, my
        else:
            px = int(0.6*prev[0] + 0.4*mx)
            py = int(0.6*prev[1] + 0.4*my)
        prev = (px, py)
        pts.append((px, py))
    else:
        px, py = None, None
        prev   = None

    valid_pts = list(pts)
    if len(valid_pts) > 10:
        xs = [p[0] for p in valid_pts[-10:]]
        ys = [p[1] for p in valid_pts[-10:]]
        is_holding = (max(xs)-min(xs) < 15 and max(ys)-min(ys) < 15)
    else:
        is_holding = False

# เพิ่มตัวแปรไว้เก็บจุดที่เริ่มง้าง (ไว้นอก Loop หรือก่อนเข้า State Machine)
    # anchor_pt = None 

    # ==========================================
    # --- FIXED STATE MACHINE (START-ANCHOR SYSTEM) ---
    # ==========================================
    if state == "IDLE":
        if is_holding: hold_counter += 1
        else:          hold_counter  = 0
        if hold_counter > 15:
            state = "READY"
            pts.clear()
            msg = "READY TO CAST!"

    elif state == "READY":
        if not is_holding: 
            # เมื่อเลิก Hold ให้จำ "จุดสมอ" (Anchor) ไว้ก่อน แต่ยังไม่เริ่ม DRAW
            anchor_pt = (px, py) if px is not None else None
            state = "START_MOVING"
            msg = "START MOVING..."

    elif state == "START_MOVING":
        if px is not None and anchor_pt is not None:
            # คำนวณว่ามือขยับห่างจากจุดสมอเกิน 35 พิกเซลหรือยัง
            dist_from_anchor = np.linalg.norm(np.array([px, py]) - np.array(anchor_pt))
            
            if dist_from_anchor > 35:
                # ถ้าห่างพอแล้ว ถึงจะเริ่มเข้าสถานะ DRAW ของจริง
                state = "DRAW"
                pts.clear()
                pts.append(anchor_pt) # ใส่จุดเริ่มเข้าไป
                pts.append((px, py))  # ใส่จุดปัจจุบัน
                draw_start_time = time.time()
                has_moved_enough = False
                msg = "DRAWING..."
        
        # ถ้าเผลอนิ่งนานเกินไปในขณะที่ยังง้างไม่เสร็จ ให้กลับไป IDLE
        if is_holding: 
            state = "IDLE"

    elif state == "DRAW":
        elapsed = time.time() - draw_start_time
        
        if len(valid_pts) > 1:
            # เช็คระยะลากรวม (จากจุดเริ่ม DRAW)
            dist_total = np.linalg.norm(np.array(valid_pts[-1]) - np.array(valid_pts[0]))
            if dist_total > 60:
                has_moved_enough = True

        # ตัดสินใจเมื่อ "นิ่ง" หลังจากเริ่มวาดไปแล้วอย่างน้อย 0.6 วินาที
        if is_holding and elapsed > 0.6:
            if has_moved_enough and len(valid_pts) > 20:
                input_ai = preprocess_for_ai(valid_pts)
                if input_ai:
                    prediction = ai_model.predict(np.array([input_ai]))[0]
                    confidence = np.max(ai_model.predict_proba(np.array([input_ai]))[0])
                    
                    if confidence > 0.5:
                        center_pt = valid_pts[len(valid_pts)//2]
                        if prediction == "Circle": active_effects.append(ButterflyEffect(center_pt))
                        elif prediction == "Triangle": active_effects.append(PotionEffect(center_pt))
                        elif prediction == "Slash": active_effects.append(FireballEffect((px, py)))
                        msg = f"SUCCESS: {prediction}!"
                    else: msg = "UNCLEAR"
            else:
                msg = "TOO SHORT!"
            
            state, hold_counter, pts = "IDLE", 0, deque(maxlen=64)
            history.clear()

    # --- อัพเดท wand position ให้ PotionEffect ---
    wand_pos = (px, py) if px is not None else None
    for effect in active_effects:
        if isinstance(effect, PotionEffect):
            effect.update_wand(wand_pos)

    # --- วาด Wand Trail ก่อน ---
    wand_trail.update(px, py)
    frame = wand_trail.draw(frame)

    # --- วาด Effects ---
    active_effects = [e for e in active_effects if not e.is_done()]
    for effect in active_effects:
        frame = effect.draw(frame)

    # Trail เส้นวาด gesture (ตอน DRAW เท่านั้น)
    if state == "DRAW":
        for i in range(1, len(pts)):
            cv2.line(frame, pts[i-1], pts[i], (0, 255, 255), 2)

    # UI
    cv2.putText(frame, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"State: {state}", (20, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,180,180), 1)

    if TEST_MODE:
        cv2.putText(frame, "[1] Butterfly  [2] Potion  [3] Fireball  [q] Quit",
                    (10, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)

    cv2.imshow("AI Magic Wand", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

    if TEST_MODE:
        center = (320, 180)
        if key == ord('1'):
            active_effects.append(ButterflyEffect(center))
            msg = "CAST: Circle!"
        elif key == ord('2'):
            active_effects.append(PotionEffect(center))
            msg = "CAST: Triangle!"
        elif key == ord('3'):
            wand_now = (px, py) if px is not None else center
            active_effects.append(FireballEffect(wand_now))
            msg = "CAST: Slash!"

cap.release()
cv2.destroyAllWindows()