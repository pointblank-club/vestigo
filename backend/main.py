import hashlib
import random
import mimetypes
import traceback
import sys
import os
import glob
import json
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from prisma import Prisma
from datetime import datetime

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Import our services
from config.logging_config import logger
from services.ingest_service import IngestService
from services.feature_extraction_service import FeatureExtractionService
from services.filesystem_scan_service import FilesystemScanService
from services.secure_boot_analysis_service import SecureBootAnalysisService
from services.crypto_library_service import CryptoLibraryService
from services.qiling_dynamic_analysis_service import QilingDynamicAnalysisService
from services.binary_converter_service import BinaryConverterService
from services.llm_analysis_service import LLMAnalysisService
from services.job_manager import job_manager, JobStatus

# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(title="Vestigo Backend")

# Initialize services
ingest_service = IngestService()
feature_service = FeatureExtractionService()
filesystem_service = FilesystemScanService()
secureboot_service = SecureBootAnalysisService()
cryptolib_service = CryptoLibraryService()
qiling_service = QilingDynamicAnalysisService()
converter_service = BinaryConverterService()
llm_service = LLMAnalysisService()

logger.info("Vestigo Backend starting up...")

# ==========================================================
# CORS CONFIG
# ==========================================================

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://[::]:8080",  # IPv6 localhost
    "https://vestigo.pointblank.club",  # Production domain
    *ALLOWED_ORIGINS,  # Additional origins from environment
]

# In development, allow all origins
is_dev = os.getenv("ENVIRONMENT", "development") == "development"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_dev else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ==========================================================
# DATABASE (PRISMA)
# ==========================================================

db = Prisma()


@app.on_event("startup")
async def startup():
    logger.info("🔌 Connecting to database…")
    await db.connect()
    logger.info("✅ Database connected.")
    logger.info("🚀 Vestigo Backend ready")


@app.on_event("shutdown")
async def shutdown():
    logger.info("🔌 Disconnecting database…")
    await db.disconnect()
    logger.info("🛑 Database disconnected.")
    logger.info("👋 Vestigo Backend shutdown complete")


# ==========================================================
# HELPERS
# ==========================================================

CRYPTO_TYPES = [
    ("AES", "AES-128", "High", "Symmetric block cipher detected"),
    ("AES", "AES-256", "Critical", "Strong AES block detected"),
    ("RSA", "RSA-1024", "Medium", "RSA key operations found"),
    ("ECC", "Curve25519", "High", "ECC operations detected"),
    ("SHA", "SHA-256", "Low", "Hashing function present"),
    ("XOR", "XOR Loop", "Critical", "Weak obfuscation loop found"),
]


def analyze(content: bytes):
    findings = []
    count = random.randint(0, 5)

    for _ in range(count):
        name, variant, sev, desc = random.choice(CRYPTO_TYPES)
        findings.append({
            "name": name,
            "algorithm": name,
            "variant": variant,
            "severity": sev,
            "description": desc,
        })

    return findings, count


def generate_hash(data: bytes):
    return hashlib.md5(data).hexdigest()


def detect_type(filename: str):
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def format_size(bytes_len: int):
    return f"{bytes_len / 1024 / 1024:.2f} MB"


def severity_level(count: int):
    if count == 0:
        return "safe"
    if count == 1:
        return "low"
    if 2 <= count <= 3:
        return "high"
    return "critical"


def collect_job_analysis_data(job_id: str) -> Dict[str, Any]:
    """
    Collect all analysis data for a job including job storage, qiling output, 
    pipeline output, and any related child jobs.
    """
    analysis_data = {
        "job_id": job_id,
        "job_storage_data": None,
        "qiling_output": None,
        "pipeline_output": None,
        "child_jobs": [],
        "related_files": []
    }
    
    # Paths for different output locations
    job_storage_dir = Path("job_storage")
    qiling_output_dir = Path("qiling_output") 
    pipeline_output_dir = Path("pipeline_output")
    
    try:
        # Load job storage data
        job_storage_file = job_storage_dir / f"{job_id}.json"
        if job_storage_file.exists():
            with open(job_storage_file, 'r') as f:
                analysis_data["job_storage_data"] = json.load(f)
        
        # Find qiling output files
        qiling_files = list(qiling_output_dir.glob(f"{job_id}_*.json"))
        if qiling_files:
            qiling_data = []
            for qiling_file in qiling_files:
                try:
                    with open(qiling_file, 'r') as f:
                        qiling_content = json.load(f)
                        qiling_data.append({
                            "filename": qiling_file.name,
                            "data": qiling_content
                        })
                except Exception as e:
                    logger.warning(f"Failed to load qiling file {qiling_file}: {e}")
            
            analysis_data["qiling_output"] = qiling_data
        
        # Find pipeline output files  
        if analysis_data["job_storage_data"]:
            filename = analysis_data["job_storage_data"].get("filename", "")
            binary_name = filename.split('.')[0] if filename else ""
            
            # Look for pipeline files matching this binary
            pipeline_files = []
            for pattern in [f"*{binary_name}*_pipeline.json", f"*{binary_name}*_pipeline_features.csv"]:
                pipeline_files.extend(list(pipeline_output_dir.glob(pattern)))
            
            if pipeline_files:
                pipeline_data = []
                for pipeline_file in pipeline_files:
                    try:
                        if pipeline_file.suffix == '.json':
                            with open(pipeline_file, 'r') as f:
                                content = json.load(f)
                        else:  # CSV files
                            with open(pipeline_file, 'r') as f:
                                content = f.read()
                        
                        pipeline_data.append({
                            "filename": pipeline_file.name,
                            "type": "json" if pipeline_file.suffix == '.json' else "csv", 
                            "data": content
                        })
                    except Exception as e:
                        logger.warning(f"Failed to load pipeline file {pipeline_file}: {e}")
                
                analysis_data["pipeline_output"] = pipeline_data
        
        # Look for child jobs (bootloader analysis jobs, crypto library jobs, etc.)
        # These would have references to the parent job in their job storage
        all_job_files = list(job_storage_dir.glob("*.json"))
        for job_file in all_job_files:
            if job_file.stem == job_id:  # Skip the main job
                continue
                
            try:
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    
                # Check if this job references our parent job
                analysis_results = job_data.get("analysis_results")
                if analysis_results and isinstance(analysis_results, dict) and analysis_results.get("parent_job_id") == job_id:
                    analysis_data["child_jobs"].append({
                        "job_id": job_file.stem,
                        "job_data": job_data
                    })
            except Exception as e:
                # Only log if it's an unexpected error, not None analysis_results
                if "NoneType" not in str(e):
                    logger.warning(f"Failed to check job file {job_file} for parent reference: {e}")
        
        # Collect information about all related files
        analysis_data["related_files"] = {
            "job_storage_files": len([f for f in job_storage_dir.glob(f"{job_id}*")]),
            "qiling_output_files": len(qiling_files) if qiling_files else 0,
            "pipeline_output_files": len(pipeline_files) if 'pipeline_files' in locals() else 0,
            "child_job_count": len(analysis_data["child_jobs"])
        }
        
        logger.info(f"Collected analysis data for job {job_id}: {analysis_data['related_files']}")
        
    except Exception as e:
        logger.error(f"Error collecting analysis data for job {job_id}: {e}", exc_info=True)
    
    return analysis_data


