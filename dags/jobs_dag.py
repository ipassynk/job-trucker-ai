import os
from pathlib import Path
from airflow.decorators import dag, task
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
# In Docker, .env should be available via volume mount or environment variables
env_path = Path("/opt/airflow") / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

def _on_failure_callback(context):
    """Callback function to execute when a task fails."""
    print(f"Task {context['task_instance'].task_id} failed")
    print(f"Error: {context['exception']}")
    print(f"Traceback: {context['traceback']}")

@dag(
    dag_id="jobs_dag",
    start_date=datetime(2025, 1, 1),
    schedule='@daily',
    catchup=False,
    default_args={'on_failure_callback': _on_failure_callback}
    on_failure_callback=_on_failure_callback
)
def jobs_dag():

    @task
    def create_collection_if_not_exists() -> None:
        """Initialize vector database collection if it doesn't exist."""
        from apps.database import get_vector_db
        vectorstore = get_vector_db()
        print("Vector database collection initialized/verified")
    
    _create_collection_if_not_exists = create_collection_if_not_exists()
    
    @task
    def list_jobs() -> List[Dict[str, str]]:
        """List all job JSON files from the jobs directory."""
        # DB_PATH can be:
        # - Absolute path like /opt/airflow/jobs (use directly)
        # - Relative path like "jobs" (resolve to absolute)
        # - Path to parent directory like /opt/airflow (append /jobs)
        db_path = os.getenv("DB_PATH", "/opt/airflow/jobs")
        
        # Convert to Path and resolve if relative
        db_path_obj = Path(db_path)
        if not db_path_obj.is_absolute():
            # If relative, resolve from /opt/airflow (default Airflow working directory)
            db_path_obj = Path("/opt/airflow") / db_path
        
        # If path doesn't end with "jobs", append it
        if db_path_obj.name != "jobs":
            jobs_dir = db_path_obj / "jobs"
        else:
            jobs_dir = db_path_obj
        
        # Make absolute for clarity
        jobs_dir = jobs_dir.resolve()
        
        print(f"Looking for jobs in: {jobs_dir}")
        if not jobs_dir.exists():
            print(f"Jobs directory does not exist: {jobs_dir}")
            return []
        
        job_files = []
        for json_file in jobs_dir.glob("*.json"):
            job_files.append({
                "file_path": str(json_file),
                "filename": json_file.name
            })
        
        print(f"Found {len(job_files)} job files")
        return job_files
    
    _list_jobs = list_jobs()
    
    @task(pool='job_processing_pool', pool_slots=1)
    def process_single_job(job_file: Dict[str, str]) -> Dict:
        """Process a single job file. Limited to 1 concurrent execution via pool."""
        import json
        from apps.rag import extract_job_info
        
        file_path = job_file["file_path"]
        try:
            print(f"Processing job file: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                url = json_data.get("url", "")
                timestamp = json_data.get("date", "")
            
            job_info = extract_job_info(file_path)
            
            # Convert Pydantic model to dict for Airflow XCom
            result = {
                "position_name": job_info.position_name,
                "position_description": job_info.position_description,
                "company": job_info.company,
                "salary": job_info.salary,
                "url": url,
                "timestamp": timestamp,
                "file_path": file_path
            }
            print(f"Processed job: {job_info.position_name} at {job_info.company}")
            return result
        except Exception as e:
            error_msg = f"Error extracting job info from {file_path}: {e}"
            print(error_msg)
            # Return error info instead of raising - allows other jobs to continue
            return {
                "error": str(e),
                "file_path": file_path,
                "position_name": None,
                "position_description": None,
                "company": None,
                "salary": None,
                "url": "",
                "timestamp": ""
            }
 
    _extracted_jobs = process_single_job.expand(job_file=_list_jobs)
    
    @task
    def load_job_to_vector_db(job_data: Dict) -> None:
        """Load a job to vector database."""
        from apps.database import get_vector_db
        from apps.rag import save_job_to_vector_db, JobInfo
        
        # Skip if there was an error in processing
        if job_data.get("error"):
            print(f"Skipping job with error: {job_data.get('file_path')} - {job_data.get('error')}")
            return
        
        try:
            job_info = JobInfo(
                position_name=job_data["position_name"],
                position_description=job_data["position_description"],
                company=job_data["company"],
                salary=job_data.get("salary")
            )
            
            url = job_data.get("url", "")
            timestamp = job_data.get("timestamp", "")
            
            # Save to vector database
            doc_id = save_job_to_vector_db(job_info, url, timestamp)
            print(f"Saved job '{job_info.position_name}' at {job_info.company} to vector DB with ID: {doc_id}")
        except Exception as e:
            print(f"Error saving job to vector DB: {e}")
            # Don't raise - allows other jobs to continue processing

    _load_job_to_vector_db = load_job_to_vector_db.expand(job_data=_extracted_jobs)
    
    # dependencies
    _create_collection_if_not_exists >> _list_jobs >> _extracted_jobs >> _load_job_to_vector_db

dag_instance = jobs_dag()