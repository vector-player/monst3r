# Fixing Blender COLMAP Import Issues

## 🔍 Problem Analysis

When importing COLMAP data into Blender using the `photogrammetry_importer` addon, you encountered:

1. **Image Not Found Warnings:**
   ```
   WARNING: Could not find image at D:\ProgramData\monst3r\demo_tmp\dynamic_mask_0.png
   ```

2. **Parsing Error:**
   ```
   ValueError: invalid literal for int() with base 10: ''
   ```

## 🎯 Root Causes

### Issue 1: Wrong Image Paths
- COLMAP `images.txt` references images like `dynamic_mask_0.png`
- Blender addon looks for them in `demo_tmp/` directory
- Actual images are in `demo_tmp/lady-running/` subdirectory
- **Solution**: Use `--copy-images` flag to copy images to output directory

### Issue 2: Non-Sequential Image Names
- Image names like `dynamic_mask_0.png`, `dynamic_mask_10.png` are not sequential
- Blender addon tries to parse frame numbers and fails
- **Solution**: Script now uses sequential naming (`image_0001.png`, `image_0002.png`)

### Issue 3: Image File Detection
- Script was finding mask files instead of RGB images
- **Solution**: Improved image detection prioritizes RGB images

## ✅ Fixes Applied

### 1. Improved Image Detection

The script now:
- **Priority 1**: Looks for `rgb_imgs/` directory
- **Priority 2**: Looks for `images/` directory  
- **Priority 3**: Filters out mask files from current directory
- **Priority 4**: Falls back to all images with proper sorting

### 2. Sequential Image Naming

All images in `images.txt` now use sequential names:
- `image_0001.png`
- `image_0002.png`
- `image_0003.png`
- etc.

This ensures Blender addon can parse frame numbers correctly.

### 3. Image Copying Option

New `--copy-images` flag:
- Copies images to `{output_dir}/images/` directory
- Renames them sequentially (`image_0001.png`, etc.)
- Updates `images.txt` to reference copied images
- Ensures Blender addon can find images

## 🚀 Usage

### Recommended: Copy Images

```bash
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap \
    --copy-images
```

This creates:
```
demo_tmp/colmap/
├── cameras.txt
├── images.txt          ← References images/image_0001.png, etc.
├── points3D.txt
└── images/             ← Images copied here with sequential names
    ├── image_0001.png
    ├── image_0002.png
    └── ...
```

### Without Copying (Images in Original Location)

```bash
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap
```

**Note**: Blender addon may not find images if they're in a subdirectory.

## 🔧 For Blender Import

### Option 1: Use Copied Images (Recommended)

1. Run converter with `--copy-images`:
   ```bash
   python convert_to_colmap.py --input demo_tmp/lady-running --output demo_tmp/colmap --copy-images
   ```

2. In Blender, import COLMAP:
   - Set model path: `demo_tmp/colmap/`
   - Set image path: `demo_tmp/colmap/images/` (or same as model path)
   - Images will be found automatically

### Option 2: Manual Image Path Setup

If you didn't use `--copy-images`:

1. Copy images manually to match `images.txt`:
   ```bash
   mkdir -p demo_tmp/colmap/images
   # Copy and rename images to match image_0001.png, image_0002.png, etc.
   ```

2. Or update Blender addon settings:
   - Set image directory to `demo_tmp/lady-running/`
   - But image names won't match (will still have warnings)

## 📋 File Structure After Fix

### With --copy-images:
```
demo_tmp/colmap/
├── cameras.txt          ← Camera parameters
├── images.txt           ← Image poses (references image_0001.png, etc.)
├── points3D.txt          ← 3D point cloud
└── images/              ← Images directory
    ├── image_0001.png   ← Sequential naming
    ├── image_0002.png
    └── ...
```

### images.txt Format (Fixed):
```
1 0.127983 0.902629 ... 1 image_0001.png
2 0.127698 0.906046 ... 2 image_0002.png
3 0.126218 0.910274 ... 3 image_0003.png
```

## ✅ Verification

After conversion, check:

1. **images.txt uses sequential names:**
   ```bash
   grep "image_" demo_tmp/colmap/images.txt | head -5
   ```

2. **Images exist (if --copy-images used):**
   ```bash
   ls demo_tmp/colmap/images/ | head -5
   ```

3. **Image count matches:**
   - Number of lines in `images.txt` = Number of images

## 🐛 Troubleshooting

### Still Getting "Image Not Found" Warnings?

1. **Check image paths in images.txt:**
   ```bash
   grep "image_" demo_tmp/colmap/images.txt | head -1
   ```

2. **Verify images exist:**
   - If using `--copy-images`: Check `{output}/images/` directory
   - If not: Check original input directory

3. **Set correct image path in Blender:**
   - Blender addon → Image directory → Set to `{output}/images/`

### Still Getting Parsing Errors?

1. **Check image names are sequential:**
   ```bash
   grep "^[0-9]" demo_tmp/colmap/images.txt | awk '{print $NF}' | head -5
   ```
   Should show: `image_0001.png`, `image_0002.png`, etc.

2. **Re-run with --copy-images:**
   ```bash
   python convert_to_colmap.py --input demo_tmp/lady-running --output demo_tmp/colmap --copy-images
   ```

## 📝 Summary

**Key Changes:**
- ✅ Sequential image naming (`image_0001.png` format)
- ✅ `--copy-images` flag to copy images to output
- ✅ Improved image detection (prefers RGB over masks)
- ✅ Better error handling

**Recommended Workflow:**
```bash
# Always use --copy-images for Blender compatibility
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap \
    --copy-images
```

This ensures:
- Images are in the right location
- Image names are sequential and parseable
- Blender addon can find all images
- No parsing errors

---

**Last Updated:** After fixing Blender COLMAP import issues