def wait_for_job_completion(job_id: str, max_wait_seconds: int = 30) -> Dict[str, Any]:
    """
    Wait for background job completion and return updated analysis data.
    This allows the API to return more complete data when possible.
    """
    import time
    
    start_time = time.time()
    while (time.time() - start_time) < max_wait_seconds:
        job = job_manager.get_job(job_id)
        if job and job.status in [JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.FEATURES_COMPLETE]:
            logger.info(f"Job {job_id} completed after {time.time() - start_time:.2f}s with status: {job.status}")
            return collect_job_analysis_data(job_id)
        
        time.sleep(0.5)  # Check every 500ms
    
    logger.info(f"Job {job_id} still processing after {max_wait_seconds}s, returning current data")
    return collect_job_analysis_data(job_id)


# ==========================================================
# ROUTES
# ==========================================================

@app.get("/")
def home():
    return {"message": "Vestigo Backend Running"}


# ----------------------------------------------------------
# UPLOAD + ANALYZE
# ----------------------------------------------------------
@app.post("/analyze")
async def upload_and_analyze(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Main endpoint for file analysis - integrates with ingest service
    """
    try:
        if file is None:
            logger.error("No file provided in upload")
            raise HTTPException(status_code=400, detail="No file provided")

        # Read file content
        content = await file.read()
        if not content:
            logger.error(f"Empty file uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        logger.info(f"Processing file upload: {file.filename} ({len(content)} bytes)")

        # Process through ingest service
        analysis_result = await ingest_service.process_uploaded_file(content, file.filename)
        job_id = analysis_result["jobId"]

        # Create job in our job manager
        job = job_manager.create_job(job_id, file.filename, len(content))

        # Update job with ingest results - extract from analysis_result structure
        if "analysis" in analysis_result:
            # Prepare ingest results structure for job manager
            ingest_results = {
                "routing": {
                    "decision": analysis_result["analysis"]["routing_decision"],
                    "reason": analysis_result["analysis"]["routing_reason"]
                },
                "file_info": {
                    "detected_type": analysis_result["analysis"]["file_type"]
                },
                "extraction": {
                    "was_extracted": analysis_result["analysis"]["extraction_success"]
                },
                "analysis_workspace": analysis_result["analysis"]["workspace_path"]
            }
            
            # Add bootloaders if found
            if "bootloaders" in analysis_result["analysis"]:
                ingest_results["bootloaders"] = analysis_result["analysis"]["bootloaders"]
            
            # Add PATH_C hard target info (includes crypto_strings with LLM analysis)
            if "hard_target_info" in analysis_result["analysis"]:
                ingest_results["hard_target_info"] = analysis_result["analysis"]["hard_target_info"]
            
            # Add PATH_A binary info
            if "binary_info" in analysis_result["analysis"]:
                ingest_results["binary_info"] = analysis_result["analysis"]["binary_info"]
            
            # Add PATH_B filesystem info
            if "filesystem_info" in analysis_result["analysis"]:
                ingest_results["filesystem_info"] = analysis_result["analysis"]["filesystem_info"]
            
            job_manager.update_job_ingest_results(job_id, ingest_results)

        # If it's PATH_A_BARE_METAL, add background task for feature extraction
        if analysis_result["analysis"]["routing_decision"] == "PATH_A_BARE_METAL":
            background_tasks.add_task(process_bare_metal_features, job_id, analysis_result)
            
            # If it's an ELF binary or object file, also run Qiling dynamic analysis in parallel
            binary_info = analysis_result["analysis"].get("binary_info", {})
            is_elf = binary_info.get("is_elf", False)
            is_object = binary_info.get("is_object_file", False)
            
            if is_elf or is_object:
                file_type = "ELF" if is_elf else "object file (.o)"
                logger.info(f"{file_type} detected - adding Qiling dynamic analysis - JobID: {job_id}")
                background_tasks.add_task(process_qiling_dynamic_analysis, job_id, analysis_result)
        
        # If it's PATH_B_LINUX_FS, add background task for filesystem scanning
        elif analysis_result["analysis"]["routing_decision"] == "PATH_B_LINUX_FS":
            background_tasks.add_task(process_filesystem_scan, job_id, analysis_result)
            
            # If bootloaders were found, create separate jobs for each
            if "bootloaders" in analysis_result["analysis"]:
                bootloaders = analysis_result["analysis"]["bootloaders"]
                if bootloaders:
                    logger.info(f"Creating separate jobs for {len(bootloaders)} bootloader(s)")
                    background_tasks.add_task(process_bootloader_analyses, job_id, bootloaders)

        logger.info(f"Analysis initiated successfully - JobID: {job_id}")
        
        # Wait for some processing to complete and collect comprehensive analysis data
        # This gives the frontend immediate access to job storage data and any completed analysis
        complete_analysis_data = wait_for_job_completion(job_id, max_wait_seconds=15)
        
        # Enhance the original response with comprehensive data
        enhanced_response = {
            **analysis_result,
            "comprehensive_data": complete_analysis_data,
            "data_collection": {
                "job_storage_available": complete_analysis_data["job_storage_data"] is not None,
                "qiling_results_available": complete_analysis_data["qiling_output"] is not None,
                "pipeline_results_available": complete_analysis_data["pipeline_output"] is not None,
                "child_jobs_count": len(complete_analysis_data.get("child_jobs", [])),
                "collection_timestamp": time.time()
            }
        }
        
        return enhanced_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def process_bare_metal_features(job_id: str, analysis_result: dict):
    """Background task to process PATH_A_BARE_METAL feature extraction"""
    try:
        logger.info(f"Starting background feature extraction - JobID: {job_id}")
        
        # Update job status
        job_manager.update_job_status(job_id, JobStatus.EXTRACTING_FEATURES)
        
        # Handle both analysis result formats (from /analyze endpoint vs manual trigger)
        if "analysis" in analysis_result:
            # Full analysis result from /analyze endpoint
            binary_info = analysis_result["analysis"].get("binary_info", {})
            workspace_path = analysis_result["analysis"]["workspace_path"]
        else:
            # Job analysis results from manual trigger
            binary_info = {}
            workspace_path = analysis_result.get("analysis_workspace")
        
        # For PATH_A_BARE_METAL, the binary file should be in the workspace
        if workspace_path:
            # Look for the binary file in workspace
            import glob
            workspace_files = glob.glob(os.path.join(workspace_path, "*"))
            binary_files = [f for f in workspace_files if os.path.isfile(f) and not f.endswith('.json')]
            
            if binary_files:
                binary_path = binary_files[0]  # Use first binary file found
                logger.info(f"Found binary file for extraction - JobID: {job_id}, Path: {binary_path}")
                
                # Run feature extraction
                feature_results = await feature_service.extract_features_from_binary(job_id, binary_path)
                
                # Update job with results
                job_manager.update_job_feature_results(job_id, feature_results)
                
                logger.info(f"Background feature extraction completed - JobID: {job_id}")
            else:
                logger.error(f"No binary files found in workspace - JobID: {job_id}")
                job_manager.mark_job_failed(job_id, "No binary files found for feature extraction")
        else:
            logger.error(f"No workspace path available - JobID: {job_id}")
            job_manager.mark_job_failed(job_id, "Workspace path not available")
            
    except Exception as e:
        logger.error(f"Background feature extraction failed - JobID: {job_id}, Error: {str(e)}", exc_info=True)
        job_manager.mark_job_failed(job_id, f"Feature extraction failed: {str(e)}")


async def process_qiling_dynamic_analysis(job_id: str, analysis_result: dict):
    """Background task to process Qiling dynamic crypto detection for ELF binaries"""
    try:
        logger.info(f"Starting background Qiling dynamic analysis - JobID: {job_id}")
        
        # Handle both analysis result formats (from /analyze endpoint vs manual trigger)
        if "analysis" in analysis_result:
            # Full analysis result from /analyze endpoint
            binary_info = analysis_result["analysis"].get("binary_info", {})
            workspace_path = analysis_result["analysis"]["workspace_path"]
        else:
            # Job analysis results from manual trigger
            binary_info = {}
            workspace_path = analysis_result.get("analysis_workspace")
        
        # For PATH_A_BARE_METAL, the binary file should be in the workspace
        if workspace_path:
            # Look for the binary file in workspace
            import glob
            workspace_files = glob.glob(os.path.join(workspace_path, "*"))
            binary_files = [f for f in workspace_files if os.path.isfile(f) and not f.endswith('.json')]
            
            if binary_files:
                binary_path = binary_files[0]  # Use first binary file found
                logger.info(f"Found binary for Qiling analysis - JobID: {job_id}, Path: {binary_path}")
                
                # Check if it's an object file that needs conversion
                is_object_file = binary_info.get("is_object_file", False) or converter_service.is_object_file(binary_path)
                
                if is_object_file:
                    logger.info(f"Object file detected - converting to ELF - JobID: {job_id}")
                    
                    # Convert .o to .elf
                    elf_path = converter_service.convert_object_to_elf(binary_path, workspace_path)
                    
                    if elf_path and os.path.exists(elf_path):
                        logger.info(f"Successfully converted .o to .elf - JobID: {job_id}, ELF: {elf_path}")
                        binary_path = elf_path  # Use converted ELF for analysis
                    else:
                        logger.error(f"Failed to convert .o to .elf - JobID: {job_id}")
                        # Continue with original file anyway - Qiling might handle it
                        logger.warning(f"Attempting Qiling analysis on original .o file - JobID: {job_id}")
                
                # Run Qiling dynamic analysis
                qiling_results = await qiling_service.analyze_elf_binary(job_id, binary_path)
                
                # Update job with Qiling results (store in a separate field)
                job_manager.update_job_qiling_results(job_id, qiling_results)
                
                logger.info(f"Background Qiling analysis completed - JobID: {job_id}")
                logger.info(f"Qiling verdict: {qiling_results.get('verdict', {}).get('crypto_detected', 'unknown')} "
                          f"(confidence: {qiling_results.get('verdict', {}).get('confidence', 'N/A')})")
                
                # TRIGGER LLM ANALYSIS if strace logs are available
                await process_llm_analysis(job_id, binary_path, qiling_results)
            else:
                logger.error(f"No binary files found in workspace - JobID: {job_id}")
        else:
            logger.error(f"No workspace path available - JobID: {job_id}")
            
    except Exception as e:
        logger.error(f"Background Qiling analysis failed - JobID: {job_id}, Error: {str(e)}", exc_info=True)
        # Don't fail the entire job - Qiling is supplementary analysis


async def process_llm_analysis(job_id: str, binary_path: str, qiling_results: dict):
    """Background task to process LLM analysis of strace logs"""
    try:
        logger.info(f"Starting LLM analysis of strace logs - JobID: {job_id}")
        
        # Find the strace log file for this binary
        # Strace logs are saved in qiling_analysis/tests/strace_logs/
        project_root = Path(__file__).parent.parent
        strace_log_dir = project_root / "qiling_analysis" / "tests" / "strace_logs"
        
        # Extract binary basename for matching strace log
        # The strace log naming convention: replace ALL dots with underscores, keep hyphens
        # Example: tmpg27iok30_libcrypto-lib-md5_sha1.o_openssl_arm64_O3.elf
        #       -> strace_tmpg27iok30_libcrypto-lib-md5_sha1_o_openssl_arm64_O3_elf_TIMESTAMP.log
        binary_basename = os.path.basename(binary_path)
        
        # Replace dots with underscores (matches verify_crypto.py line 112)
        # This preserves hyphens but replaces .elf and .o extensions
        binary_basename_normalized = binary_basename.replace('.', '_')
        
        # Look for strace log matching this binary (trying multiple patterns)
        patterns_to_try = [
            f"strace_{binary_basename_normalized}*.log",  # Normalized (dots -> underscores)
            f"strace_{binary_basename}*.log",              # Original basename (fallback)
            f"strace_*{binary_basename.split('_')[0]}*.log" if '_' in binary_basename else None  # Temp prefix
        ]
        patterns_to_try = [p for p in patterns_to_try if p]  # Remove None values
        
        matching_logs = []
        for pattern in patterns_to_try:
            matching_logs = list(strace_log_dir.glob(pattern))
            if matching_logs:
                logger.info(f"Found strace logs with pattern: {pattern}")
                break
        
        if not matching_logs:
            logger.warning(f"No strace log found for binary - JobID: {job_id}")
            logger.warning(f"Tried patterns: {patterns_to_try}")
            logger.warning(f"Binary path: {binary_path}")
            logger.warning(f"Available strace logs:")
            for log_file in strace_log_dir.glob("strace_*.log"):
                logger.warning(f"  - {log_file.name}")
            logger.info(f"LLM analysis skipped - no strace log available")
            return
        
        # Use the most recent strace log (sorted by name which includes timestamp)
        strace_log_path = str(sorted(matching_logs)[-1])
        logger.info(f"Found and using strace log: {strace_log_path}")
        
        # Run LLM analysis
        llm_results = await llm_service.analyze_crypto_telemetry(
            job_id=job_id,
            strace_log_path=strace_log_path,
            qiling_results=qiling_results
        )
        
        # Update job with LLM results
        job_manager.update_job_llm_results(job_id, llm_results)
        
        logger.info(f"LLM analysis completed - JobID: {job_id}")
        if llm_results.get("status") == "completed":
            llm_classification = llm_results.get("llm_classification", {})
            logger.info(f"LLM Classification: {llm_classification.get('crypto_classification', 'UNKNOWN')}, "
                       f"Algorithm: {llm_classification.get('crypto_algorithm', 'unknown')}, "
                       f"Confidence: {llm_classification.get('confidence', 0.0)}")
        
    except Exception as e:
        logger.error(f"LLM analysis failed - JobID: {job_id}, Error: {str(e)}", exc_info=True)
        # Don't fail the entire job - LLM is supplementary analysis


async def process_filesystem_scan(job_id: str, analysis_result: dict):
    """Background task to process PATH_B_LINUX_FS filesystem scanning"""
    try:
        logger.info(f"Starting background filesystem scan - JobID: {job_id}")
        
        # Update job status
        job_manager.update_job_status(job_id, JobStatus.EXTRACTING_FEATURES)
        
        # Get extracted filesystem path from analysis results
        extracted_path = None
        if "analysis" in analysis_result:
            if "filesystem_info" in analysis_result["analysis"]:
                extracted_path = analysis_result["analysis"]["filesystem_info"].get("extracted_path")
            elif "workspace_path" in analysis_result["analysis"]:
                # Fallback to workspace path
                workspace_path = analysis_result["analysis"]["workspace_path"]
                # Check if there's an extracted directory in the workspace
                if workspace_path and os.path.exists(workspace_path):
                    for item in os.listdir(workspace_path):
                        item_path = os.path.join(workspace_path, item)
                        if os.path.isdir(item_path):
                            extracted_path = item_path
                            break
        
        if extracted_path and os.path.exists(extracted_path):
            logger.info(f"Found extracted filesystem - JobID: {job_id}, Path: {extracted_path}")
            
            # Run filesystem scan
            scan_results = await filesystem_service.scan_filesystem(job_id, extracted_path)
            
            # Update job with results (using feature_extraction_results for now)
            job_manager.update_job_feature_results(job_id, scan_results)
            
            # If crypto libraries were found, process them
            if "crypto_libraries" in scan_results:
                crypto_libs = scan_results["crypto_libraries"]
                if crypto_libs.get("so_files") or crypto_libs.get("a_files") or crypto_libs.get("o_files"):
                    total_libs = (len(crypto_libs.get("so_files", [])) + 
                                 len(crypto_libs.get("a_files", [])) +
                                 len(crypto_libs.get("o_files", [])))
                    logger.info(f"Processing {total_libs} crypto libraries found in filesystem scan")
                    await process_crypto_libraries(job_id, crypto_libs)
            
            logger.info(f"Background filesystem scan completed - JobID: {job_id}")
        else:
            logger.error(f"Extracted filesystem path not found - JobID: {job_id}")
            job_manager.mark_job_failed(job_id, "Extracted filesystem path not available")
            
    except Exception as e:
        logger.error(f"Background filesystem scan failed - JobID: {job_id}, Error: {str(e)}", exc_info=True)
        job_manager.mark_job_failed(job_id, f"Filesystem scan failed: {str(e)}")


async def process_bootloader_analyses(parent_job_id: str, bootloaders: list):
    """Background task to create separate jobs for bootloader secure boot analysis"""
    try:
        logger.info(f"Starting bootloader analysis jobs - ParentJob: {parent_job_id}, Count: {len(bootloaders)}")
        
        import uuid
        
        for bootloader_info in bootloaders:
            # Create a new job for each bootloader analysis
            bootloader_job_id = str(uuid.uuid4())
            bootloader_name = bootloader_info.get("file", "unknown")
            
            logger.info(f"Creating bootloader analysis job - JobID: {bootloader_job_id}, Bootloader: {bootloader_name}")
            
            # Create job with bootloader- prefix for easy identification
            job = job_manager.create_job(
                bootloader_job_id, 
                f"bootloader-{bootloader_name}",
                bootloader_info.get("size", 0)
            )
            
            # Mark as bootloader analysis type
            job_manager.update_job_status(
                bootloader_job_id,
                JobStatus.EXTRACTING_FEATURES,
                routing_decision="BOOTLOADER_ANALYSIS",
                routing_reason=f"Secure boot analysis for {bootloader_info.get('type', 'unknown')} bootloader",
                workspace_path=f"parent:{parent_job_id}"
            )
            
            # Run secure boot analysis
            try:
                analysis_results = await secureboot_service.analyze_bootloader(
                    parent_job_id,
                    bootloader_info.get("path"),
                    bootloader_info
                )
                
                # Update job with results
                job_manager.update_job_feature_results(bootloader_job_id, analysis_results)
                
                logger.info(f"Bootloader analysis completed - JobID: {bootloader_job_id}")
                
            except Exception as e:
                logger.error(f"Bootloader analysis failed - JobID: {bootloader_job_id}, Error: {str(e)}")
                job_manager.mark_job_failed(bootloader_job_id, f"Bootloader analysis failed: {str(e)}")
        
        logger.info(f"All bootloader analysis jobs created - ParentJob: {parent_job_id}")
        
    except Exception as e:
        logger.error(f"Failed to create bootloader analysis jobs - ParentJob: {parent_job_id}, Error: {str(e)}", exc_info=True)


async def process_crypto_library_qiling_analysis(job_id: str, binary_path: str, is_object_file: bool):
    """Background task to run Qiling dynamic analysis on crypto library binaries (.o and .so files)"""
    try:
        logger.info(f"Starting Qiling analysis for crypto library - JobID: {job_id}, Path: {binary_path}, IsObject: {is_object_file}")
        
        if not os.path.exists(binary_path):
            logger.error(f"Binary file not found: {binary_path}")
            return
        
        # Check if the file needs conversion (handles both .o and relocatable files)
        analysis_path = binary_path
        needs_conv = is_object_file or converter_service.needs_conversion(binary_path)
        
        if needs_conv:
            logger.info(f"File needs conversion to ELF - JobID: {job_id}")
            
            # Get the directory to save the converted ELF
            output_dir = os.path.dirname(binary_path)
            
            # Convert to .elf
            elf_path = converter_service.convert_object_to_elf(binary_path, output_dir)
            
            if elf_path and os.path.exists(elf_path):
                logger.info(f"Successfully converted to .elf - JobID: {job_id}, ELF: {elf_path}")
                analysis_path = elf_path
            else:
                logger.error(f"Failed to convert to .elf - JobID: {job_id}")
                logger.warning(f"Attempting Qiling analysis on original file - JobID: {job_id}")
        
        # Check if the file is ELF (either native .so or converted)
        if not qiling_service._is_elf_binary(analysis_path):
            logger.warning(f"File is not ELF, skipping Qiling analysis - JobID: {job_id}")
            return
        
        # Run Qiling dynamic analysis
        qiling_results = await qiling_service.analyze_elf_binary(job_id, analysis_path)
        
        # Update job with Qiling results
        job_manager.update_job_qiling_results(job_id, qiling_results)
        
        logger.info(f"Qiling analysis completed for crypto library - JobID: {job_id}")
        logger.info(f"Qiling verdict: {qiling_results.get('verdict', {}).get('crypto_detected', 'unknown')} "
                  f"(confidence: {qiling_results.get('verdict', {}).get('confidence', 'N/A')})")
        
    except Exception as e:
        logger.error(f"Qiling analysis failed for crypto library - JobID: {job_id}, Error: {str(e)}", exc_info=True)
        # Don't fail the job - Qiling is supplementary


async def process_crypto_libraries(parent_job_id: str, crypto_libs: dict):
    """Background task to process crypto libraries (.so and .a files)"""
    try:
        logger.info(f"Starting crypto library processing - ParentJob: {parent_job_id}")
        
        # Process libraries using CryptoLibraryService
        results = cryptolib_service.process_crypto_libraries(crypto_libs, parent_job_id)
        
        logger.info(f"Crypto library processing complete - ParentJob: {parent_job_id}, Summary: {results.get('summary', {})}")
        
        # Get all files ready for PATH_A pipeline
        pipeline_files = cryptolib_service.get_objects_for_pipeline(results)
        
        if pipeline_files:
            logger.info(f"Creating {len(pipeline_files)} analysis jobs for crypto library objects")
            
            import uuid
            
            # Create separate jobs for object files and shared libraries
            for file_info in pipeline_files:
                if file_info.get("analysis_type") == "object_file_analysis" or file_info.get("type") == "object_file":
                    # This is a .o file (either from .a archive or standalone)
                    object_job_id = str(uuid.uuid4())
                    
                    job = job_manager.create_job(
                        object_job_id,
                        file_info["file"],
                        file_info["size"]
                    )
                    
                    # Determine source
                    source = file_info.get('parent_archive', 'filesystem')
                    reason = f"Object file from {source}"
                    
                    job_manager.update_job_status(
                        object_job_id,
                        JobStatus.EXTRACTING_FEATURES,
                        routing_decision="PATH_A_BARE_METAL",
                        routing_reason=reason,
                        workspace_path=file_info["path"]
                    )
                    
                    # Run feature extraction on the .o file
                    try:
                        features = await feature_service.extract_features_from_binary(object_job_id, file_info["path"])
                        job_manager.update_job_feature_results(object_job_id, features)
                        
                        logger.info(f"Object file analysis completed - JobID: {object_job_id}, File: {file_info['file']}")
                        
                        # Also run Qiling dynamic analysis on the .o file (after conversion)
                        logger.info(f"Starting Qiling analysis for .o file - JobID: {object_job_id}")
                        await process_crypto_library_qiling_analysis(object_job_id, file_info["path"], is_object_file=True)
                        
                    except Exception as e:
                        logger.error(f"Object file analysis failed - JobID: {object_job_id}, Error: {str(e)}")
                        job_manager.mark_job_failed(object_job_id, f"Analysis failed: {str(e)}")
                
                elif file_info.get("type") == "shared_object":
                    # This is a .so file - analyze directly
                    so_job_id = str(uuid.uuid4())
                    
                    job = job_manager.create_job(
                        so_job_id,
                        file_info["file"],
                        file_info["size"]
                    )
                    
                    job_manager.update_job_status(
                        so_job_id,
                        JobStatus.EXTRACTING_FEATURES,
                        routing_decision="PATH_A_BARE_METAL",
                        routing_reason="Shared object library analysis",
                        workspace_path=file_info["path"]
                    )
                    
                    # Run feature extraction on the .so file
                    try:
                        features = await feature_service.extract_features_from_binary(so_job_id, file_info["path"])
                        job_manager.update_job_feature_results(so_job_id, features)
                        
                        logger.info(f"Shared object analysis completed - JobID: {so_job_id}, File: {file_info['file']}")
                        
                        # Also run Qiling dynamic analysis on the .so file
                        logger.info(f"Starting Qiling analysis for .so file - JobID: {so_job_id}")
                        await process_crypto_library_qiling_analysis(so_job_id, file_info["path"], is_object_file=False)
                        
                    except Exception as e:
                        logger.error(f"Shared object analysis failed - JobID: {so_job_id}, Error: {str(e)}")
                        job_manager.mark_job_failed(so_job_id, f"Analysis failed: {str(e)}")
        
        logger.info(f"All crypto library jobs completed - ParentJob: {parent_job_id}")
        
    except Exception as e:
        logger.error(f"Crypto library processing failed - ParentJob: {parent_job_id}, Error: {str(e)}", exc_info=True)


# ==========================================================
# JOB MANAGEMENT ENDPOINTS
# ==========================================================

@app.get("/job/{job_id}/complete-analysis")
async def get_complete_analysis_data(job_id: str):
    """Get comprehensive analysis data including all generated files for a job"""
    try:
        logger.info(f"Fetching complete analysis data for job: {job_id}")
        
        # Collect all analysis data
        complete_data = collect_job_analysis_data(job_id)
        
        if not complete_data["job_storage_data"]:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Add current job status
        job = job_manager.get_job(job_id)
        if job:
            complete_data["current_status"] = {
                "status": job.status.value,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "error_message": job.error_message
            }
        
        # Add summary statistics
        complete_data["summary"] = {
            "total_analysis_files": (
                (1 if complete_data["job_storage_data"] else 0) +
                len(complete_data.get("qiling_output") or []) +
                len(complete_data.get("pipeline_output") or []) +
                len(complete_data.get("child_jobs") or [])
            ),
            "has_feature_extraction": bool(
                complete_data["job_storage_data"] and 
                complete_data["job_storage_data"].get("feature_extraction_results")
            ),
            "has_ml_classification": bool(
                complete_data["job_storage_data"] and 
                complete_data["job_storage_data"].get("feature_extraction_results") and
                complete_data["job_storage_data"]["feature_extraction_results"].get("ml_classification")
            ),
            "has_qiling_analysis": bool(complete_data.get("qiling_output")),
            "analysis_complete": job and job.status in [JobStatus.COMPLETE, JobStatus.FEATURES_COMPLETE] if job else False
        }
        
        logger.info(f"Complete analysis data collected for job {job_id}: {complete_data['summary']}")
        return complete_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get complete analysis data for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get complete analysis data: {str(e)}")


@app.get("/job/{job_id}")
async def get_job_details(job_id: str):
    """Get detailed information about a specific job"""
    try:
        job_summary = job_manager.get_job_summary(job_id)
        if not job_summary:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get full job details
        job = job_manager.get_job(job_id)
        
        response = {
            **job_summary,
            "analysis": job.analysis_results if job.analysis_results else {},
            "features": job.feature_extraction_results if job.feature_extraction_results else {},
            "classification": job.classification_results if job.classification_results else {}
        }
        
        logger.debug(f"Retrieved job details - JobID: {job_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving job details")


@app.get("/job/{job_id}/features")
async def get_job_features(job_id: str):
    """Get extracted features for a job"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.feature_extraction_results:
            raise HTTPException(status_code=404, detail="Features not yet extracted")
        
        return {
            "jobId": job_id,
            "features": job.feature_extraction_results,
            "status": "features_available"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving features for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving features")


@app.get("/job/{job_id}/cfg")
async def get_job_cfg(job_id: str):
    """Get control flow graph visualization and analysis data for a job"""
    try:
        # Get job data from job storage
        job_storage_dir = Path(__file__).parent / "job_storage"
        job_file = job_storage_dir / f"{job_id}.json"
        
        if not job_file.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Read job data
        with open(job_file, 'r') as f:
            job_data = json.load(f)
        
        # Extract control flow analysis data
        control_flow_data = None
        if "analysis_results" in job_data:
            if "hard_target_info" in job_data["analysis_results"]:
                control_flow_data = job_data["analysis_results"]["hard_target_info"].get("control_flow_analysis")
            elif "control_flow_analysis" in job_data["analysis_results"]:
                control_flow_data = job_data["analysis_results"]["control_flow_analysis"]
        
        if not control_flow_data:
            raise HTTPException(status_code=404, detail="Control flow analysis not available for this job")
        
        # Get the CFG directory and latest PNG
        cfg_directory = control_flow_data.get("cfg_directory")
        latest_cfg_png = control_flow_data.get("latest_cfg_png")
        
        # Handle path mismatch (file generated on different machine)
        if not latest_cfg_png or not os.path.exists(latest_cfg_png):
            # Try to find the PNG in the current job's CFG directory
            cfg_dir = job_storage_dir / f"{job_id}_cfg"
            if cfg_dir.exists():
                png_files = list(cfg_dir.glob("cfg_*.png"))
                dot_files = list(cfg_dir.glob("cfg_*.dot"))
                
                if png_files:
                    # Use the largest PNG (likely the most detailed)
                    latest_cfg_png = str(max(png_files, key=lambda f: f.stat().st_size))
                    cfg_directory = str(cfg_dir)
                    logger.info(f"Found CFG PNG in local storage: {latest_cfg_png}")
                elif dot_files:
                    # DOT files exist but no PNGs - graphviz conversion failed
                    raise HTTPException(
                        status_code=404, 
                        detail=f"CFG generation incomplete: {len(dot_files)} .dot files found but no PNG images. GraphViz may not be installed or conversion failed."
                    )
                else:
                    # Directory exists but is empty
                    raise HTTPException(
                        status_code=404, 
                        detail="CFG directory exists but contains no visualization files. Analysis may have failed."
                    )
            else:
                # Check the status to provide better error message
                status = control_flow_data.get("status", "unknown")
                exit_code = control_flow_data.get("exit_code", 0)
                if exit_code == 127:
                    raise HTTPException(
                        status_code=404, 
                        detail="CFG analysis failed: radare2 not found (exit code 127). Please install radare2 to generate control flow graphs."
                    )
                elif status == "completed_with_warnings" or exit_code != 0:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"CFG analysis incomplete (status: {status}, exit code: {exit_code}). No visualization files were generated."
                    )
                else:
                    raise HTTPException(status_code=404, detail="CFG directory not found")
        
        return {
            "jobId": job_id,
            "status": control_flow_data.get("status"),
            "analysis_output": control_flow_data.get("analysis_output"),
            "architecture": control_flow_data.get("architecture"),
            "cfg_directory": cfg_directory,
            "latest_cfg_png": latest_cfg_png,
            "generated_files": control_flow_data.get("generated_files"),
            "exit_code": control_flow_data.get("exit_code")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving CFG for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving CFG data")


@app.get("/job/{job_id}/cfg/image")
async def get_job_cfg_image(job_id: str):
    """Serve the CFG PNG image file for a job"""
    try:
        # Get job data from job storage
        job_storage_dir = Path(__file__).parent / "job_storage"
        job_file = job_storage_dir / f"{job_id}.json"
        
        if not job_file.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Read job data
        with open(job_file, 'r') as f:
            job_data = json.load(f)
        
        # Extract control flow analysis data
        control_flow_data = None
        if "analysis_results" in job_data:
            if "hard_target_info" in job_data["analysis_results"]:
                control_flow_data = job_data["analysis_results"]["hard_target_info"].get("control_flow_analysis")
            elif "control_flow_analysis" in job_data["analysis_results"]:
                control_flow_data = job_data["analysis_results"]["control_flow_analysis"]
        
        if not control_flow_data:
            raise HTTPException(status_code=404, detail="Control flow analysis not available for this job")
        
        latest_cfg_png = control_flow_data.get("latest_cfg_png")
        
        # Handle path mismatch (file generated on different machine)
        if not latest_cfg_png or not os.path.exists(latest_cfg_png):
            # Try to find the PNG in the current job's CFG directory
            cfg_dir = job_storage_dir / f"{job_id}_cfg"
            if cfg_dir.exists():
                png_files = list(cfg_dir.glob("cfg_*.png"))
                dot_files = list(cfg_dir.glob("cfg_*.dot"))
                
                if png_files:
                    # Use the largest PNG (likely the most detailed)
                    latest_cfg_png = str(max(png_files, key=lambda f: f.stat().st_size))
                    logger.info(f"Found CFG PNG in local storage: {latest_cfg_png}")
                elif dot_files:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"CFG PNG not available: {len(dot_files)} .dot files found but GraphViz conversion failed"
                    )
                else:
                    raise HTTPException(
                        status_code=404, 
                        detail="CFG directory is empty - analysis may have failed"
                    )
            else:
                status = control_flow_data.get("status", "unknown")
                exit_code = control_flow_data.get("exit_code", 0)
                if exit_code == 127:
                    raise HTTPException(
                        status_code=404, 
                        detail="radare2 not found (exit code 127)"
                    )
                else:
                    raise HTTPException(status_code=404, detail="CFG directory not found")
        
        return FileResponse(
            latest_cfg_png,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename=cfg_{job_id}.png"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving CFG image for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error serving CFG image")


@app.post("/job/{job_id}/extract-features")
async def trigger_feature_extraction(job_id: str, background_tasks: BackgroundTasks):
    """Manually trigger feature extraction for a job"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.routing_decision != "PATH_A_BARE_METAL":
            raise HTTPException(status_code=400, detail="Feature extraction only available for PATH_A_BARE_METAL")
        
        if job.status == JobStatus.EXTRACTING_FEATURES:
            return {"message": "Feature extraction already in progress"}
        
        # Add background task
        background_tasks.add_task(process_bare_metal_features, job_id, job.analysis_results)
        
        return {
            "message": "Feature extraction started",
            "jobId": job_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering feature extraction for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting feature extraction")


@app.post("/job/{job_id}/fs-scan")
async def trigger_filesystem_scan(job_id: str, background_tasks: BackgroundTasks):
    """Manually trigger filesystem scan for a PATH_B_LINUX_FS job"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.routing_decision != "PATH_B_LINUX_FS":
            raise HTTPException(status_code=400, detail="Filesystem scan only available for PATH_B_LINUX_FS")
        
        if job.status == JobStatus.EXTRACTING_FEATURES:
            return {"message": "Filesystem scan already in progress"}
        
        # Add background task
        background_tasks.add_task(process_filesystem_scan, job_id, job.analysis_results)
        
        return {
            "message": "Filesystem scan started",
            "jobId": job_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering filesystem scan for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting filesystem scan")


@app.get("/jobs")
async def list_jobs(limit: int = 50):
    """List all jobs"""
    try:
        jobs = job_manager.get_all_jobs(limit=limit)
        job_summaries = [job_manager.get_job_summary(job.job_id) for job in jobs]
        
        return {
            "jobs": job_summaries,
            "total": len(job_summaries)
        }
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving jobs")


@app.get("/jobs/comprehensive")
async def list_jobs_comprehensive(limit: int = 20, include_child_jobs: bool = False):
    """List all jobs with comprehensive analysis data for frontend display"""
    try:
        logger.info(f"Fetching comprehensive job list (limit: {limit}, include_child_jobs: {include_child_jobs})")
        
        jobs = job_manager.get_all_jobs(limit=limit)
        comprehensive_jobs = []
        
        for job in jobs:
            # Skip child jobs unless explicitly requested
            if not include_child_jobs:
                # Check if this is a child job by looking for parent_job_id
                if (job.analysis_results and 
                    isinstance(job.analysis_results, dict) and 
                    job.analysis_results.get("parent_job_id")):
                    continue
            
            # Get comprehensive data for this job
            job_data = collect_job_analysis_data(job.job_id)
            
            # Add job manager data
            job_data["job_manager_data"] = {
                "status": job.status.value,
                "filename": job.filename,
                "file_size": job.file_size,
                "routing_decision": job.routing_decision,
                "routing_reason": job.routing_reason,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "error_message": job.error_message
            }
            
            # Add analysis summary
            job_data["analysis_summary"] = {
                "has_features": bool(job.feature_extraction_results),
                "has_qiling": bool(job.qiling_dynamic_results),
                "has_classification": bool(job.classification_results),
                "child_jobs_count": len(job_data.get("child_jobs", [])),
                "is_complete": job.status in [JobStatus.COMPLETE, JobStatus.FEATURES_COMPLETE]
            }
            
            comprehensive_jobs.append(job_data)
        
        return {
            "jobs": comprehensive_jobs,
            "total": len(comprehensive_jobs),
            "metadata": {
                "limit": limit,
                "include_child_jobs": include_child_jobs,
                "collection_timestamp": time.time()
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing comprehensive jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving comprehensive jobs data")


@app.get("/job/{job_id}/strace-logs")
async def get_strace_logs(job_id: str):
    """Get strace logs for a job's binary analysis"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get binary path from qiling results
        qiling_results = job.qiling_dynamic_results
        if not qiling_results:
            raise HTTPException(status_code=404, detail="No Qiling analysis results available")
        
        binary_path = qiling_results.get("binary_path", "")
        binary_name = qiling_results.get("binary_name", "")
        
        if not binary_name:
            raise HTTPException(status_code=404, detail="Binary name not found in analysis results")
        
        # Find strace logs
        project_root = Path(__file__).parent.parent
        strace_log_dir = project_root / "qiling_analysis" / "tests" / "strace_logs"
        
        if not strace_log_dir.exists():
            raise HTTPException(status_code=404, detail="Strace logs directory not found")
        
        # Extract binary basename for matching strace log
        # The strace log naming convention: replace ALL dots with underscores, keep hyphens
        # Example: tmpg27iok30_libcrypto-lib-md5_sha1.o_openssl_arm64_O3.elf
        #       -> strace_tmpg27iok30_libcrypto-lib-md5_sha1_o_openssl_arm64_O3_elf_TIMESTAMP.log
        
        binary_basename = binary_name
        
        # Replace dots with underscores (matches verify_crypto.py line 112)
        # This preserves hyphens but replaces .elf and .o extensions
        binary_basename_normalized = binary_basename.replace('.', '_')
        
        # Look for strace log matching this binary (trying multiple patterns)
        patterns_to_try = [
            f"strace_{binary_basename_normalized}*.log",  # Normalized (dots -> underscores)
            f"strace_{binary_basename}*.log",              # Original basename (fallback)
            f"strace_*{binary_basename.split('_')[0]}*.log" if '_' in binary_basename else None  # Temp prefix
        ]
        patterns_to_try = [p for p in patterns_to_try if p]  # Remove None values
        
        matching_logs = []
        for pattern in patterns_to_try:
            matching_logs = list(strace_log_dir.glob(pattern))
            if matching_logs:
                logger.info(f"Found strace logs with pattern: {pattern}")
                break
        
        if not matching_logs:
            logger.warning(f"No strace logs found for binary: {binary_name}")
            logger.warning(f"Tried patterns: {patterns_to_try}")
            logger.warning(f"Available strace logs in directory:")
            for log_file in strace_log_dir.glob("strace_*.log"):
                logger.warning(f"  - {log_file.name}")
            raise HTTPException(status_code=404, detail=f"No strace logs found for binary: {binary_name}")
        
        # Use the most recent strace log
        strace_log_path = sorted(matching_logs)[-1]
        logger.info(f"Using strace log: {strace_log_path.name}")
        
        # Read the log file
        try:
            with open(strace_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                strace_content = f.read()
        except Exception as e:
            logger.error(f"Error reading strace log {strace_log_path}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error reading strace log file")
        
        # Get file stats
        file_stats = strace_log_path.stat()
        
        return {
            "job_id": job_id,
            "binary_name": binary_name,
            "strace_log_path": str(strace_log_path),
            "strace_log_name": strace_log_path.name,
            "file_size": file_stats.st_size,
            "file_modified": file_stats.st_mtime,
            "content": strace_content,
            "lines": len(strace_content.split('\n')),
            "available_logs": [str(log.name) for log in matching_logs]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving strace logs for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving strace logs")


@app.get("/job/{job_id}/analysis-logs")
async def get_analysis_logs(job_id: str):
    """Get analysis logs for a job's binary analysis"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get binary path from qiling results
        qiling_results = job.qiling_dynamic_results
        if not qiling_results:
            raise HTTPException(status_code=404, detail="No Qiling analysis results available")
        
        binary_name = qiling_results.get("binary_name", "")
        
        if not binary_name:
            raise HTTPException(status_code=404, detail="Binary name not found in analysis results")
        
        # Find analysis logs
        project_root = Path(__file__).parent.parent
        analysis_log_dir = project_root / "qiling_analysis" / "tests" / "analysis_logs"
        
        if not analysis_log_dir.exists():
            raise HTTPException(status_code=404, detail="Analysis logs directory not found")
        
        # Extract binary basename for matching analysis log
        # The analysis log naming convention: analysis_{binary_basename}_TIMESTAMP.log
        binary_basename = binary_name
        binary_basename_normalized = binary_basename.replace('.', '_')
        
        # Look for analysis log matching this binary
        patterns_to_try = [
            f"analysis_{binary_basename_normalized}*.log",  # Normalized (dots -> underscores)
            f"analysis_{binary_basename}*.log",              # Original basename (fallback)
            f"analysis_*{binary_basename.split('_')[0]}*.log" if '_' in binary_basename else None  # Temp prefix
        ]
        patterns_to_try = [p for p in patterns_to_try if p]  # Remove None values
        
        matching_logs = []
        for pattern in patterns_to_try:
            matching_logs = list(analysis_log_dir.glob(pattern))
            if matching_logs:
                logger.info(f"Found analysis logs with pattern: {pattern}")
                break
        
        if not matching_logs:
            logger.warning(f"No analysis logs found for binary: {binary_name}")
            logger.warning(f"Tried patterns: {patterns_to_try}")
            logger.warning(f"Available analysis logs in directory:")
            for log_file in analysis_log_dir.glob("analysis_*.log"):
                logger.warning(f"  - {log_file.name}")
            raise HTTPException(status_code=404, detail=f"No analysis logs found for binary: {binary_name}")
        
        # Use the most recent analysis log
        analysis_log_path = sorted(matching_logs)[-1]
        logger.info(f"Using analysis log: {analysis_log_path.name}")
        
        # Read the log file
        try:
            with open(analysis_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                analysis_content = f.read()
        except Exception as e:
            logger.error(f"Error reading analysis log {analysis_log_path}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error reading analysis log file")
        
        # Get file stats
        file_stats = analysis_log_path.stat()
        
        return {
            "job_id": job_id,
            "binary_name": binary_name,
            "analysis_log_path": str(analysis_log_path),
            "analysis_log_name": analysis_log_path.name,
            "file_size": file_stats.st_size,
            "file_modified": file_stats.st_mtime,
            "content": analysis_content,
            "lines": len(analysis_content.split('\n')),
            "available_logs": [str(log.name) for log in matching_logs]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis logs for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving analysis logs")


# ==========================================================
# LEGACY ENDPOINTS (For backward compatibility)
# ==========================================================

@app.get("/jobs/{job_id}")
async def get_legacy_job(job_id: str):
    """Legacy endpoint for backward compatibility with old frontend"""
    try:
        job = await db.job.find_unique(
            where={"id": job_id},
            include={"threats": True}
        )

        if not job:
            return {"error": "Job not found"}

        return job
    except Exception as e:
        logger.error(f"Error in legacy job endpoint: {str(e)}")
        return {"error": "Database error"}


@app.get("/jobs/{job_id}/report")
async def download_report(job_id: str):
    """Generate analysis report for a job"""
    try:
        job = await db.job.find_unique(
            where={"id": job_id},
            include={"threats": True}
        )

        if not job:
            return {"error": "Job not found"}

        # Return report data (could be enhanced to generate PDF/formatted report)
        return {
            "job": job,
            "report_generated": True,
            "format": "json"
        }
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return {"error": "Report generation failed"}
