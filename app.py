import streamlit as st
import cv2
import numpy as np
from pptx import Presentation
import io

def fix_drawn_box_in_image(image_bytes):
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if img is None:
        return image_bytes, False

    # Speed Optimization: Agar image bohot badi hai to scan ke liye scale karein
    h, w = img.shape[:2]
    max_dim = 1000
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
        # Mask ko original full-size image dimensions par wapas scaled up karna
        if scale != 1.0:
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
            x = int(best_rect[0] / scale)
            y = int(best_rect[1] / scale)
            bw = int(best_rect[2] / scale)
            bh = int(best_rect[3] / scale)
        else:
            x, y, bw, bh = best_rect

        # Fast Inpainting (Navier-Stokes Algorithm - 5x Faster)
        clean_img = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
        
        # Perfect Straight Green Box Draw karna
        cv2.rectangle(clean_img, (x, y), (x + bw, y + bh), (0, 255, 0), 4)
        
        _, encoded_img = cv2.imencode('.png', clean_img)
        return encoded_img.tobytes(), True

    return image_bytes, False

def process_ppt(ppt_bytes):
    prs = Presentation(io.BytesIO(ppt_bytes))
    modified = False

    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.shape_type == 13: # Picture Shape
                image_stream = shape.image.blob
                fixed_image_bytes, is_modified = fix_drawn_box_in_image(image_stream)
                
                if is_modified:
                    modified = True
                    new_img_stream = io.BytesIO(fixed_image_bytes)
                    left, top, width, height = shape.left, shape.top, shape.width, shape.height
                    
                    sp = shape._element
                    sp.getparent().remove(sp)
                    slide.shapes.add_picture(new_img_stream, left, top, width, height)

    out_stream = io.BytesIO()
    prs.save(out_stream)
    out_stream.seek(0)
    return out_stream.getvalue(), modified

# --- STREAMLIT UI ---
st.set_page_config(page_title="PPT Recce Mark Corrector", layout="centered")

st.title("PPT Recce Mark Corrector")
st.write("PPT upload karein, ye tool hand-drawn boxes ko straight green boxes me fix kar dega.")

uploaded_ppt = st.file_uploader("Apni PowerPoint (.pptx) file choose karein", type=["pptx"])

if uploaded_ppt is not None:
    if st.button("Process PPT", type="primary"):
        with st.spinner("Fast Processing active... Images scan ho rahi hain..."):
            processed_ppt_bytes, status = process_ppt(uploaded_ppt.read())
            
            if status:
                st.success("PPT Successfully Process Ho Gayi!")
                st.download_button(
                    label="Download Fixed PPT",
                    data=processed_ppt_bytes,
                    file_name=f"Fixed_{uploaded_ppt.name}",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
            else:
                st.warning("PPT ke images me koi hand-drawn marker box detect nahi hua.")
