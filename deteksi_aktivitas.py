import cv2
import numpy as np
import time
import threading
from datetime import datetime
import json
import os

try:
    import pyttsx3
    TTS_ENGINE_AVAILABLE = True
    tts_engine = pyttsx3.init()
    voices = tts_engine.getProperty('voices')
    if len(voices) > 1:
        tts_engine.setProperty('voice', voices[1].id)
    tts_engine.setProperty('rate', 150)
    print("✓ Text-to-speech siap digunakan.")
except ImportError:
    TTS_ENGINE_AVAILABLE = False
    print("✗ Library pyttsx3 tidak ditemukan. Fitur suara tidak akan aktif.")

class SimpleSeatMonitor:
    def __init__(self):

        self.is_person_present = False
        self.last_detection_time = 0
        self.empty_start_time = None
        
   
        self.warning_delay = 5  
        self.last_warning_time = 0
        self.warning_cooldown = 3  
        
        # Pengaturan deteksi
        self.motion_threshold = 1000 
        self.stability_frames = 10    
        self.current_stability = 0
        
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=25, detectShadows=False
        )
        
        # Status sistem
        self.monitoring_active = True
        self.session_start = time.time()
        
        print("✓ Sistem monitor tempat duduk siap")

    def speak_async(self, text):
        """Jalankan TTS secara asinkron"""
        def _speak():
            try:
                if TTS_ENGINE_AVAILABLE:
                    print(f"[SUARA] {text}")
                    tts_engine.say(text)
                    tts_engine.runAndWait()
                else:
                    print(f"[PESAN] {text}")
            except Exception as e:
                print(f"[ERROR TTS] {e}")
        
        thread = threading.Thread(target=_speak, daemon=True)
        thread.start()

    def detect_motion_simple(self, frame):
        """Deteksi gerakan sederhana menggunakan background subtraction"""
        try:
            fg_mask = self.bg_subtractor.apply(frame)
            
            motion_pixels = cv2.countNonZero(fg_mask)
            
            person_detected = motion_pixels > self.motion_threshold
            
            return person_detected, motion_pixels, fg_mask
            
        except Exception as e:
            print(f"[ERROR DETEKSI] {e}")
            return False, 0, np.zeros_like(frame[:,:,0])

    def update_presence(self, person_detected, motion_pixels):
        """Update status keberadaan dengan stabilitas"""
        current_time = time.time()
        
        print(f"[DEBUG] Motion pixels: {motion_pixels}, Detected: {person_detected}, Present: {self.is_person_present}")
        
        # Sistem stabilitas
        if person_detected:
            if self.current_stability < self.stability_frames:
                self.current_stability += 1
            
            if self.current_stability >= self.stability_frames:
                if not self.is_person_present:
                    # Orang baru duduk
                    self.is_person_present = True
                    self.empty_start_time = None
                    self.last_detection_time = current_time
                    print("[INFO] Orang terdeteksi duduk")
                    self.speak_async("Selamat datang. Anda sedang dipantau.")
                else:
                    self.last_detection_time = current_time
        else:
            self.current_stability = 0
            
            if self.is_person_present:
                self.is_person_present = False
                self.empty_start_time = current_time
                print(f"[INFO] Tempat duduk kosong pada {datetime.now().strftime('%H:%M:%S')}")
                
            elif self.empty_start_time is not None:

                empty_duration = current_time - self.empty_start_time
                self.check_warning(empty_duration, current_time)

    def check_warning(self, empty_duration, current_time):
        """Cek dan berikan peringatan jika perlu"""
        if not self.monitoring_active:
            return

        if (empty_duration >= self.warning_delay and 
            current_time - self.last_warning_time > self.warning_cooldown):
            
            self.last_warning_time = current_time
            seconds = int(empty_duration)
            warning_msg = f"Peringatan! Tempat duduk kosong selama {seconds} detik. Mohon kembali ke tempat duduk sekarang!"
            
            print(f"[WARNING] {warning_msg}")
            self.speak_async(warning_msg)

    def get_status(self):
        """Dapatkan status saat ini"""
        current_time = time.time()
        
        if self.is_person_present:
            status = "ADA"
            sitting_duration = int(current_time - self.last_detection_time)
            duration_text = f"Duduk: {sitting_duration}s"
        elif self.empty_start_time is not None:
            empty_duration = int(current_time - self.empty_start_time)
            status = "KOSONG"
            duration_text = f"Kosong: {empty_duration}s"
        else:
            status = "MENUNGGU"
            duration_text = "Menunggu deteksi..."
        
        session_time = int(current_time - self.session_start)
        
        return {
            'status': status,
            'duration_text': duration_text,
            'session_time': f"Sesi: {session_time}s"
        }

