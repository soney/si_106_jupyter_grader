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

def getNotebook(path):
    return nbformat.read(path, as_version=4)

def processGradedFile(path):
    notebook = getNotebook(path)
    problem_id = notebook['metadata']['problemID']
    student_grades = {}
    for cell in notebook.cells:
        metadata = cell['metadata']
        if 'source-id' in metadata:
            sourceID = metadata['source-id']
        if 'studentID' in metadata:
            studentID = metadata['studentID']
        
        if hasDirectiveType(cell, ExamDirectiveType.GRADE):
            directive,source = splitDirective(cell['cell_type'], cell['source'].strip())
            student = directive['student-id'].strip()

            if source == 'TODO':
                continue
            
            if source[-1] == '%':
                source = source[:-1]

            try:
                if student not in student_grades:
                    student_grades[student] = {}
                value = float(source)
                if value.is_integer():
                    value = int(value)
                assert value <= 100, "Grades should max out at 100"
                assert value >= 0, "Grades should be at least 0"
                student_grades[student]['grade'] = value
            except Exception as e:
                student_grades[student]['unparsable_grade'] = source

        if hasDirectiveType(cell, ExamDirectiveType.COMMENTS):
            directive,source = splitDirective(cell['cell_type'], cell['source'].strip())
            student = directive['student-id']
            if source:
                if student not in student_grades:
                    student_grades[student] = {}
                student_grades[student]['comments'] = source

    return (problem_id, student_grades)

def hasDirectiveType(cell, desiredDirectiveType):
    directive, source = splitDirective(cell['cell_type'], cell['source'])
    directiveType = directive['type'] if directive else None
    return directiveType == desiredDirectiveType

def getProblemValues(source_path):
    notebook = getNotebook(source_path)
    problem_values = {}
    for cell in notebook.cells:
        metadata = cell['metadata']
        problemID = metadata['id']
        if hasDirectiveType(cell, ExamDirectiveType.PROBLEM):
            directive,source = splitDirective(cell['cell_type'], cell['source'].strip())
            points = directive['points']
            problem_values[problemID] = points
    return problem_values


def getProblemSequence(student, source_path, gen_exams_path):
    if gen_exams_path:
        path = getNotebookPath(student, gen_exams_path)
    else:
        path = None
    
    # assert path != None, f'{gen_exams_path} did not turn up exam for {student}'

    if path:
        return readProblemSequenceFromGeneratedExam(path)
    else:
        return readProblemSequenceFromSourceNotebook(source_path)

def readProblemSequenceFromGeneratedExam(path):
    notebook = getNotebook(path)
    return notebook['metadata']['exam_gen_problems']

def readProblemSequenceFromSourceNotebook(source_path):
    notebook = getNotebook(source_path)
    problems = []
    for cell in notebook.cells:
        metadata = cell['metadata']
        problemID = metadata['id']
        if hasDirectiveType(cell, ExamDirectiveType.PROBLEM):
            problems.append(problemID)
    return problems


def getNotebookPath(student, gen_exams_path):
    for root, subdirs, files in os.walk(gen_exams_path):
        for name in files:
            if name == '{}_final_exam.ipynb'.format(student):
                return os.path.join(root, name)

    return False

# def getGeneratedNotebookFile

