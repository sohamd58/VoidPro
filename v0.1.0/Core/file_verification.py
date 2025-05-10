"""
File verification module for the game file compression engine.
Verifies the integrity of decompressed files to ensure no data was lost.
"""

import os
import logging
import hashlib
import binascii
import json
from pathlib import Path
import time

class FileVerifier:
    """Handles verification of file integrity after compression/decompression."""
    
    def __init__(self):
        """Initialize the file verifier."""
        self.hash_algorithms = {
            'crc32': self._calculate_crc32,
            'md5': self._calculate_md5,
            'sha1': self._calculate_sha1,
            'sha256': self._calculate_sha256
        }
        
        # Default hash algorithm to use
        self.default_hash_algorithm = 'crc32'
        
        # File extension for verification metadata
        self.verification_extension = '.gcverify'
    
    def generate_verification_data(self, file_path, algorithms=None):
        """
        Generate verification data for a file.
        
        Args:
            file_path (Path): Path to the file to verify
            algorithms (list, optional): List of hash algorithms to use
            
        Returns:
            dict: Verification data including file size and hashes
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        # Use default algorithm if none specified
        if not algorithms:
            algorithms = [self.default_hash_algorithm]
        
        # Ensure all requested algorithms are valid
        for algo in algorithms:
            if algo not in self.hash_algorithms:
                raise ValueError(f"Unknown hash algorithm: {algo}")
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Calculate hashes
        hashes = {}
        with open(file_path, 'rb') as f:
            content = f.read()
            for algo in algorithms:
                hashes[algo] = self.hash_algorithms[algo](content)
        
        # Generate timestamp
        timestamp = time.time()
        
        # Create verification data
        verification_data = {
            'file_path': str(file_path),
            'file_size': file_size,
            'hashes': hashes,
            'timestamp': timestamp,
            'verification_version': 1
        }
        
        return verification_data
    
    def save_verification_data(self, file_path, verify_data=None, algorithms=None):
        """
        Generate and save verification data for a file.
        
        Args:
            file_path (Path): Path to the file to verify
            verify_data (dict, optional): Existing verification data
            algorithms (list, optional): List of hash algorithms to use
            
        Returns:
            Path: Path to the verification data file
        """
        file_path = Path(file_path)
        
        # Generate verification data if not provided
        if not verify_data:
            verify_data = self.generate_verification_data(file_path, algorithms)
        
        # Create verification file path
        verify_file = file_path.with_suffix(self.verification_extension)
        
        # Save verification data
        with open(verify_file, 'w') as f:
            json.dump(verify_data, f, indent=2)
        
        return verify_file
    
    def verify_file(self, file_path, reference_data=None, algorithms=None):
        """
        Verify a file's integrity against reference data or stored verification data.
        
        Args:
            file_path (Path): Path to the file to verify
            reference_data (dict, optional): Reference verification data
            algorithms (list, optional): List of hash algorithms to use
            
        Returns:
            dict: Verification results
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        # If no reference data provided, try to load from verification file
        if not reference_data:
            verify_file = file_path.with_suffix(self.verification_extension)
            if verify_file.exists():
                try:
                    with open(verify_file, 'r') as f:
                        reference_data = json.load(f)
                except Exception as e:
                    logging.error(f"Error loading verification data: {str(e)}")
                    return {'verified': False, 'error': f"Error loading verification data: {str(e)}"}
            else:
                return {'verified': False, 'error': f"No verification data found for {file_path}"}
        
        # Get current file data
        current_data = self.generate_verification_data(
            file_path, 
            algorithms=algorithms or list(reference_data.get('hashes', {}).keys())
        )
        
        # Check file size
        if current_data['file_size'] != reference_data.get('file_size'):
            return {
                'verified': False,
                'error': f"File size mismatch: current={current_data['file_size']}, expected={reference_data.get('file_size')}",
                'current': current_data,
                'reference': reference_data
            }
        
        # Check hashes
        for algo, ref_hash in reference_data.get('hashes', {}).items():
            if algo not in current_data['hashes']:
                continue
                
            if current_data['hashes'][algo] != ref_hash:
                return {
                    'verified': False,
                    'error': f"Hash mismatch for {algo}: current={current_data['hashes'][algo]}, expected={ref_hash}",
                    'current': current_data,
                    'reference': reference_data
                }
        
        # All checks passed
        return {
            'verified': True,
            'current': current_data,
            'reference': reference_data
        }
    
    def verify_directory(self, source_dir, files_map=None, original_dir=None):
        """
        Verify all files in a directory against original files or verification data.
        
        Args:
            source_dir (Path): Directory containing files to verify
            files_map (dict, optional): Mapping of source files to original files
            original_dir (Path, optional): Directory containing original files
            
        Returns:
            dict: Verification results for all files
        """
        source_dir = Path(source_dir)
        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError(f"Source directory {source_dir} does not exist or is not a directory")
        
        if original_dir:
            original_dir = Path(original_dir)
            if not original_dir.exists() or not original_dir.is_dir():
                raise ValueError(f"Original directory {original_dir} does not exist or is not a directory")
        
        results = {
            'total_files': 0,
            'verified_files': 0,
            'failed_files': 0,
            'missing_verification': 0,
            'details': []
        }
        
        for root, _, files in os.walk(source_dir):
            for file in files:
                # Skip verification files
                if file.endswith(self.verification_extension):
                    continue
                    
                file_path = Path(root) / file
                results['total_files'] += 1
                
                try:
                    # Determine original file path
                    if files_map and str(file_path) in files_map:
                        original_path = Path(files_map[str(file_path)])
                    elif original_dir:
                        rel_path = file_path.relative_to(source_dir)
                        original_path = original_dir / rel_path
                    else:
                        # Use verification data if available
                        verify_result = self.verify_file(file_path)
                        if verify_result['verified']:
                            results['verified_files'] += 1
                        else:
                            results['failed_files'] += 1
                            
                        results['details'].append({
                            'file': str(file_path),
                            'verified': verify_result['verified'],
                            'error': verify_result.get('error')
                        })
                        continue
                    
                    # Check if original file exists
                    if not original_path.exists():
                        results['failed_files'] += 1
                        results['details'].append({
                            'file': str(file_path),
                            'verified': False,
                            'error': f"Original file {original_path} not found"
                        })
                        continue
                    
                    # Generate verification data for original file
                    original_data = self.generate_verification_data(original_path)
                    
                    # Verify against original
                    verify_result = self.verify_file(file_path, reference_data=original_data)
                    
                    if verify_result['verified']:
                        results['verified_files'] += 1
                    else:
                        results['failed_files'] += 1
                    
                    results['details'].append({
                        'file': str(file_path),
                        'original': str(original_path),
                        'verified': verify_result['verified'],
                        'error': verify_result.get('error')
                    })
                    
                except Exception as e:
                    logging.error(f"Error verifying {file_path}: {str(e)}")
                    results['failed_files'] += 1
                    results['details'].append({
                        'file': str(file_path),
                        'verified': False,
                        'error': str(e)
                    })
        
        # Calculate summary statistics
        results['success_rate'] = results['verified_files'] / max(results['total_files'], 1) * 100
        
        return results
    
    def _calculate_crc32(self, data):
        """Calculate CRC32 hash of data."""
        return format(binascii.crc32(data) & 0xFFFFFFFF, '08x')
    
    def _calculate_md5(self, data):
        """Calculate MD5 hash of data."""
        return hashlib.md5(data).hexdigest()
    
    def _calculate_sha1(self, data):
        """Calculate SHA1 hash of data."""
        return hashlib.sha1(data).hexdigest()
    
    def _calculate_sha256(self, data):
        """Calculate SHA256 hash of data."""
        return hashlib.sha256(data).hexdigest()