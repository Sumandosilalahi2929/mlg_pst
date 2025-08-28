import cv2
import mediapipe as mp
import os
import pickle

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5)

DATA_DIR = './data_bisindo'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


JUMLAH_KELAS = 26 
JUMLAH_SAMPEL = 100

cap = cv2.VideoCapture(0)

for j in range(JUMLAH_KELAS):
    nama_kelas = chr(65 + j)
    
    if not os.path.exists(os.path.join(DATA_DIR, nama_kelas)):
        os.makedirs(os.path.join(DATA_DIR, nama_kelas))

    print(f'Mengumpulkan data untuk kelas: {nama_kelas}')

    while True:
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        cv2.putText(frame, f'Siap? Tunjukkan huruf "{nama_kelas}". Tekan "S" untuk mulai!', (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.imshow('frame', frame)
        if cv2.waitKey(25) == ord('s'):
            break

    counter = 0
    while counter < JUMLAH_SAMPEL:
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        
        cv2.putText(frame, f'Merekam... {counter}/{JUMLAH_SAMPEL}', (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imshow('frame', frame)
        cv2.waitKey(25) 

        cv2.imwrite(os.path.join(DATA_DIR, nama_kelas, f'{counter}.jpg'), frame)
        counter += 1

cap.release()
cv2.destroyAllWindows()