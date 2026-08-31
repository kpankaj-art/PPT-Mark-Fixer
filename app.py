import streamlit as st
import cv2
import numpy as np
from pptx import Presentation
import io
import gc  # Memory cleanup ke liye module

def fix_drawn_box_in_image(image_bytes):
    try:
        file_bytes = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            return image_bytes, False

        h, w = img.shape[:2]
        max_dim = 800
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            small_img = cv2.resize(img, (int(w * scale), int(h * scale)))
        else:
            small_img = img.copy()

        gray = cv2.cvtColor(small_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 150)
        
        kernel = np.ones((3, 3), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_rect = None
        max_area = 0
        mask = np.zeros_like(gray)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 1000 and area < (small_img.shape[0] * small_img.shape[1] * 0.75):
                if area > max_area:
                    max_area = area
                    best_rect = cv2.boundingRect(cnt)
                    cv2.drawContours(mask, [cnt], -1, 255, thickness=8)

        if best_rect is not None:
            if scale != 1.0:
                mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                x = int(best_rect[0] / scale)
                y = int(best_rect[1] / scale)
                bw = int(best_rect[2] / scale)
                bh = int(best_rect[3] / scale)
            else:
                x, y, bw, bh = best_rect

            clean_img = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
            cv2.rectangle(clean_img, (x, y), (x + bw, y + bh), (0, 255, 0), 4)
            
            _, encoded_img = cv2.imencode('.png', clean_img)
            
            # Temporary Memory Clear
            del img, gray, blurred, edges, mask, clean_img
            return encoded_img.tobytes(), True

    except Exception:
        pass

    return image_bytes, False

def process_ppt(ppt_bytes):
    prs = Presentation(io.BytesIO(ppt_bytes))
    modified = False

    # Slide by Slide Processing Loop
    total_slides = len(prs.slides)
    progress_bar = st.progress(0)

    for idx, slide in enumerate(prs.slides):
        shapes_to_replace = [s for s in slide.shapes if s.shape_type == 13]
        
        for shape in shapes_to_replace:
            try:
                image_bytes = shape.image.blob
                fixed_image_bytes, is_modified = fix_drawn_box_in_image(image_bytes)
                
                if is_modified:
                    modified = True
                    shape.image._blob = fixed_image_bytes
                
                # Image level memory clean
                del image_bytes
            except Exception:
                continue
        
        # 1 Slide Done hone par progress update aur MEMORY CLEANUP
        progress_bar.progress(int((idx + 1) / total_slides * 100))
        gc.collect()  # Forcefully Server ki RAM Khali karna

    out_stream = io.BytesIO()
    prs.save(out_stream)
    out_stream.seek(0)
    
    # Progress Bar Clear
    progress_bar.empty()
    return out_stream.getvalue(), modified

# --- STREAMLIT UI ---
st.set_page_config(page_title="PPT Recce Mark Corrector", layout="centered")

st.title("PPT Recce Mark Corrector")
st.write("PPT upload karein, tool slide-by-slide process karke straight green boxes fix karega.")

uploaded_ppt = st.file_uploader("Apni PowerPoint (.pptx) file choose karein", type=["pptx"])

if uploaded_ppt is not None:
    if st.button("Process PPT", type="primary"):
        with st.spinner("Processing Slides... Please wait..."):
            processed_ppt_bytes, status = process_ppt(uploaded_ppt.read())
            
            if status:
                st.success("PPT Successfully Processed!")
                st.download_button(
                    label="Download Fixed PPT",
                    data=processed_ppt_bytes,
                    file_name=f"Fixed_{uploaded_ppt.name}",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
            else:
                st.warning("PPT ke images me koi marker box detect nahi hua.")