def draw_interface(frame, monitor, person_detected, motion_pixels):
    """Gambar interface pada frame"""
    height, width = frame.shape[:2]

    cv2.rectangle(frame, (0, 0), (width, 100), (0, 0, 0), -1)

    status_info = monitor.get_status()
    
    if status_info['status'] == "ADA":
        status_color = (0, 255, 0) 
    elif status_info['status'] == "KOSONG":
        status_color = (0, 0, 255)  
    else:
        status_color = (255, 255, 0) 
    
    cv2.putText(frame, f"STATUS: {status_info['status']}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    

    cv2.putText(frame, status_info['duration_text'], (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    #
    cv2.putText(frame, status_info['session_time'], (10, 85), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
  
    cv2.putText(frame, f"Motion: {motion_pixels}", (width-150, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.putText(frame, f"Deteksi: {'YA' if person_detected else 'TIDAK'}", 
                (width-150, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
 
    monitor_color = (0, 255, 0) if monitor.monitoring_active else (128, 128, 128)
    cv2.putText(frame, f"MONITOR: {'ON' if monitor.monitoring_active else 'OFF'}", 
                (width-150, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.4, monitor_color, 1)

    cv2.putText(frame, "T=Test, M=Toggle Monitor, Q=Keluar", 
                (10, height-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

def main():
    print("Memulai sistem monitor tempat duduk...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Kamera tidak dapat dibuka!")
        return

    monitor = SimpleSeatMonitor()
    
    print("\n" + "="*50)
    print("SISTEM MONITOR TEMPAT DUDUK")
    print("="*50)
    print("- Status ADA/KOSONG akan ditampilkan")
    print("- Peringatan suara setelah 5 detik kosong")
    print("- Tekan T untuk test suara")
    print("- Tekan M untuk toggle monitoring")
    print("- Tekan Q untuk keluar")
    print("="*50)
    
    # Pesan awal
    monitor.speak_async("Sistem monitor tempat duduk aktif")
    
    try:
        frame_count = 0
        
        while True:
            success, frame = cap.read()
            if not success:
                print("Tidak dapat membaca frame kamera")
                continue
            
            frame = cv2.flip(frame, 1)
            frame_count += 1
       
            person_detected, motion_pixels, fg_mask = monitor.detect_motion_simple(frame)
            
     
            monitor.update_presence(person_detected, motion_pixels)

            draw_interface(frame, monitor, person_detected, motion_pixels)
            
   
            cv2.imshow('Monitor Tempat Duduk', frame)
    
            if motion_pixels > 500:
                cv2.imshow('Motion Detection', fg_mask)
            
        
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("Menghentikan sistem...")
                monitor.speak_async("Sistem monitor dihentikan")
                time.sleep(1) 
                break
                
            elif key == ord('t'):
          
                monitor.speak_async("Test suara berhasil! Mohon kembali ke tempat duduk sekarang!")
                print("[TEST] Suara test dijalankan")
                
            elif key == ord('m'):
               
                monitor.monitoring_active = not monitor.monitoring_active
                status = "diaktifkan" if monitor.monitoring_active else "dinonaktifkan"
                print(f"[INFO] Monitoring {status}")
                monitor.speak_async(f"Monitoring {status}")
    
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh pengguna")
    
    except Exception as e:
        print(f"ERROR: {e}")
    
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("Program selesai")

if __name__ == "__main__":
    main()