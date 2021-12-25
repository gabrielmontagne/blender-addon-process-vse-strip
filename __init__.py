from os.path import join, isfile
from requests import post

from bpy.path import abspath, clean_name, display_name_from_filepath, relpath
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator, Panel, ImageSequence
from bpy.utils import register_class, unregister_class

bl_info = {
    'name': "Process VSE strip",
    'category': 'Development',
    'author': "Gabriel Montagné Láscaris-Comneno",
    'blender': (2, 80, 0)
}

def is_valid(active_strip):
    return active_strip is not None and isinstance(active_strip, ImageSequence)

class SEQUENCER_OP_process_clip(Operator):
    bl_idname = 'sequencer.process_strip'
    bl_label = "Process Strip"
    bl_options = {'UNDO', 'PRESET'}

    new_strip_name: StringProperty(description='Module with the process_frame method')

    server_port: IntProperty(description='Proccessing server port', default=3000)

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

        active_strip = sequence_editor.active_strip
        target_path = abspath(active_strip.directory)
        processed_dir = join(target_path, clean_name(self.new_strip_name or active_strip.name))
        window_manager = context.window_manager

        # makedirs(processed_dir, exist_ok=True)

        elements = active_strip.elements
        frame_offset_start = active_strip.frame_offset_start
        frame_final_start = active_strip.frame_final_start
        frame_final_duration = active_strip.frame_final_duration

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

            print(f'process {processed_dir} {image_path} for {original_file_name} {frame_number} {use_multiview}')

            payload = {
                'original_file_name': original_file_name,
                'image_path': image_path, 
                'processed_dir': processed_dir,
                'frame_number': frame_number
            }

            r = post(f'http://0.0.0.0:{self.server_port}/process', json=payload)
            print(r)

        window_manager.progress_end()
        return {'FINISHED'}

def register():
    register_class(SEQUENCER_OP_process_clip)

def unregister():
    unregister_class(SEQUENCER_OP_process_clip)

if __name__ == '__main__':
    register()
