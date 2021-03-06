from bpy import context
from bpy.path import abspath, clean_name, display_name_from_filepath, relpath
from bpy.types import Operator, Panel, ImageSequence
from bpy_extras.io_utils import path_reference
from os import path, makedirs, stat
from os.path import join, isfile
from stat import S_ISREG
from time import sleep
import bpy
import importlib
import numpy as np

bl_info = {
    'name': "Process VSE strip",
    'category': 'Development',
    'author': "Gabriel Montagné Láscaris-Comneno",
    'blender': (2, 80, 0)
}

loaded_modules = {}

def label(pixels, text, pos=(10, 25), colour=(255, 255, 255)):
    import cv2
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(pixels, text, pos, FONT, 1, colour, 1, cv2.LINE_8)

def split_topbottom(orig):
    return np.split(orig, 2)

def join_topbottom(a, b):
    return np.concatenate((a, b))

def prop(name, frame_number, default):
    world = bpy.context.scene.world

    fcurve = None
    if world.animation_data:
        fcurve = world.animation_data.action.fcurves.find('["{}"]'.format(name))

    if fcurve:
        result = fcurve.evaluate(frame_number)
    else:
        result = world.get(name, default)

    return result

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
        row.label(text='OK')
        row.operator('sequencer.process_strip')

class SEQUENCER_OP_process_clip(Operator):
    bl_idname = 'sequencer.process_strip'
    bl_label = "Process Strip"

    module_name: bpy.props.StringProperty(
        default='xyy', description='Module with the process_frame method')

    reload_if_loaded: bpy.props.BoolProperty(
        default=True, description='Reload module if already loaded')

    process_offline: bpy.props.BoolProperty(
        default=False, description='Process offline')

    @classmethod
    def poll(self, context):
        return is_valid(context.scene.sequence_editor.active_strip)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):

        import imageio

        scene = context.scene
        sequence_editor = scene.sequence_editor

        active_strip = sequence_editor.active_strip
        target_path = abspath(active_strip.directory)
        processed_dir = join(target_path, clean_name(active_strip.name))
        window_manager = context.window_manager

        makedirs(processed_dir, exist_ok=True)

        elements = active_strip.elements
        frame_offset_start = active_strip.frame_offset_start
        frame_final_start = active_strip.frame_final_start
        frame_final_duration = active_strip.frame_final_duration

        elements_to_process = elements[
            frame_offset_start:frame_final_duration + frame_offset_start]

        window_manager.progress_begin(0, len(elements_to_process))

        module_name = self.module_name

        if module_name in loaded_modules and self.reload_if_loaded:
            module = importlib.reload(loaded_modules.get(module_name))
        else:
            module = importlib.import_module(module_name)

        loaded_modules[module_name] = module

        use_multiview = active_strip.use_multiview

        if use_multiview:
            assert active_strip.views_format == 'STEREO_3D', 'Only STEREO_3D views formatsupported'
            assert active_strip.stereo_3d_format.display_mode == 'TOPBOTTOM', 'Only TOPBOTTOM display mode supported'

        for i, element in enumerate(elements_to_process):

            window_manager.progress_update(i)

            image_path = join(target_path, element.filename)
            original_file_name = display_name_from_filepath(element.filename)
            process_name = 'hcy_' + original_file_name

            new_file_name = process_name + '.png'
            process_full_path = path.join(processed_dir, new_file_name)
            frame_number = frame_final_start + i

            if self.process_offline:
                print('process offline')
                module.process_frame_offline(
                    image_path,
                    process_full_path,
                    frame_number,
                    process_name,
                    is_topbottom=use_multiview)

                assert isfile(process_full_path), 'image not created!'
                print('frame processed', process_full_path)
            else:
                orig = imageio.imread(image_path)
                processed = module.process_frame(
                    orig, frame_number, process_name,
                    is_topbottom=use_multiview)
                imageio.imsave(process_full_path, processed)
                print('saved image', process_full_path)

            if i == 0:
                new_sequence_name = active_strip.name + '_processed.000'
                print('Creating new image sequence "{}"'.format(new_sequence_name))
                new_sequence = sequence_editor.sequences.new_image(
                    name=new_sequence_name,
                    filepath=relpath(process_full_path),
                    frame_start=frame_final_start,
                    channel=active_strip.channel + 1)
            else:
                new_sequence.elements.append(new_file_name)

        if use_multiview:
            new_sequence.use_multiview = use_multiview
            new_sequence.views_format = 'STEREO_3D'
            new_sequence.stereo_3d_format.display_mode = 'TOPBOTTOM'

        new_sequence.blend_type = 'ALPHA_OVER'

        window_manager.progress_end()
        print('Done!')

        return {'FINISHED'}

def register():
    bpy.utils.register_class(SEQUENCER_OP_process_clip)
    bpy.utils.register_class(SEQUENCER_PT_process_clip)

def unregister():
    bpy.utils.unregister_class(SEQUENCER_OP_process_clip)
    bpy.utils.unregister_class(SEQUENCER_PT_process_clip)

if __name__ == '__main__':
    register()
