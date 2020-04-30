import os 
import re
import csv
import pathlib
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

current_path = os.path.dirname(os.path.realpath(__file__))

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



def processCSV(csv_path, relative_path, source_notebook_path):
    source_nb = nbformat.read(os.path.join(relative_path, source_notebook_path), as_version=4)
    full_csv_path = os.path.join(relative_path, csv_path)
    # rp = '/home/soney/106_W20/final_exam/submissions'
    # submissions = os.listdir(rp)
    # for submission in submissions:
    #     if os.path.isdir(submission): continue
    #     fullpath = os.path.join(rp, submission)
    #     nb = nbformat.read(fullpath, as_version=4)
    #     first_cell_source = nb.cells[0].source
    #     line = first_cell_source.splitlines()[3]
    #     print(line)
    #     m = re.findall("This exam is for .* \((.*)\)\.", line)
    #     if m:
    #         m = m[0]
    #         os.rename(fullpath, os.path.join(rp, '{}_final_exam.ipynb'.format(m)))
    problem_map = {}
    with open(full_csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            sid = row['uniquename']
            submission_file_path = os.path.join(relative_path, row['submission'])
            tests_file_path = os.path.join(relative_path, row['tests'])
            if os.path.isfile(submission_file_path) and os.path.isfile(tests_file_path):
                submission = nbformat.read(submission_file_path, as_version=4)
                tests = nbformat.read(tests_file_path, as_version=4)

                gen_problems = submission.metadata['exam_gen_problems']
                for problem_id in gen_problems:
                    
                    test_cells_source_ids = []
                    do_append = False
                    for cell in source_nb.cells:
                        if 'id' in cell.metadata:
                            source_cell_id = cell.metadata['id']
                            if source_cell_id in gen_problems:
                                if source_cell_id == problem_id:
                                    do_append = True
                                else:
                                    do_append = False
                            if do_append:
                                test_cells_source_ids.append(source_cell_id)
                    test_cells = [ cell for cell in tests.cells if ('source-id' in cell.metadata and cell.metadata['source-id'] in test_cells_source_ids)]
                    incorporated_test_cell_source_ids = [cell.metadata['source-id'] for cell in test_cells]

                    submission_cells = []

                    do_append = False
                    for cell in submission.cells:
                        if 'source-id' in cell.metadata:
                            cell_source_id = cell.metadata['source-id']
                            if cell_source_id in gen_problems:
                                if cell_source_id == problem_id:
                                    do_append = True
                                else:
                                    do_append = False
                            if do_append:
                                if cell_source_id not in incorporated_test_cell_source_ids: # no need for duplicates
                                    submission_cells.append(cell)
                    
                    if problem_id not in problem_map:
                        problem_map[problem_id] = {'students': []}

                    problem_map[problem_id]['students'].append({
                        'sid': sid,
                        'submission-cells': submission_cells,
                        'test-cells': test_cells
                    })
    for problem_id, problem_infos in problem_map.items():
        notebook = nbformat.v4.new_notebook()
        notebook_header = nbformat.v4.new_markdown_cell('# {}\n\n---\n---\n---\n'.format(problem_id))

        notebook.cells.append(notebook_header)

        for problem_info in problem_infos['students']:
            sid = problem_info['sid']
            submission_cells = problem_info['submission-cells']
            test_cells = problem_info['test-cells']
            header_cell = nbformat.v4.new_markdown_cell('# {}'.format(sid))
            grade_cell = nbformat.v4.new_markdown_cell('..grade {}\n\n'.format(sid))
            comments_cell = nbformat.v4.new_markdown_cell('..comments {}\n\n'.format(sid))
            footer_cell = nbformat.v4.new_markdown_cell('---\n'*3)
            all_cells = [header_cell] + submission_cells + test_cells + [grade_cell, comments_cell, footer_cell]

            notebook.cells += all_cells
        
        pathlib.Path(os.path.join(relative_path, 'problems')).mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, os.path.join(relative_path, 'problems', '{}.ipynb'.format(problem_id)))
        
