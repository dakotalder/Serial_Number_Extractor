import streamlit as st
from PIL import Image
import re
import fitz  # PyMuPDF
import pandas as pd
import tempfile
from io import BytesIO

# Streamlit page config
st.set_page_config(page_title="PDF Serial Extractor", layout="centered")

# Centered container CSS
st.markdown("""
    <style>
        .centered-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            max-width: 800px;
            margin: 0 auto;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="centered-container">', unsafe_allow_html=True)

# Logo and title
try:
    image = Image.open("1Frazil_Logo.png")
    st.image(image, width=300)
except FileNotFoundError:
    st.markdown("### 🔍 PDF Serial Number Extractor")
else:
    st.markdown("## 🔍 PDF Serial Number Extractor")

st.markdown("Upload one or more PDFs to extract serial numbers and associated brands.")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)

# Config
known_brands = ['FRAZIL', 'CAFE TANGO', 'ENGY', 'REFURB']
brand_map = {
    "FRAZIL": "FRAZIL",
    "CAFE TANGO": "CAFÉ TANGO",
    "ENGY": "ENERGY",
    "REFURB": "FRAZIL"
}
brand_regex = re.compile(r'\b(?:' + '|'.join(re.escape(b) for b in known_brands) + r')\b', re.IGNORECASE)
serial_pattern = r'ULT\w{7}'

# Flexible start marker regex: ULTRA NX, BA 120V with flexible spaces/commas
start_block_pattern = re.compile(r"ULTRA\s*NX[\s,]*BA\s*120V", re.IGNORECASE)
end_block_marker = "58000.0605"

if uploaded_files:
    # Extract all text from all PDFs into one string
    full_text = ""
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        with fitz.open(tmp_path) as doc:
            for page in doc:
                full_text += page.get_text() + "\n"

    serial_numbers = []
    brands = []

    # Find all start positions
    start_positions = [m.start() for m in start_block_pattern.finditer(full_text)]
    # Find all end positions
    end_positions = [m.start() for m in re.finditer(re.escape(end_block_marker), full_text)]

    used_end_indices = set()

    for start_idx in start_positions:
        # Find the closest end marker that is after start_idx and not used yet
        block_end = None
        for end_idx in end_positions:
            if end_idx > start_idx and end_idx not in used_end_indices:
                block_end = end_idx
                used_end_indices.add(end_idx)
                break

        if block_end is None:
            st.warning(f"No end marker found for block starting at index {start_idx}. Skipping.")
            continue

        block_text = full_text[start_idx:block_end]

        # Find brand inside the block
        brand_match = brand_regex.search(block_text)
        raw_brand = brand_match.group(0).upper() if brand_match else "Unknown"
        brand = brand_map.get(raw_brand, "Unknown")

        # Find serials inside the block
        serials = re.findall(serial_pattern, block_text)
        for serial in serials:
            serial_numbers.append(serial)
            brands.append(brand)

    df = pd.DataFrame({'Serial Number': serial_numbers, 'Brand': brands})

    st.success(f"✅ Extracted {len(df)} serial numbers from {len(set(brands))} brands.")
    st.dataframe(df)

    # Excel download
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    st.download_button(
        label="📥 Download Excel File",
        data=output,
        file_name="extracted_serials.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown('</div>', unsafe_allow_html=True)
