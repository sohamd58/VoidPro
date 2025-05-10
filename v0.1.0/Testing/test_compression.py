"""
Unit tests for the game file compression engine.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
import random
import string

from compression_engine import CompressEngine
from file_analyzer import FileAnalyzer
from compression_algorithms import CompressionAlgorithms
from decompression import Decompressor
from utils import get_file_size, calculate_compression_ratio

class TestGameCompression:
    """Test suite for the game file compression engine."""
    
    @pytest.fixture(scope="class")
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.fixture(scope="class")
    def compression_engine(self):
        """Create a compression engine instance."""
        return CompressEngine()
    
    @pytest.fixture(scope="class")
    def file_analyzer(self):
        """Create a file analyzer instance."""
        return FileAnalyzer()
    
    @pytest.fixture(scope="class")
    def compressor(self):
        """Create a compression algorithms instance."""
        return CompressionAlgorithms()
    
    @pytest.fixture(scope="class")
    def decompressor(self):
        """Create a decompressor instance."""
        return Decompressor()
    
    @pytest.fixture(scope="class")
    def test_files(self, temp_dir):
        """Create various test files for compression testing."""
        files = {}
        
        # 1. Text file with repeating content
        text_path = temp_dir / "text_sample.txt"
        with open(text_path, 'w') as f:
            f.write("This is a sample text file with repeating content.\n" * 100)
        files['text'] = text_path
        
        # 2. Binary file with random data
        binary_path = temp_dir / "binary_sample.bin"
        with open(binary_path, 'wb') as f:
            f.write(os.urandom(10240))  # 10KB of random data
        files['binary'] = binary_path
        
        # 3. JSON file (structured text)
        json_path = temp_dir / "data_sample.json"
        with open(json_path, 'w') as f:
            f.write('{\n')
            for i in range(100):
                f.write(f'  "key_{i}": "value_{i}",\n')
            f.write('  "array": [\n')
            for i in range(100):
                f.write(f'    {i},\n')
            f.write('  ]\n')
            f.write('}\n')
        files['json'] = json_path
        
        # 4. XML file (structured text)
        xml_path = temp_dir / "data_sample.xml"
        with open(xml_path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<root>\n')
            for i in range(100):
                f.write(f'  <item id="{i}">\n')
                f.write(f'    <name>Item {i}</name>\n')
                f.write(f'    <value>{i * 10}</value>\n')
                f.write('  </item>\n')
            f.write('</root>\n')
        files['xml'] = xml_path
        
        # 5. Game data file simulation (binary with some patterns)
        gamedata_path = temp_dir / "game_data.dat"
        with open(gamedata_path, 'wb') as f:
            # Header with some magic bytes
            f.write(b'GAMEDATA\x01\x00')
            
            # Table of contents
            for i in range(10):
                f.write(f"Section_{i}".encode().ljust(16, b'\x00'))
                f.write((i * 1000).to_bytes(4, byteorder='little'))
                f.write((1000).to_bytes(4, byteorder='little'))
            
            # Sections with some repeating patterns and some random data
            for i in range(10):
                # Section header
                f.write(f"Section_{i}".encode().ljust(16, b'\x00'))
                
                # Section data with repeating patterns
                pattern = f"This is section {i} with some repeating data pattern {i}".encode()
                f.write(pattern * 20)
                
                # Some random data
                f.write(os.urandom(200))
        files['gamedata'] = gamedata_path
        
        # 6. Shader-like file
        shader_path = temp_dir / "sample.shader"
        with open(shader_path, 'w') as f:
            f.write("// Vertex Shader\n")
            f.write("attribute vec3 position;\n")
            f.write("attribute vec2 uv;\n")
            f.write("uniform mat4 modelViewMatrix;\n")
            f.write("uniform mat4 projectionMatrix;\n")
            f.write("varying vec2 vUv;\n\n")
            f.write("void main() {\n")
            f.write("    vUv = uv;\n")
            f.write("    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);\n")
            f.write("}\n\n")
            f.write("// Fragment Shader\n")
            f.write("precision highp float;\n")
            f.write("varying vec2 vUv;\n")
            f.write("uniform sampler2D diffuseMap;\n\n")
            f.write("void main() {\n")
            f.write("    gl_FragColor = texture2D(diffuseMap, vUv);\n")
            f.write("}\n")
        files['shader'] = shader_path
        
        # 7. Already compressed file (simulate a JPEG)
        jpeg_path = temp_dir / "image_sample.jpg"
        with open(jpeg_path, 'wb') as f:
            # JPEG header
            f.write(b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01')
            # Random data that will resist further compression
            f.write(os.urandom(10240))
        files['jpeg'] = jpeg_path
        
        return files
    
    def test_file_analyzer(self, file_analyzer, test_files):
        """Test file analysis capabilities."""
        # Test text file analysis
        text_info = file_analyzer.analyze_file(test_files['text'])
        assert text_info['file_type'] == 'text'
        assert text_info['is_compressible'] == True
        
        # Test binary file analysis
        binary_info = file_analyzer.analyze_file(test_files['binary'])
        assert binary_info['file_type'] in ['gamedata', 'binary', 'executable']
        
        # Test JSON file analysis
        json_info = file_analyzer.analyze_file(test_files['json'])
        assert json_info['file_type'] == 'text'
        assert json_info['is_compressible'] == True
        
        # Test already compressed file
        jpeg_info = file_analyzer.analyze_file(test_files['jpeg'])
        assert jpeg_info['file_type'] == 'image'
        assert jpeg_info.get('is_compressible', True) == False  # Should detect as not compressible
    
    def test_algorithm_recommendations(self, file_analyzer, test_files):
        """Test algorithm recommendation logic."""
        # Text files should use algorithms good for text
        text_info = file_analyzer.analyze_file(test_files['text'])
        text_algo = file_analyzer.recommend_algorithm(text_info)
        assert text_algo in ['zstd', 'lzma', 'brotli', 'gzip']
        
        # Binary files typically use different algorithms
        binary_info = file_analyzer.analyze_file(test_files['binary'])
        binary_algo = file_analyzer.recommend_algorithm(binary_info)
        assert binary_algo in ['zstd', 'lzma', 'lz4', 'zlib']
        
        # Already compressed files should use fast algorithms
        jpeg_info = file_analyzer.analyze_file(test_files['jpeg'])
        jpeg_algo = file_analyzer.recommend_algorithm(jpeg_info)
        assert jpeg_algo in ['lz4', 'zlib', 'zstd']  # Fast with minimal overhead
    
    def test_compression_and_decompression(self, compression_engine, temp_dir, test_files):
        """Test full compression and decompression cycle."""
        # Create output directories
        compressed_dir = temp_dir / "compressed"
        decompressed_dir = temp_dir / "decompressed"
        
        # Compress all test files
        stats = compression_engine.compress_directory(temp_dir, compressed_dir)
        
        # Verify compression results
        assert stats['file_count'] > 0
        assert stats['original_size_bytes'] > 0
        assert stats['compressed_size_bytes'] > 0
        assert stats['overall_ratio'] > 1.0  # Should achieve some compression
        
        # Check that compressed files exist
        assert (compressed_dir / "text_sample.txt.gcmp").exists()
        assert (compressed_dir / "binary_sample.bin.gcmp").exists()
        
        # Decompress the files
        decompressed_count = compression_engine.decompress_directory(compressed_dir, decompressed_dir)
        
        # Verify decompression
        assert decompressed_count > 0
        assert (decompressed_dir / "text_sample.txt").exists()
        assert (decompressed_dir / "binary_sample.bin").exists()
        
        # Verify content integrity for text file
        with open(test_files['text'], 'r') as original:
            original_content = original.read()
        
        with open(decompressed_dir / "text_sample.txt", 'r') as decompressed:
            decompressed_content = decompressed.read()
        
        assert original_content == decompressed_content
    
    def test_individual_algorithms(self, compressor, decompressor, temp_dir, test_files):
        """Test each compression algorithm individually."""
        for algo in compressor.get_available_algorithms():
            # Skip test for unavailable algorithms
            if not compressor.algorithms[algo]['available']:
                continue
                
            # Compress with this algorithm
            output_file = temp_dir / f"compressed_{algo}.bin"
            metadata = compressor.compress_file(test_files['text'], output_file, algorithm=algo)
            
            # Verify compression worked
            assert output_file.exists()
            assert get_file_size(output_file) > 0
            
            # Decompress
            decompressed_file = temp_dir / f"decompressed_{algo}.txt"
            decompressor.decompress_file(output_file, decompressed_file, metadata)
            
            # Verify content integrity
            with open(test_files['text'], 'r') as original:
                original_content = original.read()
            
            with open(decompressed_file, 'r') as decompressed:
                decompressed_content = decompressed.read()
            
            assert original_content == decompressed_content
            
            # Clean up
            output_file.unlink()
            decompressed_file.unlink()
    
    def test_compression_performance(self, compressor, test_files):
        """Test and compare performance of different compression algorithms."""
        for test_file in ['text', 'binary', 'json']:
            results = compressor.test_compression_algorithms(test_files[test_file])
            
            # Verify we got results
            assert len(results) > 0
            
            # Print results
            print(f"\nCompression results for {test_file}:")
            for result in results:
                print(f"  {result['algorithm']}: Ratio={result['ratio']:.2f}x, "
                      f"Size={result['compressed_size']/1024:.2f}KB, "
                      f"Speed={result['speed_mbps']:.2f}MB/s")
            
            # Verify the best algorithm has a ratio > 1
            assert results[0]['ratio'] > 1.0
    
    def test_error_handling(self, compression_engine, temp_dir):
        """Test error handling for invalid inputs."""
        # Test with non-existent input directory
        with pytest.raises(Exception):
            compression_engine.compress_directory(temp_dir / "nonexistent", temp_dir / "output")
        
        # Test with non-existent input file
        with pytest.raises(Exception):
            compression_engine.decompress_file(temp_dir / "nonexistent.file", temp_dir)
