# MonST3R Test Run Readiness Report

**Date:** February 1, 2026  
**Status:** ⚠️ **PARTIALLY READY** - Main model checkpoint missing

## Summary

The MonST3R project is **partially ready** for a test run. The main model checkpoint is missing, but demo data and some supporting models are present.

---

## ✅ Available Components

### 1. Demo Dataset
- **Location:** `/root/monst3r/demo_data/lady-running/`
- **Status:** ✅ **READY**
- **Details:** Contains 65 images (00000.jpg to 00064.jpg)
- **Usage:** Can be used for testing with: `python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running`

### 2. RAFT Optical Flow Model
- **Location:** `/root/monst3r/third_party/RAFT/models/Tartan-C-T-TSKH-spring540x960-M.pth`
- **Status:** ✅ **READY**
- **Details:** Sea-RAFT checkpoint for optical flow computation (used in optimizer)
- **Size:** File exists (symlinked)

### 3. SAM2 Model
- **Location:** `/root/monst3r/third_party/sam2/checkpoints/sam2.1_hiera_large.pt`
- **Status:** ✅ **READY**
- **Details:** SAM2 checkpoint for segmentation (927KB)
- **Note:** May be optional depending on usage mode

---

## ❌ Missing Components

### 1. Main MonST3R Model Checkpoint
- **Expected Location:** `/root/monst3r/checkpoints/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth`
- **Status:** ❌ **MISSING** (but see potential alternative below)
- **Impact:** **CRITICAL** - Cannot run inference without this checkpoint
- **Download Options:**
  1. **Google Drive:** https://drive.google.com/file/d/1Z1jO_JmfZj0z3bgMvCwqfUhyZ1bIbc9E/view?usp=sharing
  2. **Hugging Face:** https://huggingface.co/Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt
  3. **Script:** Run `cd data && bash download_ckpt.sh`

### ⚠️ Potential Alternative Found in Downloads
- **Location:** `/root/Downloads/model.safetensors`
- **Size:** 2.2GB (reasonable for large model)
- **Status:** ⚠️ **UNVERIFIED** - May be MonST3R model in Hugging Face format
- **Note:** The code expects `.pth` format for local files. If this is the MonST3R model, it may need to be loaded via Hugging Face hub or converted.

### 2. Optional: RAFT Standard Models
- **Expected:** `third_party/RAFT/models/raft-things.pth` or `raft-sintel.pth`
- **Status:** ⚠️ **OPTIONAL** (Tartan model present)
- **Impact:** Low - The Tartan RAFT model is available and used by default
- **Note:** Some visualization code references `raft-things.pth`, but optimizer uses Tartan model

---

## 📋 Required Actions for Test Run

### Step 0: Install Missing Dependencies (if needed)
```bash
cd /root/monst3r
pip install -r requirements.txt
# Note: evo module may fail to import but is only needed for trajectory evaluation
```

### Step 0.5: Check Downloads Directory (Optional)
Found in `/root/Downloads/`:
- `model.safetensors` (2.2GB) - **May be MonST3R model** ⚠️
- `sam2.1_hiera_large.pt` - Already in project ✅
- `Tartan-C-T-TSKH-spring540x960-M.pth` - Already in project ✅

**To verify if model.safetensors is usable:**
```bash
# Try loading via Hugging Face (if it's from HF)
cd /root/monst3r
python -c "from dust3r.model import AsymmetricCroCo3DStereo; model = AsymmetricCroCo3DStereo.from_pretrained('Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt')"
```

### Step 1: Download Main Checkpoint (if model.safetensors doesn't work)
```bash
cd /root/monst3r/data
bash download_ckpt.sh
```

Or manually download from:
- Google Drive: https://drive.google.com/file/d/1Z1jO_JmfZj0z3bgMvCwqfUhyZ1bIbc9E/view?usp=sharing
- Hugging Face: `Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt`

### Step 2: Verify Checkpoint Location
After download, verify:
```bash
ls -lh /root/monst3r/checkpoints/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth
```

### Step 3: Run Test
```bash
cd /root/monst3r
python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running
```

---

## 🔍 Code Analysis

### Model Loading
- **Default checkpoint path:** `checkpoints/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth` (line 39 in `demo.py`)
- **Fallback:** Can use Hugging Face model name: `Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt`
- **Loading method:** `AsymmetricCroCo3DStereo.from_pretrained()` supports both local files and Hugging Face models

### Dependencies
- **RAFT:** Used for optical flow computation in optimizer (line 265 in `optimizer.py`)
- **SAM2:** Used for segmentation (may be optional)
- **Demo data:** 65 images in `demo_data/lady-running/` ready for testing

---

## 📊 Readiness Checklist

- [x] Demo dataset available (lady-running: 65 images)
- [x] RAFT model available (Tartan checkpoint)
- [x] SAM2 checkpoint available
- [ ] **Main MonST3R checkpoint** ⚠️ **REQUIRED**
- [x] Code structure intact
- [x] PyTorch installed (2.8.0+cu128)
- [x] Gradio installed (4.29.0)
- [x] HuggingFace Hub installed (1.1.2)
- [ ] **Python dependencies** ⚠️ **PARTIAL** (missing `evo`, `roma`, and others)

---

## 🚀 Quick Start After Downloading Checkpoint

Once the checkpoint is downloaded, you can immediately test with:

```bash
# Basic test run
python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running

# With memory-efficient optimization (lower VRAM)
python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running --not_batchify

# Real-time mode (feed-forward, faster but lower quality)
python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running --real_time
```

---

## 📝 Notes

1. **Memory Requirements:** 
   - Standard mode: ~33G VRAM for 65 frames
   - Non-batchified mode: ~23G VRAM
   - Real-time mode: Lower memory usage

2. **Hugging Face Fallback:** The code supports loading from Hugging Face if local file doesn't exist, but downloading locally is recommended for offline use.

3. **RAFT Models:** The optimizer uses the Tartan RAFT model by default, which is already present. The standard RAFT models (`raft-things.pth`, `raft-sintel.pth`) are only needed for specific visualization modes.

---

## Dependencies Status

### Installed ✅
- PyTorch: 2.8.0+cu128
- Torchvision: 0.23.0+cu128
- Gradio: 4.29.0
- HuggingFace Hub: 1.1.2

### Missing/Unverified ⚠️
- `evo` - Required for camera trajectory evaluation (may be optional for basic inference)
- `roma` - Required for inference
- Other packages from `requirements.txt` need verification

**Note:** The `evo` import error may not block basic inference, but should be installed for full functionality.

---

## Conclusion

**Current Status:** ⚠️ **2 critical items missing:**
1. Main MonST3R checkpoint (required for inference)
2. Some Python dependencies (may need installation)

**Action Required:** 
1. Install dependencies: `pip install -r requirements.txt`
2. Download the MonST3R checkpoint to proceed with testing

**Estimated Time to Ready:** ~10-15 minutes (depending on download speed and dependency installation)
