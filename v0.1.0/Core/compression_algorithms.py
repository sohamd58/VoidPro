"""
Compression algorithms module for the game file compression engine.
Provides various compression algorithms and selects the optimal one for different file types.
"""

import os
import logging
import time
from pathlib import Path
import zlib
import lzma
import bz2
import gzip
import tempfile
import shutil
import json

# Import optional compression libraries
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logging.warning("Zstandard (zstd) library not available. Will not use zstd compression.")

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False
    logging.warning("LZ4 library not available. Will not use lz4 compression.")

try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    logging.warning("Brotli library not available. Will not use brotli compression.")

class CompressionAlgorithms:
    """Provides various compression algorithms for game files."""
    
    def __init__(self):
        """Initialize compression algorithms with default settings."""
        self.algorithms = {
            'zlib': {
                'available': True,
                'compress': self._compress_zlib,
                'level_range': (1, 9),
                'default_level': 6
            },
            'gzip': {
                'available': True,
                'compress': self._compress_gzip,
                'level_range': (1, 9),
                'default_level': 6
            },
            'lzma': {
                'available': True,
                'compress': self._compress_lzma,
                'level_range': (0, 9),
                'default_level': 6
            },
            'bz2': {
                'available': True,
                'compress': self._compress_bz2,
                'level_range': (1, 9),
                'default_level': 9
            },
            'zstd': {
                'available': ZSTD_AVAILABLE,
                'compress': self._compress_zstd,
                'level_range': (1, 22),
                'default_level': 3
            },
            'lz4': {
                'available': LZ4_AVAILABLE,
                'compress': self._compress_lz4,
                'level_range': (0, 16),
                'default_level': 9
            },
            'brotli': {
                'available': BROTLI_AVAILABLE,
                'compress': self._compress_brotli,
                'level_range': (0, 11),
                'default_level': 11
            }
        }
        
        # Fallback algorithm if the requested one is not available
        self.fallback_algorithm = 'zlib'
    
    def get_available_algorithms(self):
        """
        Get list of available compression algorithms.
        
        Returns:
            list: Names of available algorithms
        """
        return [name for name, info in self.algorithms.items() if info['available']]
    
    def compress_file(self, input_file, output_file, algorithm='zstd', level=None):
        """
        Compress a file using the specified algorithm.
        
        Args:
            input_file (Path): Path to the file to compress
            output_file (Path): Path to save the compressed file
            algorithm (str): Compression algorithm to use
            level (int, optional): Compression level
        
        Returns:
            dict: Metadata about the compression
        """
        input_file = Path(input_file)
        output_file = Path(output_file)
        
        if not input_file.exists():
            raise FileNotFoundError(f"Input file {input_file} does not exist")
        
        # Make sure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if algorithm is available
        if algorithm not in self.algorithms or not self.algorithms[algorithm]['available']:
            logging.warning(f"Algorithm {algorithm} is not available. Using {self.fallback_algorithm} instead.")
            algorithm = self.fallback_algorithm
        
        # Get compression function and default level
        compress_func = self.algorithms[algorithm]['compress']
        default_level = self.algorithms[algorithm]['default_level']
        
        # Use default level if none specified or if outside valid range
        if level is None:
            level = default_level
        else:
            level_range = self.algorithms[algorithm]['level_range']
            if level < level_range[0] or level > level_range[1]:
                logging.warning(f"Compression level {level} out of range for {algorithm}. Using default level {default_level}.")
                level = default_level
        
        # Compress the file
        start_time = time.time()
        try:
            metadata = compress_func(input_file, output_file, level)
            elapsed = time.time() - start_time
            
            # Add general metadata
            metadata.update({
                'algorithm': algorithm,
                'level': level,
                'original_size': input_file.stat().st_size,
                'compressed_size': output_file.stat().st_size,
                'compression_time': elapsed
            })
            
            # Calculate compression ratio
            original_size = metadata['original_size']
            compressed_size = metadata['compressed_size']
            if original_size > 0:
                metadata['compression_ratio'] = original_size / max(compressed_size, 1)
            else:
                metadata['compression_ratio'] = 1.0
            
            return metadata
            
        except Exception as e:
            logging.error(f"Error compressing {input_file} with {algorithm}: {str(e)}")
            # If compression fails, try with fallback algorithm
            if algorithm != self.fallback_algorithm:
                logging.info(f"Trying fallback algorithm {self.fallback_algorithm}")
                return self.compress_file(input_file, output_file, algorithm=self.fallback_algorithm)
            else:
                raise
    
    def _compress_zlib(self, input_file, output_file, level):
        """Compress using zlib."""
        with open(input_file, 'rb') as f_in:
            data = f_in.read()
        
        compressed = zlib.compress(data, level)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(compressed)
        
        return {
            'format_version': 1,
            'compression_type': 'zlib'
        }
    
    def _compress_gzip(self, input_file, output_file, level):
        """Compress using gzip."""
        with open(input_file, 'rb') as f_in:
            with gzip.open(output_file, 'wb', compresslevel=level) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return {
            'format_version': 1,
            'compression_type': 'gzip'
        }
    
    def _compress_lzma(self, input_file, output_file, level):
        """Compress using lzma."""
        filters = [
            {
                "id": lzma.FILTER_LZMA2,
                "preset": level
            }
        ]
        
        with open(input_file, 'rb') as f_in:
            data = f_in.read()
        
        compressed = lzma.compress(data, format=lzma.FORMAT_XZ, filters=filters)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(compressed)
        
        return {
            'format_version': 1,
            'compression_type': 'lzma',
            'lzma_format': 'xz'
        }
    
    def _compress_bz2(self, input_file, output_file, level):
        """Compress using bz2."""
        with open(input_file, 'rb') as f_in:
            data = f_in.read()
        
        compressed = bz2.compress(data, level)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(compressed)
        
        return {
            'format_version': 1,
            'compression_type': 'bz2'
        }
    
    def _compress_zstd(self, input_file, output_file, level):
        """Compress using zstandard."""
        if not ZSTD_AVAILABLE:
            raise ImportError("Zstandard library not available")
        
        compressor = zstd.ZstdCompressor(level=level)
        
        with open(input_file, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                compressor.copy_stream(f_in, f_out)
        
        return {
            'format_version': 1,
            'compression_type': 'zstd'
        }
    
    def _compress_lz4(self, input_file, output_file, level):
        """Compress using lz4."""
        if not LZ4_AVAILABLE:
            raise ImportError("LZ4 library not available")
        
        with open(input_file, 'rb') as f_in:
            data = f_in.read()
        
        compressed = lz4.frame.compress(data, compression_level=level)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(compressed)
        
        return {
            'format_version': 1,
            'compression_type': 'lz4'
        }
    
    def _compress_brotli(self, input_file, output_file, level):
        """Compress using brotli."""
        if not BROTLI_AVAILABLE:
            raise ImportError("Brotli library not available")
        
        with open(input_file, 'rb') as f_in:
            data = f_in.read()
        
        compressed = brotli.compress(data, quality=level)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(compressed)
        
        return {
            'format_version': 1,
            'compression_type': 'brotli'
        }
    
    def test_compression_algorithms(self, input_file):
        """
        Test all available compression algorithms on a file and return stats.
        
        Args:
            input_file (Path): Path to the file to test
            
        Returns:
            list: Compression results for each algorithm
        """
        input_file = Path(input_file)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file {input_file} does not exist")
        
        original_size = input_file.stat().st_size
        results = []
        
        # Create temporary directory for compressed files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            
            for algo_name, algo_info in self.algorithms.items():
                if not algo_info['available']:
                    continue
                
                output_file = temp_dir / f"{input_file.name}.{algo_name}"
                
                try:
                    start_time = time.time()
                    metadata = self.compress_file(input_file, output_file, algorithm=algo_name)
                    elapsed = time.time() - start_time
                    
                    compressed_size = output_file.stat().st_size
                    ratio = original_size / max(compressed_size, 1)
                    
                    results.append({
                        'algorithm': algo_name,
                        'original_size': original_size,
                        'compressed_size': compressed_size,
                        'ratio': ratio,
                        'time': elapsed,
                        'speed_mbps': (original_size / 1024 / 1024) / elapsed if elapsed > 0 else 0
                    })
                    
                except Exception as e:
                    logging.error(f"Error testing {algo_name}: {str(e)}")
        
        # Sort results by compression ratio (best first)
        results.sort(key=lambda x: x['ratio'], reverse=True)
        return results
