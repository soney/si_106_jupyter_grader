import nbformat
import random
import os
from copy import copy,deepcopy
from .parseExamDirective import splitDirective, ExamDirectiveType
from pprint import pprint
import ast
import pathlib
import uuid

# https://stackoverflow.com/questions/39379331/python-exec-a-code-block-and-eval-the-last-line
def exec_then_eval(code):
    block = ast.parse(code, mode='exec')

    # assumes last node is an expression
    last = ast.Expression(block.body.pop().value)

    _globals, _locals = {}, {}
    exec(compile(block, '<string>', mode='exec'), _globals, _locals)
    return eval(compile(last, '<string>', mode='eval'), _globals, _locals)

def generateNotebooks(notebook_path, output_path):
    addUUIDs(notebook_path)
    sourceNotebook = nbformat.read(notebook_path, as_version=4)
    examStructure = getExamStructure(sourceNotebook)
    examInfos = getExamInfos(sourceNotebook, notebook_path)
    for examInfo in examInfos:
        filename = examInfo['filename']
        cells,cellMetadata,tests,testMetadata,solutions,solutionsMetadata = generateNotebook(examStructure, sourceNotebook, examInfo)

        exams_dir = os.path.join(output_path, 'exams')
        tests_dir = os.path.join(output_path, 'tests')
        solutions_dir = os.path.join(output_path, 'solutions')

        pathlib.Path(exams_dir).mkdir(parents=True, exist_ok=True)
        pathlib.Path(tests_dir).mkdir(parents=True, exist_ok=True)
        pathlib.Path(solutions_dir).mkdir(parents=True, exist_ok=True)
        nbformat.write(cellListToNotebook(cells, cellMetadata), os.path.join(exams_dir, filename))
        nbformat.write(cellListToNotebook(tests, testMetadata), os.path.join(tests_dir, filename))
        nbformat.write(cellListToNotebook(solutions, solutionsMetadata), os.path.join(solutions_dir, filename))
        print('Wrote {}'.format(filename))

def generateSamples(notebook_path, output_path):
    sourceNotebook = nbformat.read(notebook_path, as_version=4)
    examStructure = getExamStructure(sourceNotebook)
    maxAlternatives = getMaxAlternatives(examStructure)
    examInfos = getExamInfos(sourceNotebook, notebook_path)

    for examInfo in examInfos:
        for i in range(maxAlternatives):
            filename = str(i)+'-'+examInfo['filename']
            cells,cellMetadata,tests,testMetadata,solutions,solutionsMetadata = generateNotebook(examStructure, sourceNotebook, examInfo, shuffle=lambda x:x, choice=lambda L:indexOr(L, i))
            exams_dir = os.path.join(output_path, 'sample-exams')
            pathlib.Path(exams_dir).mkdir(parents=True, exist_ok=True)
            nbformat.write(cellListToNotebook(cells), os.path.join(exams_dir, filename))

def cellListToNotebook(cells, metadata={}):
    notebook = nbformat.v4.new_notebook()
    cellObjects = []
    for cell in cells:

        if cell['cell_type'] == 'markdown':
            newCell = nbformat.v4.new_markdown_cell(cell['source'])
        elif cell['cell_type'] == 'code':
            newCell = nbformat.v4.new_code_cell(cell['source'])
        elif cell['cell_type'] == 'raw':
            newCell = nbformat.v4.new_raw_cell(cell['source'])
        else:
            newCell = None

        if newCell:
            newCell['metadata'] = {
                'id': str(uuid.uuid4()),
                'source-id': cell['metadata']['id']
            }
            cellObjects.append(newCell)

    notebook['cells'] = cellObjects

    for k,v in metadata.items():
        notebook['metadata'][k] = v

    return notebook

def getMaxAlternatives(examStructure):
    maxAlternatives = 0
    for group in examStructure:
        problems = list(group['problems'].values())
        for problem in problems:
            numAlternatives = len(problem['alternatives'])
            if numAlternatives > maxAlternatives:
                maxAlternatives = numAlternatives
    return maxAlternatives

def indexOr(seq, idx, alt=random.choice):
    return seq[idx] if idx<len(seq) else alt(seq)

def generateNotebook(examStructure, sourceNotebook, providedEnv={}, shuffle=random.shuffle, choice=random.choice):
    cells = []
    cellMetadata = deepcopy(sourceNotebook['metadata'])
    tests = []
    testMetadata = deepcopy(sourceNotebook['metadata'])
    solutions = []
    solutionsMetadata = deepcopy(sourceNotebook['metadata'])
    problemIDs = []
    env = {
        'problem': 1,
        'points': 0
    }
    totalPoints = 0
    totalProblems = 0
    for key,val in providedEnv.items():
        env[key] = val

    for group in examStructure:
        problems = list(group['problems'].values())
        shuffle(problems)

        for problem in problems:
            directive = problem['directive']
            if directive and directive['type'] == ExamDirectiveType.PROBLEM:
                points = directive['points']
                env['points'] = points
                totalPoints += points
                totalProblems += 1

            selectedAlternative = choice(problem['alternatives'])
            problemIDs.append(selectedAlternative['id'])

            for cell in selectedAlternative['cells']:
                cellCopy = copy(cell)
                for key in env:
                    cellCopy['source'] = cellCopy['source'].replace('@'+key+'', str(env[key]))
                cells.append(cellCopy)
            for test in selectedAlternative['tests']:
                tests.append(copy(test))
            for solutionCell in selectedAlternative['solutionCells']:
                solutionCellCopy = copy(solutionCell)
                for key in env:
                    solutionCellCopy['source'] = solutionCellCopy['source'].replace('@'+key+'', str(env[key]))
                solutions.append(solutionCellCopy)

            if directive['type'] == ExamDirectiveType.PROBLEM:
                env['problem'] += 1

    env['totalpoints'] = totalPoints
    env['totalproblems'] = totalProblems

    for cell in cells:
        for key in ['totalpoints', 'totalproblems']:
            cell['source'] = cell['source'].replace('@'+key+'', str(env[key]))

    cellMetadata['exam_gen_problems'] = problemIDs

    return cells, cellMetadata, tests, testMetadata, solutions, solutionsMetadata

