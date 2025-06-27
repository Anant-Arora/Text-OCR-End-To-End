import streamlit as st
from PIL import Image
import tempfile
import os

from ocr_utils import extract_data_from_input, insert_into_sql

# --- Streamlit Page Config ---
st.set_page_config(page_title="Aurobindo OCR Uploader", layout="centered")

st.title("🧪 Aurobindo Handwritten Table OCR")
st.markdown("Upload a handwritten **image or PDF** to extract table data and insert into SQL Server.")

# --- Upload File ---
uploaded_file = st.file_uploader("📤 Upload Image or PDF", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file is not None:
    # Save the file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1]) as tmp_file:
        tmp_file.write(uploaded_file.read())
        file_path = tmp_file.name

    # Display preview
    if uploaded_file.type.startswith("image"):
        image = Image.open(file_path)
        st.image(image, caption="📷 Uploaded Image", use_column_width=True)
    elif uploaded_file.type == "application/pdf":
        st.info("📄 PDF uploaded. Pages will be processed as images.")

    # --- Extract and Display Data ---
    try:
        with st.spinner("🔍 Running OCR..."):
            extracted_rows = extract_data_from_input(file_path)

        if extracted_rows:
            st.success(f"✅ OCR completed. {len(extracted_rows)} rows extracted.")
            st.markdown("### 📋 Extracted Table Data:")
            st.dataframe(extracted_rows)

            if st.button("📥 Insert into SQL Server"):
                with st.spinner("📡 Inserting into SQL..."):
                    insert_into_sql(extracted_rows)
                st.success("🎯 Data inserted successfully!")
        else:
            st.warning("⚠️ No valid rows found in the uploaded file.")

    except Exception as e:
        st.error(f"❌ Error during processing:\n\n{e}")