# def processGradedProblems(csv_path, relative_path, problems_path, output_path):
def processGradedProblems(gradedFiles, source_path, output_path, gen_exams_path):
    problem_values = getProblemValues(source_path)
    ignore_students = []
    # ignore_students = ['soney']

    grade_by_student = {}
    for gradedFile in gradedFiles:
        problem_id, problem_grades = processGradedFile(gradedFile)
        for student, student_grade_dict in problem_grades.items():
            if student in ignore_students:
                continue
            # grade = student_grade_dict['grade']
            # comments = student_grade_dict['comments'] if 'comments' in student_grade_dict else False
            if student not in grade_by_student:
                grade_by_student[student] = {}
            grade_by_student[student][problem_id] = student_grade_dict

    errors_by_problem = {}
    final_grades = {}
    for student, problem_dict in grade_by_student.items():
        total_score = 0
        comments_dict = {}
        ignore = []
        # ignore = ['90383b9e-29b3-46d2-91bb-6f781c2df91e', 'd2255010-55f8-42da-808f-4ac3f9a9e146']
        ignore = ['709a114b-d1db-4ce7-b701-3c3443e9aa2d', '2fcbaa22-600e-4fe4-848d-e62082df7c2b']

        problem_sequence = [item for item in getProblemSequence(student, source_path, gen_exams_path) if item not in ignore]
        # if problem_sequence == ['90383b9e-29b3-46d2-91bb-6f781c2df91e', 'bbb7551e-17a4-43da-99a5-457c2ccdf0ae', 'c476125a-3c48-4058-95cb-59c8254ac106', '514899c1-5e4c-49dc-b328-c98dd91f9538', 'ce22c375-175f-498b-9cef-3b86d45591df', 'd373a6e4-9ae7-4f48-822a-8ec1bcedc926', 'c5aefa83-9d27-4460-9243-a9d638ef925a', '3d8a29ce-1dbd-4e8b-a218-8dcc3cf32833', 'ccacacdf-11c6-41b5-b233-a01287722fe8', '520a5ad4-675e-46dc-a874-1fad32527896', 'ff8be2c2-e876-4d3f-9cf6-e8679d9a209e', '35f7106b-d513-4bca-8bff-852de6b78ad7', '0942bb0a-48ab-40dc-950d-5a0d7df64223', '671aa3f0-08a9-4be0-b26e-16fc69c89936', '641f0a8e-aafc-4816-b270-d4221e653ef5', '72648c15-b8a6-4b9f-ac5b-a0816ff6b5b0', '6c11805d-5bb0-4a0e-85dd-a7a7fe6b0173', 'e52a06eb-abf0-4a54-b3d2-07d56365f2da']:
        #     print(student)
        # continue


        # errors = []
        ungraded_problems = {problem_id: True for problem_id in problem_sequence}
        known_problematic_ids = []
        for problem_id in problem_sequence:
            if problem_id not in errors_by_problem:
                errors_by_problem[problem_id] = {
                    'no_grade': [],
                    'unparsable_grade': []
                } 
        for problem_id, student_grade_dict in problem_dict.items():
            problem_value = problem_values[problem_id]
            if 'grade' in student_grade_dict:
                grade = problem_value * (student_grade_dict['grade']/100)
                if grade.is_integer():
                    grade = int(grade)
                total_score += grade
                ungraded_problems[problem_id] = False
            elif 'unparsable_grade' in student_grade_dict:
                grade = 0
                errors_by_problem[problem_id]['unparsable_grade'].append({ 'student': student, 'message': student_grade_dict['unparsable_grade']})
                known_problematic_ids.append(problem_id)
            else:
                grade = 0
                errors_by_problem[problem_id]['no_grade'].append({ 'student': student })
                known_problematic_ids.append(problem_id)
            
            if ('comments' in student_grade_dict) and (student_grade_dict['comments'].strip()):
                comments_dict[problem_id] = '{}/{} - {}'.format(grade, problem_value, student_grade_dict['comments'])
            else:
                comments_dict[problem_id] = '{}/{}'.format(grade, problem_value)

        

        if any(ungraded_problems.values()):
            ungraded_problem_ids = [k for k in ungraded_problems if ungraded_problems[k]]
            for problem_id in ungraded_problem_ids:
                if problem_id not in known_problematic_ids:
                    if problem_id not in errors_by_problem:
                        errors_by_problem[problem_id] = {
                                'no_grade': [],
                                'unparsable_grade': []
                            } 
                    errors_by_problem[problem_id]['no_grade'].append({ 'student': student })
            # final_grades[student] = errors
        # print(graded_problems.values())

        problem_numbers = { problem_id: idx+1 for (idx, problem_id) in enumerate(problem_sequence) }

        # print(student)
        # print(list(comments_dict.keys()))
        sorted_comments_keys = sorted(comments_dict.keys(), key = lambda problemID: problem_numbers.get(problemID, -1))
        comments = [ 'Problem {}: {}\n'.format(problem_numbers.get(key, -1), comments_dict.get(key, -1)) for key in sorted_comments_keys ]
        final_grades[student] = { 'score': total_score, 'comments': '\n'.join(comments)}

    for problem_id,errors_dict in list(errors_by_problem.items()):
        comments = []
        for k, v in errors_dict.items():
            if len(v) > 0:
                if k == 'no_grade':
                    students = sorted([d['student'] for d in v])
                    comments.append('No grade for student{} {}'.format('' if len(students)==1 else 's', ','.join(students)))
                elif k == 'unparsable_grade':
                    for d in v:
                        student = d['student']
                        message = d['message']
                        comments.append('Could not parse score "{}" (student: {})'.format(message, student))
                else:
                    raise Error("Unknown error key {}".format(k))
                    print(k, v)
        if len(comments)>0:
            print('=== PROBLEM {} GRADER ERRORS ===\n'.format(problem_id))
            print('\n'.join(comments))
            print('\n'*2)
    
    with open(output_path, 'w') as csvfile:
        fieldnames=['uniquename', 'grade', 'feedback']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for student, grade_dict in final_grades.items():
            d = {
                'uniquename': student,
                'grade': grade_dict['score'],
                'feedback': grade_dict['comments']
            }
            writer.writerow(d)
            # print(comments)
        # if len(errors) > 0:
            # print(errors)
            
        # print(total_score, '\n'.join(comments))
            # print(student_grade_dict)
            # print(problem_value)
    # print(source_path)
    # student_grades = {}
    # full_problems_path = os.path.join(relative_path, problems_path)
    # problems_files = os.listdir(full_problems_path)
    # for problem_file in problems_files:
    #     if os.path.isdir(problem_file): continue
    #     fullpath = os.path.join(full_problems_path, problem_file)
    #     nb = nbformat.read(fullpath, as_version=4)
    #     problem_id = problem_file.split(".")[0]
    #     for cell in nb.cells:
    #         try:
    #             directive,source = splitDirective(cell['cell_type'], cell['source'].strip())
    #         except Exception as e:
    #             print('problem in file {}'.format(problem_file))
    #             print(e)
    #             print()
    #         if directive:
    #             directive_type = directive['type']
    #             if directive_type == ExamDirectiveType.GRADE:
    #                 if source.strip():
    #                     student = directive['student-id']
    #                     try:
    #                         value = float(source)
    #                         if value.is_integer():
    #                             value = int(value)
    #                         if student not in student_grades:
    #                             student_grades[student] = {
    #                                 'problems': {}
    #                             }
    #                         if problem_id not in student_grades[student]['problems']:
    #                             student_grades[student]['problems'][problem_id] = {}
    #                         student_grades[student]['problems'][problem_id]['grade'] = value
    #                     except Exception as e:
    #                         print('Problem in file {} for student {}'.format(problem_file, student))
    #                         print(e)
    #                         print()
    #                         continue
    #             elif directive_type == ExamDirectiveType.COMMENTS:
    #                 student = directive['student-id']
    #                 if source.strip():
    #                     if student not in student_grades:
    #                         student_grades[student] = {
    #                             'problems': {}
    #                         }
    #                     if problem_id not in student_grades[student]['problems']:
    #                         student_grades[student]['problems'][problem_id] = {}
    #                     student_grades[student]['problems'][problem_id]['comments'] = source.strip()
    # output_rows = []
    # full_csv_path = os.path.join(relative_path, csv_path)
    # problem_issues = {}
    # with open(full_csv_path) as csvfile:
    #     reader = csv.DictReader(csvfile)
    #     for row in reader:
    #         sid = row['uniquename']
    #         if sid in student_grades:
    #             submission_file_path = os.path.join(relative_path, row['submission'])
    #             submission = nbformat.read(submission_file_path, as_version=4)
    #             problems = submission.metadata['exam_gen_problems']
    #             grades = student_grades[sid]['problems']
    #             feedback = []
    #             overallGrade = 0
    #             for index,problem in enumerate(problems):
    #                 if problem in grades:
    #                     grade = grades[problem]
    #                     if 'grade' in grade:
    #                         gradeValue = grade['grade']
    #                         overallGrade += gradeValue

    #                         if 'comments' in grade:
    #                             gradeComments = grade['comments']
    #                             feedback.append('Problem {}: {} points\n{}'.format(index, gradeValue, gradeComments))
    #                         elif gradeValue:
    #                             feedback.append('Problem {}: {} points'.format(index, gradeValue))
    #                         feedback.append('')
    #                     else:
    #                         if problem not in problem_issues:
    #                             problem_issues[problem] = []
    #                         problem_issues[problem].append('Could not parse grade for {}'.format(sid, problem))
    #                 else:
    #                     if index > 0 and index <= 23:
    #                         if problem not in problem_issues:
    #                             problem_issues[problem] = []
    #                         problem_issues[problem].append('Could not find feedback for {}'.format(sid, problem))
    #                         # if problem != '348cb33d-a7e9-47dd-b10b-f36f74abf078':
    #                             # print('Missing grade for {} for problem {}'.format(sid, problem))
    #             output_rows.append({
    #                 'uniquename': sid,
    #                 'grade': overallGrade,
    #                 'feedback': '\n'.join(feedback)
    #             })
    # for problem, issues in problem_issues.items():
    #     print('PROBLEM {}:'.format(problem))
    #     print('\n'.join(sorted(issues)))
    #     print('\n\n')
    # output_rows.sort(key = lambda d: d['uniquename'])
    # full_output_path = os.path.join(relative_path, output_path)

    # with open(full_output_path, 'w') as csvfile:
    #     fieldnames=['uniquename', 'grade', 'feedback']
    #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #     writer.writeheader()
    #     for row in output_rows:
    #         writer.writerow(row)

    # print('wrote {}'.format(full_output_path))
    # # print(student_grades)
    # #     first_cell_source = nb.cells[0].source
    # #     line = first_cell_source.splitlines()[3]
    # #     print(line)
    # #     m = re.findall("This exam is for .* \((.*)\)\.", line)
    # #     if m:
    # #         m = m[0]
    # #         os.rename(fullpath, os.path.join(rp, '{}_final_exam.ipynb'.format(m)))
