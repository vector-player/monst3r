# Downloads Directory Check Results

**Date:** February 1, 2026

## Files Found in /root/Downloads/

### ✅ Already in Project (Symlinks Found)
1. **SAM2 Checkpoint**
   - Location: `/root/Downloads/sam2.1_hiera_large.pt`
   - Status: ✅ Already copied to `/root/monst3r/third_party/sam2/checkpoints/`
   - Size: ~927KB

2. **RAFT Tartan Model**
   - Location: `/root/Downloads/Tartan-C-T-TSKH-spring540x960-M.pth`
   - Status: ✅ Already copied to `/root/monst3r/third_party/RAFT/models/`
   - Size: Symlinked

### 🔍 Potential MonST3R Model (Unverified)
3. **model.safetensors**
   - Location: `/root/Downloads/model.safetensors`
   - Size: **2.2GB** (reasonable size for large model)
   - Format: Safetensors (Hugging Face format)
   - Status: ⚠️ **NEEDS VERIFICATION**
   - Note: MonST3R typically uses `.pth` format, but Hugging Face models may use `.safetensors`

### ❌ Not Found
- **MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth** - Main checkpoint not found in Downloads

### Other Files (Unrelated)
- `lasa_depth.zip` (5.1GB) - Unrelated project
- `foundationpose/` directory - Unrelated project

---

## Recommendations

### Option 1: Try Using model.safetensors
The `model.safetensors` file (2.2GB) might be the MonST3R model in Hugging Face format. You can try:

```bash
# Test if Hugging Face can load it
cd /root/monst3r
python -c "from dust3r.model import AsymmetricCroCo3DStereo; model = AsymmetricCroCo3DStereo.from_pretrained('/root/Downloads/model.safetensors')"
```

**Note:** The model loading code uses `torch.load()` for local `.pth` files, but Hugging Face integration may handle `.safetensors` automatically.

### Option 2: Download Official Checkpoint
If `model.safetensors` doesn't work, download the official checkpoint:

```bash
cd /root/monst3r/data
bash download_ckpt.sh
```

Or manually from:
- Google Drive: https://drive.google.com/file/d/1Z1jO_JmfZj0z3bgMvCwqfUhyZ1bIbc9E/view?usp=sharing
- Hugging Face: `Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt`

---

## Next Steps

1. **Verify model.safetensors**: Check if it's the MonST3R model
2. **Copy if verified**: Move to `/root/monst3r/checkpoints/` if it's the correct model
3. **Download if not**: Use the download script or Hugging Face

---

## Summary

**Found in Downloads:**
- ✅ SAM2 checkpoint (already in project)
- ✅ RAFT Tartan model (already in project)
- ⚠️ `model.safetensors` (2.2GB, unverified - might be MonST3R)

**Missing:**
- ❌ `MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth` (official checkpoint name)
