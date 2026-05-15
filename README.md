# 🪄 MagicTracker — Real-Time Gesture Recognition & AR Visual Effects

> **FRA626 Machine Vision for Smart Factory** — Final Project  
> Real-time magic wand AR system using color tracking, gesture recognition, and animated visual effects.

---

## ✨ Demo

Hold a colored wand in front of your camera, draw a shape in the air, and watch the magic happen.

| Gesture | Shape | Effect |
|---|---|---|
| Circle | ⭕ | 9 butterflies + 40 fireflies appear |
| Triangle | 🔺 | A glowing potion bottle floats and follows your wand |
| Slash | ➡️ | A fireball charges up and explodes |

---

## 📋 Requirements

### Hardware
- Webcam (360p or higher)
- A wand with a **colored tip** — lime green or pink reflective works best
- Well-lit environment with a background that does **not** share the wand tip color

### Software

```
Python 3.8+
opencv-python
numpy
scikit-learn
pygame
```

Install all dependencies:

```bash
pip install opencv-python numpy scikit-learn pygame
```

---

## 📁 Project Structure

```
MagicTracker/
│
├── MagicTracker.py          # Main application — run this
├── data_collector.py        # Tool for recording gesture training data
├── TrainMagic.py            # Model training script
├── magic_wand_model.pkl     # Pre-trained Random Forest classifier
│
├── effects/
│   ├── animal/
│   │   └── Normal/
│   │       ├── A1/          # Butterfly sprite set 1 (20 frames)
│   │       ├── A2/          # Butterfly sprite set 2 (20 frames)
│   │       ├── ...
│   │       └── A9/          # Butterfly sprite set 9 (20 frames)
│   ├── fireball/
│   │   ├── imgs_explode/    # Fireball charge frames (35 frames)
│   │   └── explode/         # Fireball explosion frames (33 frames)
│   └── Potion/
│       └── Sprites/         # Potion animation frames (14 frames)
│
├── sound/
│   ├── fairy_dust.mp3       # Ambient charge sound (CH0)
│   ├── butterfly.mp3        # Butterfly effect sound (CH1)
│   ├── fire.mp3             # Fireball sound (CH2)
│   └── potion.mp3           # Potion effect sound (CH3)
│
└── gesture_data_20.csv      # Training data (optional — needed only to retrain)
```

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/ImJAiiiii/FRA626_Project_6559_6566.git
cd MagicTracker
```

### 2. Install dependencies

```bash
pip install opencv-python numpy scikit-learn pygame
```

### 3. Run the main application

```bash
python MagicTracker.py
```

The camera window will open. A pre-trained model (`magic_wand_model.pkl`) is included — no training required to get started.

---

## 🎮 How to Use

```
1. Point your wand at the camera
2. Hold the wand STILL for ~3 seconds
   → Spark particles appear and a charge bar fills at the bottom
3. When the bar is full → "READY TO CAST!" appears
4. Move your wand and draw one of the three gestures in the air
   → A purple trail follows your wand tip
5. Hold still again when done
   → The system recognizes the gesture and fires the effect!
```

### Test Mode

While `TEST_MODE = True` in `MagicTracker.py`, you can trigger effects instantly with keyboard shortcuts:

| Key | Effect |
|---|---|
| `1` | Butterfly (Circle) |
| `2` | Potion (Triangle) |
| `3` | Fireball (Slash) |
| `Q` | Quit |

To disable test mode, set `TEST_MODE = False` in the code.

---

## 🤖 Training Your Own Model

### Step 1 — Collect gesture data

```bash
python data_collector.py
```

**Controls during collection:**

| Key | Action |
|---|---|
| Hold still | Enter READY state |
| Move wand | Start drawing |
| `1` | Save as **Circle** |
| `2` | Save as **Triangle** |
| `3` | Save as **Slash** |
| `R` | Retry / discard current stroke |
| `Q` | Quit |

Collect at least **80 samples per gesture class** for reliable results.  
Data is saved to `gesture_data_10.csv` through `gesture_data_100.csv` (six files at different resolutions).

### Step 2 — Train the model

```bash
python TrainMagic.py
```

This will:
- Load `gesture_data_20.csv` (optimal 20-point resolution)
- Train a Random Forest classifier (100 trees, 80/20 train-test split)
- Print accuracy, classification report, and confusion matrix
- Save the trained model to `magic_wand_model.pkl`

---

## 🧠 How It Works

### System Architecture

```
Camera → Vision Pipeline → State Machine → AI Classifier → Effect Engine
                                                              ↓
                                                        Sound System
                                                              ↓
                                                      Render Pipeline → Display
