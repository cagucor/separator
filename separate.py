#!/usr/bin/env python3
"""
CSV Motion Segmentation Tool

This script takes a CSV file with timestamped robot joint data and:
1. Splits it into motion segments based on timestamp gaps
2. Creates separate CSV files for each segment
3. Identifies dominant columns (highest variation) for each segment
4. Saves segment metadata including dominant columns
"""

import pandas as pd
import numpy as np
import os
import argparse
from pathlib import Path
import json

def calculate_column_variation(df, exclude_columns=None):
    """
    Calculate variation metrics for each column.
    Uses coefficient of variation (std/mean) for ratio-scale data.
    """
    if exclude_columns is None:
        exclude_columns = []
    
    variations = {}
    
    for col in df.columns:
        if col in exclude_columns:
            continue
            
        # Skip non-numeric columns
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
            
        data = df[col].dropna()
        if len(data) == 0:
            continue
            
        # Calculate different variation metrics
        std_dev = data.std()
        
        # Range (max - min)
        range_val = data.max() - data.min()
        
        variations[col] = {
            'std': std_dev,
            'range': range_val,
            'combined_score': std_dev * range_val  # Combined metric
        }
    
    return variations

def find_dominant_columns(variations, top_n=3, method='combined_score'):
    """
    Find the columns with highest variation based on specified method.
    """
    if not variations:
        return []
    
    # Sort by the specified method
    sorted_cols = sorted(variations.items(), 
                        key=lambda x: x[1][method], 
                        reverse=True)
    
    # Return top N column names
    return [col for col, _ in sorted_cols[:top_n]]

def segment_data(df, timestamp_col, threshold=0.1):
    """
    Segment the data based on timestamp gaps.
    
    Args:
        df: DataFrame with data
        timestamp_col: Name of timestamp column
        threshold_seconds: Time gap threshold for creating new segment
    
    Returns:
        List of DataFrames, each representing a segment
    """
    # Ensure timestamp column exists
    if timestamp_col not in df.columns:
        raise ValueError(f"Timestamp column '{timestamp_col}' not found in data")
    
    # Sort by timestamp
    df = df.sort_values(timestamp_col).reset_index(drop=True)
    
    segments = []
    segment_start = 0

    for i in range(1, len(df)):
        # Calculate time difference (same units as timestamp)
        time_diff = df[timestamp_col].iloc[i] - df[timestamp_col].iloc[i-1]
        
        # If gap is larger than threshold, create new segment
        if time_diff > threshold:
            # Add current segment
            segment = df.iloc[segment_start:i].copy()
            if len(segment) > 1:  # Only add segments with more than 1 sample
                segments.append(segment)
            
            # Start new segment
            segment_start = i
    
    # Add final segment
    if segment_start < len(df):
        segment = df.iloc[segment_start:].copy()
        if len(segment) > 1:
            segments.append(segment)

    
    return segments

def save_segment_files(segments, output_dir, base_filename, timestamp_col):
    """
    Save each segment to a separate CSV file and create metadata.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        'total_segments': len(segments),
        'segments': []
    }
    
    for i, segment in enumerate(segments):
        # Create filename
        segment_filename = f"{base_filename}_segment_{i+1:03d}.csv"
        segment_path = output_path / segment_filename
        
        # Calculate segment statistics
        start_time = segment[timestamp_col].iloc[0]
        end_time = segment[timestamp_col].iloc[-1]
        
        if pd.api.types.is_datetime64_any_dtype(segment[timestamp_col]):
            duration = (end_time - start_time).total_seconds()
        else:
            duration = end_time - start_time
        
        # Calculate column variations
        variations = calculate_column_variation(segment, exclude_columns=[timestamp_col])
        
        # Find dominant columns
        dominant_cols = find_dominant_columns(variations, top_n=5)

        # Get only top N column variations for metadata
        top_variations = {}
        for col in dominant_cols:
            if col in variations:
                top_variations[col] = {k: float(v) for k, v in variations[col].items()}
        
        # Save segment to CSV
        segment.to_csv(segment_path, index=False)
        
        # Create segment metadata
        segment_info = {
            'segment_id': i + 1,
            'filename': segment_filename,
            'start_time': str(start_time),
            'end_time': str(end_time),
            'duration_seconds': duration,
            'sample_count': len(segment),
            'dominant_columns': dominant_cols,
            'column_variations': top_variations
        }
        
        metadata['segments'].append(segment_info)
        
        print(f"Segment {i+1}: {len(segment)} samples, {duration:.3f}s duration")
        print(f"  Dominant columns: {', '.join(dominant_cols)}")
        print(f"  Saved to: {segment_filename}")
    
    # Save metadata
    metadata_path = output_path / f"{base_filename}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nMetadata saved to: {metadata_path}")
    return metadata

def main():
    parser = argparse.ArgumentParser(description='Segment CSV data based on timestamp gaps')
    parser.add_argument('input_file', help='Input CSV file path')
    parser.add_argument('--timestamp-col', '-t', default='timestamp', 
                       help='Name of timestamp column (default: timestamp)')
    parser.add_argument('--threshold', '-th', type=float, default=0.1,
                       help='Time gap threshold in seconds (default: 0.1)')
    parser.add_argument('--output-dir', '-o', default='segments',
                       help='Output directory for segment files (default: segments)')

    args = parser.parse_args()
    
    # Read input file
    try:
        df = pd.read_csv(args.input_file)
        print(f"Loaded {len(df)} rows from {args.input_file}")
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Extract base filename
    base_filename = Path(args.input_file).stem
    
    # Segment the data
    try:
        segments = segment_data(df, args.timestamp_col, args.threshold)
        print(f"Found {len(segments)} motion segments")
    except Exception as e:
        print(f"Error segmenting data: {e}")
        return
    
    if not segments:
        print("No segments found. Try adjusting the threshold.")
        return
    
    # Save segments
    try:
        metadata = save_segment_files(segments, args.output_dir, base_filename, args.timestamp_col)
        print(f"\nProcessing complete! Created {len(segments)} segment files.")
    except Exception as e:
        print(f"Error saving segments: {e}")
        return

if __name__ == "__main__":
    main()

# Example usage:
# python segment_csv.py robot_data.csv --timestamp-col timestamp --threshold 0.2 --output-dir motion_segments
