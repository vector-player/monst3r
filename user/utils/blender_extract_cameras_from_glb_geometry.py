"""
Blender Script to Extract Camera Objects from Imported GLB Geometry

This script analyzes the imported GLB geometry and extracts camera objects
from the camera cone meshes. It identifies camera geometries and creates
actual Blender camera objects at their positions.

Usage:
1. Import GLB file into Blender (File → Import → glTF 2.0)
2. Open Blender Scripting workspace
3. Open this script: File → Open → select this script
4. Run the script (Alt+P or click Run button)

The script will:
- Find camera cone geometries in the imported GLB
- Extract camera positions and orientations from cone meshes
- Create Blender camera objects matching the geometry
- Optionally create camera animation
"""

import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion, Euler
import math
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

CREATE_ANIMATION = True  # Create keyframe animation for cameras
CAMERA_COLLECTION_NAME = "Extracted_Cameras"  # Collection name for cameras
CONE_VERTEX_COUNT_THRESHOLD = 20  # Maximum vertices for a cone mesh (to identify camera geometry)
SORT_BY_POSITION = True  # Sort cameras by position along trajectory (more reliable than name)

# ============================================================================
# GEOMETRY ANALYSIS FUNCTIONS
# ============================================================================

def is_camera_cone(mesh_obj):
    """Check if a mesh object is a camera cone geometry
    
    Camera cones in GLB are typically:
    - Small meshes with few vertices (cone shape)
    - Have a tip vertex (camera center) and base vertices
    """
    if mesh_obj.type != 'MESH':
        return False
    
    mesh = mesh_obj.data
    if len(mesh.vertices) > CONE_VERTEX_COUNT_THRESHOLD:
        return False
    
    # Check if it looks like a cone (has a vertex with many edges)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    # Find vertex with most edges (likely the tip)
    max_edges = 0
    tip_vertex = None
    for vert in bm.verts:
        edge_count = len(vert.link_edges)
        if edge_count > max_edges:
            max_edges = edge_count
            tip_vertex = vert
    
    bm.free()
    
    # Camera cones typically have a tip with 4+ edges
    return max_edges >= 4

def extract_camera_from_cone(cone_obj):
    """Extract camera position and orientation from cone geometry
    
    The cone tip represents the camera center (optical center).
    The cone base represents the image plane.
    Camera looks from tip toward base center.
    """
    mesh = cone_obj.data
    world_matrix = cone_obj.matrix_world
    
    # Get vertices in world space
    vertices_world = [world_matrix @ Vector(v.co) for v in mesh.vertices]
    
    # Find tip vertex (vertex with most edges, or vertex farthest from centroid)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    
    # Calculate centroid
    centroid = Vector([0, 0, 0])
    for vert in bm.verts:
        centroid += Vector(vert.co)
    centroid /= len(bm.verts)
    
    # Find tip (vertex farthest from centroid or with most edges)
    tip_local = None
    max_distance = 0
    for vert in bm.verts:
        dist = (Vector(vert.co) - centroid).length
        if dist > max_distance:
            max_distance = dist
            tip_local = Vector(vert.co)
    
    # Transform tip to world space
    tip_world = world_matrix @ tip_local
    
    # Find base center (centroid of base vertices)
    # Base vertices are those far from tip
    base_vertices = []
    for vert in bm.verts:
        if (Vector(vert.co) - tip_local).length > max_distance * 0.5:
            base_vertices.append(Vector(vert.co))
    
    if len(base_vertices) == 0:
        # Fallback: use centroid as base
        base_center_local = centroid
    else:
        base_center_local = sum(base_vertices, Vector([0, 0, 0])) / len(base_vertices)
    
    base_center_world = world_matrix @ base_center_local
    
    # Camera position is at tip
    camera_pos = tip_world
    
    # Camera looks from tip toward base center
    look_direction = (base_center_world - tip_world).normalized()
    
    # Create rotation matrix from look direction
    # Blender camera looks down -Z, so we need to align -Z with look_direction
    up = Vector([0, 0, 1])  # Blender's up direction
    right = look_direction.cross(up).normalized()
    if right.length < 0.1:
        # If look_direction is parallel to up, use different up
        up = Vector([0, 1, 0])
        right = look_direction.cross(up).normalized()
    up = right.cross(look_direction).normalized()
    
    # Build rotation matrix: columns are right, up, -look_direction
    rot_matrix = Matrix([
        [right.x, up.x, -look_direction.x],
        [right.y, up.y, -look_direction.y],
        [right.z, up.z, -look_direction.z]
    ])
    
    camera_quat = rot_matrix.to_quaternion()
    
    bm.free()
    
    return camera_pos, camera_quat

# ============================================================================
# CAMERA CREATION FUNCTIONS
# ============================================================================

def create_camera_collection(name):
    """Create or get collection for cameras"""
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection

