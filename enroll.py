import cv2
from utils import load_embeddings, save_embeddings, get_face_encoding

db = load_embeddings()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not accessible.")
    exit()

person_name = input("Enter family member name: ")

print("Press 's' to save face")
print("Press 'q' to quit")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Camera read failed.")
        break

    result = get_face_encoding(frame)

    if result is not None:
        locations, encodings = result

        for (top, right, bottom, left) in locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

    cv2.imshow("Enrollment", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):
        if result is not None:
            db[person_name] = encodings[0]
            save_embeddings(db)
            print(f"{person_name} enrolled successfully!")
            break
        else:
            print("No face detected.")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()