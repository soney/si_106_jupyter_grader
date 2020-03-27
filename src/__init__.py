import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from consolemenu import *
from consolemenu.items import *

def readNotebooks(paths):
    for path in paths:
        readNotebook(path)

def readNotebook(path):
    # with open(path, 'r') as f:

    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(nb, timeout=600, kernel_name='python3')
    client.setup_kernel()

    with client.setup_kernel():
        for index, cell in enumerate(nb.cells):
            if cell['cell_type'] == 'code':
                try:
                    result = client.execute_cell(cell, index)
                    outputs = result['outputs']
                    print(outputs)
                except CellExecutionError as e:
                    print('error')
                    # print(e)
        client.km.shutdown_kernel()