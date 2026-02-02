# MonST3R Test Run Status - Rerun

**Started:** February 1, 2026, ~10:57  
**Status:** 🟢 **RUNNING**

---

## Test Configuration

- **Input:** `demo_data/lady-running/` (65 images)
- **Output:** `demo_tmp/lady-running/`
- **Mode:** Non-batchified (memory-efficient)
- **Environment:** `monst3r` conda environment
- **Process ID:** 726640

---

## Progress

### ✅ Completed Steps

1. **Model Loading** ✅
   - Model loaded from Hugging Face automatically
   - Encoder parameters frozen
   - ⚠️ Using slow PyTorch version of RoPE2D (CUDA version not compiled)

2. **Image Loading** ✅
   - All 65 images loaded successfully
   - Images resized from 854x480 to 512x288
   - Found 65 images total

3. **Inference** 🟡
   - Currently running: ~50% complete (19/38 batches)
   - Processing speed: ~1.23 it/s
   - Estimated time remaining: ~15 seconds

### 🔄 Current Status

- **Inference Progress:** 19/38 batches completed (~50%)
- **Processing Speed:** ~1.23 it/s
- **Memory Usage:** ~0.7% RAM
- **CPU Usage:** High (133%)
- **Runtime:** ~58 seconds

---

## Next Steps (After Inference)

1. Flow precomputation (~23 seconds)
2. Global optimization (~5-10 minutes)
3. Output file generation

---

## Monitoring

**Log File:** `/root/monst3r/demo_run.log`

**Check Progress:**
```bash
tail -f /root/monst3r/demo_run.log
```

**Check Process:**
```bash
ps aux | grep demo.py
```

**Check Output (when complete):**
```bash
ls -lh /root/monst3r/demo_tmp/lady-running/
```

---

## Expected Output Files

After completion, the following files will be generated in `demo_tmp/lady-running/`:

- `pred_traj.txt` - Camera trajectory
- `pred_intrinsics.txt` - Camera intrinsics
- `depth_maps/` - Depth maps for each frame
- `dynamic_masks/` - Dynamic segmentation masks
- `conf_maps/` - Confidence maps
- `init_conf_maps/` - Initial confidence maps
- `rgb_imgs/` - RGB images
- `*.glb` - 3D model file

---

## Notes

- SAM2 checkpoint has been fixed (857MB valid file)
- Process is running smoothly
- No errors encountered so far
- Estimated total time: ~10-15 minutes
