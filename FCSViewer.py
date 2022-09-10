
import os
import requests
import subprocess

from PyFCS import ColourSelection
from PyFCS import Palette
from PyFCS import DocumentBuilder

class FCSViewer(object):
    """
    The primary interactor of the FCS web viewer.
    """

    def __init__(self, viewer_pid: int, document_operator: DocumentBuilder):
        """
        During instantiation connects to a viewer instance. 
        """
        from sys import platform

        self.viewer_id = viewer_pid
        self.viewer_url = '127.0.0.1'
        self.viewer_request_url = f'http://{self.viewer_url}:{self.viewer_id}/toFrontend'
        self.platform = platform
        self.is_available = self.has_active_viewer() # ToDo: Have some method to ping the frontend
        self.document_operator = document_operator
        self.published_object_counter = 0
        self.plugin_name = "FCSPythonProject"
        self.active_document_name = self.document_operator.get_document_name()
        self.project_folder = self.__setup_temp_folder()

    def set_plugin_name(plugin_name: str) -> None:
        """
        Repaths project folder in app data.
        """

        self.plugin_name = plugin_name
        self.project_folder = self.__setup_temp_folder()

    def has_active_viewer(self) -> bool:
        """
        Checks if the cloud viewer's port is active by pinging it. 
        
        Legacy functionality: `salome.sg.hasDesktop()`
        """

        def is_port_in_use(port: int) -> bool:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex((f'{self.viewer_url}', port)) == 0

        try:
            is_running = is_port_in_use(self.viewer_id)
            return is_running                      
        except Exception as ex:
            print(f"has_active_viewer failed: {ex}. Will assume no Viewer is connected!")
            return False

    def update_viewer(self) -> None:
        """
        Updates viewer's document. Will load all added entities to the viewer               
        Legacy functionality: `salome.sg.updateObjBrowser()`
        """
        if not self.is_available: return

        msg_request = {
                "operation":"update_viewer",
                "arguments":{
                    }
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def commit_to_document(self) -> None:
        """
        If we commit to a document it is deserialised into a file in the local working folder
        and it is uploaded to the server to synchronise with the server's working instance.

        This will enable 'Active' mode in the viewer allowing the user to actively
        interact / modify / export the model generated by the plugin. 
        """

        if not self.is_available: return;

        model_path = f"{self.project_folder}/{self.active_document_name}.cbf"

        if self.document_operator.save_document_to(self.project_folder):
            self.document_operator.close_document()

        # STEP 2: SEND data to frontend
        msg_request = {
            "operation":"commit_to_document",
            "arguments":{
                "fname" : "commit_to_document",
                "model_path" : model_path,
                }
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def hide_all(self) -> None:
        """
        Hides everything in the active document             
        Legacy functionality: `salome.sg.EraseAll()`
        """
        if not self.is_available: return

        msg_request = {
                "operation":"hide_all",
                "arguments":{
                    }
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def show_only(self, entity_id: int) -> None:
        """
        Pass in unique ID of the object to show that entity only                
        Legacy functionality: `salome.sg.DisplayOnly(model_id)`
        """
        if not self.is_available: return

        msg_request = {
                "operation": "show_only",
                "entity_id": entity_id
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def show(self, entity_id: int) -> None:
        """
        Pass in unique ID of the object to activate entity in the viewer.              
        Legacy functionality: `salome.sg.Display(model_id)`
        """
        if not self.is_available: return

        msg_request = {
                "operation": "show",
                "arguments":{
                    "entity_id": entity_id
                    }
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def set_transparency(self, entity_id: int, opacity: float) -> None:
        """
        Sets transparency of the object in the viewer.
        Legacy functionality: `gg.setTransparency(model_id)`
        """
        if not self.is_available: return

        msg_request = {
                "operation": "set_transparency",
                "arguments":{
                    "entity_id": entity_id
                    }
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def fit_all(self) -> None:
        """
        Adjust camera that all is visible               
        Legacy functionality: `salome.sg.FitAll()`
        """
        if not self.is_available: return

        msg_request = {
                "operation":"fit_all",
                "arguments":{
                    }
            }

        is_ok = self.__try_send_request(self.viewer_request_url, msg_request)["status"]

    def add_to_document(self, entity: object, name: str) -> int:
        """
        Hides everything in the active document             
        Legacy functionality: `salome.sg.addToStudy(model, name)`
        """
        if not self.is_available: return

        # Object order is not the same as the ID!
        object_order = self.published_object_counter + 1
        item_id = -1

        export_stl_name = f"{object_order}_{name}.stl"
        export_t2g_name = f"{object_order}_{name}_geom.json"

        # STEP 1: EXPORT geometry
        express_static_folder = f"{self.plugin_name}"
        t2g_path_static = express_static_folder + '/' + export_t2g_name
        stl_path_static = express_static_folder + '/' + export_stl_name
        try:
            export_to_path = self.project_folder
            item_id = self.document_operator.add_to_document(entity, f"{object_order}_{name}", export_to_path)
        except Exception as ex:
            print(f"FCSViewer: Could not publish object named {name}. Failure: {ex.args}")
            return

        # STEP 2: SEND data to frontend
        msg_request = {
            "operation":"add_to_document",
            "arguments":{
                "name" : name,
                "item_id" : str(item_id),
                "t2g_file" : export_t2g_name,
                "stl_file" : export_stl_name,
                "stl_path" : express_static_folder,
                "stl_path_static" : stl_path_static,
                "t2g_path_static" : t2g_path_static
                }
            }

        msg_response = self.__try_send_request(self.viewer_request_url, msg_request)

        # ToDo: Increment only if response is correct
        self.published_object_counter += 1

        return item_id

    def remove_from_document(self, object_id: int) -> None:
        """
        Removes all child entities under this ID.  
        """
        pass 

    def add_to_document_under(self, child_entity: object, father_entity: int, name: str) -> None:
        """
        Adds entity under a parent entity               
        Legacy functionality: `geompy.addToStudyInFather( self.Model, i_Face, str_Name )`
        """
        if not self.is_available: return

        # ToDo: Add implementation once hierarchy exists in FCS Viewer

    def find_object_from_viewer_by_name(self, name: str) -> list:
        """
        Returns all objects that can be found under the specified under
        the specified name.

        Legacy functionality: `salome.myStudy.FindObjectByName(self.name,'GEOM')[0]`
        """
        if not self.is_available: return []

        msg_request = {
            "operation":"find_object_by_name",
            "arguments":{
                "search_name": name
                }
            }

        dict_result = self.__try_send_request(self.viewer_request_url, msg_request)

        if dict_result["status"]: 
            list_result_ids = list(dict_result["result"]["IDs"])
        else:
            list_result_ids = []

        # ToDo: Use the FCS Viewer's document to access the GEOM_Object
        return list_result_ids
    
    def object_to_id(self, obj: object) -> int:
        """
        Returns ID for any FCS object.
        This only returns a positive integer if the object
        has been added to the FCS Viewer.

        Legacy functionality: `geompy.getObjectID(i_Face))`
        """
        if not self.is_available: return -1

        # ToDo: Need to extend the GEOM_Object to store
        # GUIDs unique to every single GEOM_Object

        #msg_request = {
        #    "operation":"object_to_id",
        #    "arguments":{
        #        "object_guid": obj.get_guid()
        #        }
        #    }

        #dict_result = self.__try_send_request(msg_request)
        return -1


    def set_specific_object_colour(self, id: int, red: int, green: int, blue: int) -> None:
        """
        Colours object in viewer. 
        Input are RGB integers between 0 to 255.

        Legacy functionality: `SALOMEDS.SetColor(i_Face, list_RGB))`
        """

        if not self.is_available: return

        print(f"Set colour to input : {id},{red},{green},{blue}")
        # Create paint 
        colour = Palette.get_specific_colour(red, green, blue)

        # Set colour
        self.document_operator.set_object_colour(id, colour)

        # Inform viewer
        msg_request = {
            "operation":"set_object_colour",
            "arguments":{
                "fname" : "colorModel",
                "item_id" : str(id),
                "red": colour.R,
                "green" : colour.G,
                "blue" : colour.B
                }
            }

        msg_response = self.__try_send_request(self.viewer_request_url, msg_request)

    def set_object_colour(self, id: int, selected_colour: ColourSelection) -> None:
        """
        Colours object in viewer.

        Input is a specific colour that is available in the selection.
        """
        if not self.is_available: return

        # Create paint
        colour = Palette.get_colour(selected_colour)

        # Set colour
        self.document_operator.set_object_colour(id, colour)        

        # SEND data to viewer
        msg_request = {
            "operation":"set_object_colour",
            "arguments":{
                "fname" : "colorModel",
                "item_id" : str(id),
                "red": colour.R,
                "green" : colour.G,
                "blue" : colour.B
                }
            }

        msg_response = self.__try_send_request(self.viewer_request_url, msg_request)


    def __try_send_request(self, viewer_url: str, request: dict) -> dict:
        """
        Private method to try forward request to cloud viewer.
        """

        dict_result = {
            "status": False
            }
        
        try:
            response = requests.post(viewer_url, json=request)
            dict_result = dict(response)
        except:
            dict_result = {
                "status": False
                }

        return dict_result

    def __setup_temp_folder(self):
        """
        Creates a Femsolve Kft folder if it does not yet exist.
        Returns path to AppData folder. This is only done on Windows.
        """

        str_tmp_path = ""

        if self.is_available:

            if self.platform == "win32":

                str_app_data = os.getenv('APPDATA')
                str_tmp_path = f"{str_app_data}/Femsolve Kft/{self.plugin_name}"

                if not os.path.isdir(str_tmp_path):
                    os.mkdir(str_tmp_path)

            elif self.platform == "linux":
                # ToDo: This would need to be in an environment file
                str_tmp_path = f"{os.path.abspath(os.path.dirname(__file__))}/../../FCS.Cloud/LinuxAppData/{self.plugin_name}"

                if not os.path.isdir(str_tmp_path):
                    os.mkdir(str_tmp_path)
                    print(f"Created temporary folder for STEP exports : {str_tmp_path}!")
        
        else:

            print("\n !!! WARNING !!! Because no viewer is attached to external application there will not be any model files exported"
                   +" (and thus no temporary work path is setup). Note in Batch mode, unless the user manually saves the document"
                   +" no results will be saved! \n")

        return str_tmp_path



