import cv2
import numpy as np
from collections import deque
import pickle
import time
import os
import random
import math
import pygame

# ==========================================
# SOUND SYSTEM
# ==========================================
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()
pygame.mixer.set_num_channels(8)   # เปิด 8 channel พร้อมกัน

SOUND_DIR = "sound"

def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    try:
        sound = pygame.mixer.Sound(path)
        print(f"Sound loaded: {filename}")
        return sound
    except Exception as e:
        print(f"Sound NOT loaded ({filename}): {e}")
        return None

snd_fairy_dust    = load_sound("fairy_dust.mp3")
snd_butterfly     = load_sound("butterflysound.mp3")
snd_firecharge    = load_sound("firecharge.mp3")
snd_fireexplosion = load_sound("fireexplosion.mp3")
snd_potion        = load_sound("potionsound.mp3")

# ==========================================
# SOUND MANAGER
# ==========================================
# จองช่องตายตัวให้แต่ละประเภท:
#   CH 0 — fairy_dust   (priority ต่ำสุด, โดนแทนทีหลัง)
#   CH 1 — butterfly
#   CH 2 — firecharge + fireexplosion (ผูกด้วยกัน ไม่ตัดกันเอง)
#   CH 3 — potion
#   CH 4-7 — สำรอง (ถ้า effect เดียวกัน spawn ซ้ำพร้อมกัน)
#
# Logic การเล่น:
#   1. ลองใช้ channel หลักของ sound นั้นก่อน
#   2. ถ้า channel หลักยังไม่ว่าง → ค้นหา channel สำรอง (4-7) ที่ว่าง
#   3. ถ้าสำรองเต็มหมด → แทนที่ channel priority ต่ำสุด (fairy_dust ก่อน)

CH_FAIRY     = pygame.mixer.Channel(0)
CH_BUTTERFLY = pygame.mixer.Channel(1)
CH_FIRE      = pygame.mixer.Channel(2)   # ใช้ร่วมกันระหว่าง charge+explode
CH_POTION    = pygame.mixer.Channel(3)
CH_SPARE     = [pygame.mixer.Channel(i) for i in range(4, 8)]

# map เสียง → channel หลัก + priority (ยิ่งสูง = สำคัญกว่า, โดนแทนที่ทีหลัง)
_SOUND_META = {
    "fairy":     {"ch": CH_FAIRY,     "priority": 1},
    "butterfly": {"ch": CH_BUTTERFLY, "priority": 3},
    "fire":      {"ch": CH_FIRE,      "priority": 4},  # charge & explode ใช้ key เดียวกัน
    "potion":    {"ch": CH_POTION,    "priority": 3},
}

# ติดตามว่า channel สำรองแต่ละช่องเล่น priority อะไรอยู่ (เพื่อแทนที่ถูกต้อง)
_spare_priority = [0] * len(CH_SPARE)

def _play_on_channel(ch, sound, priority, spare_fallback=True):
    """เล่น sound บน channel ที่กำหนด
    ถ้า channel ไม่ว่าง ให้หา spare channel
    ถ้า spare เต็ม ให้แทนที่ channel priority ต่ำสุด"""
    if sound is None:
        return

    if not ch.get_busy():
        # channel หลักว่าง — เล่นได้เลย
        ch.play(sound)
        return

    if spare_fallback:
        # หา spare channel ที่ว่าง
        for i, sp in enumerate(CH_SPARE):
            if not sp.get_busy():
                sp.play(sound)
                _spare_priority[i] = priority
                return

        # spare เต็มหมด → แทนที่ spare ที่ priority ต่ำสุด
        min_idx = int(np.argmin(_spare_priority))
        CH_SPARE[min_idx].stop()
        CH_SPARE[min_idx].play(sound)
        _spare_priority[min_idx] = priority

    # ถ้า spare_fallback=False (เช่น fairy) ก็แค่ข้ามไปเลย ไม่แย่งใคร

# ========== ฟังก์ชัน play สาธารณะ ==========

_last_fairy_time = 0.0
_fairy_interval  = 0.8  # วินาที

def any_effect_playing():
    """ตรวจว่ามี effect (butterfly/fire/potion) เล่นอยู่ไหม"""
    return CH_BUTTERFLY.get_busy() or CH_FIRE.get_busy() or CH_POTION.get_busy()

