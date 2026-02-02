# Configuration Guide - Unified Path Management

## 🎯 Overview

The script now uses a **unified configuration system** with a single variable to control all paths. No more hard-coded paths scattered throughout the code!

## 📋 Configuration Variables

### Primary Configuration (Set These)

```python
MONST3R_ROOT_PATH = None  # Set to your path, or None for auto-detection
SEQUENCE_NAME = "lady-running"  # Your sequence name
```

### Derived Paths (Automatically Computed)

All other paths are automatically derived from the above:

```python
MONST3R_ROOT      # Detected or set from MONST3R_ROOT_PATH
DEMO_TMP_DIR      # {MONST3R_ROOT}/demo_tmp/{SEQUENCE_NAME}
GLB_FILE          # {DEMO_TMP_DIR}/scene.glb
TRAJ_FILE         # {DEMO_TMP_DIR}/pred_traj.txt
```

## 🔧 How to Configure

### Option 1: Auto-Detection (Default)

```python
MONST3R_ROOT_PATH = None  # Auto-detect
SEQUENCE_NAME = "lady-running"
```

The script will automatically search common locations:
- `D:\ProgramData\monst3r` (Windows)
- `C:\monst3r`, `D:\monst3r`
- `~/monst3r` (User home)
- `/root/monst3r` (Linux)
- Script's parent directories

### Option 2: Set Explicit Path

```python
# Windows
MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"
SEQUENCE_NAME = "lady-running"

# Linux
MONST3R_ROOT_PATH = "/root/monst3r"
SEQUENCE_NAME = "lady-running"
```

### Option 3: Different Sequence

```python
MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"
SEQUENCE_NAME = "my-sequence"  # Change sequence name
```

## 📁 Path Structure

```
{MONST3R_ROOT_PATH}/
└── demo_tmp/
    └── {SEQUENCE_NAME}/
        ├── scene.glb          ← GLB_FILE
        ├── pred_traj.txt       ← TRAJ_FILE
        └── pred_intrinsics.txt
```

## 🔍 Where Paths Are Used

All paths are defined in **one place** at the top of the script:

```python
# Lines 16-29: Configuration section
MONST3R_ROOT_PATH = None
SEQUENCE_NAME = "lady-running"

# Lines 104-113: Derived paths (automatically computed)
DEMO_TMP_DIR = os.path.join(MONST3R_ROOT, "demo_tmp", SEQUENCE_NAME)
GLB_FILE = os.path.join(DEMO_TMP_DIR, "scene.glb")
TRAJ_FILE = os.path.join(DEMO_TMP_DIR, "pred_traj.txt")
```

**No hard-coded paths anywhere else in the code!**

## ✅ Benefits

1. **Single Source of Truth**: Change path in one place, affects everywhere
2. **Easy Configuration**: Just set two variables
3. **No Hard-Coded Paths**: All paths derived from configuration
4. **Auto-Detection**: Works out of the box for common setups
5. **Clear Structure**: Easy to understand and modify

## 🚀 Quick Start

### For Most Users (Auto-Detection)

```python
MONST3R_ROOT_PATH = None  # Already set!
SEQUENCE_NAME = "lady-running"  # Already set!
```

Just run the script - it will auto-detect paths!

### If Auto-Detection Fails

```python
MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"  # Your actual path
SEQUENCE_NAME = "lady-running"
```

## 📝 Examples

### Example 1: Windows Default Location

```python
MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"
SEQUENCE_NAME = "lady-running"
```

Results in:
- `DEMO_TMP_DIR = D:\ProgramData\monst3r\demo_tmp\lady-running`
- `GLB_FILE = D:\ProgramData\monst3r\demo_tmp\lady-running\scene.glb`

### Example 2: Different Sequence

```python
MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"
SEQUENCE_NAME = "my-test-sequence"
```

Results in:
- `DEMO_TMP_DIR = D:\ProgramData\monst3r\demo_tmp\my-test-sequence`
- `GLB_FILE = D:\ProgramData\monst3r\demo_tmp\my-test-sequence\scene.glb`

### Example 3: Linux Path

```python
MONST3R_ROOT_PATH = "/home/user/monst3r"
SEQUENCE_NAME = "lady-running"
```

Results in:
- `DEMO_TMP_DIR = /home/user/monst3r/demo_tmp/lady-running`
- `GLB_FILE = /home/user/monst3r/demo_tmp/lady-running/scene.glb`

## 🔄 Migration from Old Version

If you were using the old version with hard-coded paths:

**Old way:**
```python
DEMO_TMP_DIR = r"D:\ProgramData\monst3r\demo_tmp\lady-running"
```

**New way:**
```python
MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"
SEQUENCE_NAME = "lady-running"
```

## ⚠️ Troubleshooting

### Path Not Found?

1. **Check MONST3R_ROOT_PATH:**
   ```python
   print(f"MONST3R_ROOT: {MONST3R_ROOT}")
   print(f"DEMO_TMP_DIR: {DEMO_TMP_DIR}")
   ```

2. **Set Explicit Path:**
   ```python
   MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"  # Your actual path
   ```

3. **Verify Files Exist:**
   ```python
   import os
   print(os.path.exists(GLBFILE))
   ```

### Wrong Sequence?

Change `SEQUENCE_NAME`:
```python
SEQUENCE_NAME = "your-sequence-name"
```

## 📚 Related Files

- `blender_import_monst3r.py` - Main script with unified configuration
- `BLENDER_QUICK_START.md` - Quick start guide
- `BLENDER_VISUALIZATION_GUIDE.md` - Full documentation

---

**Last Updated:** After refactoring to unified configuration system
