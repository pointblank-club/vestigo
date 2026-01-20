"""
Control Flow Analysis Service
Runs radare2-based static analysis on binaries and captures control flow graphs
"""

import os
import subprocess
import glob
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
from config.logging_config import logger


class ControlFlowAnalyzer:
    """Service for analyzing binary control flow using test1.sh"""
    
    def __init__(self):
        # Path to test1.sh script
        self.script_path = Path(__file__).resolve().parent.parent / "test1.sh"
        if not self.script_path.exists():
            logger.warning(f"test1.sh not found at {self.script_path}")
            self.script_path = None
        else:
            logger.info(f"ControlFlowAnalyzer initialized with script: {self.script_path}")
        
        # Check for required dependencies
        self.dependencies_available = self._check_dependencies()
    
    def _check_dependencies(self) -> bool:
        """Check if required tools are available"""
        required_tools = ["r2", "radare2", "binwalk", "file"]
        missing_tools = []
        
        for tool in required_tools:
            try:
                result = subprocess.run(
                    ["which", tool],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode != 0 and tool not in ["r2", "radare2"]:
                    missing_tools.append(tool)
                elif result.returncode != 0 and tool in ["r2", "radare2"]:
                    # Only need one of r2 or radare2
                    continue
            except Exception:
                pass
        
        if missing_tools:
            logger.warning(f"Control flow analysis dependencies missing: {', '.join(missing_tools)}")
            return False
        
        return True
    
    def analyze_binary(
        self, 
        binary_path: str, 
        job_id: str,
        architecture: str = "arm64"
    ) -> Dict[str, Any]:
        """
        Run control flow analysis on a binary
        
        Args:
            binary_path: Path to the binary file
            job_id: Job ID for tracking
            architecture: Target architecture (arm64, x86, mips, etc.)
            
        Returns:
            Dict containing analysis output and CFG paths
        """
        if not self.script_path or not self.script_path.exists():
            logger.error(f"JobID: {job_id} - test1.sh script not available")
            return {
                "status": "error",
                "error": "Control flow analysis script not found"
            }
        
        if not self.dependencies_available:
            logger.warning(f"JobID: {job_id} - Control flow analysis dependencies not available")
            return {
                "status": "skipped",
                "error": "Required tools (radare2, binwalk) not installed"
            }
        
        if not os.path.exists(binary_path):
            logger.error(f"JobID: {job_id} - Binary not found: {binary_path}")
            return {
                "status": "error",
                "error": f"Binary file not found: {binary_path}"
            }
        
        try:
            # Auto-detect architecture if not explicitly set
            if architecture == "arm64":
                detected_arch = self._detect_architecture(binary_path)
                if detected_arch:
                    architecture = detected_arch
                    logger.info(f"JobID: {job_id} - Detected architecture: {architecture}")
            
            logger.info(f"JobID: {job_id} - Starting control flow analysis on {binary_path} (arch: {architecture})")
            
            # Create output directory for this job's CFG files
            cfg_dir = Path(__file__).resolve().parent.parent / "job_storage" / f"{job_id}_cfg"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            
            # Change to binary's directory to run script (it outputs files in current dir)
            binary_dir = os.path.dirname(binary_path)
            binary_name = os.path.basename(binary_path)
            
            # Run test1.sh
            result = subprocess.run(
                [str(self.script_path), binary_name, architecture],
                cwd=binary_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            analysis_output = result.stdout
            error_output = result.stderr
            
            logger.info(f"JobID: {job_id} - Control flow analysis completed (exit code: {result.returncode})")
            
            # Move generated files to job's CFG directory
            cfg_files = self._collect_generated_files(binary_dir, cfg_dir)
            
            # Find the latest/largest CFG PNG
            latest_cfg = self._find_latest_cfg(cfg_dir)
            
            # Clean up old CFG files, keep only the latest
            self._cleanup_old_cfgs(cfg_dir, latest_cfg)
            
            # Delete all .dot files after processing
            self._cleanup_dot_files(cfg_dir)
            
            return {
                "status": "success" if result.returncode == 0 else "completed_with_warnings",
                "exit_code": result.returncode,
                "analysis_output": self._format_analysis_output(analysis_output),
                "error_output": error_output if error_output else None,
                "cfg_directory": str(cfg_dir),
                "latest_cfg_png": latest_cfg,
                "generated_files": cfg_files,
                "architecture": architecture
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"JobID: {job_id} - Control flow analysis timed out after 5 minutes")
            return {
                "status": "error",
                "error": "Analysis timed out after 5 minutes"
            }
        except Exception as e:
            logger.error(f"JobID: {job_id} - Control flow analysis error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _collect_generated_files(self, source_dir: str, target_dir: Path) -> Dict[str, list]:
        """Collect and move generated analysis files to target directory"""
        files = {
            "control_flow_txt": [],
            "cfg_dot": [],
            "cfg_png": []
        }
        
        try:
            # Move control_flow_*.txt files
            for txt_file in glob.glob(os.path.join(source_dir, "control_flow_*.txt")):
                dest = target_dir / os.path.basename(txt_file)
                shutil.move(txt_file, dest)
                files["control_flow_txt"].append(str(dest))
                logger.debug(f"Moved {txt_file} to {dest}")
            
            # Move cfg_*.dot files
            for dot_file in glob.glob(os.path.join(source_dir, "cfg_*.dot")):
                dest = target_dir / os.path.basename(dot_file)
                shutil.move(dot_file, dest)
                files["cfg_dot"].append(str(dest))
                logger.debug(f"Moved {dot_file} to {dest}")
            
            # Move cfg_*.png files
            for png_file in glob.glob(os.path.join(source_dir, "cfg_*.png")):
                dest = target_dir / os.path.basename(png_file)
                shutil.move(png_file, dest)
                files["cfg_png"].append(str(dest))
                logger.debug(f"Moved {png_file} to {dest}")
                
        except Exception as e:
            logger.warning(f"Error collecting generated files: {str(e)}")
        
        return files
    
    def _find_latest_cfg(self, cfg_dir: Path) -> Optional[str]:
        """Find the latest/largest CFG PNG file"""
        png_files = list(cfg_dir.glob("cfg_*.png"))
        
        if not png_files:
            return None
        
        # Sort by file size (largest first) then by modification time
        png_files.sort(key=lambda f: (f.stat().st_size, f.stat().st_mtime), reverse=True)
        
        latest = png_files[0]
        logger.info(f"Latest CFG PNG: {latest.name} ({latest.stat().st_size} bytes)")
        
        return str(latest)
    
    def _cleanup_old_cfgs(self, cfg_dir: Path, keep_file: Optional[str]):
        """Delete all CFG PNGs except the one we want to keep"""
        if not keep_file:
            return
        
        keep_path = Path(keep_file)
        deleted_count = 0
        
        for png_file in cfg_dir.glob("cfg_*.png"):
            if png_file != keep_path:
                try:
                    png_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old CFG: {png_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {png_file}: {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old CFG PNG files")
    
    def _cleanup_dot_files(self, cfg_dir: Path):
        """Delete all .dot files after CFG generation"""
        deleted_count = 0
        
        for dot_file in cfg_dir.glob("cfg_*.dot"):
            try:
                dot_file.unlink()
                deleted_count += 1
                logger.debug(f"Deleted .dot file: {dot_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {dot_file}: {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} .dot files")
    
    def _format_analysis_output(self, raw_output: str) -> str:
        """Format the analysis output for better readability in JSON"""
        if not raw_output:
            return ""
        
        # Pretty print: preserve structure but clean up excessive whitespace
        lines = raw_output.split("\n")
        formatted_lines = []
        
        for line in lines:
            # Preserve important formatting characters
            if any(char in line for char in ["╔", "║", "╚", "┌", "│", "├", "└", "✓", "⚠", "•", "→"]):
                formatted_lines.append(line.rstrip())
            elif line.strip():  # Non-empty line
                formatted_lines.append(line.rstrip())
            elif formatted_lines and formatted_lines[-1]:  # Add max one blank line
                formatted_lines.append("")
        
        return "\n".join(formatted_lines)
    
    def _detect_architecture(self, binary_path: str) -> Optional[str]:
        """Detect binary architecture using file command"""
        try:
            result = subprocess.run(
                ["file", binary_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            file_output = result.stdout.lower()
            
            # Map file output to radare2 architecture names
            if "aarch64" in file_output or "arm64" in file_output:
                return "arm64"
            elif "arm" in file_output:
                return "arm"
            elif "x86-64" in file_output or "x86_64" in file_output:
                return "x86"
            elif "80386" in file_output or "i386" in file_output:
                return "x86"
            elif "mips" in file_output:
                if "mipsel" in file_output:
                    return "mipsel"
                return "mips"
            elif "powerpc" in file_output or "ppc" in file_output:
                return "ppc"
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to detect architecture: {str(e)}")
            return None


# Singleton instance
control_flow_analyzer = ControlFlowAnalyzer()