def getExamInfos(nb, notebook_path):
    for cell in nb.cells:
        cell_type = cell['cell_type']
        source = cell['source']
        if cell_type == 'code':
            directive, newSource = splitDirective(cell_type, source)
            if directive and directive['type'] == ExamDirectiveType.EXAMS:
                result = exec_then_eval(newSource)

                resultList = []

                for index, item in enumerate(result):
                    if type(item) == type({}):
                        if 'filename' not in item:
                            item['filename'] = '{}.ipynb'.format(index)
                        resultList.append(item)
                    else:
                        resultList.append({
                            'filename': str(item)
                        })
                return resultList
    if notebook_path:
        return [{ 'filename': os.path.basename(notebook_path) }]
    else:
        return [{ 'filename': 'out.ipynb'}]

def addUUIDs(notebook_path):
    nb = nbformat.read(notebook_path, as_version=4)
    for cell in nb.cells:
        metadata = cell['metadata']
        if 'id' not in metadata:
            metadata['id'] = str(uuid.uuid4())
    nbformat.write(nb, notebook_path)

def getExamStructure(nb):
    cellsAndDirectives = []
    for cell in nb.cells:
        cell_type = cell['cell_type']
        source = cell['source']
        directive, newSource = splitDirective(cell_type, source)

        cellCopy = copy(cell)
        cellCopy['source'] = newSource
        cellsAndDirectives.append((directive, cellCopy))
    
    notebookGroups = []
    currentGroup = False
    currentProblem = False
    currentAlternative = False
    for directive,cell in cellsAndDirectives:
        cellID = cell['metadata']['id']
        if directive == False:
            if currentAlternative:
                currentAlternative['cells'].append(cell)
                currentAlternative['solutionCells'].append(cell)
            else:
                notebookGroups.append({
                    'problems': {
                        None: {
                            'directive': directive,
                            'alternatives': [{
                                'id': cellID,
                                'cells': [cell],
                                'solutionCells': [cell],
                                'tests': []
                            }]
                        }
                    }
                })
        elif directive['type'] == ExamDirectiveType.ALWAYS_INCLUDE:
            currentAlternative = {
                'id': cellID,
                'cells': [cell],
                'solutionCells': [cell],
                'tests': []
            }
            currentProblem = {
                'directive': directive,
                'alternatives': [currentAlternative]
            }
            currentGroup = {
                'problems': { None: currentProblem }
            }
            notebookGroups.append(currentGroup)
        elif directive['type'] == ExamDirectiveType.PROBLEM:
            if currentProblem and currentProblem['directive']['type'] == directive['type'] and currentProblem['directive']['group'] == directive['group']:
                currentAlternative = {
                    'id': cellID,
                    'cells': [cell],
                    'solutionCells': [cell],
                    'tests': []
                }

                if directive['id'] in currentGroup['problems']:
                    currentGroup['problems'][directive['id']]['alternatives'].append(currentAlternative)
                else:
                    currentGroup['problems'][directive['id']] = {
                        'directive': directive,
                        'alternatives': [currentAlternative]
                    }
            else:
                currentAlternative = {
                    'id': cellID,
                    'cells': [cell],
                    'solutionCells': [cell],
                    'tests': []
                }
                currentProblem = {
                    'directive': directive,
                    'alternatives': [currentAlternative]
                }
                currentGroup = {
                    'problems': {directive['id']: currentProblem}
                }
                notebookGroups.append(currentGroup)
        elif directive['type'] == ExamDirectiveType.TEST:
            if directive['visible']:
                currentAlternative['cells'].append(cell)

            currentAlternative['tests'].append(cell)
            currentAlternative['solutionCells'].append(cell)
        elif directive['type'] == ExamDirectiveType.SOLUTION:
            currentAlternative['solutionCells'].append(cell)
        elif directive['type'] == ExamDirectiveType.EXAMS:
            continue
    return notebookGroups

def directiveMatches(d1, d2):
    if d1 == d2:
        return True
    elif (d1 == False and d2['type'] == ExamDirectiveType.ALWAYS_INCLUDE) or (d2 == False and d1['type'] == ExamDirectiveType.ALWAYS_INCLUDE):
        return True
    else:
        return d1 == d2