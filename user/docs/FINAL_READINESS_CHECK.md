# MonST3R Final Readiness Check

**Date:** February 1, 2026  
**Status:** ⚠️ **PARTIALLY READY** - Main checkpoint missing, some dependency issues

---

## ✅ Available Components

### 1. Demo Dataset
- **Location:** `/root/monst3r/demo_data/lady-running/`
- **Status:** ✅ **READY**
- **Count:** 65 images (00000.jpg to 00064.jpg)
- **Usage:** Ready for testing

### 2. RAFT Models
- **Location:** `/root/monst3r/third_party/RAFT/models/`
- **Status:** ✅ **READY** (All models copied from Downloads)
- **Files:**
  - ✅ `raft-things.pth` (21M)
  - ✅ `raft-sintel.pth` (21M)
  - ✅ `raft-kitti.pth` (21M)
  - ✅ `raft-chairs.pth` (21M)
  - ✅ `raft-small.pth` (3.9M)
  - ✅ `Tartan-C-T-TSKH-spring540x960-M.pth` (symlink)

### 3. SAM2 Model
- **Location:** `/root/monst3r/third_party/sam2/checkpoints/sam2.1_hiera_large.pt`
- **Status:** ✅ **READY**
- **Size:** 907KB

### 4. Core Dependencies
- **PyTorch:** ✅ 2.8.0+cu128 (installed)
- **Torchvision:** ✅ 0.23.0+cu128 (installed)
- **Gradio:** ⚠️ 4.29.0 (installed but has compatibility issue with huggingface_hub)
- **HuggingFace Hub:** ⚠️ 1.1.2 (installed but version mismatch with Gradio)

---

## ❌ Missing/Issues

### 1. Main MonST3R Checkpoint (CRITICAL)
- **Expected:** `/root/monst3r/checkpoints/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth`
- **Status:** ❌ **MISSING**
- **Impact:** Cannot run inference without this
- **Workaround:** Code can load from Hugging Face automatically if local file doesn't exist
- **Download:** 
  - Google Drive: https://drive.google.com/file/d/1Z1jO_JmfZj0z3bgMvCwqfUhyZ1bIbc9E/view?usp=sharing
  - Hugging Face: `Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt`

### 2. Python Dependencies (MODERATE)
- **Missing:** `evo` module
- **Impact:** Blocks model import (but may not block inference if model loads)
- **Fix:** `pip install evo`
- **Note:** Only needed for trajectory evaluation, may be optional for basic inference

### 3. Dependency Compatibility Issue (MODERATE)
- **Issue:** Gradio 4.29.0 incompatible with huggingface_hub 1.1.2
- **Error:** `ImportError: cannot import name 'HfFolder' from 'huggingface_hub'`
- **Impact:** Blocks demo.py from running
- **Fix:** Upgrade huggingface_hub: `pip install --upgrade huggingface_hub>=0.22`

---

## 🔍 Code Analysis

### Model Loading Strategy
The `demo.py` script (lines 391-396) has a fallback mechanism:
```python
if args.weights is not None and os.path.exists(args.weights):
    weights_path = args.weights
else:
    weights_path = args.model_name  # Falls back to Hugging Face model name
```

**This means:** If the local checkpoint doesn't exist, it will automatically try to load from Hugging Face (`Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt`).

### Import Issue
The `evo` import error occurs during module import, which blocks testing. However, this might not block actual inference if:
1. The model loads successfully (via Hugging Face)
2. The inference path doesn't use `vo_eval` functions

---

## 📋 Action Items for Test Run

### Step 1: Fix Dependencies
```bash
cd /root/monst3r
pip install --upgrade huggingface_hub>=0.22
pip install evo
pip install -r requirements.txt  # Install any other missing packages
```

### Step 2: Test Model Loading (Optional - will auto-download)
The code will automatically download from Hugging Face if local checkpoint is missing:
```bash
cd /root/monst3r
python -c "
import sys
sys.path.insert(0, '.')
# Workaround: temporarily comment out evo import
from dust3r.model import AsymmetricCroCo3DStereo
model = AsymmetricCroCo3DStereo.from_pretrained('Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt')
print('Model loaded successfully')
"
```

### Step 3: Run Test
```bash
cd /root/monst3r
python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running
```

**Note:** The model will be downloaded from Hugging Face automatically if not present locally.

---

## 📊 Readiness Checklist

- [x] Demo dataset (65 images)
- [x] RAFT models (all 5 models + Tartan)
- [x] SAM2 checkpoint
- [x] PyTorch installed
- [ ] **Main MonST3R checkpoint** ⚠️ (can use Hugging Face fallback)
- [ ] **Dependencies fixed** ⚠️ (evo + huggingface_hub upgrade needed)
- [x] Code structure intact

---

## 🚀 Quick Fix Commands

```bash
# Fix dependencies
cd /root/monst3r
pip install --upgrade huggingface_hub>=0.22
pip install evo
pip install roma  # If missing

# Test run (will auto-download model from HF)
python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running --not_batchify
```

---

## Conclusion

**Current Status:** ⚠️ **NEARLY READY** - Just need dependency fixes

**Blockers:**
1. ❌ Missing local checkpoint (but has Hugging Face fallback)
2. ⚠️ Dependency compatibility issues (fixable)

**Estimated Time to Ready:** ~5 minutes (dependency installation)

**Recommendation:** Fix dependencies first, then test run. The model will download automatically from Hugging Face if needed.
