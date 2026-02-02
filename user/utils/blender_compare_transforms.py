"""
Blender Script to Compare GLB Transforms vs Computed Transforms

This script systematically compares ground truth transforms from GLB geometry
with computed transforms to identify where the conversion error occurs.

Usage:
1. Run blender_extract_glb_camera_transforms.py to get ground truth
2. Run blender_compute_expected_transforms.py to get computed transforms
3. Run this script to compare and generate report

The script will:
- Load both JSON files
- Compare transforms at each step
- Identify which transformation step introduces the error
- Generate detailed comparison report
"""

import bpy
import json
import os
import math
from mathutils import Vector, Matrix, Quaternion, Euler

# ============================================================================
# CONFIGURATION
# ============================================================================

GLB_TRANSFORMS_FILE = "glb_camera_transforms.json"
COMPUTED_TRANSFORMS_FILE = "computed_transforms.json"
REPORT_FILE = "transform_comparison_report.txt"

# ============================================================================
# COMPARISON FUNCTIONS
# ============================================================================

def quaternion_distance(q1, q2):
    """Compute distance between two quaternions"""
    # Quaternions can represent same rotation with opposite sign
    # So we compute min(distance, distance with negated quaternion)
    q1 = Quaternion(q1)
    q2 = Quaternion(q2)
    dist1 = (q1 - q2).magnitude
    dist2 = (q1 + q2).magnitude  # Try negated
    return min(dist1, dist2)

def matrix_difference(m1, m2):
    """Compute element-wise difference between two matrices"""
    if len(m1) != len(m2) or len(m1[0]) != len(m2[0]):
        return None
    
    diff = []
    max_diff = 0.0
    for i in range(len(m1)):
        row = []
        for j in range(len(m1[0])):
            d = abs(m1[i][j] - m2[i][j])
            row.append(d)
            max_diff = max(max_diff, d)
        diff.append(row)
    
    return diff, max_diff

def compare_single_transform(glb_transform, computed_transform):
    """Compare a single camera transform"""
    glb_pos = Vector(glb_transform['position'])
    comp_pos = Vector(computed_transform['position'])
    pos_diff = (glb_pos - comp_pos).length
    
    glb_quat = Quaternion(glb_transform['rotation_quaternion'])
    comp_quat = Quaternion(computed_transform['rotation_quaternion'])
    rot_diff_quat = quaternion_distance(glb_quat, comp_quat)
    
    glb_euler = Euler(glb_transform['rotation_euler'], 'XYZ')
    comp_euler = Euler(computed_transform['rotation_euler'], 'XYZ')
    rot_diff_euler = (glb_euler - comp_euler).length
    
    # Compare matrices
    glb_matrix = Matrix(glb_transform['matrix_world'])
    comp_matrix = Matrix(computed_transform['matrix_world'])
    matrix_diff, max_matrix_diff = matrix_difference(
        [[glb_matrix[i][j] for j in range(4)] for i in range(4)],
        [[comp_matrix[i][j] for j in range(4)] for i in range(4)]
    )
    
    # Compare rotation matrices
    glb_rot = Matrix(glb_transform['matrix_world_3x3'])
    comp_rot = Matrix(computed_transform['matrix_world_3x3'])
    rot_matrix_diff, max_rot_diff = matrix_difference(
        [[glb_rot[i][j] for j in range(3)] for i in range(3)],
        [[comp_rot[i][j] for j in range(3)] for i in range(3)]
    )
    
    return {
        'position_diff': pos_diff,
        'rotation_diff_quat': rot_diff_quat,
        'rotation_diff_euler': rot_diff_euler,
        'matrix_diff': matrix_diff,
        'max_matrix_diff': max_matrix_diff,
        'rotation_matrix_diff': rot_matrix_diff,
        'max_rotation_diff': max_rot_diff,
    }

