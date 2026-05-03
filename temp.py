import cv2
import requests
import numpy as np
from io import BytesIO
import time
from datetime import datetime
from typing import Optional

class WebcamAccessCheck:
    cap: Optional[cv2.VideoCapture] = None 
    
    def __init__(self, api_url, gate_id=3):
        self.api_url = api_url
        self.gate_id = gate_id
        self.cap = None
        self.frames_buffer = []
        self.max_frames = 3
        self.is_capturing = False
        
    def start_webcam(self):
        """Initialize and start webcam capture"""
        self.cap = cv2.VideoCapture(0)  # 0 for default webcam
        
        if not self.cap.isOpened():
            print("Error: Could not open webcam")
            return False
        
        # Set resolution (optional)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        print("Webcam started successfully!")
        print("\nControls:")
        print("- Press 'SPACE' to capture 3 frames and send to API")
        print("- Press 'ENTER' to capture 3 frames and send to API")
        print("- Press 'q' or 'ESC' to quit")
        print("- Press 'c' to clear frame buffer")
        print("\n" + "="*50)
        
        return True
    
    def capture_frames(self):
        """Capture 3 frames from webcam"""
        self.frames_buffer = []
        self.is_capturing = True
        
        print("\n📸 Capturing 3 frames...")
        
        for i in range(self.max_frames):
            if self.cap:
                ret, frame = self.cap.read()
                if ret:
                    self.frames_buffer.append(frame.copy())
                    print(f"  ✓ Frame {i+1}/{self.max_frames} captured")
                    # Small delay between captures to get slightly different frames
                    time.sleep(0.1)
                else:
                    print(f"  ✗ Failed to capture frame {i+1}")
            else:
                print('error in connecting to camera')
        
        self.is_capturing = False
        print(f"✅ Captured {len(self.frames_buffer)} frames")
        print("="*50)
        
        return len(self.frames_buffer) > 0
    
    def frame_to_bytes(self, frame):
        """Convert OpenCV frame to bytes for API request"""
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return BytesIO(buffer.tobytes())
    
    def send_to_api(self):
        """Send captured frames to the API"""
        if not self.frames_buffer:
            print("❌ No frames to send. Capture frames first.")
            return None
        
        print("\n🚀 Sending request to API...")
        
        # Prepare files for multipart form-data
        files = []
        for idx, frame in enumerate(self.frames_buffer):
            frame_bytes = self.frame_to_bytes(frame)
            files.append(
                ('images', (f'capture_{idx+1}.jpg', frame_bytes, 'image/jpeg'))
            )
        
        # Prepare data
        data = {'gate': self.gate_id}
        
        try:
            start_time = time.time()
            response = requests.post(self.api_url, files=files, data=data)
            elapsed_time = (time.time() - start_time) * 1000
            
            print(f"📡 Response Status: {response.status_code}")
            print(f"⏱️  Request took: {elapsed_time:.2f}ms")
            
            if response.status_code == 200:
                result = response.json()
                self.display_result(result['data'])
                return result['data']
            else:
                print(f"❌ Error Response: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error: Could not connect to API server")
            return None
        except Exception as e:
            print(f"❌ Error sending request: {str(e)}")
            return None
    
    def display_result(self, result):
        """Display API response in a formatted way"""
        print("\n" + "="*50)
        print("📋 API RESPONSE")
        print(result)
        print("="*50)
        
        if 'access' in result:
            access = result['access']
            status = access.get('status', 'UNKNOWN')
            reason = access.get('reason', 'No reason provided')
            confidence = access.get('confidence', 0)
            
            # Color code the status
            if status == 'ALLOWED':
                status_display = f"✅ {status}"
            else:
                status_display = f"❌ {status}"
            
            print(f"Status: {status_display}")
            print(f"Reason: {reason}")
            
            if confidence:
                print(f"Confidence: {confidence:.2%}")
            
            if 'user' in access and access['user']:
                user = access['user']
                print(f"\n👤 User Info:")
                print(f"  ID: {user.get('id', 'N/A')}")
                print(f"  Name: {user.get('first_name', '')} {user.get('last_name', '')}")
                print(f"  Employee #: {user.get('employe_number', 'N/A')}")
            
            if 'gate' in access and access['gate']:
                gate = access['gate']
                print(f"\n🚪 Gate Info:")
                print(f"  ID: {gate.get('id', 'N/A')}")
                print(f"  Name: {gate.get('name', 'N/A')}")
                print(f"  Role: {gate.get('role', 'N/A')}")
            
            if 'area' in access and access['area']:
                area = access['area']
                print(f"\n📍 Area Info:")
                print(f"  ID: {area.get('id', 'N/A')}")
                print(f"  Name: {area.get('name', 'N/A')}")
            
            if 'processing_time_ms' in result:
                print(f"\n⏱️  Server Processing Time: {result['processing_time_ms']:.2f}ms")
        
        print("="*50)
    
    def draw_ui(self, frame):
        """Draw UI elements on the frame"""
        h, w = frame.shape[:2]
        
        # Add semi-transparent overlay at the bottom
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h-100), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        
        # Show number of frames in buffer
        buffer_text = f"Frames in buffer: {len(self.frames_buffer)}/{self.max_frames}"
        cv2.putText(frame, buffer_text, (10, h-60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show instructions
        if self.is_capturing:
            status_text = "CAPTURING..."
            color = (0, 255, 255)
        else:
            status_text = "Press SPACE/ENTER to capture & send"
            color = (0, 255, 0)
        
        cv2.putText(frame, status_text, (10, h-30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw frame counter if capturing
        if self.is_capturing:
            cv2.putText(frame, f"Capturing frame {len(self.frames_buffer)+1}...", 
                       (w-250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Draw timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (w-200, h-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def run(self):
        """Main loop"""
        if not self.start_webcam():
            return
        
        last_result = None
        result_display_time = 0
        
        while True:
            if self.cap:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Failed to grab frame")
                    break
                
                # Draw UI
                display_frame = self.draw_ui(frame.copy())
                
                # Display last result if available (show for 3 seconds)
                if last_result and (time.time() - result_display_time) < 3:
                    access = last_result.get('access', {})
                    status = access.get('status', 'UNKNOWN')
                    if status == 'ALLOWED':
                        cv2.putText(display_frame, "ACCESS GRANTED", 
                                (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    else:
                        cv2.putText(display_frame, "ACCESS DENIED", 
                                (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                
                cv2.imshow('Webcam Access Check', display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == 27 or key == ord('q'):  # ESC or 'q' to quit
                    print("\n👋 Shutting down...")
                    break
                elif key == 32 or key == 13:  # SPACE or ENTER
                    if not self.is_capturing:
                        if self.capture_frames():
                            last_result = self.send_to_api()
                            result_display_time = time.time()
                elif key == ord('c'):  # 'c' to clear buffer
                    self.frames_buffer = []
                    print("\n🗑️  Frame buffer cleared")
            else:
                print('error in connecting to camera')
            
        # Cleanup
        if self.cap:
            self.cap.release()
            cv2.destroyAllWindows()
        print("✅ Webcam released and windows closed")


def main():
    # Configuration
    API_URL = 'http://localhost:8000/api/access/check/image/'
    GATE_ID = 1
    
    # Create and run the webcam access check
    webcam_check = WebcamAccessCheck(API_URL, GATE_ID)
    webcam_check.run()


if __name__ == "__main__":
    main()