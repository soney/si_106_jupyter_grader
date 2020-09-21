import argparse
import generateGradeableExams
import os
import csv

def getAllFiles(paths, desiredExtensions=['.ipynb']):
    result = []
    for path in paths:
        abspath = os.path.abspath(path)
        if os.path.isdir(abspath):
            filenames = os.listdir(abspath)
            allFiles = [os.path.join(abspath, fname) for fname in filenames]
            result += allFiles
        elif os.path.isfile(abspath):
            result += abspath
    result = [p for p in result if (os.path.splitext(p)[-1] in desiredExtensions)]
    return result

def getStudentID(path):
    (head, fullFilename) = os.path.split(path)
    (filename, ext) = os.path.splitext(fullFilename)
    split_filename = filename.split('_')

    student_id = split_filename[1] if split_filename[1] != 'LATE' else split_filename[2]
    return student_id


parser = argparse.ArgumentParser(description='SI 106 Jupyter Notebook Grader')
parser.add_argument('ipynb_path', metavar='notebook', help='The path to the .ipynb file', nargs='+')
# parser.add_argument('--rubric', '-r', dest='rubric_path', help='The path to the grading rubric JSON file')
parser.add_argument('--csv', '-c', dest='csv_path', help='The path to the CSV file containing submissions and test files')
parser.add_argument('--relative_path', '-r', dest='relative_path', help='The path to treat all other file paths relative to')
parser.add_argument('--problems', '-p', dest='problems', help='Path to the problems directory')
parser.add_argument('--output', '-o', dest='output', help='Path to grades output')
parser.add_argument('--ids', '-id', dest='student_ids', help='The path to the IDs')
parser.add_argument('--source', '-source', dest='source_path', help='The path to the source notebook')

args = parser.parse_args()

# src.readNotebooks(args.ipynb_path)
if args.problems:
    src.processGradedProblems(args.csv_path, args.relative_path, args.problems, args.output)
elif args.csv_path:
    src.processCSV(args.csv_path, args.relative_path, args.ipynb_path[0])
else:
    filenameByStudentID = { getStudentID(filename): filename for filename in getAllFiles(args.ipynb_path) }
    with open(args.student_ids) as studentIDCSVFile:
        reader = csv.DictReader(studentIDCSVFile)
        studentIDs = { row['ID']: row for row in reader}
    generateGradeableExams.handleSubmissions(filenameByStudentID, studentIDs, args.source_path, os.path.abspath(args.output))