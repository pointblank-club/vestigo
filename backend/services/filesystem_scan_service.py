"""
Filesystem Scan Service for Vestigo Backend
Handles scanning extracted firmware filesystems for cryptographic libraries and configurations
"""

import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess
import re

from config.logging_config import logger

# Add parent directory to path to import fs_scan module if it exists
# Add parent directory to path to import fs_scan module if it exists
# Use resolve() for robust absolute path
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

class FilesystemScanService:
    """Service for scanning extracted firmware filesystems"""
    
    def __init__(self):
        logger.info("FilesystemScanService initialized")
    
    async def scan_filesystem(self, job_id: str, extracted_path: str) -> Dict[str, Any]:
        """
        Scan an extracted firmware filesystem for cryptographic assets
        
        Args:
            job_id: Unique identifier for this analysis job
            extracted_path: Path to the extracted filesystem
            
        Returns:
            Dict containing scan results with libraries, configs, and keys found
        """
        logger.info(f"Starting filesystem scan - JobID: {job_id}, Path: {extracted_path}")
        
        if not os.path.exists(extracted_path):
            logger.error(f"Extracted path does not exist: {extracted_path}")
            raise FileNotFoundError(f"Extracted path not found: {extracted_path}")
        
        scan_results = {
            "job_id": job_id,
            "scan_path": extracted_path,
            "status": "completed",
            "crypto_libraries": {"so_files": [], "a_files": [], "o_files": []},
            "ssl_configs": [],
            "certificates": [],
            "private_keys": [],
            "hardcoded_secrets": [],
            "binaries": [],
            "summary": {
                "total_crypto_libraries": 0,
                "total_configs": 0,
                "total_certificates": 0,
                "total_private_keys": 0,
                "total_secrets": 0,
                "total_binaries": 0
            }
        }
        
        try:
            # 1. Find crypto libraries (.so, .a, .o files)
            logger.info(f"Scanning for crypto libraries - JobID: {job_id}")
            scan_results["crypto_libraries"] = self._find_crypto_libraries(extracted_path)
            total_libs = (len(scan_results["crypto_libraries"].get("so_files", [])) + 
                         len(scan_results["crypto_libraries"].get("a_files", [])) +
                         len(scan_results["crypto_libraries"].get("o_files", [])))
            scan_results["summary"]["total_crypto_libraries"] = total_libs
            
            # 2. Find SSL/TLS configurations
            logger.info(f"Scanning for SSL/TLS configurations - JobID: {job_id}")
            scan_results["ssl_configs"] = self._find_ssl_configs(extracted_path)
            scan_results["summary"]["total_configs"] = len(scan_results["ssl_configs"])
            
            # 3. Find certificates and keys
            logger.info(f"Scanning for certificates and keys - JobID: {job_id}")
            certs, keys = self._find_certificates_and_keys(extracted_path)
            scan_results["certificates"] = certs
            scan_results["private_keys"] = keys
            scan_results["summary"]["total_certificates"] = len(certs)
            scan_results["summary"]["total_private_keys"] = len(keys)
            
            # 4. Find hardcoded secrets
            logger.info(f"Scanning for hardcoded secrets - JobID: {job_id}")
            scan_results["hardcoded_secrets"] = self._find_hardcoded_secrets(extracted_path)
            scan_results["summary"]["total_secrets"] = len(scan_results["hardcoded_secrets"])
            
            # 5. Find binary executables
            logger.info(f"Scanning for binaries - JobID: {job_id}")
            scan_results["binaries"] = self._find_binaries(extracted_path)
            scan_results["summary"]["total_binaries"] = len(scan_results["binaries"])
            
            logger.info(f"Filesystem scan completed - JobID: {job_id}")
            logger.info(f"Found: {scan_results['summary']['total_crypto_libraries']} libraries, "
                       f"{scan_results['summary']['total_configs']} configs, "
                       f"{scan_results['summary']['total_certificates']} certs, "
                       f"{scan_results['summary']['total_private_keys']} keys, "
                       f"{scan_results['summary']['total_binaries']} binaries")
            
            return scan_results
            
        except Exception as e:
            logger.error(f"Filesystem scan failed - JobID: {job_id}, Error: {str(e)}", exc_info=True)
            scan_results["status"] = "failed"
            scan_results["error"] = str(e)
            return scan_results
    
    def _find_crypto_libraries(self, search_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Find cryptographic libraries (.so, .a, .o files)"""
        so_files = []
        a_files = []
        o_files = []
        crypto_patterns = [
            "libcrypto", "libssl", "libustream", "libtls", "libmbedtls",
            "libwolfssl", "libopenssl", "libgcrypt", "libnettle", "aes", "rsa", 
            "sha", "md5", "crypto", "cipher"
        ]
        
        for root, dirs, files in os.walk(search_path):
            for file in files:
                # Check for .so, .a, and .o files
                if file.endswith(('.so', '.a', '.o')) or '.so.' in file:
                    # Check if it's a crypto-related library
                    file_lower = file.lower()
                    for pattern in crypto_patterns:
                        if pattern in file_lower:
                            full_path = os.path.join(root, file)
                            lib_info = {
                                "file": file,
                                "path": full_path,
                                "matched_pattern": pattern,
                                "size": os.path.getsize(full_path)
                            }
                            
                            # Separate into .so, .a, and .o files
                            if '.so' in file:
                                so_files.append(lib_info)
                            elif file.endswith('.a'):
                                a_files.append(lib_info)
                            elif file.endswith('.o'):
                                o_files.append(lib_info)
                            break
        
        return {"so_files": so_files, "a_files": a_files, "o_files": o_files}
    
    def _find_ssl_configs(self, search_path: str) -> List[Dict[str, Any]]:
        """Find SSL/TLS configuration files with insecure settings"""
        configs = []
        config_patterns = [
            r"ssl_protocols",
            r"ssl_ciphers",
            r"tls_ciphers",
            r"PermitRootLogin",
            r"SSLProtocol",
            r"SSLCipherSuite"
        ]
        
        try:
            for pattern in config_patterns:
                cmd = ["grep", "-r", "-i", "-n", "-I", pattern, search_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines[:50]:  # Limit to first 50 matches per pattern
                        if ":" in line:
                            parts = line.split(":", 2)
                            if len(parts) >= 3:
                                configs.append({
                                    "file": parts[0],
                                    "line_number": parts[1],
                                    "content": parts[2][:200],  # Truncate long lines
                                    "pattern": pattern
                                })
        except subprocess.TimeoutExpired:
            logger.warning(f"Grep search timed out for SSL configs")
        except Exception as e:
            logger.warning(f"Error searching for SSL configs: {e}")
        
        return configs
    
    def _find_certificates_and_keys(self, search_path: str) -> tuple:
        """Find certificates and private keys"""
        certificates = []
        private_keys = []
        
        cert_extensions = ['.pem', '.crt', '.cer', '.der', '.p12', '.pfx']
        key_extensions = ['.key', '.pem']
        
        for root, dirs, files in os.walk(search_path):
            for file in files:
                file_lower = file.lower()
                full_path = os.path.join(root, file)
                
                # Check for certificates
                if any(file_lower.endswith(ext) for ext in cert_extensions):
                    if 'cert' in file_lower or any(file_lower.endswith(ext) for ext in ['.crt', '.cer', '.der']):
                        certificates.append({
                            "filename": file,
                            "path": full_path,
                            "size": os.path.getsize(full_path)
                        })
                
                # Check for private keys
                if any(file_lower.endswith(ext) for ext in key_extensions):
                    if 'key' in file_lower or 'priv' in file_lower:
                        private_keys.append({
                            "filename": file,
                            "path": full_path,
                            "size": os.path.getsize(full_path)
                        })
        
        # Also search for embedded PEM blocks
        try:
            cmd = ["grep", "-r", "-i", "-n", "-I", "BEGIN.*PRIVATE KEY", search_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines[:20]:  # Limit results
                    if ":" in line:
                        parts = line.split(":", 2)
                        if len(parts) >= 2:
                            private_keys.append({
                                "filename": os.path.basename(parts[0]),
                                "path": parts[0],
                                "type": "embedded_pem",
                                "line_number": parts[1]
                            })
        except Exception as e:
            logger.warning(f"Error searching for embedded keys: {e}")
        
        return certificates, private_keys
    
    def _find_hardcoded_secrets(self, search_path: str) -> List[Dict[str, Any]]:
        """Find hardcoded API keys and secrets"""
        secrets = []
        secret_patterns = [
            r"private_key",
            r"secret_key",
            r"auth_token",
            r"api_key",
            r"password\s*=",
            r"passwd\s*="
        ]
        
        try:
            for pattern in secret_patterns:
                cmd = ["grep", "-r", "-i", "-n", "-I", pattern, search_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines[:30]:  # Limit to first 30 matches per pattern
                        if ":" in line:
                            parts = line.split(":", 2)
                            if len(parts) >= 3:
                                secrets.append({
                                    "file": parts[0],
                                    "line_number": parts[1],
                                    "content": parts[2][:150],  # Truncate and hide actual values
                                    "pattern": pattern,
                                    "severity": "high" if "password" in pattern else "medium"
                                })
        except subprocess.TimeoutExpired:
            logger.warning(f"Grep search timed out for secrets")
        except Exception as e:
            logger.warning(f"Error searching for secrets: {e}")
        
        return secrets
    
    def _find_binaries(self, search_path: str) -> List[Dict[str, Any]]:
        """Find binary executables in the filesystem"""
        binaries = []
        binary_dirs = ['bin', 'sbin', 'usr/bin', 'usr/sbin', 'usr/local/bin']
        
        for root, dirs, files in os.walk(search_path):
            # Focus on common binary directories
            if any(bd in root for bd in binary_dirs):
                for file in files:
                    full_path = os.path.join(root, file)
                    if os.path.isfile(full_path):
                        # Check if file is executable
                        if os.access(full_path, os.X_OK):
                            try:
                                binaries.append({
                                    "filename": file,
                                    "path": full_path,
                                    "size": os.path.getsize(full_path),
                                    "directory": os.path.basename(root)
                                })
                            except Exception:
                                pass
        
        return binaries[:100]  # Limit to first 100 binaries
