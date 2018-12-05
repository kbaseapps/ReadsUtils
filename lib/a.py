from installed_clients.baseclient import ServerError as WorkspaceError
from installed_clients.baseclient import ServerError as DFUError
from installed_clients.baseclient import ServerError

def apple():
    raise ServerError("1","2","3","4")

try:
    apple()
except WorkspaceError as e:
    print "This is a workspace error message!"
    print(e)
except DFUError as e:
    print "This is a DFU error message!"
    print(e)
except ServerError as e:
    print "This is a Server error message!"
    print(e)
