"""
Secure Boot Analysis Service for Vestigo Backend
Analyzes bootloaders for secure boot implementation and chain of trust
"""

import os
import sys
import subprocess
import json
from typing import Dict, Any, Optional
from pathlib import Path

from config.logging_config import logger

# Add parent directory to path
# Add parent directory to path
# Use resolve() for robust absolute path
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

class SecureBootAnalysisService:
    """Service for analyzing bootloader secure boot implementation"""
    
    def __init__(self):
        self.analyze_script = Path(__file__).parent.parent.parent / "analyze_secure_boot.py"
        
        if not self.analyze_script.exists():
            logger.warning(f"Secure boot analysis script not found: {self.analyze_script}")
        
        logger.info("SecureBootAnalysisService initialized")
    
    async def analyze_bootloader(self, job_id: str, bootloader_path: str, bootloader_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a bootloader binary for secure boot implementation
        
        Args:
            job_id: Parent job ID (for reference)
            bootloader_path: Path to the bootloader binary file
            bootloader_info: Information about the bootloader from detection
            
        Returns:
            Dict containing secure boot analysis results
        """
        logger.info(f"Starting secure boot analysis - ParentJob: {job_id}, Bootloader: {os.path.basename(bootloader_path)}")
        
        if not os.path.exists(bootloader_path):
            logger.error(f"Bootloader file not found: {bootloader_path}")
            raise FileNotFoundError(f"Bootloader file not found: {bootloader_path}")
        
        if not self.analyze_script.exists():
            logger.error(f"Analysis script not found: {self.analyze_script}")
            raise FileNotFoundError(f"Analysis script not found: {self.analyze_script}")
        
        analysis_results = {
            "parent_job_id": job_id,
            "bootloader_file": os.path.basename(bootloader_path),
            "bootloader_path": bootloader_path,
            "bootloader_type": bootloader_info.get("type", "unknown"),
            "bootloader_size": bootloader_info.get("size", 0),
            "detection_reason": bootloader_info.get("reason", ""),
            "status": "completed",
            "secure_boot_analysis": {}
        }
        
        try:
            # Run the analysis script in JSON mode
            logger.debug(f"Executing analysis script on {bootloader_path}")
            
            result = subprocess.run(
                ["python3", str(self.analyze_script), "--json", bootloader_path],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse JSON output
                try:
                    secure_boot_data = json.loads(result.stdout)
                    analysis_results["secure_boot_analysis"] = secure_boot_data
                    
                    # Add summary flags
                    analysis_results["summary"] = {
                        "has_secure_boot": secure_boot_data.get("secure_boot_logic", False),
                        "has_chain_of_trust": secure_boot_data.get("chain_of_trust_verified", False),
                        "has_hardware_anchor": secure_boot_data.get("hardware_anchor", False),
                        "hash_algorithms": secure_boot_data.get("hash_algorithms", []),
                        "signature_algorithms": secure_boot_data.get("signature_algorithms", []),
                        "fit_format": secure_boot_data.get("fit_image_format", False)
                    }
                    
                    logger.info(f"Secure boot analysis completed - Bootloader: {os.path.basename(bootloader_path)}")
                    logger.info(f"  Secure Boot: {analysis_results['summary']['has_secure_boot']}")
                    logger.info(f"  Chain of Trust: {analysis_results['summary']['has_chain_of_trust']}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse analysis output: {e}")
                    analysis_results["status"] = "failed"
                    analysis_results["error"] = f"Failed to parse analysis output: {str(e)}"
                    analysis_results["raw_output"] = result.stdout
            else:
                logger.warning(f"Analysis script returned error: {result.stderr}")
                analysis_results["status"] = "failed"
                analysis_results["error"] = result.stderr or "Analysis script failed"
                
        except subprocess.TimeoutExpired:
            logger.error(f"Secure boot analysis timeout - Bootloader: {bootloader_path}")
            analysis_results["status"] = "timeout"
            analysis_results["error"] = "Analysis timed out after 120 seconds"
            
        except Exception as e:
            logger.error(f"Secure boot analysis failed - Error: {str(e)}", exc_info=True)
            analysis_results["status"] = "failed"
            analysis_results["error"] = str(e)
        
        return analysis_results
    
    async def analyze_multiple_bootloaders(self, parent_job_id: str, bootloaders: list) -> list:
        """
        Analyze multiple bootloaders
        
        Args:
            parent_job_id: ID of the parent firmware analysis job
            bootloaders: List of bootloader info dicts from detection
            
        Returns:
            List of analysis results for each bootloader
        """
        results = []
        
        for bootloader_info in bootloaders:
            bootloader_path = bootloader_info.get("path")
            if not bootloader_path or not os.path.exists(bootloader_path):
                logger.warning(f"Skipping bootloader - invalid path: {bootloader_path}")
                continue
            
            try:
                analysis = await self.analyze_bootloader(parent_job_id, bootloader_path, bootloader_info)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze bootloader {bootloader_path}: {e}")
                results.append({
                    "parent_job_id": parent_job_id,
                    "bootloader_file": os.path.basename(bootloader_path) if bootloader_path else "unknown",
                    "bootloader_path": bootloader_path,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
