from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import json
import os

# Load .env from project root (../../.env relative to this file)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
DB_PATH = os.getenv("DB_PATH")

app = FastAPI(title="Job Saver API")

# Define request schema
class JobPage(BaseModel):
    url: str
    html: str

# Endpoint for Chrome extension to send page
@app.post("/api/save-job")
async def save_job(job: JobPage):
    print(f"Received job URL: {job.url}")

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"{DB_PATH}/jobs/{now}.json", "w") as f:
        f.write(json.dumps({
            "url": job.url,
            "html": job.html,
            "date": now
        }))
    
    # For now, just return a success message
    return {"status": "success", "url": job.url}