```

### Vision Pipeline

Each frame is processed through:
1. **HSV masking** — isolates the wand tip color
2. **Contour detection** — finds the topmost point of the wand
3. **Tip smoother** — median history filter + lerp filter to eliminate jitter

### State Machine

```
IDLE ──(hold 90 frames)──► READY ──(move 10+ frames)──► DRAW ──(hold + 0.8s)──► AI Predict
 ▲                                                                                      │
 └──────────────────────────────── Reset ◄──────────────────────────────────────────────┘
```

### Gesture Preprocessing

Raw gesture points are transformed into a position- and size-independent feature vector:

1. **Resample** — linspace to exactly 20 evenly spaced points
2. **Bounding box** — find min x/y and scale
3. **Normalize** — all coordinates mapped to 0.0–1.0
4. **Flatten** — `[x0, y0, x1, y1, ..., x19, y19]` = 40 features

### Sampling Point Optimization

| Points | Accuracy | Notes |
|---|---|---|
| 10p | 100% | Perfect — noise filtered naturally |
| **20p** | **100%** | **✅ Optimal — chosen for final model** |
| 30p | 97.92% | Hand jitter begins to corrupt Slash |
| 50p | 95.83% | More misclassifications |
| 80p | 95.83% | Plateaus — no improvement |
| 100p | 95.83% | Plateaus — feature importance spreads thin |

---

## ⚡ Performance Notes

The following optimizations are applied to maintain ~30 fps:

- **No `frame.copy()` in particle loops** — alpha baked into draw color instead of addWeighted
- **`math.sin/cos` instead of `np.sin/cos`** for scalar values (~3–5× faster)
- **`morphologyEx`** instead of separate erode + dilate
- **Morph kernel precomputed** outside the main loop
- **40 fireflies** (reduced from 60 — visually equivalent)
- **Precomputed `end_time`** in all effect classes instead of elapsed time checks each frame

---

## 🔧 Troubleshooting

**Camera won't open**
```
Error: Cannot open camera!
```
Try changing the camera index in `MagicTracker.py`:
```python
cap = cv2.VideoCapture(0)  # Try 0, 1, or 2
```

**Wand not detected**
- Make sure the wand tip color matches the HSV range in the code (`lower = [40, 80, 80]`, `upper = [89, 255, 255]` — this targets green)
- Improve lighting — avoid backlighting
- Remove background objects with similar color to the wand tip

**Gesture not recognized**
- Draw more slowly and deliberately
- Make sure the gesture fills a reasonable portion of the frame
- Re-collect training data if the model was retrained with low sample count

**Frame rate drops during Butterfly effect**
- This is a known issue — reduce `FIREFLY_COUNT` at the top of `ButterflyEffect.__init__()` from 40 to 20 if needed

---

## 🗺️ Future Development

- [ ] Expand gesture vocabulary beyond 3 spells
- [ ] Power scaling based on drawing speed
- [ ] Combo system for chained gestures
- [ ] Face/body detection for targeted effects (OpenCV DNN)
- [ ] Score system and on-screen targets
- [ ] 2-player split-screen duel mode

---

## 👥 Team

| Member | Student ID |
|---|---|
| Apichaya Sriwong | 65340500059 |
| Chananchida Progjit | 65340500066 |

**Course:** FRA626 Machine Vision for Smart Factory  
**Faculty:** FIBO, King Mongkut's University of Technology Thonburi

---

## 📄 License

This project was developed for academic purposes as part of FRA626.  
Sprite assets and sound files are for educational use only.
