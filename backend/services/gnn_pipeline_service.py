"""
GNN Pipeline Service for Vestigo Backend
Runs Graph Neural Network model for cryptographic function detection
"""

import os
import subprocess
import json
from typing import Dict, Any
from pathlib import Path
import time

from config.logging_config import logger


class GNNPipelineService:
    """
    Service for running GNN-based crypto detection pipeline.
    
    This service:
    1. Takes Ghidra JSON output
    2. Runs new_gnn.py --inference
    3. Returns GNN predictions
    """
    
    def __init__(self):
        # Path to project root and GNN script
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.gnn_script = self.project_root / "ml" / "new_gnn.py"
        
        # Output directory for GNN results
        self.gnn_output_dir = self.project_root / "gnn_output"
        self.gnn_output_dir.mkdir(exist_ok=True)
        
        # Model paths (adjust based on your setup)
        self.model_path = self.project_root / "ml" / "gnn_models" / "best_model.pth"
        self.metadata_path = self.project_root / "ml" / "gnn_models" / "metadata.pkl"
        
        # Python executable - use Qiling venv if available (has torch-geometric and dependencies)
        self.qiling_venv = self.project_root / "qiling_analysis" / "qiling_env"
        self.python_executable = self.qiling_venv / "bin" / "python3"
        
        # Fallback to system python3 if venv doesn't exist
        if not os.path.exists(self.python_executable):
            logger.warning(f"Qiling venv Python not found at {self.python_executable}")
            logger.warning("Using system python3 instead")
            self.python_executable = "python3"
        
        # Check if GNN script and models exist
        if not os.path.exists(self.gnn_script):
            logger.warning(f"GNN script not found: {self.gnn_script}")
            logger.warning("GNN pipeline will be skipped")
        
        if not os.path.exists(self.model_path):
            logger.warning(f"GNN model not found: {self.model_path}")
            logger.warning("GNN inference will be skipped")
        
        logger.info(f"GNNPipelineService initialized")
        logger.info(f"Python executable: {self.python_executable}")
        logger.info(f"GNN script: {self.gnn_script}")
        logger.info(f"Model path: {self.model_path}")
        logger.info(f"Metadata path: {self.metadata_path}")
        logger.info(f"Output directory: {self.gnn_output_dir}")
    
    async def run_gnn_inference(self, ghidra_json_path: str, binary_name: str, job_id: str) -> Dict[str, Any]:
        """
        Run GNN inference on Ghidra JSON output
        
        Args:
            ghidra_json_path: Path to Ghidra JSON features file
            binary_name: Name of the binary being analyzed
            job_id: Job ID for tracking
            
        Returns:
            Dict containing GNN analysis results
        """
        logger.info(f"Starting GNN inference - JobID: {job_id}, Binary: {binary_name}")
        
        # Check if GNN script exists
        if not os.path.exists(self.gnn_script):
            logger.warning(f"GNN script not found, skipping GNN analysis - JobID: {job_id}")
            return {
                "status": "skipped",
                "reason": "GNN script not found"
            }
        
        # Check if models exist
        if not os.path.exists(self.model_path) or not os.path.exists(self.metadata_path):
            logger.warning(f"GNN models not found, skipping GNN analysis - JobID: {job_id}")
            return {
                "status": "skipped",
                "reason": "GNN models not found"
            }
        
        # Create output path for GNN results
        gnn_output_path = self.gnn_output_dir / f"{binary_name}_gnn.json"
        
        # Build GNN command
        # python ml/new_gnn.py --inference --input <json> --output <output> --model <model> --metadata <metadata>
        gnn_cmd = [
            str(self.python_executable),
            str(self.gnn_script),
            "--inference",
            "--input", str(ghidra_json_path),
            "--output", str(gnn_output_path),
            "--model", str(self.model_path),
            "--metadata", str(self.metadata_path)
        ]
        
        logger.debug(f"GNN command: {' '.join(gnn_cmd)}")
        
        try:
            start_time = time.time()
            
            # Run GNN inference
            result = subprocess.run(
                gnn_cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self.project_root)
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode != 0:
                logger.error(f"GNN inference failed - JobID: {job_id}, Return code: {result.returncode}")
                logger.error(f"GNN stderr: {result.stderr}")
                logger.error(f"GNN stdout: {result.stdout}")
                return {
                    "status": "failed",
                    "error": result.stderr,
                    "stdout": result.stdout,
                    "execution_time": execution_time
                }
            
            logger.info(f"GNN inference completed - JobID: {job_id}, Time: {execution_time:.2f}s")
            logger.debug(f"GNN stdout: {result.stdout}")
            
            # Read GNN output
            if os.path.exists(gnn_output_path):
                with open(gnn_output_path, 'r') as f:
                    gnn_result = json.load(f)
                
                logger.info(f"Loaded GNN analysis results - JobID: {job_id}")
                
                # Parse GNN output format
                # Structure depends on new_gnn.py output format
                parsed_result = self._parse_gnn_output(gnn_result, job_id)
                
                parsed_result.update({
                    "status": "success",
                    "gnn_output_path": str(gnn_output_path),
                    "ghidra_input_path": str(ghidra_json_path),
                    "execution_time": execution_time
                })
                
                return parsed_result
            else:
                logger.error(f"GNN output file not found: {gnn_output_path}")
                return {
                    "status": "failed",
                    "error": "GNN output file not found",
                    "execution_time": execution_time
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"GNN inference timeout - JobID: {job_id}")
            return {
                "status": "failed",
                "error": "GNN inference timed out after 5 minutes"
            }
        except Exception as e:
            logger.error(f"GNN inference error - JobID: {job_id}, Error: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_gnn_output(self, gnn_result: Dict, job_id: str) -> Dict[str, Any]:
        """
        Parse GNN output JSON into structured format
        
        Args:
            gnn_result: Raw GNN output dictionary
            job_id: Job ID for tracking
            
        Returns:
            Structured GNN analysis results
        """
        parsed = {
            "analysis_type": "gnn",
            "job_id": job_id,
            "model_type": "graph_neural_network"
        }
        
        # Extract function-level predictions
        function_predictions = []
        
        # GNN output format has two separate arrays: crypto_functions and non_crypto_functions
        # Combine them and mark which are crypto
        crypto_funcs = gnn_result.get("crypto_functions", [])
        non_crypto_funcs = gnn_result.get("non_crypto_functions", [])
        
        # Process crypto functions
        for func in crypto_funcs:
            function_predictions.append({
                "function_name": func.get("name", "unknown"),
                "function_address": func.get("address", "unknown"),
                "predicted_class": func.get("class", "unknown"),
                "confidence": func.get("confidence", 0.0),
                "is_crypto": True,
                "probabilities": func.get("probabilities", {}),
                "graph_features": {
                    "num_nodes": func.get("num_basic_blocks", 0),
                    "num_edges": func.get("num_edges", 0)
                }
            })
        
        # Process non-crypto functions
        for func in non_crypto_funcs:
            function_predictions.append({
                "function_name": func.get("name", "unknown"),
                "function_address": func.get("address", "unknown"),
                "predicted_class": func.get("class", "NON_CRYPTO"),
                "confidence": func.get("confidence", 0.0),
                "is_crypto": False,
                "probabilities": func.get("probabilities", {}),
                "graph_features": {
                    "num_nodes": func.get("num_basic_blocks", 0),
                    "num_edges": func.get("num_edges", 0)
                }
            })
        
        parsed["function_predictions"] = function_predictions
        
        # Calculate summary from parsed data
        total_functions = len(function_predictions)
        crypto_count = len(crypto_funcs)
        non_crypto_count = len(non_crypto_funcs)
        
        parsed["summary"] = {
            "total_functions": total_functions,
            "crypto_functions": crypto_count,
            "non_crypto_functions": non_crypto_count,
            "crypto_percentage": (crypto_count / total_functions * 100) if total_functions > 0 else 0
        }
        
        # Extract binary info if available
        parsed["binary_info"] = gnn_result.get("binary", "unknown")
        
        # Count algorithm distribution from crypto functions only
        algorithm_counts = {}
        for func in crypto_funcs:
            algo = func.get("class", "unknown")
            algorithm_counts[algo] = algorithm_counts.get(algo, 0) + 1
        
        parsed["algorithm_distribution"] = algorithm_counts
        
        return parsed
