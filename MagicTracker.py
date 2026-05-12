import cv2
import numpy as np
from collections import deque
import pickle
import time
import os
import random
import math

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
        self.color = (random.randint(200, 255), random.randint(200, 255), 255)
        self.life = 1.0
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.05

    def draw(self, frame):
        alpha = self.life
        s = int(self.size * alpha * 2)
        if s > 0:
            ix, iy = int(self.x), int(self.y)
            cv2.line(frame, (ix - s, iy), (ix + s, iy), self.color, 1)
            cv2.line(frame, (ix, iy - s), (ix, iy + s), self.color, 1)


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

    def update(self, px, py):
        # อัพเดท Trail หลัก
        for p in self.trail:
            p['life'] -= 0.035
        while self.trail and self.trail[0]['life'] <= 0:
            self.trail.popleft()
        if px is not None:
            self.trail.append({'x': px, 'y': py, 'life': 1.0})

    def draw(self, frame):
        pts_list = list(self.trail)
        if len(pts_list) < 2:
            return frame
        overlay = frame.copy()
        for i in range(1, len(pts_list)):
            p  = pts_list[i]
            pp = pts_list[i - 1]
            if p['life'] <= 0:
                continue
            alpha = p['life']
            b = int(255)
            g = int(60  * alpha)
            r = int(120 + 135 * (1 - alpha))
            color = (b, g, r)
            thickness = max(1, int(alpha * 7))
            cv2.line(overlay, (pp['x'], pp['y']), (p['x'], p['y']),
                     color, thickness, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        if pts_list:
            head = pts_list[-1]
            if head['life'] > 0.5:
                for radius, alpha_layer in [(14, 0.18), (9, 0.35), (5, 0.7)]:
                    glow = frame.copy()
                    cv2.circle(glow, (head['x'], head['y']), radius, (255, 80, 220), -1, cv2.LINE_AA)
                    cv2.addWeighted(glow, alpha_layer, frame, 1 - alpha_layer, 0, frame)
                cv2.circle(frame, (head['x'], head['y']), 3, (255, 255, 255), -1, cv2.LINE_AA)
        return frame


class FireflyParticle:
    """หิ่งห้อยตัวเดียว — กระจายเต็มจอ ลอยช้าๆ กระพริบ มีหางสั้น"""
    def __init__(self, duration):
        angle      = random.uniform(0, 2 * math.pi)
        speed      = random.uniform(0.4, 1.4)
        self.x     = random.uniform(20, 620)
        self.y     = random.uniform(20, 340)
        # OPT: use math.cos/sin — faster than np for single floats
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.life  = 1.0
        self.decay = 1.0 / (duration * 30)
        self.blink = random.uniform(0, 2 * math.pi)
        self.blink_speed = random.uniform(0.08, 0.18)
        self.wobble = random.uniform(0, 2 * math.pi)
        self.size  = random.uniform(2.0, 4.0)
        self.trail = deque(maxlen=10)
        self.color = (
            random.randint(80, 140),
            random.randint(200, 255),
            random.randint(100, 200),
        )

    def update(self):
        self.blink  += self.blink_speed
        self.wobble += 0.05
        # OPT: math.sin/cos instead of np.sin/cos for scalars
        self.vx += math.sin(self.wobble * 0.7) * 0.04
        self.vy += math.cos(self.wobble * 0.5) * 0.04
        self.vx *= 0.97
        self.vy *= 0.97
        self.x  += self.vx
        self.y  += self.vy
        self.trail.append((int(self.x), int(self.y)))
        self.life -= self.decay
        if self.x < 5 or self.x > 635: self.vx *= -1
        if self.y < 5 or self.y > 355: self.vy *= -1
        self.x = max(5, min(635, self.x))
        self.y = max(5, min(355, self.y))

    def draw(self, frame):
        # OPT: math.sin instead of np.sin for scalar
        glow_val   = (math.sin(self.blink) * 0.5 + 0.5)
        fade       = self.life ** 3
        brightness = glow_val * fade
        if brightness < 0.05:
            return frame

        # OPT: draw trail directly — no frame.copy() per segment
        # Bake alpha into color instead of addWeighted (was 600 copies/frame for 60 fireflies)
        trail_pts = list(self.trail)
        for i in range(1, len(trail_pts)):
            t = i / len(trail_pts)
            a = t * brightness * 0.4
            dimmed = (
                int(self.color[0] * a),
                int(self.color[1] * a),
                int(self.color[2] * a),
            )
            cv2.line(frame, trail_pts[i - 1], trail_pts[i],
                     dimmed, max(1, int(self.size * t * 0.5)), cv2.LINE_AA)

        # glow รัศมีรอบตัว — OPT: skip frame.copy(), draw with dimmed color
        glow_r = int(self.size * 4)
        if glow_r > 1:
            g = brightness * 0.3
            glow_color = (int(self.color[0] * g), int(self.color[1] * g), int(self.color[2] * g))
            cv2.circle(frame, (int(self.x), int(self.y)), glow_r, glow_color, -1, cv2.LINE_AA)

        # จุดสว่างตรงกลาง — OPT: skip frame.copy(), scale color by brightness
        dot_r = max(1, int(self.size * (0.5 + glow_val * 0.5)))
        dot_color = (
            int(self.color[0] * brightness),
            int(self.color[1] * brightness),
            int(self.color[2] * brightness),
        )
        cv2.circle(frame, (int(self.x), int(self.y)), dot_r, dot_color, -1, cv2.LINE_AA)

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
                "frame_idx":   random.randint(0, len(fset) - 1),
                "x":           float(sx),
                "y":           float(sy),
                "vx":          vx,
                "vy":          vy,
                "scale":       random.uniform(0.8, 1.5),
                "wobble":      random.uniform(0, 2 * math.pi),
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
        # OPT: precompute end time once instead of calling time.time() every is_done() check
        self.end_time      = self.start_time + self.duration

        firefly_duration = self.duration
        self.fireflies = [FireflyParticle(firefly_duration) for _ in range(40)]  # OPT: 60→40, visually similar

    def draw(self, frame):
        now     = time.time()
        elapsed = now - self.start_time
        step    = (now - self.anim_timer) > self.fps_interval
        if step:
            self.anim_timer = now

        for f in self.fireflies:
            f.update()
            frame = f.draw(frame)
        self.fireflies = [f for f in self.fireflies if not f.is_done()]

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
            # OPT: math.sin/cos instead of np.sin/cos for scalars
            b["x"] += b["vx"] + math.sin(b["wobble"]) * 1.5
            b["y"] += b["vy"] + math.cos(b["wobble"]) * 1.0

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
        # OPT: compare against precomputed end_time instead of computing duration every call
        return time.time() > self.end_time


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
        # OPT: precompute end time
        self.end_time = self.start_time + self.duration

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
        return time.time() > self.end_time


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
        self.time_offset  = random.uniform(0, 2 * math.pi)
        self.fade_start   = 5.0
        self.fade_dur     = 1.0
        # OPT: precompute end time
        self.end_time     = self.start_time + self.duration

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

        # OPT: math.sin instead of np.sin for scalar
        sway   = math.sin((elapsed + self.time_offset) * 2.5) * 6.0
        draw_x = max(30, min(610, int(self.x + sway)))
        draw_y = max(30, min(330, int(self.y)))

        breathe = 1.0 + math.sin(elapsed * 3.0) * 0.04
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
        return time.time() > self.end_time

# ==========================================
# PART 4: UI Helper
# ==========================================

_tutorial_start = time.time()

def draw_tutorial_panel(frame):
    """วาด tutorial สอนวาดท่าทางบนหน้า UI (มุมขวาล่าง)"""
    h, w = frame.shape[:2]

    panel_x, panel_y = w - 210, 56
    panel_w, panel_h = 205, 170

    # OPT: draw semi-transparent panel without frame.copy() by drawing filled rect
    # then blending only the panel region — much cheaper than copying whole frame
    sub = frame[panel_y:panel_y + panel_h, panel_x:panel_x + panel_w]
    rect = np.full(sub.shape, (20, 10, 40), dtype=np.uint8)
    cv2.addWeighted(rect, 0.70, sub, 0.30, 0, sub)
    frame[panel_y:panel_y + panel_h, panel_x:panel_x + panel_w] = sub

    cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (120, 40, 180), 1)

    cv2.putText(frame, "HOW TO CAST", (panel_x + 8, panel_y + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 80, 255), 1)
    cv2.line(frame, (panel_x, panel_y + 22), (panel_x + panel_w, panel_y + 22), (80, 30, 120), 1)

    t = (time.time() - _tutorial_start) % 2.0 / 2.0

    slot_cx = [panel_x + 36, panel_x + 105, panel_x + 174]
    slot_y  = panel_y + 75
    label_y = panel_y + 125

    labels = ["Circle", "Triangle", "Line"]
    colors = [(0, 220, 255), (100, 255, 100), (255, 160, 50)]

    for i, (cx, label, col) in enumerate(zip(slot_cx, labels, colors)):
        if label == "Circle":
            radius = 20
            cv2.circle(frame, (cx, slot_y), radius, (60, 60, 80), 1, cv2.LINE_AA)
            sweep = int(270 * t)
            if sweep > 5:
                cv2.ellipse(frame, (cx, slot_y), (radius, radius), -90, 0, sweep, col, 2, cv2.LINE_AA)
            cv2.circle(frame, (cx, slot_y - radius), 3, (255, 255, 255), -1, cv2.LINE_AA)
            # OPT: math.radians/cos/sin instead of np for scalars
            ang = math.radians(-90 + sweep)
            tip_x = int(cx + radius * math.cos(ang))
            tip_y = int(slot_y + radius * math.sin(ang))
            perp  = ang + math.pi / 2
            ax1 = int(tip_x - 5 * math.cos(ang) + 3 * math.cos(perp))
            ay1 = int(tip_y - 5 * math.sin(ang) + 3 * math.sin(perp))
            ax2 = int(tip_x - 5 * math.cos(ang) - 3 * math.cos(perp))
            ay2 = int(tip_y - 5 * math.sin(ang) - 3 * math.sin(perp))
            if sweep > 10:
                cv2.line(frame, (tip_x, tip_y), (ax1, ay1), col, 2, cv2.LINE_AA)
                cv2.line(frame, (tip_x, tip_y), (ax2, ay2), col, 2, cv2.LINE_AA)

        elif label == "Triangle":
            r = 20
            pts_tri = [
                (cx,     slot_y - r),
                (cx - r, slot_y + r),
                (cx + r, slot_y + r),
            ]
            for j in range(3):
                cv2.line(frame, pts_tri[j], pts_tri[(j + 1) % 3], (60, 60, 80), 1, cv2.LINE_AA)
            total_edges = 3
            progress = t * total_edges
            seg = int(progress)
            frac = progress - seg
            for j in range(min(seg, total_edges)):
                cv2.line(frame, pts_tri[j], pts_tri[(j + 1) % 3], col, 2, cv2.LINE_AA)
            if seg < total_edges:
                p0   = np.array(pts_tri[seg])
                p1   = np.array(pts_tri[(seg + 1) % 3])
                pmid = (p0 + (p1 - p0) * frac).astype(int)
                cv2.line(frame, tuple(p0), tuple(pmid), col, 2, cv2.LINE_AA)
            cv2.circle(frame, pts_tri[0], 3, (255, 255, 255), -1, cv2.LINE_AA)

        elif label == "Line":
            lx1, lx2 = cx - 22, cx + 22
            ly = slot_y
            cv2.line(frame, (lx1, ly), (lx2, ly), (60, 60, 80), 1, cv2.LINE_AA)
            cur_x = int(lx1 + (lx2 - lx1) * t)
            cv2.line(frame, (lx1, ly), (cur_x, ly), col, 2, cv2.LINE_AA)
            if t > 0.05:
                cv2.line(frame, (cur_x, ly), (cur_x - 5, ly - 4), col, 2, cv2.LINE_AA)
                cv2.line(frame, (cur_x, ly), (cur_x - 5, ly + 4), col, 2, cv2.LINE_AA)
            cv2.circle(frame, (lx1, ly), 3, (255, 255, 255), -1, cv2.LINE_AA)

        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        cv2.putText(frame, label, (cx - tw // 2, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv2.LINE_AA)

    return frame


def draw_ui(frame, msg, state, hold_counter, TEST_MODE):
    h, w = frame.shape[:2]

    # OPT: blend only the bar region instead of copying the whole frame
    bar_h = 48
    sub_top = frame[0:bar_h, 0:w]
    rect_top = np.full(sub_top.shape, (20, 10, 40), dtype=np.uint8)
    cv2.addWeighted(rect_top, 0.55, sub_top, 0.45, 0, sub_top)
    frame[0:bar_h, 0:w] = sub_top
    cv2.line(frame, (0, bar_h), (w, bar_h), (180, 60, 255), 1)

    msg_color = (255, 255, 255)
    color_map = {
        "WAITING...":      (160, 100, 255),
        "READY TO CAST!":  (0, 220, 255),
        "CASTING...":      (0, 255, 200),
        "TOO SHORT!":      (0, 100, 255),
        "UNCLEAR GESTURE": (80, 80, 255),
    }
    for k, v in color_map.items():
        if k in msg:
            msg_color = v
            break
    if msg.startswith("CAST:"):
        msg_color = (50, 255, 180)

    cv2.putText(frame, msg, (22, 33), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 0, 0), 3)
    cv2.putText(frame, msg, (20, 31), cv2.FONT_HERSHEY_DUPLEX, 0.85, msg_color, 2)

    badge_txt   = f"[ {state} ]"
    badge_color = {"IDLE": (130, 50, 200), "READY": (0, 180, 220), "DRAW": (0, 210, 140)}.get(state, (150, 150, 150))
    (tw, _), _  = cv2.getTextSize(badge_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    bx = w - tw - 14
    cv2.putText(frame, badge_txt, (bx + 1, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(frame, badge_txt, (bx,     30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, badge_color, 1)

    # OPT: blend only the bottom bar region
    bot_y = h - 36
    sub_bot = frame[bot_y:h, 0:w]
    rect_bot = np.full(sub_bot.shape, (20, 10, 40), dtype=np.uint8)
    cv2.addWeighted(rect_bot, 0.55, sub_bot, 0.45, 0, sub_bot)
    frame[bot_y:h, 0:w] = sub_bot
    cv2.line(frame, (0, bot_y), (w, bot_y), (180, 60, 255), 1)

    if state == "IDLE" and hold_counter > 0:
        progress = min(hold_counter / 90, 1.0)
        bar_w    = int((w - 40) * progress)
        cv2.rectangle(frame, (20, bot_y + 6), (20 + bar_w, bot_y + 14), (200, 80, 255), -1)
        cv2.rectangle(frame, (20, bot_y + 6), (w - 20,     bot_y + 14), (100, 40, 140), 1)
        cv2.putText(frame, f"Charging... {int(progress * 100)}%",
                    (22, bot_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 120, 255), 1)
    elif TEST_MODE:
        hint = "[ 1 ] Butterfly    [ 2 ] Potion    [ 3 ] Fireball    [ Q ] Quit"
        cv2.putText(frame, hint, (14, bot_y + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 100, 220), 1)

    dc = (120, 40, 180)
    cv2.line(frame, (0, bar_h + 2),   (12, bar_h + 2),   dc, 1)
    cv2.line(frame, (0, bar_h + 2),   (0,  bar_h + 14),  dc, 1)
    cv2.line(frame, (w - 1, bar_h + 2), (w - 13, bar_h + 2), dc, 1)
    cv2.line(frame, (w - 1, bar_h + 2), (w - 1,  bar_h + 14), dc, 1)
    cv2.line(frame, (0,   bot_y - 2), (12,   bot_y - 2), dc, 1)
    cv2.line(frame, (0,   bot_y - 2), (0,    bot_y - 14), dc, 1)
    cv2.line(frame, (w - 1, bot_y - 2), (w - 13, bot_y - 2), dc, 1)
    cv2.line(frame, (w - 1, bot_y - 2), (w - 1,  bot_y - 14), dc, 1)

    frame = draw_tutorial_panel(frame)

    return frame

# ==========================================
# PART 5: Charge Spark Effect
# ==========================================

def draw_charge_sparks(frame, px, py, charge):
    """Spark burst that grows denser and wilder as charge (0.0–1.0) fills up."""
    if px is None or py is None or charge <= 0:
        return frame

    num_sparks  = int(4 + charge * 14)       # 4 sparks at start → 18 at full
    max_len     = 10 + charge * 28            # sparks grow longer as charge builds
    base_hue_b  = int(180 + charge * 75)      # blue channel shifts purple → white

    for _ in range(num_sparks):
        angle  = random.uniform(0, 2 * math.pi)
        length = random.uniform(max_len * 0.4, max_len)
        x2     = int(px + math.cos(angle) * length)
        y2     = int(py + math.sin(angle) * length)

        # Color: purple-blue tones, brightening toward white at full charge
        b = min(255, base_hue_b + random.randint(0, 40))
        g = min(255, int(100 * charge + random.randint(0, 60)))
        r = min(255, int(160 + charge * 95))
        color = (b, g, r)  # BGR

        cv2.line(frame, (px, py), (x2, y2), color, 1, cv2.LINE_AA)

    # Bright core dot — grows slightly with charge
    core_r = max(2, int(3 + charge * 4))
    cv2.circle(frame, (px, py), core_r + 2, (int(180 * charge), int(100 * charge), 255), -1, cv2.LINE_AA)
    cv2.circle(frame, (px, py), core_r,     (255, 255, 255), -1, cv2.LINE_AA)

    return frame

# ==========================================
# PART 6: CORE SYSTEM
# ==========================================

try:
    with open('magic_wand_model.pkl', 'rb') as f:
        ai_model = pickle.load(f)
    print("AI Model Loaded!")
except Exception:
    print("Error: Model file not found!")
    exit()

def preprocess_for_ai(points, num_points=50):
    """OPT: pure numpy instead of list comprehensions — faster resampling & normalization"""
    if len(points) < 15:
        return None
    pts_arr  = np.array(points, dtype=np.float32)
    indices  = np.linspace(0, len(points) - 1, num_points).astype(int)
    resampled = pts_arr[indices]                          # shape (50, 2)
    mins  = resampled.min(axis=0)                         # [min_x, min_y]
    scale = max(np.ptp(resampled, axis=0).max(), 1e-5)    # np.ptp = max-min
    normalized = ((resampled - mins) / scale).flatten()   # shape (100,)
    return normalized.tolist()

# OPT: fixed camera index + removed Windows-only CAP_DSHOW flag
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open camera!")
    exit()

cv2.namedWindow("AI Magic Wand", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("AI Magic Wand", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

pts     = deque(maxlen=64)
history = deque(maxlen=5)
prev    = None

lower = np.array([40, 80, 80])
upper = np.array([89, 255, 255])

# OPT: precompute morphology kernel outside the loop
morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

state            = "IDLE"
hold_counter     = 0
release_counter  = 0   # counts how many frames wand has been moving after READY
msg              = "WAITING..."
has_moved_enough = False
active_effects   = []
draw_start_time  = 0

wand_trail = WandTrail()

TEST_MODE = True   # True = กด 1/2/3 เพื่อ test | False = โหมดจริง

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 360))
    hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower, upper)
    # OPT: one morphologyEx call instead of separate erode + dilate
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, morph_kernel)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tip = None
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) > 200:
            pts_c = c.reshape(-1, 2)
            tip   = tuple(pts_c[np.argmin(pts_c[:, 1])])

    if tip:
        history.append(tip)
        mx = int(np.median([p[0] for p in history]))
        my = int(np.median([p[1] for p in history]))
        if prev is None:
            px, py = mx, my
        else:
            px = int(0.7 * prev[0] + 0.3 * mx)
            py = int(0.7 * prev[1] + 0.3 * my)
        prev = (px, py)
        pts.append((px, py))
    else:
        px, py = None, None
        prev   = None

    valid_pts = list(pts)
    if len(valid_pts) > 10:
        recent = valid_pts[-10:]
        xs = [p[0] for p in recent]
        ys = [p[1] for p in recent]
        is_holding = (max(xs) - min(xs) < 15 and max(ys) - min(ys) < 15)
    else:
        is_holding = False

    # STATE MACHINE
    if state == "IDLE":
        if is_holding: hold_counter += 1
        else:          hold_counter  = 0
        if hold_counter > 30:  # ~1 sec at 30fps (was 15 = ~0.5 sec)
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
        if len(valid_pts) > 1:
            if np.linalg.norm(np.array(valid_pts[-1]) - np.array(valid_pts[0])) > 40:
                has_moved_enough = True
        if is_holding:
            if has_moved_enough and len(valid_pts) > 20:
                input_ai = preprocess_for_ai(valid_pts)

                if input_ai:
                    pred_probs = ai_model.predict_proba(np.array([input_ai]))[0]
                    prediction = ai_model.predict(np.array([input_ai]))[0]
                    confidence = np.max(ai_model.predict_proba(np.array([input_ai]))[0])
                    if confidence > 0.5:
                        center_pt = valid_pts[len(valid_pts)//2]
                        if prediction == "Circle":
                            active_effects.append(ButterflyEffect(center_pt))
                        elif prediction == "Triangle":
                            active_effects.append(PotionEffect(center_pt))
                        elif prediction == "Slash":
                            wand_now = (px, py) if px is not None else center_pt
                            active_effects.append(FireballEffect(wand_now))
                        msg = f"CAST: {prediction}! ({confidence:.0%})"
                    else:
                        msg = "UNCLEAR GESTURE"
            else:
                msg = "TOO SHORT!"
            state        = "IDLE"
            hold_counter = 0
            pts.clear()

    # --- อัพเดท wand position ให้ PotionEffect ---
    wand_pos = (px, py) if px is not None else None
    for effect in active_effects:
        if isinstance(effect, PotionEffect):
            effect.update_wand(wand_pos)

    # --- วาด Wand Trail ก่อน ---
    wand_trail.update(px, py)
    frame = wand_trail.draw(frame)

    # --- Charge sparks (only while holding still in IDLE) ---
    if state == "IDLE" and hold_counter > 0 and px is not None:
        charge = min(hold_counter / 90, 1.0)
        frame  = draw_charge_sparks(frame, px, py, charge)

    # --- วาด Effects ---
    active_effects = [e for e in active_effects if not e.is_done()]
    for effect in active_effects:
        frame = effect.draw(frame)

    # Trail เส้นวาด gesture (ตอน DRAW เท่านั้น)
    if state == "DRAW":
        for i in range(1, len(pts)):
            alpha = i / len(pts)  # fade from dim to bright toward the tip
            color = (int(255 * alpha), int(120 * alpha), int(220 * alpha))  # purple, BGR
            cv2.line(frame, pts[i - 1], pts[i], color, 2, cv2.LINE_AA)

    # UI
    frame = draw_ui(frame, msg, state, hold_counter, TEST_MODE)

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