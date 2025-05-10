"""
File analyzer module for the game file compression engine.
Analyzes files to determine their characteristics and recommends
the most suitable compression algorithm.
"""

import os
import logging
import magic
import binascii
import re
from pathlib import Path
import numpy as np
from collections import Counter

class FileAnalyzer:
    """
    Analyzes files to determine their characteristics and the best
    compression algorithm to use.
    """
    
    def __init__(self):
        """Initialize the file analyzer with known file type patterns."""
        # File type categories and their common extensions
        self.file_categories = {
            'text': ['.txt', '.log', '.xml', '.json', '.html', '.css', '.js', '.lua', '.py', '.c', '.cpp', '.h', '.java'],
            'image': ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tga', '.webp'],
            'audio': ['.wav', '.mp3', '.ogg', '.flac', '.aac'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
            'executable': ['.exe', '.dll', '.so', '.bin'],
            'model': ['.obj', '.fbx', '.dae', '.blend', '.3ds', '.glb', '.gltf'],
            'shader': ['.glsl', '.hlsl', '.shader', '.vert', '.frag', '.comp'],
            'font': ['.ttf', '.otf', '.woff', '.woff2'],
            'database': ['.db', '.sqlite', '.sql'],
            'gamedata': ['.unity3d', '.asset', '.pak', '.uasset', '.dat', '.sav']
        }
        
        # Reversed lookup for extension to category
        self.extension_to_category = {}
        for category, extensions in self.file_categories.items():
            for ext in extensions:
                self.extension_to_category[ext] = category
        
        # Algorithm recommendations based on file types
        self.algorithm_recommendations = {
            'text': ['zstd', 'lzma', 'brotli', 'gzip'],
            'image': ['lz4', 'zstd', 'zlib'],     # Most images are already compressed
            'audio': ['lz4', 'zstd', 'zlib'],     # Audio compression depends on format
            'video': ['lz4', 'zlib'],             # Videos are already compressed
            'archive': ['zstd', 'lzma', 'lz4'],   # Archives may already be compressed
            'executable': ['zstd', 'lzma', 'bz2'], # Executables compress well with dictionary based algorithms
            'model': ['zstd', 'lzma', 'brotli'],  # 3D models often have repetitive structures
            'shader': ['zstd', 'lzma', 'brotli', 'gzip'], # Shader code is similar to text
            'font': ['brotli', 'zstd', 'lzma'],   # Fonts have specific patterns
            'database': ['zstd', 'lzma', 'bz2'],  # Databases often have repetitive structures
            'gamedata': ['zstd', 'lzma', 'brotli'] # Game-specific data varies
        }
        
        # Entropy thresholds for algorithm selection
        self.entropy_thresholds = {
            'low': 3.0,      # Low entropy (highly compressible)
            'medium': 5.0,   # Medium entropy
            'high': 7.0      # High entropy (less compressible)
        }
        
        # Fallback algorithm for unknown file types
        self.default_algorithm = 'zstd'
    
    def analyze_file(self, file_path):
        """
        Analyze a file to determine its characteristics.
        
        Args:
            file_path (Path): Path to the file to analyze
            
        Returns:
            dict: File characteristics including type, size, entropy, etc.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        file_size = file_path.stat().st_size
        extension = file_path.suffix.lower()
        
        # Basic file info
        file_info = {
            'path': str(file_path),
            'size': file_size,
            'extension': extension,
            'file_type': self._determine_file_type(file_path, extension)
        }
        
        # Skip very large files for detailed analysis
        if file_size > 100 * 1024 * 1024:  # 100 MB
            logging.info(f"File {file_path} is large ({file_size / 1024 / 1024:.2f} MB), skipping detailed analysis")
            file_info.update({
                'entropy': None,
                'byte_distribution': None,
                'is_compressible': True,
                'chunk_similarity': None
            })
            return file_info
        
        # For smaller files, perform more detailed analysis
        try:
            # Read the file content (limited to first 5MB for large files)
            with open(file_path, 'rb') as f:
                content = f.read(min(file_size, 5 * 1024 * 1024))
            
            # Calculate entropy and byte distribution
            entropy = self._calculate_entropy(content)
            byte_distribution = self._get_byte_distribution(content)
            
            # Determine if the file is likely already compressed
            is_compressible = self._is_likely_compressible(content, extension, entropy)
            
            # Analyze chunk similarity for appropriate-sized files
            chunk_similarity = None
            if 1024 <= file_size <= 10 * 1024 * 1024:  # Between 1KB and 10MB
                chunk_similarity = self._analyze_chunk_similarity(content)
            
            file_info.update({
                'entropy': entropy,
                'byte_distribution': byte_distribution,
                'is_compressible': is_compressible,
                'chunk_similarity': chunk_similarity
            })
            
        except Exception as e:
            logging.error(f"Error analyzing file {file_path}: {str(e)}")
            # Fall back to basic info if detailed analysis fails
            file_info.update({
                'entropy': None,
                'byte_distribution': None,
                'is_compressible': True,
                'chunk_similarity': None
            })
        
        return file_info
    
    def recommend_algorithm(self, file_info):
        """
        Recommend the best compression algorithm based on file analysis.
        
        Args:
            file_info (dict): File characteristics from analyze_file()
            
        Returns:
            str: Recommended compression algorithm
        """
        file_type = file_info['file_type']
        extension = file_info['extension']
        entropy = file_info.get('entropy')
        is_compressible = file_info.get('is_compressible', True)
        chunk_similarity = file_info.get('chunk_similarity')
        
        # If the file is likely already compressed, use fast algorithm
        if not is_compressible:
            return 'lz4'  # Fastest algorithm with minimal overhead
        
        # Get recommendation based on file type
        recommendations = self.algorithm_recommendations.get(file_type, [self.default_algorithm])
        
        # Adjust recommendation based on entropy if available
        if entropy is not None:
            if entropy < self.entropy_thresholds['low']:
                # Low entropy: Favor high compression ratio algorithms
                if 'lzma' in recommendations:
                    return 'lzma'
                elif 'brotli' in recommendations:
                    return 'brotli'
                elif 'zstd' in recommendations:
                    return 'zstd'
            elif entropy > self.entropy_thresholds['high']:
                # High entropy: Favor fast algorithms
                if 'lz4' in recommendations:
                    return 'lz4'
                elif 'zlib' in recommendations:
                    return 'zlib'
                elif 'zstd' in recommendations:
                    return 'zstd'
        
        # If we have chunk similarity data, use it to refine recommendation
        if chunk_similarity is not None:
            if chunk_similarity > 0.5:  # High similarity between chunks
                # Dictionary-based algorithms work well with repetitive data
                if 'zstd' in recommendations:
                    return 'zstd'
                elif 'brotli' in recommendations:
                    return 'brotli'
        
        # Use the first recommendation as default
        return recommendations[0]
    
    def _determine_file_type(self, file_path, extension):
        """
        Determine the file type category based on extension and content.
        
        Args:
            file_path (Path): Path to the file
            extension (str): File extension
            
        Returns:
            str: File type category
        """
        # Check if we can categorize by extension
        if extension in self.extension_to_category:
            return self.extension_to_category[extension]
        
        # If extension is unknown, try to determine type using libmagic
        try:
            mime_type = magic.from_file(str(file_path), mime=True)
            
            # Map MIME types to our categories
            if mime_type.startswith('text/'):
                return 'text'
            elif mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('video/'):
                return 'video'
            elif mime_type in ['application/x-executable', 'application/x-dosexec', 'application/x-sharedlib']:
                return 'executable'
            elif mime_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
                return 'archive'
            elif mime_type == 'application/octet-stream':
                # For binary data, try to guess by extension pattern
                if re.search(r'\.(model|mesh|obj|fbx)$', str(file_path), re.IGNORECASE):
                    return 'model'
                elif re.search(r'\.(shader|vert|frag)$', str(file_path), re.IGNORECASE):
                    return 'shader'
                elif re.search(r'\.(save|sav|dat|pak|asset)$', str(file_path), re.IGNORECASE):
                    return 'gamedata'
                
                # Default for binary data
                return 'gamedata'
        except Exception as e:
            logging.warning(f"Error determining file type for {file_path}: {str(e)}")
        
        # Default for unknown files
        return 'gamedata'
    
    def _calculate_entropy(self, data):
        """
        Calculate Shannon entropy of the data.
        
        Args:
            data (bytes): Binary data
            
        Returns:
            float: Entropy value (0-8)
        """
        if not data:
            return 0
        
        # Count byte occurrences
        byte_counts = Counter(data)
        data_len = len(data)
        
        # Calculate entropy
        entropy = 0
        for count in byte_counts.values():
            probability = count / data_len
            entropy -= probability * np.log2(probability)
        
        return entropy
    
    def _get_byte_distribution(self, data):
        """
        Get distribution of byte values in the data.
        
        Args:
            data (bytes): Binary data
            
        Returns:
            dict: Histogram of byte values
        """
        # Count occurrences of each byte value
        counts = Counter(data)
        
        # Convert to a simplified histogram (percentages)
        total = len(data)
        if total == 0:
            return {}
        
        histogram = {}
        for byte_val, count in counts.most_common(20):  # Top 20 most common bytes
            histogram[byte_val] = count / total * 100
        
        return histogram
    
    def _is_likely_compressible(self, data, extension, entropy):
        """
        Determine if a file is likely to be compressible.
        
        Args:
            data (bytes): Binary data
            extension (str): File extension
            entropy (float): Calculated entropy
            
        Returns:
            bool: True if the file is likely compressible
        """
        # Files with very high entropy are likely already compressed or encrypted
        if entropy and entropy > 7.9:
            return False
        
        # Check file extensions known to be already compressed
        compressed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.zip', '.rar', 
            '.7z', '.gz', '.xz', '.bz2', '.webp', '.webm', '.opus', '.aac'
        ]
        
        if extension in compressed_extensions:
            return False
        
        # Check for compression signatures in the data
        if len(data) >= 4:
            # Check for common compression format signatures
            signatures = [
                b'PK\x03\x04',  # ZIP
                b'Rar!\x1A',    # RAR
                b'\x1F\x8B',     # GZIP
                b'BZh',          # BZIP2
                b'\xFD7zXZ',     # XZ
                b'\x89PNG',      # PNG
                b'\xFF\xD8\xFF'  # JPEG
            ]
            
            for sig in signatures:
                if data.startswith(sig):
                    return False
        
        return True
    
    def _analyze_chunk_similarity(self, data, chunk_size=1024):
        """
        Analyze similarity between chunks of data.
        
        Args:
            data (bytes): Binary data
            chunk_size (int): Size of chunks to compare
            
        Returns:
            float: Similarity score (0-1)
        """
        if len(data) < chunk_size * 2:
            return 0
        
        # Split data into chunks
        chunks = [data[i:i+chunk_size] for i in range(0, len(data) - chunk_size, chunk_size)]
        if len(chunks) < 2:
            return 0
        
        # Sample a reasonable number of chunks for comparison
        max_chunks = min(20, len(chunks))
        sample_indices = np.linspace(0, len(chunks)-1, max_chunks, dtype=int)
        sample_chunks = [chunks[i] for i in sample_indices]
        
        # Calculate CRC32 for each chunk
        chunk_hashes = [binascii.crc32(chunk) for chunk in sample_chunks]
        
        # Count duplicate hashes
        hash_counts = Counter(chunk_hashes)
        duplicates = sum(count - 1 for count in hash_counts.values() if count > 1)
        
        # Calculate similarity score
        similarity = duplicates / (len(sample_chunks) - 1) if len(sample_chunks) > 1 else 0
        
        return similarity