def play_fairy_dust():
    """เล่น fairy_dust เป็นระยะๆ — หยุดทันทีถ้ามี effect เล่นอยู่"""
    global _last_fairy_time
    if snd_fairy_dust is None:
        return
    # มี effect เล่นอยู่ → หยุด fairy แล้วออกไปเลย
    if any_effect_playing():
        if CH_FAIRY.get_busy():
            CH_FAIRY.stop()
        return
    now = time.time()
    if now - _last_fairy_time >= _fairy_interval:
        _last_fairy_time = now
        _play_on_channel(CH_FAIRY, snd_fairy_dust, priority=1, spare_fallback=False)

def play_butterfly():
    _play_on_channel(CH_BUTTERFLY, snd_butterfly, priority=3)

def play_firecharge():
    """เริ่ม charge — หยุด explode เก่าในช่องไฟก่อน (ถ้ามี) แล้วเล่น charge"""
    if snd_firecharge is None:
        return
    CH_FIRE.stop()
    CH_FIRE.play(snd_firecharge)

def play_fireexplosion():
    """ระเบิด — หยุด charge แล้วเล่น explosion ในช่องเดิม"""
    if snd_fireexplosion is None:
        return
    CH_FIRE.stop()
    CH_FIRE.play(snd_fireexplosion)

def play_potion():
    _play_on_channel(CH_POTION, snd_potion, priority=3)

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
        self.trail    = deque(maxlen=45)
        self.sparkles = []   # fix: was missing — caused AttributeError on first update()

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
            # เล่นเสียง fairy_dust เมื่อขยับไม้
            play_fairy_dust()

        # อัพเดทวิงซ์ๆ
        for s in self.sparkles:
            s.update()
        self.sparkles = [s for s in self.sparkles if s.life > 0]

    def draw(self, frame):
        pts_list = list(self.trail)
        if len(pts_list) < 2:
            return frame
        # OPT: bake alpha into color — no frame.copy() per segment
        for i in range(1, len(pts_list)):
            p  = pts_list[i]
            pp = pts_list[i - 1]
            if p['life'] <= 0:
                continue
            alpha = p['life'] * 0.75   # replicate the 0.75 blend weight
            b = int(255 * alpha)
            g = int(60  * alpha * alpha)
            r = int((120 + 135 * (1 - alpha)) * alpha)
            color = (b, g, r)
            thickness = max(1, int(p['life'] * 7))
            cv2.line(frame, (pp['x'], pp['y']), (p['x'], p['y']),
                     color, thickness, cv2.LINE_AA)
        if pts_list:
            head = pts_list[-1]
            if head['life'] > 0.5:
                # OPT: bake glow alpha into color instead of frame.copy() per layer
                for radius, a in [(14, 0.18), (9, 0.35), (5, 0.7)]:
                    gc = (int(255 * a), int(80 * a), int(220 * a))
                    cv2.circle(frame, (head['x'], head['y']), radius, gc, -1, cv2.LINE_AA)
                cv2.circle(frame, (head['x'], head['y']), 3, (255, 255, 255), -1, cv2.LINE_AA)
        # fix: sparkles were updated every frame but never drawn
        for sp in self.sparkles:
            sp.draw(frame)
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

        # เล่นเสียงผีเสื้อทันทีที่ spawn
        play_butterfly()

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
        done = time.time() - self.start_time > self.duration
        if done and CH_BUTTERFLY.get_busy():
            CH_BUTTERFLY.stop()
        return done


class FireballEffect:
    def __init__(self, wand_pos):
        self.center     = wand_pos if wand_pos is not None else (320, 180)
        self.start_time = time.time()
        self.anim_timer = time.time()
        self.frame_idx  = 0
        self.phase      = "charge"
        self._explode_sound_played = False  # ป้องกันเสียงระเบิดเล่นซ้ำ

        self.charge_fps  = 0.05
        self.explode_fps = 0.045

        total = len(frames_fire) * self.charge_fps + len(frames_fire_explode) * self.explode_fps
        self.duration = total
        # OPT: precompute end time
        self.end_time = self.start_time + self.duration

        # เล่นเสียงชาร์จทันทีที่ spawn
        play_firecharge()

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
                    # เล่นเสียงระเบิดเมื่อเข้า phase explode
                    if not self._explode_sound_played:
                        play_fireexplosion()
                        self._explode_sound_played = True

            if self.phase == "charge" and frames_fire:
                t     = self.frame_idx / max(len(frames_fire) - 1, 1)
                scale = 0.4 + t * 1.8
                frame = overlay_png(frame, frames_fire[self.frame_idx], cx, cy, scale=scale)

        if self.phase == "explode" and frames_fire_explode:
            if now - self.anim_timer > self.explode_fps:
                if self.frame_idx < len(frames_fire_explode) - 1:
                    self.frame_idx += 1
                    self.anim_timer = now  # only advance timer while there are frames left
            t     = self.frame_idx / max(len(frames_fire_explode) - 1, 1)
            scale = 2.2 + t * 0.5
            frame = overlay_png(frame, frames_fire_explode[self.frame_idx], cx, cy, scale=scale)

        return frame

    def is_done(self):
        # จบจริงเมื่อ explode เล่นถึงเฟรมสุดท้ายแล้วเท่านั้น ไม่ใช้ time-based
        done = (self.phase == "explode" and
                self.frame_idx >= len(frames_fire_explode) - 1 and
                time.time() - self.anim_timer > self.explode_fps * 3)
        if done and CH_FIRE.get_busy():
            CH_FIRE.stop()
        return done


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

        # เล่นเสียง potion ทันทีที่ spawn
        play_potion()

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
        done = time.time() - self.start_time > self.duration
        if done and CH_POTION.get_busy():
            CH_POTION.stop()
        return done
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