def create_camera_from_pose(index, pos, quat, collection, frame=None):
    """Create a Blender camera object from pose"""
    cam_name = f"Camera_{index:04d}"
    cam_data = bpy.data.cameras.new(name=cam_name)
    cam_data.lens = 50.0  # Default focal length
    
    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    collection.objects.link(cam_obj)
    
    cam_obj.location = pos
    cam_obj.rotation_mode = 'QUATERNION'
    cam_obj.rotation_quaternion = quat
    
    if CREATE_ANIMATION and frame is not None:
        cam_obj.keyframe_insert(data_path="location", frame=frame)
        cam_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    
    return cam_obj

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to extract cameras from GLB geometry"""
    print("=" * 60)
    print("Extracting Cameras from GLB Geometry")
    print("=" * 60)
    
    # Find all mesh objects that look like camera cones
    camera_cones = []
    for obj in bpy.data.objects:
        if is_camera_cone(obj):
            camera_cones.append(obj)
    
    print(f"Found {len(camera_cones)} potential camera geometries")
    
    if len(camera_cones) == 0:
        print("ERROR: No camera cone geometries found in imported GLB")
        print("Make sure you have imported the GLB file first")
        return
    
    # Sort cones to maintain correct sequence order
    # Multiple strategies to ensure correct ordering
    
    def extract_number_from_name(name):
        """Extract frame number from object name"""
        import re
        # Try to find numbers in name (e.g., "mesh_001", "Camera_42", etc.)
        numbers = re.findall(r'\d+', name)
        if numbers:
            # Use the last number (usually the frame/index)
            return int(numbers[-1])
        return -1  # No number found
    
    # Strategy 1: Try sorting by extracted numbers from names
    camera_cones_with_numbers = [(extract_number_from_name(cone.name), cone) for cone in camera_cones]
    camera_cones_with_numbers.sort(key=lambda x: x[0])
    
    # Check if all cameras have numbers
    all_have_numbers = all(num >= 0 for num, _ in camera_cones_with_numbers)
    
    if all_have_numbers and len(set(num for num, _ in camera_cones_with_numbers)) == len(camera_cones):
        # All cameras have unique numbers, use number-based sorting
        camera_cones = [cone for _, cone in camera_cones_with_numbers]
        print(f"Sorted cameras by frame numbers extracted from names")
    elif SORT_BY_POSITION and len(camera_cones) > 1:
        # Sort by position along trajectory (more reliable for geometry)
        # Get all positions first
        positions = [cone_obj.matrix_world.translation for cone_obj in camera_cones]
        
        # Find principal trajectory direction using PCA or first-to-last
        # Simple approach: use first-to-last direction
        first_pos = positions[0]
        last_pos = positions[-1]
        trajectory_vec = last_pos - first_pos
        
        if trajectory_vec.length > 0.001:  # Valid trajectory
            trajectory_dir = trajectory_vec.normalized()
            
            # Project positions onto trajectory direction and sort
            def get_projection(cone_obj):
                pos = cone_obj.matrix_world.translation
                # Project onto trajectory direction from first position
                return (pos - first_pos).dot(trajectory_dir)
            
            camera_cones.sort(key=get_projection)
            print(f"Sorted {len(camera_cones)} cameras by position along trajectory")
        else:
            # Trajectory is too short, try sorting by distance from origin
            def get_distance(cone_obj):
                pos = cone_obj.matrix_world.translation
                return pos.length
            
            camera_cones.sort(key=get_distance)
            print(f"Sorted cameras by distance from origin (trajectory too short)")
    else:
        # Fallback: sort by name (alphabetical)
        camera_cones.sort(key=lambda x: x.name)
        print(f"Sorted cameras by name (alphabetical fallback)")
        print(f"  Warning: Order may not match camera sequence!")
    
    # Create collection for cameras
    collection = create_camera_collection(CAMERA_COLLECTION_NAME)
    
    # Set scene frame range if creating animation
    if CREATE_ANIMATION:
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = len(camera_cones)
        print(f"Animation range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
    
    # Extract cameras from cones
    created_cameras = []
    for i, cone_obj in enumerate(camera_cones):
        try:
            pos, quat = extract_camera_from_cone(cone_obj)
            
            frame = i + 1 if CREATE_ANIMATION else None
            cam_obj = create_camera_from_pose(i, pos, quat, collection, frame)
            created_cameras.append(cam_obj)
            
            if (i + 1) % 10 == 0:
                print(f"Extracted {i + 1}/{len(camera_cones)} cameras...")
        except Exception as e:
            print(f"Warning: Could not extract camera from {cone_obj.name}: {e}")
            continue
    
    print(f"\nSuccessfully extracted {len(created_cameras)} camera objects!")
    print(f"Cameras are in collection: '{CAMERA_COLLECTION_NAME}'")
    
    if CREATE_ANIMATION:
        print(f"Camera animation created from frame {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
    
    # Select first camera
    if created_cameras:
        bpy.context.view_layer.objects.active = created_cameras[0]
        created_cameras[0].select_set(True)
        print(f"\nFirst camera selected: {created_cameras[0].name}")

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    main()
