import streamlit as st
import fitz  # PyMuPDF
import re
import pandas as pd
import tempfile
from io import BytesIO
from PIL import Image

# === SETTINGS ===
known_brands = ['FRAZIL', 'CAFE TANGO', 'ENGY', 'REFURB']

# Precompiled regex for brand detection
brand_regex = re.compile(r'\b(?:' + '|'.join(re.escape(b) for b in known_brands) + r')\b', re.IGNORECASE)

# Serial number pattern
serial_pattern = r'ULT\w{7}'

# Block markers
block_start_marker = "Shipped Serial Numbers/Asset Numbers"
block_end_marker = "58000.0605"

# Brand display mapping
brand_map = {
    "FRAZIL": "FRAZIL",
    "CAFE TANGO": "CAFÉ TANGO",
    "ENGY": "ENERGY",
    "REFURB": "FRAZIL"
}

# === STREAMLIT UI ===
st.set_page_config(page_title="PDF Serial Extractor", layout="centered")
image = Image.open("1Frazil_Logo.png")
st.image(image, width=300)  # Adjust width as needed
st.title("🔍 PDF Serial Number Extractor")
st.markdown("Upload one or more PDFs to extract serial numbers and associated brands.")

uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    serial_numbers = []
    brands = []

    for uploaded_file in uploaded_files:
        # Save uploaded file to a temporary path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        # Read full PDF text
        with fitz.open(tmp_path) as doc:
            full_text = "".join(page.get_text() for page in doc)

        # Find start and end positions
        start_positions = [m.start() for m in re.finditer(re.escape(block_start_marker), full_text)]
        end_positions = [m.start() for m in re.finditer(re.escape(block_end_marker), full_text)]
        used_end_indices = set()

        for start_idx in start_positions:
            # Find the nearest unused end marker after the start
            block_end = None
            for end_idx in end_positions:
                if end_idx > start_idx and end_idx not in used_end_indices:
                    block_end = end_idx
                    used_end_indices.add(end_idx)
                    break

            if block_end is None:
                st.warning(f"No end marker found for block starting at index {start_idx}. Skipping.")
                continue

            # Extract block text and look behind for brand
            block_text = full_text[start_idx:block_end]
            preceding_text = full_text[max(0, start_idx - 50):start_idx]
            brand_match = brand_regex.search(preceding_text)
            raw_brand = brand_match.group(0).upper() if brand_match else "Unknown"
            brand = brand_map.get(raw_brand, "Unknown")

            # Extract serial numbers
            serials = re.findall(serial_pattern, block_text)
            for serial in serials:
                serial_numbers.append(serial)
                brands.append(brand)

    # Create a DataFrame
    df = pd.DataFrame({
        'Serial Number': serial_numbers,
        'Brand': brands
    })

    st.success(f"✅ Extracted {len(df)} serial numbers from {len(set(brands))} brands.")
    st.dataframe(df)

    # Export to Excel and allow download
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    st.download_button(
        label="📥 Download Excel File",
        data=output.getvalue(),
        file_name="extracted_serials.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
