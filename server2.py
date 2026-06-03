import cv2
import urllib.request
import numpy as np
from detect import process_frame  

STREAM_URL = "http://10.220.62.237/stream" 

def get_blur_score(image):
    # Calculates the sharpness of a frame using Laplacian variance
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def main():
    print(f"Connecting to optimized stream: {STREAM_URL}")
    try:
        stream = urllib.request.urlopen(STREAM_URL)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    bytes_buffer = bytes()
    frame_batch = []
    
    while True:
        try:
            bytes_buffer += stream.read(4096)
            a = bytes_buffer.find(b'\xff\xd8') 
            b = bytes_buffer.find(b'\xff\xd9') 
            
            if a != -1 and b != -1:
                jpg = bytes_buffer[a:b+2]
                bytes_buffer = bytes_buffer[b+2:]
                
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Render the live stream window continuously at maximum speed
                    cv2.imshow("Real-Time Security Feed", frame)
                    
                    # Collect a rapid burst of 5 frames
                    frame_batch.append(frame)
                    
                    if len(frame_batch) >= 5:
                        # Find the single sharpest frame in the batch with the least motion blur
                        sharpest_frame = max(frame_batch, key=get_blur_score)
                        
                        # Run the AI engine ONLY on that perfect frame
                        cv2.imwrite("latest_capture.jpg", sharpest_frame)
                        ai_result = process_frame(sharpest_frame)
                        print(f"[AI VERDICT ON SHARPEST FRAME]: {ai_result}")
                        
                        # Clear the batch buffer to pull the next group of fresh frames
                        frame_batch = []
                    
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except Exception as err:
            continue

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()