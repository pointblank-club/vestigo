"""
Qiling Dynamic Analysis Service for Vestigo Backend
Orchestrates dynamic crypto detection for ELF binaries using Qiling framework
"""

import os
import sys
import json
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path

from config.logging_config import logger


class QilingDynamicAnalysisService:
    """
    Service for running Qiling-based dynamic crypto detection on ELF binaries.
    
    This service:
    1. Validates ELF binaries
    2. Runs verify_crypto.py script from qiling_analysis
    3. Parses console output and extracts JSON results
    4. Saves structured results to qiling_output/
    """
    
    def __init__(self):
        # Path to qiling_analysis directory
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.qiling_analysis_dir = self.project_root / "qiling_analysis"
        self.verify_crypto_script = self.qiling_analysis_dir / "tests" / "verify_crypto.py"
        
        # Output directory for JSON results (inside backend for easy access)
        self.output_dir = Path(__file__).parent.parent / "qiling_output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Qiling virtual environment
        self.qiling_venv = self.qiling_analysis_dir / "qiling_env"
        self.python_executable = self.qiling_venv / "bin" / "python3"
        
        # Check if qiling is set up
        if not self.verify_crypto_script.exists():
            logger.warning(f"Qiling verify_crypto.py not found at: {self.verify_crypto_script}")
        
        if not self.python_executable.exists():
            logger.warning(f"Qiling virtual environment not found at: {self.qiling_venv}")
            logger.warning("Using system python3 instead")
            self.python_executable = "python3"
        
        logger.info(f"QilingDynamicAnalysisService initialized")
        logger.info(f"Qiling analysis dir: {self.qiling_analysis_dir}")
        logger.info(f"Verify crypto script: {self.verify_crypto_script}")
        logger.info(f"Output directory: {self.output_dir}")
    
    async def analyze_elf_binary(self, job_id: str, binary_path: str) -> Dict[str, Any]:
        """
        Run Qiling dynamic analysis on an ELF binary
        
        Args:
            job_id: Unique identifier for this analysis job
            binary_path: Absolute path to the ELF binary (including converted .o files)
            
        Returns:
            Dict containing analysis results with crypto detection findings
            
        Note:
            This function accepts both:
            - Standard ELF executables
            - ELF files converted from object files (.o)
            The analysis behavior is the same for both types.
        """
        logger.info(f"Starting Qiling dynamic analysis - JobID: {job_id}, Binary: {binary_path}")
        
        # Check if this was converted from an object file
        is_converted = binary_path.endswith('.elf') and os.path.exists(binary_path.replace('.elf', '.o'))
        if is_converted:
            logger.info(f"Analyzing converted object file (.o -> .elf) - JobID: {job_id}")
        
        if not os.path.exists(binary_path):
            logger.error(f"Binary file not found: {binary_path}")
            return self._create_error_result(job_id, binary_path, "Binary file not found")
        
        # Validate ELF format
        if not self._is_elf_binary(binary_path):
            logger.error(f"File is not an ELF binary: {binary_path}")
            return self._create_error_result(job_id, binary_path, "Not an ELF binary")
        
        try:
            # Run the verify_crypto.py script
            result = await self._run_qiling_analysis(binary_path)
            
            # Parse the output
            parsed_result = self._parse_qiling_output(result, job_id, binary_path)
            
            # Save to JSON file
            output_file = self._save_results(job_id, parsed_result)
            
            logger.info(f"Qiling analysis completed - JobID: {job_id}, Output: {output_file}")
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Qiling analysis failed - JobID: {job_id}: {str(e)}", exc_info=True)
            return self._create_error_result(job_id, binary_path, str(e))
    
    def _is_elf_binary(self, binary_path: str) -> bool:
        """Check if file is an ELF binary"""
        try:
            with open(binary_path, 'rb') as f:
                magic = f.read(4)
                return magic == b'\x7fELF'
        except Exception as e:
            logger.error(f"Error checking ELF magic: {e}")
            return False
    
    async def _run_qiling_analysis(self, binary_path: str) -> Dict[str, Any]:
        """
        Execute the verify_crypto.py script
        
        Returns dict with:
            - stdout: console output
            - stderr: error output
            - returncode: exit code
            - execution_time: seconds
        """
        start_time = time.time()
        
        try:
            # Run verify_crypto.py with the binary
            cmd = [str(self.python_executable), str(self.verify_crypto_script), binary_path]
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            # Run with timeout (60 seconds max)
            process = subprocess.run(
                cmd,
                cwd=str(self.qiling_analysis_dir / "tests"),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            return {
                "stdout": process.stdout,
                "stderr": process.stderr,
                "returncode": process.returncode,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Qiling analysis timed out after 60 seconds")
            return {
                "stdout": "",
                "stderr": "Analysis timed out after 60 seconds",
                "returncode": -1,
                "execution_time": 60.0
            }
        except Exception as e:
            logger.error(f"Error running Qiling analysis: {str(e)}")
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "execution_time": time.time() - start_time
            }
    
    def _parse_qiling_output(self, result: Dict[str, Any], job_id: str, binary_path: str) -> Dict[str, Any]:
        """
        Parse the console output from verify_crypto.py into structured JSON
        """
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        
        # Initialize result structure
        parsed = {
            "job_id": job_id,
            "binary_path": binary_path,
            "binary_name": os.path.basename(binary_path),
            "analysis_timestamp": time.time(),
            "execution_time": result.get("execution_time", 0),
            "status": "completed" if result.get("returncode") == 0 else "failed",
            "analysis_tool": "qiling_dynamic_analysis",
            "phases": {
                "packer_detection": {},
                "yara_analysis": {},
                "constant_detection": {},
                "function_symbols": {},
                "dynamic_analysis": {}
            },
            "verdict": {
                "crypto_detected": False,
                "confidence": "UNKNOWN",
                "confidence_score": 0,
                "reasons": []
            },
            "raw_output": stdout,
            "errors": stderr if stderr else None
        }
        
        # Parse each phase from output
        lines = stdout.split('\n')
        
        # PHASE -1: Packer Detection
        for i, line in enumerate(lines):
            if "PHASE -1:" in line:
                if "No packer detected" in stdout:
                    parsed["phases"]["packer_detection"] = {"packed": False}
                elif "Packed binary detected:" in stdout:
                    # Extract packer name
                    for j in range(i, min(i+5, len(lines))):
                        if "Packed binary detected:" in lines[j]:
                            packer_info = lines[j].split("Packed binary detected:")[1].strip()
                            parsed["phases"]["packer_detection"] = {
                                "packed": True,
                                "packer": packer_info
                            }
                break
        
        # PHASE 0: YARA Analysis
        for i, line in enumerate(lines):
            if "PHASE 0:" in line:
                yara_results = {"detected": [], "total_matches": 0, "scan_time": 0}
                for j in range(i, min(i+10, len(lines))):
                    if "YARA detected:" in lines[j]:
                        detected_str = lines[j].split("YARA detected:")[1].strip()
                        yara_results["detected"] = [x.strip() for x in detected_str.split(',')]
                    elif "Total matches:" in lines[j]:
                        try:
                            yara_results["total_matches"] = int(lines[j].split("Total matches:")[1].strip())
                        except: pass
                    elif "Scan time:" in lines[j]:
                        try:
                            yara_results["scan_time"] = float(lines[j].split("Scan time:")[1].strip().rstrip('s'))
                        except: pass
                parsed["phases"]["yara_analysis"] = yara_results
                break
        
        # PHASE 1: Constant Detection
        for i, line in enumerate(lines):
            if "PHASE 1:" in line:
                constants = {}
                for j in range(i, min(i+15, len(lines))):
                    if lines[j].strip().startswith("- "):
                        algo = lines[j].strip()[2:].strip()
                        constants[algo] = True
                parsed["phases"]["constant_detection"] = {
                    "algorithms_detected": list(constants.keys()),
                    "count": len(constants)
                }
                break
        
        # PHASE 2: Function Symbols
        for i, line in enumerate(lines):
            if "PHASE 2:" in line:
                if "No crypto function names detected" in stdout:
                    parsed["phases"]["function_symbols"] = {"detected": False, "stripped": True}
                else:
                    # Count functions mentioned
                    function_count = 0
                    for j in range(i, min(i+20, len(lines))):
                        if lines[j].strip().startswith("- ") and "@" in lines[j]:
                            function_count += 1
                    parsed["phases"]["function_symbols"] = {
                        "detected": function_count > 0,
                        "count": function_count
                    }
                break
        
        # PHASE 3: Dynamic Analysis Results
        dynamic_results = {}
        for i, line in enumerate(lines):
            if "ENHANCED ANALYSIS RESULTS" in line or "Basic Block Analysis:" in line:
                # Extract metrics
                for j in range(i, min(i+30, len(lines))):
                    if "Total Basic Blocks:" in lines[j]:
                        try:
                            dynamic_results["total_basic_blocks"] = int(lines[j].split(":")[1].strip())
                        except: pass
                    elif "Total Instructions Executed:" in lines[j]:
                        try:
                            dynamic_results["total_instructions"] = int(lines[j].split(":")[1].strip())
                        except: pass
                    elif "Crypto Operations:" in lines[j]:
                        try:
                            dynamic_results["crypto_operations"] = int(lines[j].split(":")[1].strip())
                        except: pass
                    elif "Crypto-Op Ratio:" in lines[j]:
                        try:
                            ratio_str = lines[j].split(":")[1].strip().rstrip('%')
                            dynamic_results["crypto_op_ratio"] = float(ratio_str)
                        except: pass
                    elif "Crypto-Heavy Blocks:" in lines[j]:
                        try:
                            dynamic_results["crypto_heavy_blocks"] = int(lines[j].split(":")[1].strip())
                        except: pass
                    elif "Found" in lines[j] and "crypto loop" in lines[j]:
                        try:
                            # Extract number of loops
                            import re
                            match = re.search(r'Found (\d+) crypto loop', lines[j])
                            if match:
                                dynamic_results["crypto_loops"] = int(match.group(1))
                        except: pass
                
                parsed["phases"]["dynamic_analysis"] = dynamic_results
                break
        
        # Parse Verdict - handle multiple output formats
        verdict_found = False
        
        # Format 1: Look for explicit "VERDICT:" line
        for i, line in enumerate(lines):
            if "VERDICT:" in line:
                verdict_found = True
                # Check for any crypto detection patterns
                if ("Crypto behavior detected" in line or 
                    "Crypto functions detected" in line or
                    "Crypto detected" in line):
                    parsed["verdict"]["crypto_detected"] = True
                    # Extract confidence
                    if "Confidence:" in line:
                        conf_match = line.split("Confidence:")[1].strip().rstrip(')')
                        parsed["verdict"]["confidence"] = conf_match
                else:
                    # Any other verdict means no crypto detected
                    parsed["verdict"]["crypto_detected"] = False
                    if "Confidence:" in line:
                        conf_match = line.split("Confidence:")[1].strip().rstrip(')')
                        parsed["verdict"]["confidence"] = conf_match
                
                # Extract confidence score
                for j in range(i, min(i+10, len(lines))):
                    if "Confidence Score:" in lines[j]:
                        try:
                            score_str = lines[j].split("Confidence Score:")[1].strip().split('/')[0]
                            parsed["verdict"]["confidence_score"] = int(score_str)
                        except: pass
                    elif "Reasons:" in lines[j]:
                        # Extract reasons
                        reasons = []
                        for k in range(j+1, min(j+10, len(lines))):
                            if lines[k].strip().startswith("- "):
                                reasons.append(lines[k].strip()[2:])
                            elif lines[k].strip().startswith("==="):
                                break
                        parsed["verdict"]["reasons"] = reasons
                break
        
        # Format 2: If no explicit verdict, infer from detection results
        if not verdict_found:
            # Check if crypto functions or algorithms were detected
            has_crypto_functions = False
            has_crypto_constants = False
            detected_algorithms = []
            function_count = 0
            constant_count = 0
            
            for line in lines:
                # Check for crypto function candidates
                if "Found" in line and "crypto candidate" in line:
                    try:
                        import re
                        match = re.search(r'Found (\d+) crypto candidate', line)
                        if match:
                            count = int(match.group(1))
                            if count > 0:
                                has_crypto_functions = True
                                function_count = count
                    except: pass
                
                # Check for algorithm classification - only accept standard algorithms
                if "PRIMARY CLASSIFICATION:" in line:
                    # Only treat as crypto if it's a KNOWN standard algorithm
                    if ("AES" in line and "PROPRIETARY" not in line) or \
                       ("RSA" in line and "PROPRIETARY" not in line) or \
                       ("SHA" in line and "PROPRIETARY" not in line) or \
                       ("DES" in line and "PROPRIETARY" not in line) or \
                       ("ChaCha" in line and "PROPRIETARY" not in line) or \
                       ("Blowfish" in line and "PROPRIETARY" not in line) or \
                       ("Twofish" in line and "PROPRIETARY" not in line):
                        detected_algorithms.append(line.split("PRIMARY CLASSIFICATION:")[1].strip())
                    # Ignore PROPRIETARY/custom algorithm classifications unless there's other evidence
                
                # Check for constant detection with actual count
                if "Found constants for" in line and "algorithm(s)" in line:
                    try:
                        import re
                        match = re.search(r'Found constants for (\d+) algorithm', line)
                        if match:
                            count = int(match.group(1))
                            if count > 0:
                                has_crypto_constants = True
                                constant_count = count
                    except: pass
            
            # More strict criteria: require actual evidence, not just proprietary classification
            # Crypto detected ONLY if:
            # 1. Has crypto functions (named functions with crypto signatures), OR
            # 2. Has crypto constants (known algorithm constants), OR
            # 3. Has KNOWN standard algorithm detected (not just proprietary)
            if has_crypto_functions or has_crypto_constants or detected_algorithms:
                parsed["verdict"]["crypto_detected"] = True
                parsed["verdict"]["confidence"] = "MEDIUM" if (has_crypto_functions and has_crypto_constants) else "LOW"
                
                # Build reasons list
                reasons = []
                if has_crypto_functions:
                    reasons.append(f"{function_count} crypto function candidates detected")
                if has_crypto_constants:
                    reasons.append(f"{constant_count} crypto constants found")
                if detected_algorithms:
                    reasons.append(f"Algorithms: {', '.join(detected_algorithms)}")
                
                parsed["verdict"]["reasons"] = reasons
                parsed["verdict"]["confidence_score"] = 60 if (has_crypto_functions and has_crypto_constants) else 30
            else:
                # No concrete evidence - mark as no crypto detected
                parsed["verdict"]["crypto_detected"] = False
                parsed["verdict"]["confidence"] = "HIGH"  # High confidence it's NOT crypto
                parsed["verdict"]["confidence_score"] = 10
                parsed["verdict"]["reasons"] = ["No crypto functions, constants, or known algorithms detected"]
        
        return parsed
    
    def _save_results(self, job_id: str, results: Dict[str, Any]) -> str:
        """Save analysis results to JSON file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        binary_name = results.get("binary_name", "unknown")
        filename = f"{job_id}_{binary_name}_{timestamp}_qiling.json"
        output_path = self.output_dir / filename
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Saved Qiling results to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to save Qiling results: {str(e)}")
            return ""
    
    def _create_error_result(self, job_id: str, binary_path: str, error_message: str) -> Dict[str, Any]:
        """Create an error result structure"""
        return {
            "job_id": job_id,
            "binary_path": binary_path,
            "binary_name": os.path.basename(binary_path),
            "analysis_timestamp": time.time(),
            "status": "error",
            "analysis_tool": "qiling_dynamic_analysis",
            "error": error_message,
            "verdict": {
                "crypto_detected": False,
                "confidence": "ERROR",
                "confidence_score": 0,
                "reasons": [f"Analysis failed: {error_message}"]
            }
        }
