import os 
import re
import csv
import pathlib
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from enum import Enum
import uuid
from parseExamDirective import ExamDirectiveType, splitDirective, parseDirective

def handleSubmissions(filenames, students, source_path, output_path):
    allProblems = {}
    for studentID, filename in filenames.items():
        if studentID not in students:
            print('Skipping unknown student with ID {}'.format(studentID))
            continue

        submissionNotebook = getNotebook(filename)
        problemIDs = getProblemIDs(submissionNotebook)

        for problemID in problemIDs:
            if problemID not in allProblems:
                allProblems[problemID] = {}
            allProblems[problemID][studentID] = getNotebookProblemCells(problemID, submissionNotebook, problemIDs)

    sourceNotebook = getNotebook(source_path)
    sourceNotebookProblemIDs = getSourceNotebookProblemIDs(sourceNotebook)

    for problemID in allProblems:
        problemNotebook = nbformat.v4.new_notebook()

        sourceNotebookProblemCells = getNotebookProblemCells(problemID, sourceNotebook, sourceNotebookProblemIDs, True)
        testCells = getTestCells(problemID, sourceNotebook)
        solutionCells = getSolutionCells(problemID, sourceNotebook)

        problemNotebook.cells += generateProblemNotebookHeaders(problemID, solutionCells, [sourceNotebookProblemCells[0]])

        # print('PROBLEM {}'.format(problemID))
        for studentID, studentCells in sorted(allProblems[problemID].items(), key = lambda x: students[x[0]]['SIS Login ID']):
            student = students[studentID]
            # print('\tstudent {}'.format(student['Student']))

            toAddForStudent = []
            toAddForStudent += generateStudentProblemNotebookHeaders(student, problemID)
            toAddForStudent += removeProblemDescriptionCell(problemID, getNonTestCells(studentCells, testCells))
            toAddForStudent += [cloneCell(cell) for cell in testCells]

            toAddForStudent += generateStudentProblemNotebookFooters(student, problemID, 'TODO')

            for cell in studentCells:
                cell['metadata']['studentID'] = studentID
            
            problemNotebook.cells += toAddForStudent
        

        # print([type(c) for c in problemNotebook.cells])
        fullNotebookPath = os.path.join(output_path, 'problems', '{}.ipynb'.format(problemID))

        executeNotebook(problemNotebook)

        pathlib.Path(os.path.join(output_path, 'problems')).mkdir(parents=True, exist_ok=True)
        nbformat.write(problemNotebook, fullNotebookPath)

        print('Wrote {}'.format(fullNotebookPath))

def removeProblemDescriptionCell(problemID, cells):
    result = []
    for cell in cells:
        cellMetadata = cell['metadata']
        cellSourceID = cellMetadata['source-id'] if 'source-id' in cellMetadata else None
        if cellSourceID != problemID:
            result.append(cell)

    return result


def getNonTestCells(studentCells, sourceNotebookTestCells):
    result = []
    sourceNotebookTestCellIDs = [cell['metadata']['id'] for cell in sourceNotebookTestCells]
    for cell in studentCells:
        cellMetadata = cell['metadata']
        cellSourceID = cellMetadata['source-id'] if 'source-id' in cellMetadata else None
        if cellSourceID not in sourceNotebookTestCellIDs:
            result.append(cell)

    return result


def generateProblemNotebookHeaders(problemID, solutionCells, extraCells=[]):
    cells = []
    cells += [ nbformat.v4.new_markdown_cell('# {}'.format(problemID)) ]
    cells += extraCells
    cells += [ nbformat.v4.new_markdown_cell('## Sample Solution:') ]
    cells += solutionCells
    cells += [ nbformat.v4.new_markdown_cell('---\n---\n---\n\n') ]

    return cells

def generateStudentProblemNotebookHeaders(student, problemID):
    return [ nbformat.v4.new_markdown_cell('# {}'.format(student['SIS Login ID'])) ]

def generateStudentProblemNotebookFooters(student, problemID, presetScore):
    sid = student['SIS Login ID']

    gradeCell = nbformat.v4.new_markdown_cell('..grade {}\n\n{}'.format(sid, presetScore))
    commentsCell = nbformat.v4.new_markdown_cell('..comments {}\n\n'.format(sid))

    return [ gradeCell, commentsCell, nbformat.v4.new_markdown_cell('---\n'*2) ]

def cloneCell(cell):
    return nbformat.notebooknode.NotebookNode(
        cell_type = cell['cell_type'],
        source = cell['source'],
        metadata = nbformat.notebooknode.NotebookNode(cell['metadata'])
    )

current_path = os.path.dirname(os.path.realpath(__file__))

def hasDirectiveType(cell, desiredDirectiveType):
    directive, source = splitDirective(cell['cell_type'], cell['source'])
    directiveType = directive['type'] if directive else None
    return directiveType == desiredDirectiveType

def getCellsWithDirective(problemID, sourceNotebook, directiveType):
    allProblemIDs = getSourceNotebookProblemIDs(sourceNotebook)
    problemCells = getNotebookProblemCells(problemID, sourceNotebook, allProblemIDs, True)
    return [cell for cell in problemCells if hasDirectiveType(cell, directiveType)]

def getTestCells(problemID, sourceNotebook):
    return getCellsWithDirective(problemID, sourceNotebook, ExamDirectiveType.TEST)

def getSolutionCells(problemID, sourceNotebook):
    return getCellsWithDirective(problemID, sourceNotebook, ExamDirectiveType.SOLUTION)


def getSourceNotebookProblemIDs(sourceNotebook):
    return [ cell['metadata']['id'] for cell in sourceNotebook['cells'] if hasDirectiveType(cell, ExamDirectiveType.PROBLEM)]

