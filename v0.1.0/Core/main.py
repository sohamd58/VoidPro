#!/usr/bin/env python3
"""
Main entry point for the game file compression engine.
This script coordinates the file analysis, compression, and decompression processes.
"""

import os
import argparse
import logging
from pathlib import Path
import time

from compression_engine import CompressEngine
from utils import setup_logging, create_output_dir

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Game File Compression Engine')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress game files')
    compress_parser.add_argument('input_dir', type=str, help='Directory containing game files to compress')
    compress_parser.add_argument('-o', '--output_dir', type=str, help='Directory to store compressed files')
    compress_parser.add_argument('-d', '--detailed', action='store_true', help='Show detailed compression statistics')
    compress_parser.add_argument('--force', action='store_true', help='Force recompression of already compressed files')
    
    # Decompress command
    decompress_parser = subparsers.add_parser('decompress', help='Decompress game files')
    decompress_parser.add_argument('input_file', type=str, help='Compressed file or directory to decompress')
    decompress_parser.add_argument('-o', '--output_dir', type=str, help='Directory to store decompressed files')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze game files without compression')
    analyze_parser.add_argument('input_dir', type=str, help='Directory containing game files to analyze')
    
    return parser.parse_args()

def main():
    """Main function to execute compression or decompression based on arguments."""
    args = parse_arguments()
    setup_logging()
    
    engine = CompressEngine()
    
    if args.command == 'compress':
        input_path = Path(args.input_dir)
        if not input_path.exists():
            logging.error(f"Input directory {input_path} does not exist.")
            return
        
        if not input_path.is_dir():
            logging.error(f"Input path {input_path} is not a directory.")
            return
        
        output_dir = args.output_dir or f"{args.input_dir}_compressed"
        output_path = create_output_dir(output_dir)
        
        start_time = time.time()
        stats = engine.compress_directory(
            input_path, 
            output_path, 
            show_detailed=args.detailed,
            force=args.force
        )
        elapsed = time.time() - start_time
        
        if not stats:
            logging.error("Compression failed")
            return
            
        logging.info(f"Compression completed in {elapsed:.2f} seconds")
        logging.info(f"Total original size: {stats['original_size_bytes'] / (1024*1024):.2f} MB")
        logging.info(f"Total compressed size: {stats['compressed_size_bytes'] / (1024*1024):.2f} MB")
        logging.info(f"Overall compression ratio: {stats['overall_ratio']:.2f}x")
        logging.info(f"Space saved: {stats['space_saved_percentage']:.2f}%")
        
    elif args.command == 'decompress':
        input_path = Path(args.input_file)
        if not input_path.exists():
            logging.error(f"Input file/directory {input_path} does not exist.")
            return
        
        output_dir = args.output_dir or f"{os.path.splitext(args.input_file)[0]}_decompressed"
        if input_path.is_dir():
            output_dir = args.output_dir or f"{args.input_file}_decompressed"
        
        output_path = create_output_dir(output_dir)
        
        start_time = time.time()
        result = None
        try:
            if input_path.is_file():
                result = engine.decompress_file(input_path, output_path)
            else:
                result = engine.decompress_directory(input_path, output_path)
        except Exception as e:
            logging.error(f"Decompression failed: {str(e)}")
            return
            
        elapsed = time.time() - start_time
        
        if result is None:
            logging.error("Decompression failed")
            return
            
        logging.info(f"Decompression completed in {elapsed:.2f} seconds")
        
    elif args.command == 'analyze':
        input_path = Path(args.input_dir)
        if not input_path.exists():
            logging.error(f"Input directory {input_path} does not exist.")
            return
            
        if not input_path.is_dir():
            logging.error(f"Input path {input_path} is not a directory.")
            return
        
        stats = engine.analyze_directory(input_path)
        if not stats:
            logging.error("Analysis failed")
            return
            
        logging.info(f"Analysis complete. Found {stats['total_files']} files.")
        logging.info(f"File types distribution: {stats['file_types']}")
        logging.info(f"Recommended compression algorithms: {stats['recommendations']}")
    
    else:
        logging.error("No command specified. Use --help for usage information.")

if __name__ == "__main__":
    main()
