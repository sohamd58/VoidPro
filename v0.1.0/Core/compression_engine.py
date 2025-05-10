"""
Compression Engine for game files.
This module provides the main functionality for analyzing, compressing,
and decompressing game files using optimal algorithms.
"""

import os
import logging
from pathlib import Path
import shutil
import json
from datetime import datetime
from collections import defaultdict

from file_analyzer import FileAnalyzer
from compression_algorithms import CompressionAlgorithms
from decompression import Decompressor
from utils import get_file_size, calculate_compression_ratio

class CompressEngine:
    """Main engine for compressing game files."""
    
    def __init__(self):
        """Initialize the compression engine."""
        self.analyzer = FileAnalyzer()
        self.compressor = CompressionAlgorithms()
        self.decompressor = Decompressor()
        self.metadata_extension = '.gcmeta'
        self.compressed_extension = '.gcmp'
    
    def compress_directory(self, input_dir, output_dir, show_detailed=False, force=False):
        """
        Compress all files in a directory using optimal algorithms.
        
        Args:
            input_dir (Path): Directory containing files to compress
            output_dir (Path): Directory to save compressed files
            show_detailed (bool): Whether to show detailed stats for each file
            force (bool): Whether to force recompression of already compressed files
            
        Returns:
            dict: Compression statistics
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        if not input_dir.exists() or not input_dir.is_dir():
            logging.error(f"Input directory {input_dir} does not exist or is not a directory")
            return {}
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Analyze the directory first to get file statistics
        analysis_stats = self.analyze_directory(input_dir)
        logging.info(f"Found {analysis_stats['total_files']} files to compress")
        
        # Statistics tracking
        stats = {
            'original_size_bytes': 0,
            'compressed_size_bytes': 0,
            'file_count': 0,
            'skipped_count': 0,
            'failed_count': 0,
            'algorithm_usage': defaultdict(int),
            'compression_by_type': defaultdict(lambda: {'original': 0, 'compressed': 0, 'count': 0}),
            'details': []
        }
        
        # Process all files in the directory (including subdirectories)
        for file_path in self._get_all_files(input_dir):
            relative_path = file_path.relative_to(input_dir)
            output_file = output_dir / relative_path.with_suffix(self.compressed_extension)
            output_meta = output_dir / relative_path.with_suffix(self.metadata_extension)
            
            # Create parent directories if they don't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Skip already compressed files
            if file_path.suffix == self.compressed_extension and not force:
                logging.info(f"Skipping already compressed file: {file_path}")
                stats['skipped_count'] += 1
                continue
                
            # Get original file size
            original_size = get_file_size(file_path)
            stats['original_size_bytes'] += original_size
            
            try:
                # Analyze file to determine optimal compression
                file_info = self.analyzer.analyze_file(file_path)
                best_algorithm = self.analyzer.recommend_algorithm(file_info)
                
                # Compress the file
                logging.info(f"Compressing {file_path} using {best_algorithm}")
                metadata = self.compressor.compress_file(
                    file_path, 
                    output_file, 
                    algorithm=best_algorithm
                )
                
                # Save metadata
                metadata.update({
                    'original_path': str(relative_path),
                    'original_size': original_size,
                    'compressed_size': get_file_size(output_file),
                    'compression_date': datetime.now().isoformat(),
                    'file_type': file_info['file_type'],
                    'file_extension': file_info['extension']
                })
                
                with open(output_meta, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Update statistics
                compressed_size = get_file_size(output_file)
                ratio = calculate_compression_ratio(original_size, compressed_size)
                stats['compressed_size_bytes'] += compressed_size
                stats['file_count'] += 1
                stats['algorithm_usage'][best_algorithm] += 1
                
                file_type = file_info['file_type']
                stats['compression_by_type'][file_type]['original'] += original_size
                stats['compression_by_type'][file_type]['compressed'] += compressed_size
                stats['compression_by_type'][file_type]['count'] += 1
                
                if show_detailed:
                    stats['details'].append({
                        'file': str(relative_path),
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'ratio': ratio,
                        'algorithm': best_algorithm,
                        'file_type': file_type
                    })
                    
                logging.info(f"Compressed {file_path} - Ratio: {ratio:.2f}x, Saved: {100 - (compressed_size / original_size * 100):.2f}%")
                
            except Exception as e:
                logging.error(f"Failed to compress {file_path}: {str(e)}")
                stats['failed_count'] += 1
        
        # Calculate overall compression ratio
        if stats['original_size_bytes'] > 0:
            stats['overall_ratio'] = stats['original_size_bytes'] / max(stats['compressed_size_bytes'], 1)
            stats['space_saved_percentage'] = 100 - (stats['compressed_size_bytes'] / stats['original_size_bytes'] * 100)
        else:
            stats['overall_ratio'] = 1.0
            stats['space_saved_percentage'] = 0.0
        
        # Save overall stats to the output directory
        with open(output_dir / 'compression_stats.json', 'w') as f:
            # Convert defaultdicts to regular dicts for JSON serialization
            serializable_stats = {
                **stats,
                'algorithm_usage': dict(stats['algorithm_usage']),
                'compression_by_type': {k: dict(v) for k, v in stats['compression_by_type'].items()}
            }
            json.dump(serializable_stats, f, indent=2)
        
        return stats
    
    def decompress_file(self, input_file, output_dir):
        """
        Decompress a single compressed file.
        
        Args:
            input_file (Path): Compressed file to decompress
            output_dir (Path): Directory to save decompressed file
        
        Returns:
            Path: Path to the decompressed file
        """
        input_file = Path(input_file)
        output_dir = Path(output_dir)
        
        if not input_file.exists():
            logging.error(f"Input file {input_file} does not exist")
            return None
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if the file is a compressed file
        if input_file.suffix != self.compressed_extension:
            logging.warning(f"File {input_file} is not a compressed file (expected suffix {self.compressed_extension})")
            # Copy the file as-is
            output_file = output_dir / input_file.name
            shutil.copy2(input_file, output_file)
            return output_file
        
        # Look for metadata file
        metadata_file = input_file.with_suffix(self.metadata_extension)
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            original_path = metadata.get('original_path')
            if original_path:
                output_file = output_dir / original_path
                output_file.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Fallback: remove the .gcmp extension
                output_file = output_dir / input_file.stem
        else:
            # No metadata, just remove the .gcmp extension
            output_file = output_dir / input_file.stem
            metadata = None
        
        try:
            # Decompress the file
            self.decompressor.decompress_file(input_file, output_file, metadata)
            logging.info(f"Decompressed {input_file} to {output_file}")
            return output_file
        except Exception as e:
            logging.error(f"Failed to decompress {input_file}: {str(e)}")
            return None
    
    def decompress_directory(self, input_dir, output_dir):
        """
        Decompress all compressed files in a directory.
        
        Args:
            input_dir (Path): Directory containing compressed files
            output_dir (Path): Directory to save decompressed files
        
        Returns:
            int: Number of successfully decompressed files
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        if not input_dir.exists() or not input_dir.is_dir():
            logging.error(f"Input directory {input_dir} does not exist or is not a directory")
            return 0
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        fail_count = 0
        
        # Process all compressed files in the directory (including subdirectories)
        for file_path in self._get_all_files(input_dir):
            if file_path.suffix == self.compressed_extension:
                try:
                    relative_path = file_path.relative_to(input_dir)
                    file_output_dir = output_dir / relative_path.parent
                    self.decompress_file(file_path, file_output_dir)
                    success_count += 1
                except Exception as e:
                    logging.error(f"Failed to decompress {file_path}: {str(e)}")
                    fail_count += 1
        
        logging.info(f"Decompression complete. Successfully decompressed {success_count} files. Failed: {fail_count}")
        return success_count
    
    def analyze_directory(self, directory):
        """
        Analyze all files in a directory to determine optimal compression algorithms.
        
        Args:
            directory (Path): Directory to analyze
            
        Returns:
            dict: Analysis statistics
        """
        directory = Path(directory)
        stats = {
            'total_files': 0,
            'total_size_bytes': 0,
            'file_types': defaultdict(int),
            'extensions': defaultdict(int),
            'recommendations': defaultdict(lambda: defaultdict(int))
        }
        
        for file_path in self._get_all_files(directory):
            stats['total_files'] += 1
            stats['total_size_bytes'] += get_file_size(file_path)
            
            try:
                file_info = self.analyzer.analyze_file(file_path)
                best_algorithm = self.analyzer.recommend_algorithm(file_info)
                
                file_type = file_info['file_type']
                extension = file_info['extension']
                
                stats['file_types'][file_type] += 1
                stats['extensions'][extension] += 1
                stats['recommendations'][file_type][best_algorithm] += 1
                
                logging.debug(f"File {file_path}: Type={file_type}, Best algorithm={best_algorithm}")
                
            except Exception as e:
                logging.error(f"Failed to analyze {file_path}: {str(e)}")
        
        # Convert defaultdicts to regular dicts for easier handling
        stats['file_types'] = dict(stats['file_types'])
        stats['extensions'] = dict(stats['extensions'])
        stats['recommendations'] = {k: dict(v) for k, v in stats['recommendations'].items()}
        
        return stats
    
    def _get_all_files(self, directory):
        """
        Get all files in a directory and its subdirectories.
        
        Args:
            directory (Path): Directory to scan
            
        Returns:
            list: List of Path objects for all files
        """
        for root, _, files in os.walk(directory):
            for file in files:
                # Skip metadata files
                if file.endswith(self.metadata_extension):
                    continue
                yield Path(root) / file
