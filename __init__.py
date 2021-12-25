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
        return {'FINISHED'}

def register():
    register_class(SEQUENCER_OP_process_clip)

def unregister():
    unregister_class(SEQUENCER_OP_process_clip)

if __name__ == '__main__':
    register()