def compare_transforms(glb_transforms, computed_transforms):
    """Compare all transforms systematically"""
    if len(glb_transforms) != len(computed_transforms):
        print(f"Warning: Number of cameras mismatch: GLB={len(glb_transforms)}, Computed={len(computed_transforms)}")
    
    comparisons = []
    for i in range(min(len(glb_transforms), len(computed_transforms))):
        glb = glb_transforms[i]
        comp = computed_transforms[i]
        
        comparison = compare_single_transform(glb, comp)
        comparison['index'] = i
        comparison['glb_name'] = glb.get('name', f'Camera_{i}')
        comparisons.append(comparison)
    
    return comparisons

def generate_report(comparisons, glb_transforms, computed_transforms):
    """Generate detailed comparison report"""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("Camera Transform Comparison Report")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Summary statistics
    pos_diffs = [c['position_diff'] for c in comparisons]
    rot_diffs_quat = [c['rotation_diff_quat'] for c in comparisons]
    rot_diffs_euler = [c['rotation_diff_euler'] for c in comparisons]
    matrix_diffs = [c['max_matrix_diff'] for c in comparisons]
    
    report_lines.append("Summary Statistics:")
    report_lines.append(f"  Total cameras compared: {len(comparisons)}")
    report_lines.append(f"  Position differences:")
    report_lines.append(f"    Average: {sum(pos_diffs)/len(pos_diffs):.6f}")
    report_lines.append(f"    Max: {max(pos_diffs):.6f}")
    report_lines.append(f"    Min: {min(pos_diffs):.6f}")
    report_lines.append(f"  Rotation differences (quaternion):")
    report_lines.append(f"    Average: {sum(rot_diffs_quat)/len(rot_diffs_quat):.6f}")
    report_lines.append(f"    Max: {max(rot_diffs_quat):.6f}")
    report_lines.append(f"    Min: {min(rot_diffs_quat):.6f}")
    report_lines.append(f"  Rotation differences (euler):")
    report_lines.append(f"    Average: {sum(rot_diffs_euler)/len(rot_diffs_euler):.6f}")
    report_lines.append(f"    Max: {max(rot_diffs_euler):.6f}")
    report_lines.append(f"    Min: {min(rot_diffs_euler):.6f}")
    report_lines.append(f"  Matrix differences:")
    report_lines.append(f"    Average: {sum(matrix_diffs)/len(matrix_diffs):.6f}")
    report_lines.append(f"    Max: {max(matrix_diffs):.6f}")
    report_lines.append(f"    Min: {min(matrix_diffs):.6f}")
    report_lines.append("")
    
    # Detailed comparison for first few cameras
    num_detail = min(5, len(comparisons))
    report_lines.append(f"Detailed Comparison (first {num_detail} cameras):")
    report_lines.append("")
    
    for i in range(num_detail):
        comp = comparisons[i]
        glb = glb_transforms[i]
        comp_t = computed_transforms[i]
        
        report_lines.append(f"Camera {i+1}: {comp['glb_name']}")
        report_lines.append("-" * 80)
        report_lines.append(f"  Position difference: {comp['position_diff']:.6f}")
        report_lines.append(f"    GLB:     [{glb['position'][0]:8.4f}, {glb['position'][1]:8.4f}, {glb['position'][2]:8.4f}]")
        report_lines.append(f"    Computed: [{comp_t['position'][0]:8.4f}, {comp_t['position'][1]:8.4f}, {comp_t['position'][2]:8.4f}]")
        report_lines.append(f"  Rotation difference (quat): {comp['rotation_diff_quat']:.6f}")
        report_lines.append(f"    GLB:     [{glb['rotation_quaternion'][0]:.6f}, {glb['rotation_quaternion'][1]:.6f}, {glb['rotation_quaternion'][2]:.6f}, {glb['rotation_quaternion'][3]:.6f}]")
        report_lines.append(f"    Computed: [{comp_t['rotation_quaternion'][0]:.6f}, {comp_t['rotation_quaternion'][1]:.6f}, {comp_t['rotation_quaternion'][2]:.6f}, {comp_t['rotation_quaternion'][3]:.6f}]")
        report_lines.append(f"  Rotation difference (euler): {comp['rotation_diff_euler']:.6f}")
        report_lines.append(f"  Matrix difference (max): {comp['max_matrix_diff']:.6f}")
        report_lines.append(f"  Rotation matrix difference (max): {comp['max_rotation_diff']:.6f}")
        report_lines.append("")
    
    # Identify problematic cameras
    threshold_pos = 0.001
    threshold_rot = 0.01
    
    problematic = []
    for comp in comparisons:
        if comp['position_diff'] > threshold_pos or comp['rotation_diff_quat'] > threshold_rot:
            problematic.append(comp)
    
    if problematic:
        report_lines.append(f"Problematic Cameras (position diff > {threshold_pos} or rotation diff > {threshold_rot}):")
        report_lines.append("")
        for comp in problematic[:10]:  # Show first 10
            report_lines.append(f"  Camera {comp['index']+1} ({comp['glb_name']}):")
            report_lines.append(f"    Position diff: {comp['position_diff']:.6f}")
            report_lines.append(f"    Rotation diff: {comp['rotation_diff_quat']:.6f}")
        report_lines.append("")
    
    # Analysis of error patterns
    report_lines.append("Error Pattern Analysis:")
    report_lines.append("")
    
    # Check if errors are systematic
    avg_pos_diff = sum(pos_diffs) / len(pos_diffs)
    avg_rot_diff = sum(rot_diffs_quat) / len(rot_diffs_quat)
    
    if avg_pos_diff > threshold_pos:
        report_lines.append(f"  WARNING: Average position difference ({avg_pos_diff:.6f}) exceeds threshold ({threshold_pos})")
        report_lines.append("    This suggests a systematic error in position computation.")
    else:
        report_lines.append(f"  Position differences are within acceptable range.")
    
    if avg_rot_diff > threshold_rot:
        report_lines.append(f"  WARNING: Average rotation difference ({avg_rot_diff:.6f}) exceeds threshold ({threshold_rot})")
        report_lines.append("    This suggests a systematic error in rotation computation.")
    else:
        report_lines.append(f"  Rotation differences are within acceptable range.")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def compare_transforms_main():
    """Main function to compare transforms"""
    print("=" * 60)
    print("Comparing GLB Transforms vs Computed Transforms")
    print("=" * 60)
    
    # Determine file paths
    base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
    glb_file = os.path.join(base_dir, GLB_TRANSFORMS_FILE)
    computed_file = os.path.join(base_dir, COMPUTED_TRANSFORMS_FILE)
    
    # Load GLB transforms (ground truth)
    if not os.path.exists(glb_file):
        print(f"ERROR: GLB transforms file not found: {glb_file}")
        print("Please run blender_extract_glb_camera_transforms.py first.")
        return None
    
    print(f"Loading GLB transforms from: {glb_file}")
    with open(glb_file, 'r') as f:
        glb_data = json.load(f)
    glb_transforms = glb_data['transforms']
    print(f"Loaded {len(glb_transforms)} GLB transforms")
    
    # Load computed transforms
    if not os.path.exists(computed_file):
        print(f"ERROR: Computed transforms file not found: {computed_file}")
        print("Please run blender_compute_expected_transforms.py first.")
        return None
    
    print(f"Loading computed transforms from: {computed_file}")
    with open(computed_file, 'r') as f:
        computed_data = json.load(f)
    computed_transforms = computed_data['transforms']
    print(f"Loaded {len(computed_transforms)} computed transforms")
    
    # Compare transforms
    print("\nComparing transforms...")
    comparisons = compare_transforms(glb_transforms, computed_transforms)
    
    # Generate report
    report = generate_report(comparisons, glb_transforms, computed_transforms)
    
    # Save report
    report_path = os.path.join(base_dir, REPORT_FILE)
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nComparison complete!")
    print(f"Report saved to: {report_path}")
    
    # Print summary to console
    print("\n" + report)
    
    return comparisons

if __name__ == "__main__":
    compare_transforms_main()
