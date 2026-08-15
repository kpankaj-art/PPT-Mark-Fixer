import os
import io
import gc
import streamlit as st
from pptx import Presentation
from PIL import Image, ImageDraw, ImageFilter

def process_image(image_bytes, mode_choice):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return image_bytes

    if mode_choice == "1":
        # Clean Image Option: Minor noise smooth out karna
        processed_img = img.filter(ImageFilter.MEDIAN_FILTER(size=3))
    elif mode_choice == "2":
        # Fix Option: Bounding Box Overlay
        processed_img = img.copy()
        draw = ImageDraw.Draw(processed_img)
        w, h = processed_img.size
        # Draw a sharp clean box near boundaries
        draw.rectangle([int(w*0.1), int(h*0.1), int(w*0.9), int(h*0.9)], outline="red", width=4)
    else:
        processed_img = img

    output = io.BytesIO()
    processed_img.save(output, format="PNG")
    return output.getvalue()

st.title("PPT Image Fixer Tool")
st.write("Apni PPT Upload Karein aur Options Select Karein.")

option = st.radio("Konsa action perform karna hai?", ["1. Clean Image", "2. Fix & Square Boxes"])
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
                if shape.has_image:
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
        
        st.success("Processing Complete!")
        st.download_button(
            label="Download Fixed PPT",
            data=output_stream,
            file_name="fixed_presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
