import os
import numpy as np
import bpy

# from photogrammetry_importer.point import Point

from photogrammetry_importer.utils.blender_utils import add_collection

from photogrammetry_importer.file_handler.meshroom_json_file_handler import MeshroomJSONFileHandler
from photogrammetry_importer.file_handler.openmvg_json_file_handler import OpenMVGJSONFileHandler
from photogrammetry_importer.file_handler.colmap_file_handler import ColmapFileHandler
from photogrammetry_importer.file_handler.nvm_file_handler import NVMFileHandler
from photogrammetry_importer.file_handler.ply_file_handler import PLYFileHandler
from photogrammetry_importer.file_handler.transformation_file_handler import TransformationFileHandler

from photogrammetry_importer.camera_import_properties import CameraImportProperties
from photogrammetry_importer.point_import_properties import PointImportProperties
from photogrammetry_importer.transformation_import_properties import TransformationImportProperties

# Notes:
#   http://sinestesia.co/blog/tutorials/using-blenders-filebrowser-with-python/
#       Nice blender tutorial
#   https://blog.michelanders.nl/2014/07/inheritance-and-mixin-classes-vs_13.html
#       - The class that is actually used as operator must inherit from bpy.types.Operator and ImportHelper
#       - Properties defined in the parent class, which inherits from bpy.types.Operator and ImportHelper
#         are not considered  
# https://blender.stackexchange.com/questions/717/is-it-possible-to-print-to-the-report-window-in-the-info-view
#   The color depends on the type enum: INFO gets green, WARNING light red, and ERROR dark red

from bpy.props import (CollectionProperty,
                       StringProperty,
                       BoolProperty,
                       EnumProperty,
                       FloatProperty,
                       IntProperty
                       )

from bpy_extras.io_utils import (ImportHelper,
                                 ExportHelper,
                                 axis_conversion)


def get_default_image_path(reconstruction_fp, image_dp):
    if image_dp == '':
        image_default_same_dp = os.path.dirname(reconstruction_fp)
        image_default_sub_dp = os.path.join(image_default_same_dp, 'images')
        if os.path.isdir(image_default_sub_dp):
            image_dp = image_default_sub_dp
        else:
            image_dp = image_default_same_dp
    return image_dp

class ImportColmap(CameraImportProperties, PointImportProperties, bpy.types.Operator):
    
    """Blender import operator for colmap model folders. """
    bl_idname = "import_scene.colmap_model"
    bl_label = "Import Colmap Model Folder"
    bl_options = {'PRESET'}

    directory = StringProperty()
    #filter_folder = BoolProperty(default=True, options={'HIDDEN'})

    # The following properties of CameraImportProperties are not required, 
    # since the corresponding data is always part of the colmap reconstruction result
    default_width: IntProperty(options={'HIDDEN'})
    default_height: IntProperty(options={'HIDDEN'})
    default_pp_x: FloatProperty(options={'HIDDEN'})
    default_pp_y: FloatProperty(options={'HIDDEN'})

    def execute(self, context):

        path = self.directory
        # Remove trailing slash
        path = os.path.dirname(path)
        self.report({'INFO'}, 'path: ' + str(path))

        self.path_to_images = get_default_image_path(
            path, self.path_to_images)
        self.report({'INFO'}, 'path_to_images: ' + str(self.path_to_images))
        
        cameras, points = ColmapFileHandler.parse_colmap_model_folder(path, self)

        self.report({'INFO'}, 'Number cameras: ' + str(len(cameras)))
        self.report({'INFO'}, 'Number points: ' + str(len(points)))

        reconstruction_collection = add_collection('Reconstruction Collection')
        self.import_photogrammetry_cameras(cameras, reconstruction_collection)
        self.import_photogrammetry_points(points, reconstruction_collection)

        self.report({'INFO'}, 'Parse Colmap model folder: Done')

        return {'FINISHED'}

    def invoke(self, context, event):
        # See: 
        # https://blender.stackexchange.com/questions/14738/use-filemanager-to-select-directory-instead-of-file/14778
        # https://docs.blender.org/api/current/bpy.types.WindowManager.html#bpy.types.WindowManager.fileselect_add
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        self.draw_camera_options(layout)
        self.draw_point_options(layout)


class ImportNVM(CameraImportProperties, PointImportProperties, bpy.types.Operator, ImportHelper):
    
    """Blender import operator for NVM files. """
    bl_idname = "import_scene.nvm"
    bl_label = "Import NVM"
    bl_options = {'PRESET'}

    filepath: StringProperty(
        name="NVM File Path",
        description="File path used for importing the NVM file")
    directory: StringProperty()
    filter_glob: StringProperty(default="*.nvm", options={'HIDDEN'})

    def enhance_camera_with_images(self, cameras):
        # Overwrites CameraImportProperties.enhance_camera_with_images()
        cameras, success = NVMFileHandler.parse_camera_image_files(
        cameras, self.path_to_images, self.default_width, self.default_height, self)
        return cameras, success

    def execute(self, context):

        path = os.path.join(self.directory, self.filepath)
        self.report({'INFO'}, 'path: ' + str(path))

        self.path_to_images = get_default_image_path(
            path, self.path_to_images)
        self.report({'INFO'}, 'path_to_images: ' + str(self.path_to_images))

        cameras, points = NVMFileHandler.parse_nvm_file(path, self)
        self.report({'INFO'}, 'Number cameras: ' + str(len(cameras)))
        self.report({'INFO'}, 'Number points: ' + str(len(points)))
        
        reconstruction_collection = add_collection('Reconstruction Collection')
        self.import_photogrammetry_cameras(cameras, reconstruction_collection)
        self.import_photogrammetry_points(points, reconstruction_collection)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.draw_camera_options(layout, draw_size_and_pp=True)
        self.draw_point_options(layout)

    
