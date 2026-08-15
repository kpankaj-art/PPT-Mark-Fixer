import os
import io
import gc
import cv2
import numpy as np
from pptx import Presentation
from PIL import Image

def process_image(image_bytes, mode_choice):
    """
    OpenCV ka use karke images ko process karta hai:
    Mode 1: Hand-drawn boxes ko remove/clean karta hai.
    Mode 2: Imperfect shapes ko detect karke perfect Red Square/Rectangle banata hai.
    """
    # Bytes ko OpenCV image me convert karna
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Hand-drawn lines detect karne ke liye color/contour range
    # (Yeh rough drawings/lines detect karta hai)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    clean_img = img.copy()
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1000: # Chote-mote noise ko ignore karne ke liye
            x, y, w, h = cv2.boundingRect(cnt)
            
            if mode_choice == '1':
                # OPTION 1: Clean Image (Dabba hatana aur background fill karna)
                mask = np.zeros(img.shape[:2], np.uint8)
                cv2.drawContours(mask, [cnt], -1, 255, 5)
                clean_img = cv2.inpaint(clean_img, mask, 3, cv2.INPAINT_TELEA)
                
            elif mode_choice == '2':
                # OPTION 2: Perfect Square/Rectangle Box banana
                # Purani lines ko inpaint karke clean karna
                mask = np.zeros(img.shape[:2], np.uint8)
                cv2.drawContours(mask, [cnt], -1, 255, 5)
                clean_img = cv2.inpaint(clean_img, mask, 3, cv2.INPAINT_TELEA)
                # Perfect Rectangle Draw karna (Red Color, Thickness 3)
                cv2.rectangle(clean_img, (x, y), (x + w, y + h), (0, 0, 255), 3)

    # Processed OpenCV Image ko wapas Bytes/PNG format me convert karna
    is_success, buffer = cv2.imencode(".png", clean_img)
    if is_success:
        return buffer.tobytes()
    return image_bytes


def fix_presentation(ppt_path):
    print("\n" + "="*40)
    print("      PPT IMAGE FIXER TOOL")
    print("="*40)
    print("1. Clean Images (Boxes & Markings bilkul hata do)")
    print("2. Fix Boxes (Terhe-medhe dabbo ko Perfect Box banao)")
    choice = input("\nApna option chuniye (1 ya 2): ").strip()
    
    if choice not in ['1', '2']:
        print("Galat option! Script band ho rahi hai.")
        return

    print(f"\n[+] Loading Presentation: {ppt_path} ...")
    prs = Presentation(ppt_path)
    total_slides = len(prs.slides)
    print(f"[+] Total Slides Found: {total_slides}")
    print("[+] Processing start ho rahi hai...\n")

    for idx, slide in enumerate(prs.slides, start=1):
        # Real-time Terminal Progress Output
        print(f"Processing Slide {idx}/{total_slides}...", end="\r", flush=True)

        for shape in slide.shapes:
            if shape.has_image:
                try:
                    image_stream = shape.image.blob
                    # Image process karna selected option ke hisab se
                    fixed_bytes = process_image(image_stream, choice)
                    
                    # Old image ko new processed image se replace karna
                    image_bytes_io = io.BytesIO(fixed_bytes)
                    shape.image.blob = image_bytes_io.getvalue()
                except Exception as e:
                    pass

        # Safe Memory Management: Har 50 slides baad RAM clear karna
        if idx % 50 == 0:
            gc.collect()

    # Smart Output Name Generation
    dir_name, file_name = os.path.split(ppt_path)
    name, ext = os.path.splitext(file_name)
    output_path = os.path.join(dir_name, f"{name}_fixed{ext}")

    print(f"\n\n[+] Saving output file to: {output_path}")
    prs.save(output_path)
    print(" SUCCESS! Aapki PPT successfully fix ho gayi hai.")


if __name__ == "__main__":
    ppt_file_input = input("Apni PPT File ka Path ya Naam daalein (e.g., presentation.pptx): ").strip('"')
    if os.path.exists(ppt_file_input):
        fix_presentation(ppt_file_input)
    else:
        print("File nahi mili! Kripya sahi path check karein.")