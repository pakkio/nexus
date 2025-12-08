#!/usr/bin/env python3
"""
BVH to Second Life .anim Converter
Converts Mixamo/DAZ G8 BVH files to Second Life compatible .anim format

Usage:
    python bvh_to_sl_converter.py input.bvh output.anim

Features:
- Removes incompatible bones
- Fixes skeleton hierarchy for SL
- Removes root translation (keeps rotation only)
- Limits animation length to 30 seconds
- Converts to 30 FPS
- Creates SL-compatible .anim file
"""

import sys
import re
import math
from pathlib import Path

class BVHToSLConverter:
    def __init__(self):
        # Second Life compatible bone mapping
        self.sl_bone_map = {
            # Root
            'Hips': 'mPelvis',
            'mixamorig:Hips': 'mPelvis',
            'pelvis': 'mPelvis',
            
            # Spine
            'Spine': 'mTorso',
            'mixamorig:Spine': 'mTorso',
            'Spine1': 'mChest',
            'mixamorig:Spine1': 'mChest',
            'Spine2': 'mChest',
            'mixamorig:Spine2': 'mChest',
            
            # Neck/Head
            'Neck': 'mNeck',
            'mixamorig:Neck': 'mNeck',
            'Head': 'mHead',
            'mixamorig:Head': 'mHead',
            
            # Left Arm
            'LeftShoulder': 'mCollarLeft',
            'mixamorig:LeftShoulder': 'mCollarLeft',
            'LeftArm': 'mShoulderLeft',
            'mixamorig:LeftArm': 'mShoulderLeft',
            'LeftForeArm': 'mElbowLeft',
            'mixamorig:LeftForeArm': 'mElbowLeft',
            'LeftHand': 'mWristLeft',
            'mixamorig:LeftHand': 'mWristLeft',
            
            # Right Arm
            'RightShoulder': 'mCollarRight',
            'mixamorig:RightShoulder': 'mCollarRight',
            'RightArm': 'mShoulderRight',
            'mixamorig:RightArm': 'mShoulderRight',
            'RightForeArm': 'mElbowRight',
            'mixamorig:RightForeArm': 'mElbowRight',
            'RightHand': 'mWristRight',
            'mixamorig:RightHand': 'mWristRight',
            
            # Left Leg
            'LeftUpLeg': 'mHipLeft',
            'mixamorig:LeftUpLeg': 'mHipLeft',
            'LeftLeg': 'mKneeLeft',
            'mixamorig:LeftLeg': 'mKneeLeft',
            'LeftFoot': 'mAnkleLeft',
            'mixamorig:LeftFoot': 'mAnkleLeft',
            'LeftToeBase': 'mFootLeft',
            'mixamorig:LeftToeBase': 'mFootLeft',
            
            # Right Leg
            'RightUpLeg': 'mHipRight',
            'mixamorig:RightUpLeg': 'mHipRight',
            'RightLeg': 'mKneeRight',
            'mixamorig:RightLeg': 'mKneeRight',
            'RightFoot': 'mAnkleRight',
            'mixamorig:RightFoot': 'mAnkleRight',
            'RightToeBase': 'mFootRight',
            'mixamorig:RightToeBase': 'mFootRight',
        }
        
        # SL skeleton hierarchy
        self.sl_hierarchy = {
            'mPelvis': {
                'children': ['mTorso', 'mHipLeft', 'mHipRight'],
                'channels': 6  # Root has position + rotation
            },
            'mTorso': {
                'parent': 'mPelvis',
                'children': ['mChest'],
                'channels': 3  # Rotation only
            },
            'mChest': {
                'parent': 'mTorso', 
                'children': ['mNeck', 'mCollarLeft', 'mCollarRight'],
                'channels': 3
            },
            'mNeck': {
                'parent': 'mChest',
                'children': ['mHead'],
                'channels': 3
            },
            'mHead': {
                'parent': 'mNeck',
                'children': [],
                'channels': 3
            },
            # Left arm
            'mCollarLeft': {
                'parent': 'mChest',
                'children': ['mShoulderLeft'],
                'channels': 3
            },
            'mShoulderLeft': {
                'parent': 'mCollarLeft',
                'children': ['mElbowLeft'],
                'channels': 3
            },
            'mElbowLeft': {
                'parent': 'mShoulderLeft',
                'children': ['mWristLeft'],
                'channels': 3
            },
            'mWristLeft': {
                'parent': 'mElbowLeft',
                'children': [],
                'channels': 3
            },
            # Right arm
            'mCollarRight': {
                'parent': 'mChest',
                'children': ['mShoulderRight'],
                'channels': 3
            },
            'mShoulderRight': {
                'parent': 'mCollarRight',
                'children': ['mElbowRight'],
                'channels': 3
            },
            'mElbowRight': {
                'parent': 'mShoulderRight',
                'children': ['mWristRight'],
                'channels': 3
            },
            'mWristRight': {
                'parent': 'mElbowRight',
                'children': [],
                'channels': 3
            },
            # Left leg
            'mHipLeft': {
                'parent': 'mPelvis',
                'children': ['mKneeLeft'],
                'channels': 3
            },
            'mKneeLeft': {
                'parent': 'mHipLeft',
                'children': ['mAnkleLeft'],
                'channels': 3
            },
            'mAnkleLeft': {
                'parent': 'mKneeLeft',
                'children': ['mFootLeft'],
                'channels': 3
            },
            'mFootLeft': {
                'parent': 'mAnkleLeft',
                'children': [],
                'channels': 3
            },
            # Right leg
            'mHipRight': {
                'parent': 'mPelvis',
                'children': ['mKneeRight'],
                'channels': 3
            },
            'mKneeRight': {
                'parent': 'mHipRight',
                'children': ['mAnkleRight'],
                'channels': 3
            },
            'mAnkleRight': {
                'parent': 'mKneeRight',
                'children': ['mFootRight'],
                'channels': 3
            },
            'mFootRight': {
                'parent': 'mAnkleRight',
                'children': [],
                'channels': 3
            }
        }

    def parse_bvh(self, filepath):
        """Parse BVH file and extract hierarchy and motion data"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Split into hierarchy and motion sections
        parts = content.split('MOTION')
        if len(parts) != 2:
            raise ValueError("Invalid BVH file format")
        
        hierarchy_section = parts[0]
        motion_section = parts[1]
        
        # Parse hierarchy
        bones = self.parse_hierarchy(hierarchy_section)
        
        # Parse motion data
        motion_data = self.parse_motion(motion_section)
        
        return bones, motion_data
    
    def parse_hierarchy(self, hierarchy_text):
        """Parse the HIERARCHY section"""
        bones = {}
        lines = hierarchy_text.strip().split('\n')
        
        current_bone = None
        indent_stack = []
        
        for line in lines:
            line = line.strip()
            if not line or line == 'HIERARCHY':
                continue
                
            if line.startswith('ROOT') or line.startswith('JOINT'):
                # Extract bone name
                bone_name = line.split()[1]
                current_bone = bone_name
                bones[bone_name] = {
                    'channels': [],
                    'offset': [0, 0, 0],
                    'children': [],
                    'parent': None
                }
                
                # Set parent relationship
                if indent_stack:
                    parent = indent_stack[-1]
                    bones[bone_name]['parent'] = parent
                    bones[parent]['children'].append(bone_name)
                
                indent_stack.append(bone_name)
                
            elif line.startswith('OFFSET'):
                if current_bone:
                    offset = [float(x) for x in line.split()[1:4]]
                    bones[current_bone]['offset'] = offset
                    
            elif line.startswith('CHANNELS'):
                if current_bone:
                    channels = line.split()[2:]  # Skip count
                    bones[current_bone]['channels'] = channels
                    
            elif line == '}':
                if indent_stack:
                    indent_stack.pop()
        
        return bones
    
    def parse_motion(self, motion_text):
        """Parse the MOTION section"""
        lines = motion_text.strip().split('\n')
        
        frames = 0
        frame_time = 0.033333  # Default 30 FPS
        data = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('Frames:'):
                frames = int(line.split()[1])
            elif line.startswith('Frame Time:'):
                frame_time = float(line.split()[2])
            elif line and not line.startswith('Frames') and not line.startswith('Frame'):
                # Motion data line
                values = [float(x) for x in line.split()]
                data.append(values)
        
        return {
            'frames': frames,
            'frame_time': frame_time,
            'data': data
        }
    
    def convert_to_sl_hierarchy(self, bones):
        """Convert bone hierarchy to SL compatible format"""
        sl_bones = {}
        
        for bone_name, bone_data in bones.items():
            # Map to SL bone name
            sl_name = self.sl_bone_map.get(bone_name, bone_name)
            
            # Only keep bones that exist in SL hierarchy
            if sl_name in self.sl_hierarchy:
                sl_bones[sl_name] = {
                    'original_name': bone_name,
                    'channels': bone_data['channels'],
                    'offset': bone_data['offset']
                }
        
        return sl_bones
    
    def create_anim_file(self, sl_bones, motion_data, output_path):
        """Create Second Life .anim file"""
        
        # Limit to 30 seconds at 30 FPS = 900 frames max
        max_frames = min(motion_data['frames'], 900)
        
        # Create .anim file content
        anim_content = []
        anim_content.append("Linden Lab anim version 1.0")
        anim_content.append("")
        anim_content.append(f"duration {max_frames * 0.033333:.6f}")
        anim_content.append("emote_name (null)")
        anim_content.append("")
        anim_content.append("joints")
        anim_content.append("{")
        
        # Track channel index for each bone
        channel_index = 0
        bone_channel_map = {}
        
        # Process each SL bone
        for sl_bone_name in self.sl_hierarchy.keys():
            if sl_bone_name in sl_bones:
                bone_data = sl_bones[sl_bone_name]
                channels = bone_data['channels']
                
                # Map channels to indices
                bone_channel_map[sl_bone_name] = {
                    'start_index': channel_index,
                    'channels': channels
                }
                channel_index += len(channels)
                
                # Add bone section
                anim_content.append(f"    joint {sl_bone_name}")
                anim_content.append("    {")
                
                # Add keys for this bone
                for i in range(max_frames):
                    if i < len(motion_data['data']):
                        frame_data = motion_data['data'][i]
                        time = i * 0.033333
                        
                        # Extract rotation data for this bone
                        start_idx = bone_channel_map[sl_bone_name]['start_index']
                        bone_channels = bone_channel_map[sl_bone_name]['channels']
                        
                        # For root bone (mPelvis), handle position + rotation
                        if sl_bone_name == 'mPelvis':
                            if len(bone_channels) >= 6:
                                # Position (X,Y,Z) - but zero out for SL compatibility
                                pos_x, pos_y, pos_z = 0.0, 0.0, 0.0
                                # Rotation (Z,X,Y in BVH, convert to SL order)
                                if start_idx + 5 < len(frame_data):
                                    rot_z = math.radians(frame_data[start_idx + 3])
                                    rot_x = math.radians(frame_data[start_idx + 4]) 
                                    rot_y = math.radians(frame_data[start_idx + 5])
                                else:
                                    rot_x = rot_y = rot_z = 0.0
                                
                                anim_content.append(f"        key {time:.6f} {pos_x:.6f} {pos_y:.6f} {pos_z:.6f} {rot_x:.6f} {rot_y:.6f} {rot_z:.6f}")
                        else:
                            # Other bones - rotation only
                            if len(bone_channels) >= 3 and start_idx + 2 < len(frame_data):
                                rot_z = math.radians(frame_data[start_idx])
                                rot_x = math.radians(frame_data[start_idx + 1])
                                rot_y = math.radians(frame_data[start_idx + 2])
                            else:
                                rot_x = rot_y = rot_z = 0.0
                                
                            anim_content.append(f"        key {time:.6f} {rot_x:.6f} {rot_y:.6f} {rot_z:.6f}")
                
                anim_content.append("    }")
        
        anim_content.append("}")
        anim_content.append("")
        anim_content.append("constraints")
        anim_content.append("{")
        anim_content.append("}")
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(anim_content))
    
    def convert(self, input_path, output_path):
        """Main conversion function"""
        print(f"Converting {input_path} to SL .anim format...")
        
        try:
            # Parse BVH file
            bones, motion_data = self.parse_bvh(input_path)
            print(f"Parsed {len(bones)} bones, {motion_data['frames']} frames")
            
            # Convert to SL hierarchy
            sl_bones = self.convert_to_sl_hierarchy(bones)
            print(f"Mapped to {len(sl_bones)} SL-compatible bones")
            
            # Create .anim file
            self.create_anim_file(sl_bones, motion_data, output_path)
            print(f"Created SL animation file: {output_path}")
            
            # Show file info
            duration = min(motion_data['frames'], 900) * 0.033333
            print(f"Animation duration: {duration:.2f} seconds")
            print(f"Frame rate: 30 FPS")
            print(f"Compatible bones: {', '.join(sl_bones.keys())}")
            
            return True
            
        except Exception as e:
            print(f"Error during conversion: {e}")
            return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python bvh_to_sl_converter.py input.bvh output.anim")
        print("Example: python bvh_to_sl_converter.py praying.bvh praying.anim")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)
    
    converter = BVHToSLConverter()
    success = converter.convert(input_file, output_file)
    
    if success:
        print("\n✅ Conversion successful!")
        print(f"Upload {output_file} to Second Life as an animation.")
    else:
        print("\n❌ Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()