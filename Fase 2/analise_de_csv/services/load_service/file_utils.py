import zipfile
import os
import shutil
import re
from fastapi import HTTPException, status

from config import UPLOAD_DIR

CABECALHO_SUFFIX = "_NFs_Cabecalho.csv"
ITENS_SUFFIX = "_NFs_Itens.csv" # Corrected from _Nfs_Itens.csv to _NFs_Itens.csv based on user query

def ensure_upload_dir_exists():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def clean_upload_dir():
    """Clean up previous uploads in the upload directory"""
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

def process_zip_file(file_path: str) -> tuple[str, str]:
    # Only ensure directory exists, don't clean it
    ensure_upload_dir_exists()
    extracted_files = []
    cabecalho_file = None
    itens_file = None

    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Check for invalid characters in filenames within the zip
            for member_name in zip_ref.namelist():
                if '..' in member_name or member_name.startswith('/'):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zip file contains invalid or malicious file paths.")
            
            zip_ref.extractall(UPLOAD_DIR)
            # Get only the extracted files, not including the original zip file
            all_files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
            # Filter out the original zip file from the list
            extracted_files = [f for f in all_files if not f.endswith('.zip')]
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ZIP file.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing ZIP file: {e}")

    if len(extracted_files) != 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Expected 2 files in the ZIP, but found {len(extracted_files)}.")

    for f_path in extracted_files:
        filename = os.path.basename(f_path)
        if filename.endswith(CABECALHO_SUFFIX):
            if cabecalho_file:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Multiple Cabecalho files found.")
            cabecalho_file = f_path
        elif filename.endswith(ITENS_SUFFIX):
            if itens_file:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Multiple Itens files found.")
            itens_file = f_path
        else:
            # This check is a bit redundant given the exact match logic, but good for robustness
            # or if suffix matching becomes more complex.
            # For now, if it doesn't match either, it's an unexpected file.
            pass # Let the later checks for None handle missing specific files

    if not cabecalho_file or not itens_file:
        missing = []
        if not cabecalho_file: missing.append("Cabecalho file (e.g., *" + CABECALHO_SUFFIX + ")")
        if not itens_file: missing.append("Itens file (e.g., *" + ITENS_SUFFIX + ")")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Missing required files: {', '.join(missing)}.")

    # Check if files are empty
    if os.path.getsize(cabecalho_file) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cabecalho file is empty.")
    if os.path.getsize(itens_file) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Itens file is empty.")

    return cabecalho_file, itens_file 