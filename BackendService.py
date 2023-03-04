
from FCSViewer import FCSViewer
from FCSViewer import GeometryBuilder, gb
from FCSViewer import DocumentBuilder

class BackendService(object):
    """
    Template class for hosting specific plugins.
    """

    def __init__(self, app_guid: str):
        """
        Constructor.
        """
        self.app_guid = app_guid
        self.fv: FCSViewer
        self.db: DocumentBuilder
        self.gb: GeometryBuilder

    def set_existing_services(self, fcs_viewer: FCSViewer) -> None: 
        """
        To any backend service connect we pass on the instances of the main operators.
        """

        self.fv = fcs_viewer
        self.gb = gb
        self.db = self.fv.db

    def run_command(self, command_name: str, command_args: dict={}) -> bool:
        """
        Returns true, if the command was found and run (even if it failed).
        Return false otherwise.
        """
        try:
            command_ptr = getattr(self, command_name)
            command_ptr(command_args)
        except AttributeError:
            print(f'Could not find {command_name}!')
            return False
        except Exception as ex:
            print(f'Something failed: {ex.args}!')
        finally:
            return True

#--------------------------------------------------------------------------------------------------
# Pure virtual methods that require implementation
#--------------------------------------------------------------------------------------------------

    def get_available_callbacks(self) -> list:
        """
        List of available callbacks to be forwarded to the listeners of the cloud application.
        """
        raise NotImplementedError("`get_available_callbacks` needs to be implemented in the base class!")
