from os import path, makedirs, stat
from os.path import join, isfile, basename
from requests import post
from IPython import embed

from bpy.path import abspath, clean_name, display_name_from_filepath, relpath
from bpy.props import IntProperty, StringProperty, BoolProperty
from bpy.types import Operator, Panel, ImageSequence
from bpy.utils import register_class, unregister_class
from pprint import pformat

bl_info = {
    'name': "Process VSE strip",
    'category': 'Development',
    'author': "Gabriel Montagné Láscaris-Comneno",
    'blender': (2, 80, 0)
}

def is_valid(active_strip):
    return active_strip is not None and isinstance(active_strip, ImageSequence)


class SEQUENCER_PT_process_clip(Panel):
    bl_label = "Process Clip"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(self, context):
        return context.scene.sequence_editor and is_valid(context.scene.sequence_editor.active_strip)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator('sequencer.process_strip')

class SEQUENCER_OP_process_clip(Operator):
    bl_idname = 'sequencer.process_strip'
    bl_label = "Process Strip"
    bl_options = {'UNDO', 'PRESET'}

    new_strip_name: StringProperty(description='Module with the process_frame method')

    server_port: IntProperty(description='Proccessing server port', default=3000)

    copy_transform_and_crop: BoolProperty(description='Copy transform and crop', default=True)

    @classmethod
    def poll(self, context):
        return is_valid(context.scene.sequence_editor.active_strip)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        print('process VSE')

        scene = context.scene
        sequence_editor = scene.sequence_editor

        effective_strip_name = self.new_strip_name or active_strip.name

        active_strip = sequence_editor.active_strip
        target_path = abspath(active_strip.directory)
        processed_dir = join(target_path, clean_name(effective_strip_name))
        makedirs(processed_dir, exist_ok=True)


        elements = active_strip.elements
        frame_offset_start = active_strip.frame_offset_start
        frame_final_start = active_strip.frame_final_start
        frame_final_duration = active_strip.frame_final_duration

        window_manager = context.window_manager

        elements_to_process = elements[
            frame_offset_start:frame_final_duration + frame_offset_start]

        window_manager.progress_begin(0, len(elements_to_process))

        use_multiview = active_strip.use_multiview

        if use_multiview:
            assert active_strip.views_format == 'STEREO_3D', 'Only STEREO_3D views formatsupported'
            assert active_strip.stereo_3d_format.display_mode == 'TOPBOTTOM', 'Only TOPBOTTOM display mode supported'

        for i, element in enumerate(elements_to_process):

            window_manager.progress_update(i)
            image_path = join(target_path, element.filename)
            original_file_name = display_name_from_filepath(element.filename)
            frame_number = frame_final_start + i

            payload = {
                'original_file_name': original_file_name,
                'image_path': image_path, 
                'processed_dir': processed_dir,
                'use_multiview': use_multiview,
                'frame_number': frame_number
            }

            r = post(f'http://0.0.0.0:{self.server_port}/process', json=payload)
            process_full_path = r.text
            assert isfile(process_full_path), 'Image not created!'

            if i == 0:
                new_sequence_name = effective_strip_name  + '.000'
                print('Creating new image sequence "{}"'.format(new_sequence_name))
                new_sequence = sequence_editor.sequences.new_image(
                    name=new_sequence_name,
                    filepath=relpath(process_full_path),
                    frame_start=frame_final_start,
                    channel=active_strip.channel + 1)
            else:
                print('append file', basename(process_full_path))
                new_sequence.elements.append(basename(process_full_path))

        if use_multiview:
            new_sequence.use_multiview = use_multiview
            new_sequence.views_format = 'STEREO_3D'
            new_sequence.stereo_3d_format.display_mode = 'TOPBOTTOM'

        new_sequence.blend_type = 'ALPHA_OVER'
        if self.copy_transform_and_crop:

            new_sequence.crop.max_x = active_strip.crop.max_x
            new_sequence.crop.max_y = active_strip.crop.max_y
            new_sequence.crop.min_x = active_strip.crop.min_x
            new_sequence.crop.min_y = active_strip.crop.min_y

            new_sequence.transform.offset_x = active_strip.transform.offset_x
            new_sequence.transform.offset_y = active_strip.transform.offset_y
            new_sequence.transform.scale_x = active_strip.transform.scale_x
            new_sequence.transform.scale_y = active_strip.transform.scale_y
            new_sequence.transform.rotation = active_strip.transform.rotation
            new_sequence.transform.origin = active_strip.transform.origin

        window_manager.progress_end()
        return {'FINISHED'}

def register():
    register_class(SEQUENCER_OP_process_clip)
    register_class(SEQUENCER_PT_process_clip)

def unregister():
    unregister_class(SEQUENCER_PT_process_clip)
    unregister_class(SEQUENCER_OP_process_clip)

if __name__ == '__main__':
    register()