def getNotebookProblemCells(problemID, notebook, allProblemIDs, isSourceNotebook=False):
    includedCells = []
    isPartOfProblem = False
    for cell in notebook['cells']:
        cellMetadata = cell['metadata']
        cellID = cellMetadata['id'] if 'id' in cellMetadata else None
        cellSourceID = cellID if isSourceNotebook else (cellMetadata['source-id'] if 'source-id' in cellMetadata else None)

        if cellSourceID == problemID:
            isPartOfProblem = True
        elif isPartOfProblem and (cellSourceID in allProblemIDs):
            isPartOfProblem = False
            break
        
        if isPartOfProblem:
            includedCells.append(cell)

    return includedCells


def getProblemIDs(notebook):
    return notebook['metadata']['exam_gen_problems']

def readNotebooks(paths):
    for path in paths:
        readNotebook(path)

def executeNotebook(nb):
    client = NotebookClient(nb, timeout=600, kernel_name='python3')
    client.setup_kernel()

    with client.setup_kernel():
        for index, cell in enumerate(nb.cells):
            if cell['cell_type'] == 'code':
                try:
                    result = client.execute_cell(cell, index)
                    outputs = result['outputs']
                except CellExecutionError as e:
                    pass
                    # print(e)
        client.km.shutdown_kernel()

def getNotebook(path):
    return nbformat.read(path, as_version=4)


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
        
directivePrefix = '..'

def processGradedProblems(csv_path, relative_path, problems_path, output_path):
    print(csv_path, relative_path, problems_path, output_path)
    student_grades = {}
    full_problems_path = os.path.join(relative_path, problems_path)
    problems_files = os.listdir(full_problems_path)
    for problem_file in problems_files:
        if os.path.isdir(problem_file): continue
        fullpath = os.path.join(full_problems_path, problem_file)
        nb = nbformat.read(fullpath, as_version=4)
        problem_id = problem_file.split(".")[0]
        for cell in nb.cells:
            try:
                directive,source = splitDirective(cell['cell_type'], cell['source'].strip())
            except Exception as e:
                print('problem in file {}'.format(problem_file))
                print(e)
                print()
            if directive:
                directive_type = directive['type']
                if directive_type == ExamDirectiveType.GRADE:
                    if source.strip():
                        student = directive['student-id']
                        try:
                            value = float(source)
                            if value.is_integer():
                                value = int(value)
                            if student not in student_grades:
                                student_grades[student] = {
                                    'problems': {}
                                }
                            if problem_id not in student_grades[student]['problems']:
                                student_grades[student]['problems'][problem_id] = {}
                            student_grades[student]['problems'][problem_id]['grade'] = value
                        except Exception as e:
                            print('Problem in file {} for student {}'.format(problem_file, student))
                            print(e)
                            print()
                            continue
                elif directive_type == ExamDirectiveType.COMMENTS:
                    student = directive['student-id']
                    if source.strip():
                        if student not in student_grades:
                            student_grades[student] = {
                                'problems': {}
                            }
                        if problem_id not in student_grades[student]['problems']:
                            student_grades[student]['problems'][problem_id] = {}
                        student_grades[student]['problems'][problem_id]['comments'] = source.strip()
    output_rows = []
    full_csv_path = os.path.join(relative_path, csv_path)
    problem_issues = {}
    with open(full_csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            sid = row['uniquename']
            if sid in student_grades:
                submission_file_path = os.path.join(relative_path, row['submission'])
                submission = nbformat.read(submission_file_path, as_version=4)
                problems = submission.metadata['exam_gen_problems']
                grades = student_grades[sid]['problems']
                feedback = []
                overallGrade = 0
                for index,problem in enumerate(problems):
                    if problem in grades:
                        grade = grades[problem]
                        if 'grade' in grade:
                            gradeValue = grade['grade']
                            overallGrade += gradeValue

                            if 'comments' in grade:
                                gradeComments = grade['comments']
                                feedback.append('Problem {}: {} points\n{}'.format(index, gradeValue, gradeComments))
                            elif gradeValue:
                                feedback.append('Problem {}: {} points'.format(index, gradeValue))
                            feedback.append('')
                        else:
                            if problem not in problem_issues:
                                problem_issues[problem] = []
                            problem_issues[problem].append('Could not parse grade for {}'.format(sid, problem))
                    else:
                        if index > 0 and index <= 23:
                            if problem not in problem_issues:
                                problem_issues[problem] = []
                            problem_issues[problem].append('Could not find feedback for {}'.format(sid, problem))
                            # if problem != '348cb33d-a7e9-47dd-b10b-f36f74abf078':
                                # print('Missing grade for {} for problem {}'.format(sid, problem))
                output_rows.append({
                    'uniquename': sid,
                    'grade': overallGrade,
                    'feedback': '\n'.join(feedback)
                })
    for problem, issues in problem_issues.items():
        print('PROBLEM {}:'.format(problem))
        print('\n'.join(sorted(issues)))
        print('\n\n')
    output_rows.sort(key = lambda d: d['uniquename'])
    full_output_path = os.path.join(relative_path, output_path)

    with open(full_output_path, 'w') as csvfile:
        fieldnames=['uniquename', 'grade', 'feedback']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)

    print('wrote {}'.format(full_output_path))
    # print(student_grades)
    #     first_cell_source = nb.cells[0].source
    #     line = first_cell_source.splitlines()[3]
    #     print(line)
    #     m = re.findall("This exam is for .* \((.*)\)\.", line)
    #     if m:
    #         m = m[0]
    #         os.rename(fullpath, os.path.join(rp, '{}_final_exam.ipynb'.format(m)))
