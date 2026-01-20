"""
Ingest Service for Vestigo Backend
Handles file ingestion, routing decisions, and initial analysis setup
"""

import os
import sys
import tempfile
import shutil
from typing import Dict, Any, Optional
import uuid
from pathlib import Path

# Add scripts directory to path to import ingest module
# Add scripts directory to path to import ingest module
# Use resolve() to ensure we get the absolute path, avoiding issues with relative paths in containers
file_path = Path(__file__).resolve()
parent_dir = file_path.parent.parent.parent
scripts_dir = parent_dir / "scripts"

# Add to sys.path if not present
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))
    # We can't use logger here easily as it might not be initialized or circular import
    print(f"Added scripts directory to sys.path: {scripts_dir}")

if not scripts_dir.exists():
    print(f"WARNING: Scripts directory not found at {scripts_dir}")

from ingest import IngestionModule
from config.logging_config import logger
from services.crypto_string_detector import crypto_string_detector
from services.control_flow_analyzer import control_flow_analyzer

class IngestService:
    """Service for handling file ingestion and routing decisions"""
    
    def __init__(self, analysis_workspace_base: str = "./analysis_workspace"):
        self.analysis_workspace_base = os.path.abspath(analysis_workspace_base)
        self.ingest_module = IngestionModule(output_base_dir=self.analysis_workspace_base)
        logger.info(f"IngestService initialized with workspace: {self.analysis_workspace_base}")
    
    async def process_uploaded_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process an uploaded file through the ingest pipeline
        
        Args:
            file_content (bytes): Raw file content
            filename (str): Original filename

        Returns:
            Dict containing analysis results and routing information
        """
        job_id = str(uuid.uuid4())
        logger.info(f"Processing file upload - JobID: {job_id}, Filename: {filename}")
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            logger.debug(f"Created temporary file: {temp_file_path}")
            
            # Process file with ingest module
            logger.info(f"Starting ingest analysis for JobID: {job_id}")
            ingest_result = self.ingest_module.process(temp_file_path)
            
            logger.info(f"Ingest analysis completed - JobID: {job_id}, Route: {ingest_result['routing']['decision']}")
            
            # Prepare structured response
            response = self._prepare_response(job_id, filename, len(file_content), ingest_result)
            
            logger.debug(f"Response prepared for JobID: {job_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing file upload - JobID: {job_id}, Error: {str(e)}", exc_info=True)
            raise
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
    
    def _prepare_response(self, job_id: str, filename: str, file_size: int, ingest_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare structured response for frontend consumption"""
        
        routing_decision = ingest_result["routing"]["decision"]
        logger.debug(f"Preparing response for JobID: {job_id}, Route: {routing_decision}")
        
        response = {
            "jobId": job_id,
            "fileName": filename,
            "fileSize": self._format_size(file_size),
            "fileSizeBytes": file_size,
            "status": "analyzed",
            "analysis": {
                "routing_decision": routing_decision,
                "routing_reason": ingest_result["routing"]["reason"],
                "file_type": ingest_result["file_info"]["detected_type"],
                "extraction_success": ingest_result["extraction"]["was_extracted"],
                "next_steps": ingest_result["next_steps"],
                "workspace_path": ingest_result.get("analysis_workspace")
            },
            "processing": {
                "ingest_complete": True,
                "ready_for_next_step": True
            }
        }
        
        # Add bootloader information if found
        if "bootloaders_found" in ingest_result["extraction"]:
            response["analysis"]["bootloaders"] = ingest_result["extraction"]["bootloaders_found"]
        
        # Add routing-specific information
        if routing_decision == "PATH_A_BARE_METAL":
            self._add_bare_metal_info(response, ingest_result)
        elif routing_decision == "PATH_B_LINUX_FS":
            self._add_linux_fs_info(response, ingest_result)
        elif routing_decision == "PATH_C_HARD_TARGET":
            self._add_hard_target_info(response, ingest_result)
        
        logger.debug(f"Response structure complete for JobID: {job_id}")
        return response
    
    def _add_bare_metal_info(self, response: Dict[str, Any], ingest_result: Dict[str, Any]):
        """Add PATH_A_BARE_METAL specific information"""
        binary_analysis = ingest_result.get("binary_analysis", {})
        
        # For PATH_A_BARE_METAL, the binary file is in the workspace directory
        # Find the binary file in the workspace
        workspace_path = ingest_result.get("analysis_workspace")
        file_path = None
        is_elf = False
        is_object_file = False
        
        if workspace_path and os.path.exists(workspace_path):
            # Look for binary files in workspace (not .json files)
            import glob
            workspace_files = glob.glob(os.path.join(workspace_path, "*"))
            binary_files = [f for f in workspace_files if os.path.isfile(f) and not f.endswith('.json')]
            
            if binary_files:
                file_path = binary_files[0]  # Use first binary file found
                is_elf = self._is_elf_file(file_path)
                is_object_file = self._is_object_file(file_path)
                logger.info(f"Found binary in workspace: {file_path}, is_elf: {is_elf}, is_object: {is_object_file}")
            else:
                logger.warning(f"No binary files found in workspace: {workspace_path}")
        else:
            logger.warning(f"Workspace path not available or doesn't exist: {workspace_path}")
        
        response["analysis"]["binary_info"] = {
            "is_binary": True,
            "is_elf": is_elf,
            "is_object_file": is_object_file,
            "needs_conversion": is_object_file and not is_elf,  # .o files need conversion to .elf
            "analysis_ready": binary_analysis.get("processed", False),
            "features_extracted": binary_analysis.get("features_extracted", False),
            "classification_complete": binary_analysis.get("classification_complete", False),
            "analysis_type": binary_analysis.get("analysis_type", "unknown"),
            "file_path": binary_analysis.get("file_path"),
            "qiling_analysis_available": is_elf or is_object_file  # Both ELF and .o can be analyzed (after conversion)
        }
        
        next_actions = [
            {
                "action": "extract_features",
                "endpoint": f"/job/{response['jobId']}/extract-features",
                "description": "Extract binary features using Ghidra analysis",
                "ready": True
            }
        ]
        
        # Add Qiling dynamic analysis if it's an ELF binary or object file
        if is_elf or is_object_file:
            description = "Run Qiling dynamic crypto detection (for ELF binaries)"
            if is_object_file:
                description = "Convert .o to .elf and run Qiling dynamic crypto detection"
            
            next_actions.append({
                "action": "qiling_dynamic_analysis",
                "endpoint": f"/job/{response['jobId']}/qiling-analysis",
                "description": description,
                "ready": True,
                "parallel": True,  # Can run in parallel with feature extraction
                "requires_conversion": is_object_file
            })
        
        next_actions.append({
            "action": "classify_crypto", 
            "endpoint": f"/job/{response['jobId']}/classify",
            "description": "Classify cryptographic functions",
            "ready": False,  # Available after feature extraction
            "depends_on": "extract_features"
        })
        
        response["next_actions"] = next_actions
        
        logger.info(f"Added PATH_A_BARE_METAL info for JobID: {response['jobId']}, ELF: {is_elf}")
    
    def _add_linux_fs_info(self, response: Dict[str, Any], ingest_result: Dict[str, Any]):
        """Add PATH_B_LINUX_FS specific information"""
        response["analysis"]["filesystem_info"] = {
            "is_filesystem": True,
            "extracted_path": ingest_result["extraction"].get("extracted_path")
        }
        
        response["next_actions"] = [
            {
                "action": "scan_filesystem",
                "endpoint": f"/job/{response['jobId']}/fs-scan", 
                "description": "Scan extracted filesystem for binaries",
                "ready": True
            }
        ]
        
        logger.info(f"Added PATH_B_LINUX_FS info for JobID: {response['jobId']}")
    
    def _add_hard_target_info(self, response: Dict[str, Any], ingest_result: Dict[str, Any]):
        """Add PATH_C_HARD_TARGET specific information"""
        
        # For PATH_C, run crypto string detection on the original binary
        workspace_path = ingest_result.get("analysis_workspace")
        crypto_strings_result = None
        control_flow_result = None
        
        if workspace_path and os.path.exists(workspace_path):
            # Find the binary file in workspace
            import glob
            workspace_files = glob.glob(os.path.join(workspace_path, "*"))
            binary_files = [f for f in workspace_files if os.path.isfile(f) and not f.endswith('.json')]
            
            if binary_files:
                binary_path = binary_files[0]
                logger.info(f"Running crypto string detection on PATH_C binary - JobID: {response['jobId']}")
                
                # Get file type for better LLM analysis
                file_type = ingest_result.get("file_info", {}).get("detected_type", "unknown")
                
                crypto_strings_result = crypto_string_detector.extract_crypto_strings(
                    binary_path, 
                    job_id=response['jobId'],
                    file_type=file_type,
                    use_llm=True
                )
                
                # Run control flow analysis using test1.sh
                logger.info(f"Running control flow analysis on PATH_C binary - JobID: {response['jobId']}")
                control_flow_result = control_flow_analyzer.analyze_binary(
                    binary_path,
                    job_id=response['jobId'],
                    architecture="arm64"  # Default, can be detected from file type
                )
        
        response["analysis"]["hard_target_info"] = {
            "is_encrypted": True,
            "extraction_failed": not ingest_result["extraction"]["was_extracted"],
            "crypto_strings": crypto_strings_result,
            "control_flow_analysis": control_flow_result
        }
        
        response["next_actions"] = [
            {
                "action": "entropy_analysis",
                "endpoint": f"/job/{response['jobId']}/entropy",
                "description": "Analyze file entropy for encryption detection", 
                "ready": True
            },
            {
                "action": "signature_detection",
                "endpoint": f"/job/{response['jobId']}/signatures",
                "description": "Detect file signatures and magic bytes",
                "ready": True
            }
        ]
        
        logger.info(f"Added PATH_C_HARD_TARGET info for JobID: {response['jobId']}")
    
    def _format_size(self, bytes_size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    def _is_elf_file(self, file_path: str) -> bool:
        """Check if file is an ELF binary"""
        if not file_path or not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(4)
                return magic == b'\x7fELF'
        except Exception as e:
            logger.error(f"Error checking ELF magic for {file_path}: {e}")
            return False
    
    def _is_object_file(self, file_path: str) -> bool:
        """
        Check if file is an object file (.o)
        
        Object files are relocatable ELF files that need to be linked into executables
        """
        if not file_path or not os.path.exists(file_path):
            return False
        
        # Quick check: .o extension
        if file_path.endswith('.o'):
            return True
        
        # More thorough check: use readelf to check ELF type
        try:
            import subprocess
            result = subprocess.run(
                ['readelf', '-h', file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Look for "Type: REL (Relocatable file)"
                if 'REL (Relocatable file)' in output:
                    logger.debug(f"Detected relocatable object file: {file_path}")
                    return True
        except Exception as e:
            logger.debug(f"readelf check failed for {file_path}: {e}")
        
        return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job (placeholder for database integration)"""
        logger.info(f"Getting job status for JobID: {job_id}")
        
        # TODO: Implement database lookup
        # For now, return a placeholder response
        return {
            "jobId": job_id,
            "status": "not_found",
            "message": "Job status lookup not yet implemented with database"
        }