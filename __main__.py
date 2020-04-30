import argparse
import src

parser = argparse.ArgumentParser(description='SI 106 Jupyter Notebook Grader')
parser.add_argument('ipynb_path', metavar='notebook', help='The path to the .ipynb file', nargs='+')
parser.add_argument('--rubric', '-r', dest='rubric_path', help='The path to the grading rubric JSON file')
parser.add_argument('--csv', '-c', dest='csv_path', help='The path to the CSV file containing submissions and test files')
parser.add_argument('--relative_path', '-p', dest='relative_path', help='The path to treat all other file paths relative to')

args = parser.parse_args()

# src.readNotebooks(args.ipynb_path)
if args.csv_path:
    src.processCSV(args.csv_path, args.relative_path, args.ipynb_path[0])