class ImportOpenMVG(CameraImportProperties, PointImportProperties, bpy.types.Operator, ImportHelper):

    """Blender import operator for OpenMVG JSON files. """
    bl_idname = "import_scene.openmvg_json"
    bl_label = "Import OpenMVG JSON"
    bl_options = {'PRESET'}

    filepath: StringProperty(
        name="OpenMVG JSON File Path",
        description="File path used for importing the OpenMVG JSON file")
    directory: StringProperty()
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    # The following properties of CameraImportProperties are not required, 
    # since the corresponding data is always part of the openmvg reconstruction result
    default_width: IntProperty(options={'HIDDEN'})
    default_height: IntProperty(options={'HIDDEN'})
    default_pp_x: FloatProperty(options={'HIDDEN'})
    default_pp_y: FloatProperty(options={'HIDDEN'})

    def execute(self, context):

        path = os.path.join(self.directory, self.filepath)
        self.report({'INFO'}, 'path: ' + str(path))
 
        self.path_to_images = get_default_image_path(
            path, self.path_to_images)
        self.report({'INFO'}, 'path_to_images: ' + str(self.path_to_images))
        
        cameras, points = OpenMVGJSONFileHandler.parse_openmvg_file(
            path, self.path_to_images, self)
        
        self.report({'INFO'}, 'Number cameras: ' + str(len(cameras)))
        self.report({'INFO'}, 'Number points: ' + str(len(points)))
        
        reconstruction_collection = add_collection('Reconstruction Collection')
        self.import_photogrammetry_cameras(cameras, reconstruction_collection)
        self.import_photogrammetry_points(points, reconstruction_collection)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.draw_camera_options(layout)
        self.draw_point_options(layout)

class ImportMeshroom(CameraImportProperties, PointImportProperties, bpy.types.Operator, ImportHelper):

    """Blender import operator for OpenMVG JSON files. """
    bl_idname = "import_scene.meshroom_sfm_json"
    bl_label = "Import Meshroom SfM/JSON"
    bl_options = {'PRESET'}

    filepath: StringProperty(
        name="Meshroom JSON File Path",
        description="File path used for importing the Meshroom SfM/JSON file")
    directory: StringProperty()
    filter_glob: StringProperty(default="*sfm;*.json", options={'HIDDEN'})

    # The following properties of CameraImportProperties are not required, 
    # since the corresponding data is always part of the openmvg reconstruction result
    default_width: IntProperty(options={'HIDDEN'})
    default_height: IntProperty(options={'HIDDEN'})
    default_pp_x: FloatProperty(options={'HIDDEN'})
    default_pp_y: FloatProperty(options={'HIDDEN'})

    def execute(self, context):

        path = os.path.join(self.directory, self.filepath)
        self.report({'INFO'}, 'path: ' + str(path))

        self.path_to_images = get_default_image_path(
            path, self.path_to_images)
        self.report({'INFO'}, 'path_to_images: ' + str(self.path_to_images))
        
        cameras, points = MeshroomJSONFileHandler.parse_meshroom_file(
            path, self)
        
        self.report({'INFO'}, 'Number cameras: ' + str(len(cameras)))
        self.report({'INFO'}, 'Number points: ' + str(len(points)))
        
        reconstruction_collection = add_collection('Reconstruction Collection')
        self.import_photogrammetry_cameras(cameras, reconstruction_collection)
        self.import_photogrammetry_points(points, reconstruction_collection)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.draw_camera_options(layout)
        self.draw_point_options(layout)

class ImportPLY(PointImportProperties, TransformationImportProperties, bpy.types.Operator, ImportHelper):

    """Blender import operator for PLY files. """
    bl_idname = "import_scene.ply"
    bl_label = "Import PLY"
    bl_options = {'PRESET'}

    filepath: StringProperty(
        name="PLY File Path",
        description="File path used for importing the PLY file")
    directory: StringProperty()
    filter_glob: StringProperty(default="*.ply", options={'HIDDEN'})

    def execute(self, context):
        path = os.path.join(self.directory, self.filepath)
        self.report({'INFO'}, 'path: ' + str(path))

        points = PLYFileHandler.parse_ply_file(path)
        self.report({'INFO'}, 'Number points: ' + str(len(points)))

        transformations_sorted = TransformationFileHandler.parse_transformation_folder(
            self.path_to_transformations, self)

        reconstruction_collection = add_collection('Reconstruction Collection')
        self.import_photogrammetry_points(points, reconstruction_collection, transformations_sorted)

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        self.draw_point_options(layout)
        self.draw_transformation_options(layout)