def draw_charge_sparks(frame, px, py, charge):
    """เปลี่ยนเป็นประกายไฟสีเหลืองทองที่สว่างขึ้นเรื่อยๆ ตามการชาร์จ"""
    if px is None or py is None or charge <= 0:
        return frame

    num_sparks  = int(4 + charge * 14)       
    max_len     = 10 + charge * 28            
    
    for _ in range(num_sparks):
        angle  = random.uniform(0, 2 * math.pi)
        length = random.uniform(max_len * 0.4, max_len)
        x2     = int(px + math.cos(angle) * length)
        y2     = int(py + math.sin(angle) * length)

        # ปรับค่าสีเป็นโทนเหลือง (BGR)
        # Blue: น้อยๆ เพื่อให้คงความเหลือง
        # Green: สูง (ประมาณ 180-255)
        # Red: สูง (255)
        b = int(20 + charge * 60) # เพิ่มน้ำเงินนิดหน่อยตอนชาร์จเต็มเพื่อให้ดูขาวนวลขึ้น
        g = int(180 + charge * 75)
        r = 255
        color = (b, g, r) 

        cv2.line(frame, (px, py), (x2, y2), color, 1, cv2.LINE_AA)

    # วาดจุดแกนกลาง (Core) ให้เป็นสีเหลืองสว่าง/ขาว
    core_r = max(2, int(3 + charge * 4))
    # วาดวงนอกเป็นสีเหลืองเข้ม
    cv2.circle(frame, (px, py), core_r + 2, (0, 200, 255), -1, cv2.LINE_AA)
    # วาดวงในเป็นสีเหลืองอ่อนจนถึงขาว
    cv2.circle(frame, (px, py), core_r, (150, 255, 255), -1, cv2.LINE_AA)

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

def preprocess_for_ai(points, num_points=20):
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
        if hold_counter >= 90:  # fix: was > 30 (~33%) but bar fills over 90 frames — now requires 100% charge
            state = "READY"
            pts.clear()
            msg = "READY TO CAST!"

    elif state == "READY":
        if not is_holding:
            release_counter += 1
        else:
            release_counter = 0   # wobble resets counter — must be a real release
        if release_counter >= 10:
            release_counter = 0
            state = "DRAW"
            pts.clear()
            has_moved_enough = False
            draw_start_time  = time.time()
            msg = "CASTING..."

    elif state == "DRAW":
        if len(valid_pts) > 1:
            if np.linalg.norm(np.array(valid_pts[-1]) - np.array(valid_pts[0])) > 30:
                has_moved_enough = True
        if is_holding:
            elapsed_draw = time.time() - draw_start_time
            if elapsed_draw < 0.8:
                pass  # too early — don't judge yet, ignore brief wobble-stops
            else:
                if has_moved_enough and len(valid_pts) > 10:
                    input_ai = preprocess_for_ai(valid_pts)
                    if input_ai:
                        pred_probs = ai_model.predict_proba(np.array([input_ai]))[0]
                        confidence = float(np.max(pred_probs))
                        prediction = ai_model.classes_[int(np.argmax(pred_probs))]
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
                        msg = "UNCLEAR GESTURE"
                else:
                    msg = "TOO SHORT!"
                state           = "IDLE"
                hold_counter    = 0
                release_counter = 0
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
            color = (int(50 * alpha), int(215 * alpha), int(255 * alpha))
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
pygame.mixer.quit()