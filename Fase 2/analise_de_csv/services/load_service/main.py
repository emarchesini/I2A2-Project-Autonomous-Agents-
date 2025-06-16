# main.py
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, status
import shutil
import os
import logging
import asyncio

from config import UPLOAD_DIR
from file_utils import process_zip_file
from db_utils import create_db_and_tables, load_data_from_csv, get_database_statistics

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def try_db_connect_with_retry(create_db_and_tables, retries=10, delay=2):
    for attempt in range(retries):
        try:
            await create_db_and_tables()
            logger.info("Database initialized successfully.")
            return
        except Exception as e:
            logger.error(f"Database connection failed (attempt {attempt+1}/{retries}): {e}")
            await asyncio.sleep(delay)
    logger.error("Could not connect to the database after several attempts.")

@app.on_event("startup")
async def startup_event():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
    # Attempt to create DB and tables on startup if they don't exist, with retry logic.
    await try_db_connect_with_retry(create_db_and_tables)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "load_service"}

@app.get("/status")
async def status_check():
    """Status check endpoint with database statistics"""
    try:
        db_stats = await get_database_statistics()
        return {
            "status": "online",
            "service": "load_service",
            **db_stats
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "status": "online",
            "service": "load_service",
            "notas_fiscais": 0,
            "itens_nota_fiscal": 0,
            "total_records": 0,
            "total_value": 0.0,
            "last_upload": None
        }

@app.post("/upload-nfe-zip/")
async def upload_nfe_zip(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Only ZIP files are allowed.")

    temp_zip_path = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")

    try:
        # Save the uploaded zip file temporarily
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Temporary ZIP file saved to {temp_zip_path}")

        # Process the zip file (extract and validate)
        cabecalho_csv_path, itens_csv_path = process_zip_file(temp_zip_path)
        logger.info(f"ZIP file processed. Cabecalho: {cabecalho_csv_path}, Itens: {itens_csv_path}")

        # Create database and tables (idempotent - will drop and recreate)
        # Consider if dropping tables every time is desired, or if you want to append/update.
        # For this example, we recreate to ensure a clean state for each upload.
        await create_db_and_tables()
        logger.info("Database and tables created/recreated.")

        # Load data from CSV files into the database
        await load_data_from_csv(cabecalho_csv_path, itens_csv_path)
        logger.info("Data loaded into database successfully.")

        return {"message": f"File '{file.filename}' processed, data loaded into database successfully."}

    except HTTPException as e:
        logger.error(f"HTTP Exception during upload: {e.detail}")
        raise e # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # Clean up the temporary zip file
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
            logger.info(f"Temporary ZIP file {temp_zip_path} removed.")
        # The extracted CSVs are currently left in UPLOAD_DIR. 
        # You might want to clean them up too, or move them to an archive.
        # For now, file_utils.ensure_upload_dir_exists() cleans UPLOAD_DIR on next run.

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 