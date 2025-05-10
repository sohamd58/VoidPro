"""
Decompression module for the game file compression engine.
Handles decompression of files compressed with various algorithms.
"""

import os
import logging
import time
import zlib
import lzma
import bz2
import gzip
import json
from pathlib import Path
import shutil

# Import optional decompression libraries
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logging.warning("Zstandard (zstd) library not available. Will not be able to decompress zstd files.")

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False
    logging.warning("LZ4 library not available. Will not be able to decompress lz4 files.")

try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    logging.warning("Brotli library not available. Will not be able to decompress brotli files.")

class Decompressor:
    """Handles decompression of compressed game files."""
    
    def __init__(self):
        """Initialize the decompressor with supported algorithms."""
        self.decompressors = {
            'zlib': self._decompress_zlib,
            'gzip': self._decompress_gzip,
            'lzma': self._decompress_lzma,
            'bz2': self._decompress_bz2,
            'zstd': self._decompress_zstd,
            'lz4': self._decompress_lz4,
            'brotli': self._decompress_brotli
        }
        
        # Mapping of file extensions to compression types (for when no metadata is available)
        self.extension_to_type = {
            '.gz': 'gzip',
            '.xz': 'lzma',
            '.bz2': 'bz2',
            '.zst': 'zstd',
            '.lz4': 'lz4',
            '.br': 'brotli',
            '.z': 'zlib'
        }
    
    def decompress_file(self, input_file, output_file, metadata=None):
        """
        Decompress a file using the appropriate algorithm.
        
        Args:
            input_file (Path): Path to the compressed file
            output_file (Path): Path to save the decompressed file
            metadata (dict, optional): Metadata containing compression information
            
        Returns:
            bool: True if decompression was successful
        """
        input_file = Path(input_file)
        output_file = Path(output_file)
        
        if not input_file.exists():
            raise FileNotFoundError(f"Input file {input_file} does not exist")
        
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # If no metadata is provided, try to determine compression type
        if metadata is None:
            compression_type = self._determine_compression_type(input_file)
        else:
            compression_type = metadata.get('compression_type')
            
        if not compression_type:
            raise ValueError(f"Could not determine compression type for {input_file}")
            
        # Check if we have a decompressor for this type
        if compression_type not in self.decompressors:
            raise ValueError(f"Unsupported compression type: {compression_type}")
            
        # Get the decompression function
        decompress_func = self.decompressors[compression_type]
        
        # Decompress the file
        start_time = time.time()
        try:
            decompress_func(input_file, output_file, metadata)
            elapsed = time.time() - start_time
            
            logging.info(f"Decompressed {input_file} ({compression_type}) in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            logging.error(f"Error decompressing {input_file}: {str(e)}")
            raise
    
    def _determine_compression_type(self, file_path):
        """
        Try to determine the compression type of a file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            str: Compression type or None if could not determine
        """
        # Try to find a metadata file
        metadata_file = file_path.with_suffix('.gcmeta')
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    if 'compression_type' in metadata:
                        return metadata['compression_type']
            except Exception as e:
                logging.warning(f"Error reading metadata file {metadata_file}: {str(e)}")
        
        # Check file extension
        for ext, comp_type in self.extension_to_type.items():
            if file_path.name.endswith(ext):
                return comp_type
        
        # Try to determine by inspecting file header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)  # Read first 8 bytes
                
                # Check for common compression format signatures
                if header.startswith(b'\x1F\x8B'):
                    return 'gzip'
                elif header.startswith(b'\xFD7zXZ'):
                    return 'lzma'
                elif header.startswith(b'BZh'):
                    return 'bz2'
                elif header.startswith(b'\x28\xB5\x2F\xFD'):
                    return 'zstd'
                elif header.startswith(b'\x04\x22\x4D\x18'):
                    return 'lz4'
        except Exception as e:
            logging.warning(f"Error reading header of {file_path}: {str(e)}")
        
        # Fallback: assume zlib (most common)
        logging.warning(f"Could not determine compression type for {file_path}, assuming zlib")
        return 'zlib'
    
    def _decompress_zlib(self, input_file, output_file, metadata=None):
        """Decompress using zlib."""
        with open(input_file, 'rb') as f_in:
            compressed_data = f_in.read()
        
        decompressed_data = zlib.decompress(compressed_data)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(decompressed_data)
    
    def _decompress_gzip(self, input_file, output_file, metadata=None):
        """Decompress using gzip."""
        with gzip.open(input_file, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _decompress_lzma(self, input_file, output_file, metadata=None):
        """Decompress using lzma."""
        lzma_format = metadata.get('lzma_format', 'xz') if metadata else 'xz'
        
        with open(input_file, 'rb') as f_in:
            compressed_data = f_in.read()
        
        if lzma_format == 'xz':
            decompressed_data = lzma.decompress(compressed_data, format=lzma.FORMAT_XZ)
        else:
            decompressed_data = lzma.decompress(compressed_data)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(decompressed_data)
    
    def _decompress_bz2(self, input_file, output_file, metadata=None):
        """Decompress using bz2."""
        with open(input_file, 'rb') as f_in:
            compressed_data = f_in.read()
        
        decompressed_data = bz2.decompress(compressed_data)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(decompressed_data)
    
    def _decompress_zstd(self, input_file, output_file, metadata=None):
        """Decompress using zstandard."""
        if not ZSTD_AVAILABLE:
            raise ImportError("Zstandard library not available")
        
        decompressor = zstd.ZstdDecompressor()
        
        with open(input_file, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                decompressor.copy_stream(f_in, f_out)
    
    def _decompress_lz4(self, input_file, output_file, metadata=None):
        """Decompress using lz4."""
        if not LZ4_AVAILABLE:
            raise ImportError("LZ4 library not available")
        
        with open(input_file, 'rb') as f_in:
            compressed_data = f_in.read()
        
        decompressed_data = lz4.frame.decompress(compressed_data)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(decompressed_data)
    
    def _decompress_brotli(self, input_file, output_file, metadata=None):
        """Decompress using brotli."""
        if not BROTLI_AVAILABLE:
            raise ImportError("Brotli library not available")
        
        with open(input_file, 'rb') as f_in:
            compressed_data = f_in.read()
        
        decompressed_data = brotli.decompress(compressed_data)
        
        with open(output_file, 'wb') as f_out:
            f_out.write(decompressed_data)
