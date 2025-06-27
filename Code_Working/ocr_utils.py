import easyocr
import pandas as pd
import pyodbc
import tempfile
import os
from typing import List, Union
from pdf2image import convert_from_path
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

# --- Streamlit cache to load OCR only once ---
@st.cache_resource
def load_easyocr_model():
    return easyocr.Reader(['en'], gpu=True)

reader = load_easyocr_model()

# --- Function 1: OCR Extractor ---
def extract_table_data(image_path: str) -> List[List[str]]:
    results = reader.readtext(image_path)

    def get_y_center(bbox): return (bbox[0][1] + bbox[2][1]) / 2
    def get_x_left(bbox): return bbox[0][0]

    annotated = [(get_y_center(bbox), get_x_left(bbox), text) for bbox, text, _ in results]
    annotated.sort(key=lambda x: x[0])

    grouped_rows = []
    current_row = []
    threshold = 10

    for item in annotated:
        y, x, text = item
        if not current_row:
            current_row.append(item)
        else:
            prev_y = current_row[-1][0]
            if abs(y - prev_y) <= threshold:
                current_row.append(item)
            else:
                grouped_rows.append(current_row)
                current_row = [item]
    if current_row:
        grouped_rows.append(current_row)

    final_rows = []
    for row in grouped_rows:
        row.sort(key=lambda x: x[1])
        final_rows.append([text for _, _, text in row])

    # Keep only rows with exactly 5 fields
    cleaned_rows = [r for r in final_rows if len(r) == 5]

    if not cleaned_rows:
        print("⚠️ No valid rows found.")
    else:
        print("📊 Extracted Rows:")
        for row in cleaned_rows:
            print(row)

    return cleaned_rows


# --- Helper: Handle PDF or Image input ---
def extract_data_from_input(file_path: str) -> List[List[str]]:
    if file_path.lower().endswith(".pdf"):
        # Convert all pages to images
        pages = convert_from_path(file_path, dpi=200, thread_count=4)

        image_paths = []
        for i, page in enumerate(pages):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                page.save(tmp.name, format='JPEG')
                image_paths.append(tmp.name)

        # Parallel OCR for speed
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(extract_table_data, image_paths))

        # Flatten all extracted rows
        all_rows = [row for page_rows in results for row in page_rows]
        return all_rows

    else:
        return extract_table_data(file_path)


# --- Function 2: Insert to SQL ---
def insert_into_sql(rows: List[List[str]]):
    conn_str = (
        "Driver={SQL Server};"
        "Server=Anant;"
        "Database=eugiaDB;"
        "Trusted_Connection=yes;"
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    sql_query = """
        INSERT INTO dbo.final 
        ([Material Code], [UOM], [Quantity Required], [Quantity Issued], [Lot No])
        VALUES (?, ?, ?, ?, ?)
    """

    for i, row in enumerate(rows):
        if len(row) != 5:
            print(f"⚠️ Skipping row {i+1}: {row}")
            continue
        try:
            cursor.execute(sql_query, tuple(row))
            print(f"✅ Inserted row {i+1}")
        except Exception as e:
            print(f"❌ Failed row {i+1}: {e}")

    conn.commit()
    conn.close()
