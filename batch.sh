#!/bin/sh

# Script to process joint value recordings and merge by joint number
# Usage: ./process_joints.sh

# Set paths
DATA_DIR="data"
OUTPUT_BASE="processed_output"

# Create output directory structure
mkdir -p "${OUTPUT_BASE}"

echo "Processing files in ${DATA_DIR}..."

# Process each CSV file in the trial directory
for csv_file in "${DATA_DIR}"/*.csv; do
    # Check if file exists (handles case where no CSV files found)
    if [ ! -f "$csv_file" ]; then
        echo "No CSV files found in ${DATA_DIR}"
        continue
    fi
    
    # Get base filename without path and extension
    base_name=$(basename "$csv_file" .csv)
    
    echo "Processing: $base_name"
    
    # Run the separate.py script
    python separate.py "$csv_file" --output-dir "${OUTPUT_BASE}/${base_name}_output"
    
    if [ $? -ne 0 ]; then
        echo "Error processing $csv_file"
        continue
    fi
done

echo "Individual processing complete. Starting merge process..."

# Create joint directories and move files
for joint_num in 1 2 3 4 5 6 7; do
    joint_dir="${OUTPUT_BASE}/joint_${joint_num}"
    mkdir -p "$joint_dir"
    
    echo "Organizing joint_${joint_num} files..."
    
    # Find all files with joint_n pattern and move them to joint directory
    files_found=0
    for output_dir in "${OUTPUT_BASE}"/*_output; do
        if [ -d "$output_dir" ]; then
            # Look for files matching the joint pattern
            for file in "$output_dir"/*joint_${joint_num}*; do
                if [ -f "$file" ]; then
                    # Get just the filename for the destination
                    filename=$(basename "$file")
                    # Copy file to joint directory (use cp to preserve original)
                    cp "$file" "$joint_dir/$filename"
                    echo "  Moved: $filename -> joint_${joint_num}/"
                    files_found=1
                fi
            done
        fi
    done
    
    if [ $files_found -eq 0 ]; then
        echo "  No files found for joint_${joint_num}"
        # Remove empty directory
        rmdir "$joint_dir" 2>/dev/null
    fi
done

echo "Processing complete!"
echo "Files organized by joint in: ${OUTPUT_BASE}/joint_*/"

