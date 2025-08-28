import cv2
import mediapipe as mp
import numpy as np
import math
import time
import threading
from collections import deque
import tempfile
import os

TTS_ENGINE = None
TTS_METHOD = "NONE"

try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    voices = tts_engine.getProperty('voices')
    if len(voices) > 1:
        tts_engine.setProperty('voice', voices[1].id)
    tts_engine.setProperty('rate', 150)
    TTS_ENGINE = "PYTTSX3"
    TTS_METHOD = "PYTTSX3"
    print("✓ Text-to-speech (pyttsx3) siap digunakan.")
except ImportError:
    print("✗ pyttsx3 tidak tersedia, mencoba gTTS...")

if TTS_METHOD == "NONE":
    try:
        from gtts import gTTS
        import pygame
        pygame.mixer.init()
        TTS_ENGINE = "GTTS"
        TTS_METHOD = "GTTS"
        print("✓ Text-to-speech (gTTS + pygame) siap digunakan.")
    except ImportError as e:
        print(f"✗ gTTS/pygame tidak tersedia: {e}")

if TTS_METHOD == "NONE":
    try:
        import win32com.client
        sapi_engine = win32com.client.Dispatch("SAPI.SpVoice")
        TTS_ENGINE = "SAPI"
        TTS_METHOD = "SAPI"
        print("✓ Text-to-speech (Windows SAPI) siap digunakan.")
    except ImportError:
        print("✗ Windows SAPI tidak tersedia")

if TTS_METHOD == "NONE":
    print("✗ Tidak ada engine TTS yang tersedia. Program akan berjalan tanpa suara.")

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

