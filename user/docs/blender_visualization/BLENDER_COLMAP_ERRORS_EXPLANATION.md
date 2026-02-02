# Blender COLMAP Import Errors Explanation

## Error 1: Parsing Error (`ValueError: invalid literal for int() with base 10: ''`)

### Error Details

```
Traceback (most recent call last):
  File "...\camera_animation_utility.py", line 373, in add_camera_animation
    cameras_sorted = sorted(
                     ^^^^^^^
  File "...\camera_animation_utility.py", line 375, in <lambda>
    key=lambda camera: int(
                       ^^^^
ValueError: invalid literal for int() with base 10: ''
```

### What's Happening

The Blender `photogrammetry_importer` addon is trying to create camera animation by:
1. Extracting frame numbers from image names in `images.txt`
2. Sorting cameras by these frame numbers
3. Creating keyframes for animation

**The Problem**: The addon's parsing logic is encountering an **empty string** (`''`) when trying to extract a frame number from an image name, and `int('')` fails.

### Root Cause

This happens when the image name in `images.txt` is:
- **Empty** (just whitespace or completely missing)
- **Malformed** (doesn't contain a parseable frame number)
- **Incorrectly formatted** (the addon expects a specific format to extract numbers)

### Why This Occurs

The Blender addon likely uses a regex or string parsing method to extract frame numbers from image names like:
- `image_0001.png` → extracts `0001` → converts to `int(0001)` = `1`
- `image_0025.png` → extracts `0025` → converts to `int(0025)` = `25`

If the image name is empty or doesn't match the expected pattern, the extraction returns an empty string, causing the error.

### Solution

The `convert_to_colmap.py` script has been updated to:
1. **Always ensure image names are not empty** - Multiple validation checks prevent empty strings
2. **Use sequential naming** - Always generates `image_XXXX.png` format where `XXXX` is a zero-padded number
3. **Validate before writing** - Checks that image names are valid before writing to `images.txt`

### How to Verify Fix

After running `convert_to_colmap.py`, check `images.txt`:
```bash
head -5 output_dir/images.txt
```

Should show:
```
1 0.123456 0.234567 ... 1 images/image_0001.png

2 0.123456 0.234567 ... 1 images/image_0002.png

```

**Key points**:
- Image names should **never be empty**
- Image names should follow pattern: `image_XXXX.png` or `images/image_XXXX.png`
- Each image line should be followed by an empty line (for points2D data)

---

## Error 2: Invalid COLMAP Model (`AssertionError: Invalid colmap model / workspace`)

### Error Details

```
File "...\colmap_file_handler.py", line 311, in parse_colmap_folder
    assert False, "Invalid colmap model / workspace"
           ^^^^^
AssertionError: Invalid colmap model / workspace
```

### What's Happening

The Blender addon is checking if the selected folder is a valid COLMAP model directory, and the validation is **failing**.

### Root Cause

The Blender addon expects a COLMAP model folder to contain **specific required files**:
- `cameras.txt` - Camera intrinsics
- `images.txt` - Image poses and metadata
- `points3D.txt` - 3D point cloud (optional but often expected)

**The error occurs when**:
1. One or more required files are **missing**
2. Files are in the **wrong location** (not in the selected folder)
3. Files are **malformed** or **empty**
4. The **folder structure** doesn't match COLMAP format

### Common Causes

1. **Wrong folder selected**: User selected `demo_tmp` instead of `demo_tmp/colmap_output`
   - The addon needs the folder containing `cameras.txt`, `images.txt`, `points3D.txt`
   - Not the parent directory

2. **Missing files**: Conversion didn't complete successfully
   - Check if all three files exist in the output directory

3. **Empty files**: Files exist but are empty or corrupted
   - `cameras.txt` should have camera definitions
   - `images.txt` should have image entries
   - `points3D.txt` can be empty (just header) but should exist

4. **File format issues**: Files don't match COLMAP format
   - Wrong headers
   - Incorrect number of columns
   - Invalid data types

### Solution

1. **Verify output directory structure**:
   ```bash
   ls -la output_dir/
   ```
   Should show:
   ```
   cameras.txt
   images.txt
   points3D.txt
   images/          # If --copy-images was used
   ```

2. **Check file contents**:
   ```bash
   head -5 output_dir/cameras.txt
   head -5 output_dir/images.txt
   head -5 output_dir/points3D.txt
   ```

3. **Select correct folder in Blender**:
   - In Blender's file browser, select the **COLMAP output directory**
   - This is the folder containing `cameras.txt`, `images.txt`, `points3D.txt`
   - **NOT** the parent directory (`demo_tmp`)
   - **NOT** a subdirectory (`images/`)

4. **Re-run conversion if needed**:
   ```bash
   python convert_to_colmap.py --input demo_tmp/lady-running --output demo_tmp/colmap_output --copy-images
   ```

### Expected Folder Structure

```
demo_tmp/
├── lady-running/          # MonST3R input
│   ├── pred_traj.txt
│   ├── pred_intrinsics.txt
│   └── rgb_imgs/
└── colmap_output/          # COLMAP output (SELECT THIS IN BLENDER)
    ├── cameras.txt         # Required
    ├── images.txt          # Required
    ├── points3D.txt        # Required
    └── images/             # Optional (if --copy-images used)
        ├── image_0001.png
        ├── image_0002.png
        └── ...
```

### How to Fix

1. **Ensure conversion completed**: Check that all three files were created
2. **Verify file format**: Check that files have correct headers and data
3. **Select correct folder**: In Blender, navigate to and select the folder containing `cameras.txt`, `images.txt`, `points3D.txt`
4. **Check file permissions**: Ensure files are readable

---

## Summary

### Error 1: Parsing Error
- **Cause**: Empty or malformed image names in `images.txt`
- **Fix**: Script now ensures all image names are valid and non-empty
- **Status**: Should be fixed in latest version of `convert_to_colmap.py`

### Error 2: Invalid Model Error
- **Cause**: Wrong folder selected or missing required files
- **Fix**: Select the correct COLMAP output folder (containing `cameras.txt`, `images.txt`, `points3D.txt`)
- **Status**: User action required - select correct folder in Blender

### Quick Checklist

- [ ] Run conversion with `--copy-images` flag
- [ ] Verify all three files exist: `cameras.txt`, `images.txt`, `points3D.txt`
- [ ] Check that `images.txt` contains valid image names (not empty)
- [ ] In Blender, select the folder containing these three files (not parent directory)
- [ ] Ensure image paths in `images.txt` are relative (e.g., `images/image_0001.png`)
