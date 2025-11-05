from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

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
    with open(f"jobs/{now}.json", "w") as f:
        f.write(json.dumps({
            "url": job.url,
            "html": job.html,
            "date": now
        }))
    
    # For now, just return a success message
    return {"status": "success", "url": job.url}
