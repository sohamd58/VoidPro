# Game File Compression Engine

A Python-based compression engine that analyzes game files and applies the optimal compression algorithm for each file type.

## Features

- Intelligent file analysis to determine optimal compression algorithms
- Support for multiple compression algorithms (zstd, lzma, bz2, gzip, zlib, lz4, brotli)
- File type detection and categorization
- Metadata tracking for compressed files
- Lossless compression with integrity verification
- Detailed compression statistics and benchmarking
- Command-line interface for easy integration

## Usage

### Compression

```bash
python main.py compress <input_directory> [options]
```

Options:
- `-o, --output_dir`: Specify output directory (default: input_directory_compressed)
- `-d, --detailed`: Show detailed compression statistics
- `--force`: Force recompression of already compressed files
- `--with-verification`: Generate verification data for integrity checking

### Decompression

```bash
python main.py decompress <input_file_or_directory> [options]
```

Options:
- `-o, --output_dir`: Specify output directory (default: input_file_decompressed)
- `--verify`: Verify integrity of decompressed files

### Analysis

```bash
python main.py analyze <input_directory>
```

Analyzes files without compression and shows recommended algorithms.

### Verification

```bash
python main.py verify <files_directory> [options]
```

Options:
- `-o, --original_dir`: Directory containing original files for comparison
- `-d, --detailed`: Show detailed verification results

## Requirements

- Python 3.11+
- Libraries: brotli, lz4, zstandard, python-magic, numpy

## Project Structure

- `main.py`: Main entry point and CLI interface
- `compression_engine.py`: Core engine that coordinates operations
- `file_analyzer.py`: Analyzes file characteristics
- `compression_algorithms.py`: Implements various compression algorithms
- `decompression.py`: Handles decompression of compressed files
- `file_verification.py`: Verifies file integrity
- `utils.py`: Utility functions

## Development Status

This engine currently handles files up to ~100MB efficiently and can handle files up to ~1GB at most. Future developements and optimizations are planned to make the engine capable of handling files of up to 300GB.


