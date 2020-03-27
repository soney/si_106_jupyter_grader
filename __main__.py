import argparse
import src

parser = argparse.ArgumentParser(description='SI 106 Jupyter Notebook Grader')
parser.add_argument('ipynb_path', metavar='notebook', help='The path to the .ipynb file', nargs='+')
parser.add_argument('--rubric', '-r', dest='rubric_path', metavar='rubric', help='The path to the grading rubric JSON file')

args = parser.parse_args()

src.readNotebooks(args.ipynb_path)