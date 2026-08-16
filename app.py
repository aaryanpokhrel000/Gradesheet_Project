import csv
from flask import Flask, abort, render_template

app = Flask(__name__)


def calculate_subject_grade(score):
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def read_all_students():
    """Reads CSV rows and normalizes column headers to prevent stray spaces or casing bugs."""
    students_list = []
    try:
        with open("students.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            # Normalizes column headers: converts everything to lowercase and strips blank spaces
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

            for row in reader:
                # Normalizes the internal values to clean out accidental whitespaces inside row cells
                cleaned_row = {key: value.strip() for key, value in row.items() if key}
                students_list.append(cleaned_row)
    except FileNotFoundError:
        pass
    return students_list


@app.route("/")
def home():
    students = read_all_students()
    return render_template("index.html", students=students)


@app.route("/report/<roll_number>")
def generate_report(roll_number):
    students = read_all_students()
    student_data = None

    # Matches roll number safely
    for student in students:
        if student.get("roll_number") == roll_number.strip():
            student_data = student
            break

    if not student_data:
        return abort(404, description="Student record not found in data matrix.")

    # Safely convert to integer, defaulting to 0 if a cell is missing or corrupted
    def safe_int(val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0


    # All dictionary lookup keys are now strictly lowercase to ensure a perfect match
    marks = {
        "math": safe_int(student_data.get("math")),
        "science": safe_int(student_data.get("science")),
        "english": safe_int(student_data.get("english")),
        "history": safe_int(student_data.get("history")),
        "computer": safe_int(student_data.get("computer")),
        "social": safe_int(student_data.get("social")),
    }

    grades = {subject: calculate_subject_grade(score) for subject, score in marks.items()}

    total_marks = sum(marks.values())
    percentage = round((total_marks / 600) * 100, 2)

    if percentage >= 90:
        final_grade = "Distinction (A+)"
    elif percentage >= 80:
        final_grade = "First Division (A)"
    elif percentage >= 70:
        final_grade = "First Division (B)"
    elif percentage >= 60:
        final_grade = "Second Division (C)"
    elif percentage >= 50:
        final_grade = "Pass Division (D)"
    else:
        final_grade = "Fail (F)"

    return render_template(
        "report.html",
        student_name=student_data.get("student_name"),
        roll_number=student_data.get("roll_number"),
        marks=marks,
        grades=grades,
        total_marks=total_marks,
        percentage=percentage,
        final_grade=final_grade,
    )


if __name__ == "__main__":
    app.run(debug=True)
