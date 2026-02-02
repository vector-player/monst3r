# SAM2 Checkpoint Fix

**Date:** February 1, 2026  
**Status:** ✅ **FIXED**

---

## Issue

The SAM2 checkpoint file in the project was corrupted:
- **Location:** `/root/monst3r/third_party/sam2/checkpoints/sam2.1_hiera_large.pt`
- **Size:** 907KB (corrupted/incomplete)
- **Expected:** ~857MB
- **Error:** `RuntimeError: PytorchStreamReader failed reading zip archive`

---

## Solution

Found valid checkpoint in `/root/Downloads/`:
- **Size:** 857MB ✅
- **Status:** Valid PyTorch checkpoint ✅
- **Verification:** Loads successfully with torch.load()

**Action Taken:**
1. Removed corrupted file
2. Copied valid file from Downloads to project location
3. Verified file loads correctly

---

## File Details

**Source:** `/root/Downloads/sam2.1_hiera_large.pt`
- Size: 857MB
- Format: PyTorch checkpoint (Zip archive)
- Status: Valid ✅

**Destination:** `/root/monst3r/third_party/sam2/checkpoints/sam2.1_hiera_large.pt`
- Size: 857MB ✅ (copied successfully)
- Status: Valid and verified ✅
- Verification: Loads successfully with torch.load() ✅

---

## Verification

```bash
# File size check
ls -lh /root/monst3r/third_party/sam2/checkpoints/sam2.1_hiera_large.pt
# Should show: 857M

# Load test
python -c "import torch; torch.load('third_party/sam2/checkpoints/sam2.1_hiera_large.pt', map_location='cpu')"
# Should load without errors
```

---

## Next Steps

The SAM2 checkpoint is now fixed. You can:
1. Re-run the test: `python demo.py --input demo_data/lady-running --output_dir demo_tmp --seq_name lady-running --not_batchify`
2. The test should now complete successfully without the SAM2 loading error

---

## Summary

✅ **SAM2 checkpoint fixed and verified**
✅ **Ready for test run**
