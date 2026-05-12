import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns
import pickle
import matplotlib
import matplotlib.pyplot as plt

# 1. โหลดข้อมูล
data = pd.read_csv('gesture_data_50.csv')

# แยก Label (ชื่อท่า) ออกจาก Features (พิกัด x, y)
X = data.drop('label', axis=1)  # ข้อมูลพิกัด 60 คอลัมน์
y = data['label']               # ชื่อท่าทาง

# 2. แบ่งข้อมูลสำหรับ Train และ Test (80/20)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
# 3. สร้างและฝึกสอน AI
# เราใช้ Random Forest เพราะมันแยกแยะความแตกต่างของเส้นวาดได้ดีมาก
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"--- Training Complete ---")
print(f"Accuracy: {acc * 100:.2f}%")

# เพิ่ม Classification Report: ดูความแม่นยำแยกรายท่าทาง
print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred))

# เพิ่ม Confusion Matrix: ดูว่าโมเดลสับสนท่าไหนกับท่าไหน
cm = confusion_matrix(y_test, y_pred, labels=model.classes_)
print("\n--- Confusion Matrix ---")
print(cm)

# (Optional) วาดรูป Confusion Matrix ให้ดูง่ายด้วย Seaborn
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=model.classes_, yticklabels=model.classes_)
plt.title('Confusion Matrix of Magic Gestures')
plt.ylabel('Actual Label')
plt.xlabel('Predicted Label')
plt.show()

# ==========================================
# ส่วนที่เพิ่มใหม่: การวิเคราะห์ความสำคัญของข้อมูล (Feature Importance)
# ==========================================
importances = model.feature_importances_

# เนื่องจากข้อมูลเรามี 60 คอลัมน์ (x0, y0, x1, y1, ..., x29, y29)
# เราสามารถวาดกราฟเพื่อดูว่า "จุดที่เท่าไหร่" มีผลต่อการตัดสินใจของ AI มากที่สุด
plt.figure(figsize=(10, 5))
plt.plot(importances, color='teal', marker='o', linestyle='-', markersize=2)
plt.title("Feature Importance (Coordinate Points: x0, y0...x9, y99)")
plt.xlabel("Feature Index (0-199)")
plt.ylabel("Importance Score")
plt.grid(True, alpha=0.3)
plt.show()

# ==========================================

# 5. บันทึกโมเดลไว้ใช้งาน
with open('magic_wand_model.pkl', 'wb') as f:
    pickle.dump(model, f)