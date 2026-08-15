import io
import gc
import cv2
import numpy as np
import streamlit as st
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from PIL import Image

def process_image(image_bytes, mode_choice):
    try:
        # Convert bytes to OpenCV BGR format
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        # Grayscale & Edges detect karna hand-drawn marks dhundne ke liye
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Contours (Shapes) find karna
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        clean_img = img.copy()

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Sirf medium aur bade dabbo ko target karein
            if area > 800:
                x, y, w, h = cv2.boundingRect(cnt)

                if mode_choice == "1":
                    # OPTION 1: Terhe-medhe hand-drawn box ko completely erase/clean karna
                    mask = np.zeros(img.shape[:2], np.uint8)
                    cv2.drawContours(mask, [cnt], -1, 255, 7)
                    clean_img = cv2.inpaint(clean_img, mask, 5, cv2.INPAINT_TELEA)

                elif mode_choice == "2":
                    # OPTION 2: Hand-drawn box ko erase karke Perfect Straight Red Box banana
                    mask = np.zeros(img.shape[:2], np.uint8)
                    cv2.drawContours(mask, [cnt], -1, 255, 7)
                    clean_img = cv2.inpaint(clean_img, mask, 5, cv2.INPAINT_TELEA)
                    # Draw sharp perfect rectangle
                    cv2.rectangle(clean_img, (x, y), (x + w, y + h), (0, 0, 255), 4)

        # Convert back to PNG bytes
        is_success, buffer = cv2.imencode(".png", clean_img)
        if is_success:
            return buffer.tobytes()
        return image_bytes

    except Exception as e:
        return image_bytes

st.title("PPT Image Fixer Tool (Real CV2 Engine)")
st.write("Hand-drawn boxes ko detect karke fix ya remove karne ka tool.")

option = st.radio("Konsa action perform karna hai?", ["1. Clean Image (Remove Hand-Drawn Boxes)", "2. Fix & Square Boxes (Convert to Perfect Red Boxes)"])
uploaded_file = st.file_uploader("Choose PPTX File", type=["pptx"])

if uploaded_file is not None:
    if st.button("Process PPT"):
        prs = Presentation(uploaded_file)
        total_slides = len(prs.slides)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, slide in enumerate(prs.slides, start=1):
            status_text.text(f"Processing Slide {idx}/{total_slides}...")
            
            for shape in slide.shapes:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    try:
                        image_bytes = shape.image.blob
                        fixed_bytes = process_image(image_bytes, option[0])
                        shape.image.blob = fixed_bytes
                    except Exception:
                        pass
            
            progress_bar.progress(idx / total_slides)
            if idx % 50 == 0:
                gc.collect()

        output_stream = io.BytesIO()
        prs.save(output_stream)
        output_stream.seek(0)
        
        st.success("PPT Fix Ho Gayi Hai! Download karein:")
        st.download_button(
            label="Download Fixed PPT",
            data=output_stream,
            file_name="fixed_presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