class BISINDOTranslator:
    def __init__(self):
        self.current_gesture = "Tidak Ada"
        self.last_gesture = "Tidak Ada"
        self.stability_counter = 0
        self.stability_threshold = 8
        self.last_speak_time = 0
        self.speak_cooldown = 2.0
        
        self.letter_buffer = deque(maxlen=20)
        self.word_buffer = []
        self.sentence_buffer = []
        self.last_letter_time = 0
        self.letter_timeout = 3.0
        self.word_timeout = 5.0
        
        self.mode = "ALFABET"
        self.show_help = False
        
        self.temp_files = []

    def speak(self, text):
        if TTS_METHOD == "NONE":
            print(f"[SILENT] {text}")
            return
            
        current_time = time.time()
        if current_time - self.last_speak_time > self.speak_cooldown:
            self.last_speak_time = current_time
            threading.Thread(target=self._speak_threaded, args=(text,), daemon=True).start()

    def _speak_threaded(self, text):
        try:
            print(f"[TTS-{TTS_METHOD}] {text}")
            
            if TTS_METHOD == "PYTTSX3":
                tts_engine.say(text)
                tts_engine.runAndWait()
                
            elif TTS_METHOD == "GTTS":
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.close()
                
                tts = gTTS(text=text, lang='id', slow=False)
                tts.save(temp_file.name)
                
                pygame.mixer.music.load(temp_file.name)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                try:
                    os.unlink(temp_file.name)
                except:
                    self.temp_files.append(temp_file.name)
                    
            elif TTS_METHOD == "SAPI":
                sapi_engine.Speak(text)
                
        except Exception as e:
            print(f"[ERROR TTS] {e}")

    def cleanup_temp_files(self):
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        self.temp_files.clear()

    def hitung_jarak(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def hitung_sudut(self, p1, p2, p3):
        v1 = np.array([p1.x - p2.x, p1.y - p2.y])
        v2 = np.array([p3.x - p2.x, p3.y - p2.y])
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        angle = math.degrees(math.acos(np.clip(cos_angle, -1.0, 1.0)))
        return angle

    def deteksi_jari_terangkat(self, landmarks):
        jari_terangkat = []
        tip_ids = [4, 8, 12, 16, 20]
        
        if landmarks[tip_ids[0]].x < landmarks[tip_ids[0] - 1].x:
            jari_terangkat.append(1)
        else:
            jari_terangkat.append(0)
            
        for i in range(1, 5):
            if landmarks[tip_ids[i]].y < landmarks[tip_ids[i] - 2].y:
                jari_terangkat.append(1)
            else:
                jari_terangkat.append(0)
                
        return jari_terangkat

    def deteksi_alfabet_bisindo(self, landmarks, jari_terangkat):
        jumlah_jari = sum(jari_terangkat)
        
        jarak_jempol_telunjuk = self.hitung_jarak(landmarks[4], landmarks[8])
        jarak_jempol_tengah = self.hitung_jarak(landmarks[4], landmarks[12])
        jarak_telunjuk_tengah = self.hitung_jarak(landmarks[8], landmarks[12])
        
        sudut_telunjuk = self.hitung_sudut(landmarks[6], landmarks[7], landmarks[8])
        
        telunjuk_y = landmarks[8].y
        tengah_y = landmarks[12].y
        manis_y = landmarks[16].y
        kelingking_y = landmarks[20].y
        
        if jumlah_jari == 1 and jari_terangkat[0] == 1:
            return "A"
        
        if jumlah_jari == 4 and jari_terangkat[0] == 0:
            return "B"
            
        if jumlah_jari == 2 and jari_terangkat[0] == 1 and jari_terangkat[1] == 1:
            if jarak_jempol_telunjuk > 0.06:
                return "C"
        
        if jumlah_jari == 1 and jari_terangkat[1] == 1:
            if jarak_jempol_tengah < 0.05:
                return "D"
        
        if jumlah_jari == 0:
            return "E"
        
        if jarak_jempol_telunjuk < 0.04 and jumlah_jari >= 3:
            return "F"
        
        if jumlah_jari == 2 and jari_terangkat[0] == 1 and jari_terangkat[1] == 1:
            if abs(landmarks[4].y - landmarks[8].y) < 0.03:
                return "G"
        
        if jumlah_jari == 2 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1:
            if abs(telunjuk_y - tengah_y) < 0.03:
                return "H"
        
        if jumlah_jari == 1 and jari_terangkat[4] == 1:
            return "I"
        
        if jumlah_jari == 3 and jari_terangkat[0] == 1 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1:
            return "K"
        
        if jumlah_jari == 2 and jari_terangkat[0] == 1 and jari_terangkat[1] == 1:
            if abs(landmarks[4].x - landmarks[8].x) > 0.08:
                return "L"
        
        if jumlah_jari == 0 and landmarks[4].y < landmarks[8].y:
            return "M"
        
        if jumlah_jari == 1 and jari_terangkat[0] == 1 and landmarks[4].y < landmarks[12].y:
            return "N"
        
        if jumlah_jari == 0:
            jarak_avg = (jarak_jempol_telunjuk + jarak_jempol_tengah) / 2
            if jarak_avg < 0.06:
                return "O"
        
        if jumlah_jari == 2 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1:
            if telunjuk_y < tengah_y:
                return "P"
        
        if jumlah_jari == 2 and jari_terangkat[0] == 1 and jari_terangkat[1] == 1:
            if landmarks[8].y > landmarks[4].y:
                return "Q"
        
        if jumlah_jari == 2 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1:
            if jarak_telunjuk_tengah < 0.03:
                return "R"
        
        if jumlah_jari == 0:
            return "S"
        
        if jumlah_jari == 1 and jari_terangkat[0] == 1:
            if landmarks[4].y > landmarks[8].y and landmarks[4].y > landmarks[12].y:
                return "T"
        
        if jumlah_jari == 2 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1:
            return "U"
        
        if jumlah_jari == 2 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1:
            if jarak_telunjuk_tengah > 0.04:
                return "V"
        
        if jumlah_jari == 3 and jari_terangkat[1] == 1 and jari_terangkat[2] == 1 and jari_terangkat[3] == 1:
            return "W"
        
        if jumlah_jari == 1 and jari_terangkat[1] == 1:
            if sudut_telunjuk < 160:
                return "X"
        
        if jumlah_jari == 2 and jari_terangkat[0] == 1 and jari_terangkat[4] == 1:
            return "Y"
        
        if jumlah_jari == 1 and jari_terangkat[1] == 1:
            return "Z"
        
        return "Tidak Dikenal"

    def deteksi_kata_bisindo(self, landmarks, jari_terangkat):
        jumlah_jari = sum(jari_terangkat)
        
        if jumlah_jari == 5:
            return "HALO"
        
        if jumlah_jari == 5 and landmarks[9].y > 0.6:
            return "TERIMA KASIH"
        
        if jumlah_jari == 0:
            return "YA"
        
        if jumlah_jari == 1 and jari_terangkat[1] == 1:
            return "TIDAK"
        
        if jumlah_jari == 5 and landmarks[0].y > 0.5:
            return "MAAF"
        
        if jumlah_jari == 1 and jari_terangkat[0] == 1:
            return "BAIK"
        
        return "Tidak Dikenal"

    def proses_frame(self, hand_landmarks_list):
        if not hand_landmarks_list:
            return "Tidak Ada Tangan"
        
        hand_landmarks = hand_landmarks_list[0]
        jari_terangkat = self.deteksi_jari_terangkat(hand_landmarks)
        
        if self.mode == "ALFABET":
            gesture = self.deteksi_alfabet_bisindo(hand_landmarks, jari_terangkat)
        elif self.mode == "KATA":
            gesture = self.deteksi_kata_bisindo(hand_landmarks, jari_terangkat)
        else:
            gesture = self.deteksi_alfabet_bisindo(hand_landmarks, jari_terangkat)

        if gesture == self.last_gesture:
            self.stability_counter += 1
        else:
            self.last_gesture = gesture
            self.stability_counter = 0

        if self.stability_counter >= self.stability_threshold:
            if self.current_gesture != gesture:
                self.current_gesture = gesture
                current_time = time.time()
                
                if self.mode == "ALFABET" and gesture != "Tidak Dikenal":
                    if len(gesture) == 1:
                        self.letter_buffer.append(gesture)
                        self.last_letter_time = current_time
                        self.speak(gesture)
                
                elif self.mode == "KATA" and gesture != "Tidak Dikenal":
                    self.word_buffer.append(gesture)
                    self.speak(gesture)
        
        return self.current_gesture

    def get_current_word(self):
        return ''.join(list(self.letter_buffer))
    
    def clear_buffers(self):
        self.letter_buffer.clear()
        self.word_buffer.clear()
        self.sentence_buffer.clear()

    def __del__(self):
        self.cleanup_temp_files()

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Kamera tidak dapat dibuka.")
        return

    translator = BISINDOTranslator()
    
    if TTS_METHOD != "NONE":
        translator.speak("Penerjemah BISINDO siap digunakan")
    
    print("\n" + "="*60)
    print("PENERJEMAH BAHASA ISYARAT BISINDO")
    print("="*60)
    print(f"TTS Engine: {TTS_METHOD}")
    print("="*60)
    print("KONTROL:")
    print("- Tekan '1' untuk mode Alfabet")
    print("- Tekan '2' untuk mode Kata")
    print("- Tekan 'c' untuk clear buffer")
    print("- Tekan 't' untuk test suara")
    print("- Tekan 'h' untuk bantuan")
    print("- Tekan 'q' untuk keluar")
    print("="*60)

    try:
        while True:
            success, frame = cap.read()
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            height, width, _ = frame.shape
            
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)
            
            gesture_terdeteksi = "Tidak Ada Tangan"
            hand_landmarks_list = []

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                    hand_landmarks_list.append(hand_landmarks.landmark)
                
                gesture_terdeteksi = translator.proses_frame(hand_landmarks_list)

            cv2.rectangle(frame, (0, 0), (width, 140), (0, 0, 0), -1)
            
            tts_color = (0, 255, 0) if TTS_METHOD != "NONE" else (0, 0, 255)
            cv2.putText(frame, f'TTS: {TTS_METHOD}', (10, 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, tts_color, 1)
            
            cv2.putText(frame, f'MODE: {translator.mode}', (150, 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f'GESTURE: {gesture_terdeteksi}', (10, 65), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            if translator.mode == "ALFABET":
                current_word = translator.get_current_word()
                cv2.putText(frame, f'KATA: {current_word}', (10, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            cv2.putText(frame, "1:Alfabet 2:Kata C:Clear T:Test H:Help Q:Keluar", 
                        (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            if translator.show_help:
                help_text = [
                    "ALFABET BISINDO:",
                    "A=Jempol, B=4jari, C=JempolTelunjuk",
                    "D=Telunjuk+JempolTengah, E=Kepalan",
                    "F=OK, G=JempolTelunjukHorizontal",
                    "H=TelunjukTengahHorizontal, I=Kelingking",
                    "L=LShape, V=Peace, Y=JempolKelingking",
                    "",
                    "KATA DASAR:",
                    "5jari=HALO, Kepalan=YA, Telunjuk=TIDAK",
                    f"",
                    f"Engine TTS: {TTS_METHOD}"
                ]
                
                y_offset = 160
                for i, text in enumerate(help_text):
                    cv2.putText(frame, text, (10, y_offset + i*20), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            
            cv2.imshow('Penerjemah BISINDO', frame)

            key = cv2.waitKey(5) & 0xFF
            if key == ord('q'):
                translator.speak("Program selesai")
                time.sleep(2)
                break
            elif key == ord('1'):
                translator.mode = "ALFABET"
                translator.speak("Mode Alfabet")
            elif key == ord('2'):
                translator.mode = "KATA"
                translator.speak("Mode Kata")
            elif key == ord('c'):
                translator.clear_buffers()
                translator.speak("Buffer dibersihkan")
            elif key == ord('t'):
                translator.speak("Test suara berhasil. Sistem berfungsi dengan baik!")
                print(f"[TEST] TTS engine: {TTS_METHOD}")
            elif key == ord('h'):
                translator.show_help = not translator.show_help
    
    except KeyboardInterrupt:
        print("\nProgram dihentikan...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        translator.cleanup_temp_files()
        cap.release()
        cv2.destroyAllWindows()
        if TTS_METHOD == "GTTS":
            pygame.mixer.quit()
        print("Program selesai.")

if __name__ == "__main__":
    main()