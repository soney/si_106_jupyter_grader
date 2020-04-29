import argparse
import src

parser = argparse.ArgumentParser(description='SI 106 Jupyter Notebook Grader')
parser.add_argument('ipynb_path', metavar='notebook', help='The path to the .ipynb file', nargs='*')
parser.add_argument('--exams', '-e', dest='exams_csv', metavar='exams', help='The path to the exams .csv file')
parser.add_argument('--rubric', '-r', dest='rubric_path', metavar='rubric', help='The path to the grading rubric JSON file')
parser.add_argument('--relpath', '-p', dest='relative_path', metavar='rel_path', help='The relative path to search for files')

args = parser.parse_args()

if args.exams_csv:
    src.readCSV(args.exams_csv, args.relative_path)
else:
    src.readNotebooks(args.ipynb_path)