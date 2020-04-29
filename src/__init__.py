import os.path
import csv
import json
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from consolemenu import *
from consolemenu.items import *
from pprint import pprint
import pathlib
from shutil import copyfile

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

rain_snow_solution = '''
def getCol(forYear, col):
    with open('aa_weather.csv', 'r') as aa_weather_file:
        for line in aa_weather_file.readlines()[1:]:
            cells = line.split(',')
            year = int(cells[0])
            if year == forYear:
                return float(cells[col])
def getRain(forYear): return getCol(forYear, 1)
def getSnow(forYear): return getCol(forYear, 2)
'''
    
def readCSV(csv_path, relative_path):
    wrongByStudent = {}
    with open(csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            exam_path = row['Exam']
            test_path = row['Test']
            full_exam_path = os.path.join(relative_path, exam_path)
            full_test_path = os.path.join(relative_path, test_path)

            exam_nb = nbformat.read(full_exam_path, as_version=4)
            # test_nb = nbformat.read(full_test_path, as_version=4)

            exam_cell_count = len(exam_nb.cells)

            # exam_nb.cells += test_nb.cells

            basename = os.path.basename(exam_path)
            username = basename[:basename.find('_')]
            correct = 0
            incorrect = 0
            palindromeProblemCount = 0

            # exam_client = NotebookClient(exam_nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': relative_path}})

            found_rs_assert = False
            rs_index = -1
            assertions_next = False
            for index,cell in enumerate(exam_nb.cells):
                if cell['cell_type'] == 'markdown' or cell['cell_type'] == 'raw':
                    if '(part 2)' in cell['source']:
                        assertions_next = True
                elif cell['cell_type'] == 'code' and assertions_next and ('assert' in cell['source']) :
                    found_rs_assert = cell
                    rs_index = index
                    assertions_next = False
            if found_rs_assert != False:
                exam_client = NotebookClient(exam_nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': relative_path}})
                with exam_client.setup_kernel():
                    solution_cell = nbformat.from_dict({
                        'cell_type': 'code',
                        'source': rain_snow_solution,
                        'metadata': {}
                    })
                    exam_nb.cells.append(solution_cell)
                    exam_client.execute_cell(solution_cell, len(exam_nb.cells)-1)
                    solution_passed = True
                    try:
                        exam_client.execute_cell(found_rs_assert, rs_index)
                    except CellExecutionError as e:
                        solution_passed = False
                        # return
                    print("""
## {}
{}

```python
{}
```

---
                    """.format(username, '' if solution_passed else 'FAILED', found_rs_assert['source']))
                exam_client.km.shutdown_kernel()
            # else:
                # print(found_rs_assert['source'])


            continue

            incorrect_answers = []
            signatures = {}
            with exam_client.setup_kernel():
                for index,cell in enumerate(exam_nb.cells):
                    if cell['cell_type'] == 'code':
                        try:
                            cellSignature = getCellSignature(cell['source'])
                            if len(cellSignature) == 1:
                                signatures[cellSignature[0]] = cell
                            elif len(cellSignature) > 1:
                                pass
                                # print(cellSignature)
                            # print(cell['source'])
                            # print(index)
                            isPalindromeProblem = False
                            if 'longestPalindrome' in cell['source'] and 'def' not in cell['source'] and 'assert' in cell['source']:
                                isPalindromeProblem = True
                                palindromeProblemCount+=1
                            if 'biggestPalindrome' in cell['source'] and 'def' not in cell['source'] and 'assert' in cell['source']:
                                isPalindromeProblem = True
                                palindromeProblemCount+=1
                            result = exam_client.execute_cell(cell, index)
                            # outputs = result['outputs']
                            # print(outputs)
                            if index >= exam_cell_count or isPalindromeProblem:
                                correct += 1
                        except CellExecutionError as e:
                            if index >= exam_cell_count or isPalindromeProblem:
                                if len(cellSignature) == 1:
                                    group, problemName = cellSignature[0]
                                    if problemName not in wrongByStudent:
                                        wrongByStudent[problemName] = []
                                    if username not in wrongByStudent[problemName]:
                                        wrongByStudent[problemName].append(username)
                                    # if ('exams', problemName) in signatures:
                                    #     solutionCell = signatures[('exams', problemName)]
                                    # else:
                                    #     print('NF', cellSignature)
                                else:
                                    print(cellSignature)
                                incorrect += 1
                                # print(e)
                            # print('error')
                exam_client.km.shutdown_kernel()
            print('processed {}'.format(username))
            # print('{}: {} of {}'.format(username, correct, correct+incorrect))
    pprint(wrongByStudent)

def getCellSignature(source):
    passedTests = []
    for group, tests in problemSignatures.items():
        for name,test in tests.items():
            if test(source):
                passedTests.append((group, name))
    return passedTests

def checkIsTupleAssignment(s, vars):
    for line in s.splitlines():
        if all([ v in line for v in vars]):
            return True
    return False

hgroupings = [
    ('abc', 'xyz'),
    ('myDict2', 'myDict3'),
    ('square', 'plusOne'),
    ('keyCount', 'wordCount'),
    ('add', 'mul'),
    ('ageRankings', 'warmCityRankings'),
    ('showRatings', 'carPrices'),
    ('createPhonebook', 'createAddressbook'),
    ('longestPalindrome', 'biggestPalindrome'),
    ('shortestWordWithout', 'shortestWordWithoutVowel'),
    ('getCountryCapital', 'getCountryArea'),
    ('getRain', 'getSnow'),
]
problemSignatures = {
    'exams': {
        'abc': lambda s: checkIsTupleAssignment(s, ['a', 'b', 'c', ',', '=']) and ('def' not in s) and ('assert' not in s) and len(s.splitlines()) <=3,
        'xyz': lambda s: checkIsTupleAssignment(s, ['x', 'y', 'z', ',', '=']) and ('def' not in s) and ('assert' not in s) and len(s.splitlines()) <=3,
        'myDict2': lambda s: ('{' in s) and ('myDict2' in s) and ('def' not in s) and ('assert' not in s),
        'myDict3': lambda s: ('{' in s) and ('myDict3' in s) and ('def' not in s) and ('assert' not in s),
        'square': lambda s: ('square' in s) and ('def' in s) and ('assert' not in s),
        'plusOne': lambda s: ('plusOne' in s) and ('def' in s) and ('assert' not in s),
        'keyCount': lambda s: ('keyCount' in s) and ('def' in s) and ('assert' not in s),
        'wordCount': lambda s: ('wordCount' in s) and ('def' in s) and ('assert' not in s),
        'add': lambda s: ('def add' in s) and ('def' in s) and ('assert' not in s),
        'mul': lambda s: ('mul' in s) and ('def' in s) and ('assert' not in s),
        'ageRankings': lambda s: ('personInfo' in s) and ('ageRankings' in s),
        'warmCityRankings': lambda s: ('cityInfo' in s) and ('warmCityRankings' in s),
        'showRatings': lambda s: ('shows' in s) and ('showRatings' in s),
        'carPrices': lambda s: ('cars' in s) and ('carPrices' in s),
        'createPhonebook': lambda s: ('createPhonebook' in s) and ('def' in s),
        'createAddressbook': lambda s: ('createAddressbook' in s) and ('def' in s),
        'longestPalindrome': lambda s: ('longestPalindrome' in s) and ('def' in s),
        'biggestPalindrome': lambda s: ('biggestPalindrome' in s) and ('def' in s),
        'shortestWordWithout': lambda s: ('shortestWordWithout' in s) and ('def' in s) and ('shortestWordWithoutVowel' not in s),
        'shortestWordWithoutVowel': lambda s: ('shortestWordWithoutVowel' in s) and ('def' in s),
        'getCountryCapital': lambda s: ('getCountryCapital' in s) and ('def' in s),
        'getCountryArea': lambda s: ('getCountryArea' in s) and ('def' in s),
        'getRain': lambda s: ('getRain' in s) and ('def' in s),
        'getSnow': lambda s: ('getSnow' in s) and ('def' in s),
    },
    'tests': {
        'abc': lambda s: ('a == 1' in s) and ('def' not in s) and ('assert' in s),
        'xyz': lambda s: ('x == 1' in s) and ('def' not in s) and ('assert' in s),
        'myDict2': lambda s:  ('myDict2' in s) and ('def' not in s) and ('assert' in s),
        'myDict3': lambda s: ('myDict3' in s) and ('def' not in s) and ('assert' in s),
        'square': lambda s: ('square' in s) and ('def' not in s) and ('assert' in s),
        'plusOne': lambda s: ('plusOne' in s) and ('def' not in s) and ('assert' in s),
        'keyCount': lambda s: ('keyCount' in s) and ('def' not in s) and ('assert' in s),
        'wordCount': lambda s: ('wordCount' in s) and ('def' not in s) and ('assert' in s),
        'add': lambda s: ('add' in s) and ('def' not in s) and ('assert' in s),
        'mul': lambda s: ('mul' in s) and ('def' not in s) and ('assert' in s),
        'ageRankings': lambda s: ('ageRankings' in s) and ('def' not in s) and ('assert' in s),
        'warmCityRankings': lambda s: ('warmCityRankings' in s) and ('def' not in s) and ('assert' in s),
        'carPrices': lambda s: ('assert carPrices == {' in s),
        'showRatings': lambda s: ('assert showRatings == {' in s) and ('def' not in s),
        'createPhonebook': lambda s: ('assert createPhonebook([])' in s) and ('def' not in s),
        'createAddressbook': lambda s: ('assert createAddressbook([])') in s,
        'longestPalindrome': lambda s: ('longestPalindrome' in s) and ('def' not in s) and ('assert' in s),
        'biggestPalindrome': lambda s: ('biggestPalindrome' in s) and ('def' not in s) and ('assert' in s),
        'shortestWordWithout': lambda s: ('shortestWordWithout' in s) and ('shortestWordWithoutVowel' not in s) and ('def' not in s) and ('assert' in s),
        'shortestWordWithoutVowel': lambda s: ('shortestWordWithoutVowel' in s) and ('def' not in s) and ('assert' in s),
        'getCountryCapital': lambda s: ('getCountryCapital' in s) and ('def' not in s) and ('assert' in s),
        'getCountryArea': lambda s: ('getCountryArea' in s) and ('def' not in s) and ('assert' in s),
        'getRain': lambda s: ('getRain' in s) and ('def' not in s) and ('assert' in s),
        'getSnow': lambda s: ('getSnow' in s) and ('def' not in s) and ('assert' in s),
    }
}

potentiallyWrong = {'abc': ['adsturza',
         'btaboga',
         'danmlee',
         'emchoe',
         'justinka',
         'kaubrey',
         'nsnavarr'],
 'add': ['emwells'],
 'ageRankings': ['alextrev',
                 'amording',
                 'emchoe',
                 'emwells',
                 'jbachus',
                 'micmark',
                 'nsnavarr',
                 'ogawrych',
                 'sdar',
                 'wilton'],
 'biggestPalindrome': ['alextrev',
                       'andiec',
                       'changela',
                       'couchj',
                       'darrylwi',
                       'emilynkr',
                       'micmark',
                       'nadiamk',
                       'nesreene',
                       'ogawrych',
                       'sarayud',
                       'singhgu',
                       'vartikap',
                       'wilton',
                       'xcen'],
 'carPrices': ['emwells',
               'fortneys',
               'gigishea',
               'micmark',
               'nadiamk',
               'nesreene'],
 'createAddressbook': ['changela',
                       'danmlee',
                       'emchoe',
                       'epoto',
                       'ivalice',
                       'micmark',
                       'mihousey',
                       'nadiamk',
                       'nesreene',
                       'nsnavarr',
                       'yerinek'],
 'createPhonebook': ['aschoe',
                     'ecsm',
                     'emilynkr',
                     'emwells',
                     'fortneys',
                     'hogeterp',
                     'madpax',
                     'ogawrych',
                     'singhgu',
                     'vartikap'],
 'getCountryArea': ['anncyu',
                    'ashw',
                    'bretthro',
                    'darrylwi',
                    'ecan',
                    'ecsm',
                    'eliyang',
                    'ellarad',
                    'emchoe',
                    'epoto',
                    'evanras',
                    'gigishea',
                    'jasonyl',
                    'jbachus',
                    'jmfadden',
                    'krasnev',
                    'lsohyun',
                    'madpax',
                    'maimich',
                    'maryamm',
                    'msilb',
                    'nesreene',
                    'nsnavarr',
                    'ogawrych',
                    'paulhen',
                    'psreeram',
                    'singhgu',
                    'walicia',
                    'wilton',
                    'winorris'],
 'getCountryCapital': ['aegold',
                       'amording',
                       'aschoe',
                       'bradharr',
                       'couchj',
                       'dcoh',
                       'deguiaa',
                       'emilynkr',
                       'emwells',
                       'fortneys',
                       'insunk',
                       'ivalice',
                       'kvtravis',
                       'lasyak',
                       'lmasterm',
                       'lucianrm',
                       'mekarls',
                       'micmark',
                       'mihousey',
                       'nadiamk',
                       'nruffini',
                       'sgajdjis',
                       'vartikap',
                       'vstahl',
                       'wwyuen',
                       'yerinek',
                       'zmelissa'],
 'getRain': ['aiyana',
             'ajsovel',
             'alexchoi',
             'alextrev',
             'alyssads',
             'amording',
             'andiec',
             'anncyu',
             'aschoe',
             'blguo',
             'bradharr',
             'changela',
             'couchj',
             'deguiaa',
             'ecan',
             'emchoe',
             'emiliaob',
             'emilynkr',
             'emwells',
             'epoto',
             'gigishea',
             'gphughe',
             'insunk',
             'krasnev',
             'maryamm',
             'micmark',
             'mkishore',
             'mkmce',
             'mktani',
             'msilb',
             'nadiamk',
             'paulhen',
             'sarayud',
             'singhgu',
             'skstupak',
             'wilton',
             'wwyuen',
             'xcen',
             'yerinek'],
 'getSnow': ['allepore',
             'amfarkas',
             'annezhao',
             'arbiehl',
             'bertleon',
             'darrylwi',
             'dcoh',
             'dyclee',
             'ecsm',
             'eliyang',
             'ellarad',
             'evanras',
             'fortneys',
             'ivalice',
             'kvtravis',
             'lucianrm',
             'maimich',
             'mekarls',
             'mhutt',
             'mihousey',
             'mjmarx',
             'nesreene',
             'nsnavarr',
             'ogawrych',
             'pisupati',
             'rayshadr',
             'rtberger',
             'sgajdjis',
             'swchoye',
             'vartikap',
             'vstahl',
             'walicia',
             'winorris',
             'wisniejd',
             'zmelissa'],
 'keyCount': ['emwells'],
 'longestPalindrome': ['anwolfe',
                       'arbiehl',
                       'aschoe',
                       'dcoh',
                       'emchoe',
                       'fortneys',
                       'gphughe',
                       'kvtravis',
                       'lucianrm',
                       'maryamm',
                       'mihousey',
                       'mkishore',
                       'msilb',
                       'nsnavarr',
                       'paulhen',
                       'skstupak',
                       'walicia',
                       'wwyuen',
                       'yerinek'],
 'mul': ['nsnavarr'],
 'myDict2': ['changela', 'ogawrych'],
 'myDict3': ['fortneys', 'hayounki'],
 'shortestWordWithout': ['amording',
                         'anncyu',
                         'anwolfe',
                         'couchj',
                         'danmlee',
                         'dcoh',
                         'emilynkr',
                         'emwells',
                         'fortneys',
                         'gigishea',
                         'jsweis',
                         'krasnev',
                         'kvtravis',
                         'linowess',
                         'lucianrm',
                         'madpax',
                         'maryamm',
                         'mkmce',
                         'mktani',
                         'msilb',
                         'nesreene',
                         'nruffini',
                         'pisupati',
                         'sarayud',
                         'singhgu',
                         'sknirman',
                         'skstupak',
                         'vstahl',
                         'wilton',
                         'wwyuen',
                         'yerinek'],
 'shortestWordWithoutVowel': ['amfarkas',
                              'andiec',
                              'aschoe',
                              'changela',
                              'darrylwi',
                              'ellarad',
                              'emchoe',
                              'emiliaob',
                              'jasonmoy',
                              'mhutt',
                              'mihousey',
                              'mkishore',
                              'nadiamk',
                              'nsnavarr',
                              'ogawrych',
                              'sophafen',
                              'vartikap',
                              'walicia'],
 'showRatings': ['ecsm',
                 'ellarad',
                 'emchoe',
                 'emilynkr',
                 'krasnev',
                 'nsnavarr',
                 'singhgu',
                 'vartikap',
                 'wilton',
                 'winorris'],
 'warmCityRankings': ['aschoe',
                      'changela',
                      'evanras',
                      'krasnev',
                      'mhutt',
                      'nadiamk',
                      'paulhen',
                      'rtberger',
                      'vartikap',
                      'yerinek'],
 'wordCount': ['ellarad', 'winorris'],
 'xyz': ['aashpat',
         'aegold',
         'ashw',
         'changela',
         'dcoh',
         'hellere',
         'jasonmoy',
         'jongmok',
         'kvtravis',
         'linowess',
         'mkishore',
         'ogawrych',
         'pisupati',
         'rmurthi',
         'sdar',
         'shendl',
         'sknirman',
         'swchoye',
         'vartikap',
         'wisniejd',
         'wwyuen']}