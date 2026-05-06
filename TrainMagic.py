import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle

# 1. โหลดข้อมูล
data = pd.read_csv('gesture_data.csv')

# แยก Label (ชื่อท่า) ออกจาก Features (พิกัด x, y)
X = data.drop('label', axis=1)  # ข้อมูลพิกัด 60 คอลัมน์
y = data['label']               # ชื่อท่าทาง

# 2. แบ่งข้อมูลสำหรับ Train และ Test (80/20)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. สร้างและฝึกสอน AI
# เราใช้ Random Forest เพราะมันแยกแยะความแตกต่างของเส้นวาดได้ดีมาก
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. วัดผลความแม่นยำ
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"--- Training Complete ---")
print(f"Accuracy: {acc * 100:.2f}%")
print(f"Classes: {model.classes_}")

# 5. บันทึกโมเดลไว้ใช้งาน (เป็นไฟล์ .pkl)
with open('magic_wand_model.pkl', 'wb') as f:
    pickle.dump(model, f)
    
print("Model saved as 'magic_wand_model.pkl'")