"""
Utility functions for the game file compression engine.
"""

import os
import logging
import sys
from pathlib import Path
import shutil

def setup_logging(level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_file_size(file_path):
    """
    Get size of a file in bytes.
    
    Args:
        file_path (Path): Path to the file
        
    Returns:
        int: File size in bytes
    """
    return Path(file_path).stat().st_size

def calculate_compression_ratio(original_size, compressed_size):
    """
    Calculate compression ratio.
    
    Args:
        original_size (int): Original file size in bytes
        compressed_size (int): Compressed file size in bytes
        
    Returns:
        float: Compression ratio (original_size / compressed_size)
    """
    if compressed_size == 0:
        return float('inf')  # Avoid division by zero
    return original_size / compressed_size

def calculate_space_saved(original_size, compressed_size):
    """
    Calculate percentage of space saved.
    
    Args:
        original_size (int): Original file size in bytes
        compressed_size (int): Compressed file size in bytes
        
    Returns:
        float: Percentage of space saved
    """
    if original_size == 0:
        return 0.0
    return 100 * (1 - compressed_size / original_size)

def format_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_file_extension(file_path):
    """
    Get the extension of a file.
    
    Args:
        file_path (Path): Path to the file
        
    Returns:
        str: File extension (lowercase, with dot)
    """
    return os.path.splitext(file_path)[1].lower()

def create_output_dir(output_dir):
    """
    Create output directory if it doesn't exist.
    
    Args:
        output_dir (str or Path): Directory path to create
        
    Returns:
        Path: Path object of the created directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path

def clean_directory(directory):
    """
    Clean (remove and recreate) a directory.
    
    Args:
        directory (str or Path): Directory to clean
        
    Returns:
        Path: Path object of the cleaned directory
    """
    directory = Path(directory)
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def get_relative_path(file_path, base_dir):
    """
    Get path relative to base directory.
    
    Args:
        file_path (Path): Full path to file
        base_dir (Path): Base directory
        
    Returns:
        Path: Relative path
    """
    return file_path.relative_to(base_dir)

def copy_directory_structure(source_dir, target_dir):
    """
    Copy directory structure (without files) from source to target.
    
    Args:
        source_dir (Path): Source directory
        target_dir (Path): Target directory
    """
    source_dir = Path(source_dir)
    target_dir = Path(target_dir)
    
    # Create the target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Walk through the source directory
    for root, dirs, _ in os.walk(source_dir):
        # Get the relative path from source_dir
        rel_path = Path(root).relative_to(source_dir)
        
        # Create the same directory structure in target_dir
        for dir_name in dirs:
            (target_dir / rel_path / dir_name).mkdir(parents=True, exist_ok=True)

def is_binary_file(file_path, sample_size=8192):
    """
    Check if a file is binary.
    
    Args:
        file_path (Path): Path to the file
        sample_size (int): Number of bytes to sample
        
    Returns:
        bool: True if the file is likely binary
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(sample_size)
        # Check for null bytes and high concentration of non-printable characters
        return b'\x00' in chunk or sum(1 for b in chunk if b < 32 and b != 9 and b != 10 and b != 13) > len(chunk) * 0.3
    except Exception:
        return True  # If we can't read the file, assume it's binary
