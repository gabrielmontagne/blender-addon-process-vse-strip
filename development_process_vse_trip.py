from bpy import context
from bpy.path import abspath, clean_name, display_name_from_filepath, relpath
from bpy.types import Operator, Panel, ImageSequence
from bpy_extras.io_utils import path_reference
from os import path, makedirs
from os.path import join
from scipy import misc
from time import sleep
import bpy
import importlib
import numpy as np

loaded_modules = {}


def is_valid(active_strip):
    return active_strip is not None and isinstance(active_strip, ImageSequence)


class SEQUENCER_PT_process_clip(Panel):
    bl_label = "Process Clip"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'

    @classmethod
    def poll(self, context):
        return is_valid(context.scene.sequence_editor.active_strip)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text='OK')
        row.operator('sequencer.process_strip')


class SequencerProcessClip(Operator):
    bl_idname = 'sequencer.process_strip'
    bl_label = "Process strip"

    module_name = bpy.props.StringProperty(
        default='roperot', description='Module with the process_frame method')
    reload_if_loaded = bpy.props.BoolProperty(
        default=True, description='Reload module if already loaded')

    @classmethod
    def poll(self, context):
        return is_valid(context.scene.sequence_editor.active_strip)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
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

        print('Module_name', self.module_name, self.reload_if_loaded)

        module_name = self.module_name

        if module_name in loaded_modules and self.reload_if_loaded:
            module = importlib.reload(loaded_modules.get(module_name))
        else:
            module = importlib.import_module(module_name)

        loaded_modules[module_name] = module

        for i, element in enumerate(elements_to_process):

            window_manager.progress_update(i)
            orig = misc.imread(join(target_path, element.filename))
            original_file_name = display_name_from_filepath(element.filename)
            process_name = original_file_name + '_hcy'
            processed = module.process_frame(
                orig, frame_final_start + i, process_name)

            new_file_name = process_name + '.png'
            process_full_path = path.join(processed_dir, new_file_name)
            misc.imsave(process_full_path, processed)

            if i == 0:
                print('Filepath', process_full_path)
                new_sequence = sequence_editor.sequences.new_image(
                    name=active_strip.name + ' (hcy)',
                    filepath=relpath(process_full_path),
                    frame_start=frame_final_start,
                    channel=active_strip.channel + 1)
            else:
                new_sequence.elements.append(new_file_name)

            new_sequence.blend_type = 'ALPHA_OVER'

        window_manager.progress_end()
        print('Done!')

        return {'FINISHED'}


def register():
    print('Register Process strip')
    bpy.utils.register_class(SequencerProcessClip)
    bpy.utils.register_class(SEQUENCER_PT_process_clip)


def unregister():
    print('Unregister Process strip')
    bpy.utils.unregister_class(SequencerProcessClip)
    bpy.utils.unregister_class(SEQUENCER_PT_process_clip)


if __name__ == '__main__':
    register()
