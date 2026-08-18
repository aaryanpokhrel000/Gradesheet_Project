import csv
import os
from flask import Flask, abort, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "super_secure_academic_secret_key"

CSV_FILE_PATH = "students.csv"
TEACHER_PASSWORD = "admin123"

def calculate_subject_grade(score):
    if score >= 90: return "A+"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    elif score >= 50: return "D"
    else: return "F"

def read_all_students_with_rankings():
    """Reads spreadsheet records, normalizes data, and automatically computes class ranks."""
    students_list = []
    if not os.path.exists(CSV_FILE_PATH):
        return students_list

    try:
        with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
            for row in reader:
                if row.get("roll_number"):
                    cleaned_row = {key: value.strip() for key, value in row.items() if key}
                    students_list.append(cleaned_row)
    except Exception:
        pass

    # Compute totals and sort to assign ranks dynamically
    for student in students_list:
        subjects = ["math", "science", "english", "history", "computer", "social"]
        total = sum(int(student.get(sub, 0)) for sub in subjects)
        student["total_marks_computed"] = total
        student["percentage_computed"] = round((total / 600) * 100, 2)

    # Sort students descending by total score
    students_list.sort(key=lambda x: x["total_marks_computed"], reverse=True)

    # Assign sequential ranks
    for index, student in enumerate(students_list):
        student["class_rank"] = index + 1

    return students_list

def get_subject_toppers(students):
    subjects = ["math", "science", "english", "history", "computer", "social"]
    toppers = {}
    for sub in subjects:
        highest_score = -1
        topper_name = "N/A"
        for student in students:
            score = int(student.get(sub, 0))
            if score > highest_score:
                highest_score = score
                topper_name = student.get("student_name", "Unknown")
        toppers[sub] = {"name": topper_name, "score": highest_score}
    return toppers

@app.route("/")
def index():
    return render_template("portal.html")

@app.route("/login", methods=["POST"])
def login():
    role = request.form.get("role")
    if role == "teacher":
        password = request.form.get("password")
        if password == TEACHER_PASSWORD:
            session["role"] = "teacher"
            return redirect(url_for("teacher_dashboard"))
        return render_template("portal.html", error="Invalid Teacher Password. Please try again.")

    elif role == "student":
        roll_number = request.form.get("roll_number", "").strip()
        students = read_all_students_with_rankings()
        if any(s.get("roll_number") == roll_number for s in students):
            session["role"] = "student"
            session["student_roll"] = roll_number
            return redirect(url_for("view_report", roll_number=roll_number))
        return render_template("portal.html", error="Roll Number not found in institutional logs.")
    return redirect(url_for("index"))

@app.route("/teacher/dashboard")
def teacher_dashboard():
    if session.get("role") != "teacher":
        return redirect(url_for("index"))
    students = read_all_students_with_rankings()
    toppers = get_subject_toppers(students)
    return render_template("index.html", students=students, toppers=toppers)

@app.route("/teacher/add_student", methods=["POST"])
def add_student():
    if session.get("role") != "teacher":
        return redirect(url_for("index"))

    new_student = {
        "roll_number": request.form.get("roll_number", "").strip(),
        "student_name": request.form.get("student_name", "").strip(),
        "math": request.form.get("math", "0").strip(),
        "science": request.form.get("science", "0").strip(),
        "english": request.form.get("english", "0").strip(),
        "history": request.form.get("history", "0").strip(),
        "computer": request.form.get("computer", "0").strip(),
        "social": request.form.get("social", "0").strip(),
    }

    students = read_all_students_with_rankings()
    if any(s.get("roll_number") == new_student["roll_number"] for s in students):
        return "Error: A student with this Roll Number already exists.", 400

    file_exists = os.path.exists(CSV_FILE_PATH)
    fieldnames = ["roll_number", "student_name", "math", "science", "english", "history", "computer", "social"]

    # Write data immediately and flush to disk
    with open(CSV_FILE_PATH, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists or os.stat(CSV_FILE_PATH).st_size == 0:
            writer.writeheader()
        writer.writerow(new_student)
        file.flush()
        os.fsync(file.fileno())

    return redirect(url_for("teacher_dashboard"))

@app.route("/report/<roll_number>")
def view_report(roll_number):
    if session.get("role") == "student" and session.get("student_roll") != roll_number:
        return abort(403, description="Access Denied.")
    if not session.get("role"):
        return redirect(url_for("index"))

    students = read_all_students_with_rankings()
    student_data = next((s for s in students if s.get("roll_number") == roll_number), None)
    if not student_data:
        return abort(404, description="Student profile missing.")

    def safe_int(val):
        try: return int(val)
        except (ValueError, TypeError): return 0

    marks = {sub: safe_int(student_data.get(sub)) for sub in ["math", "science", "english", "history", "computer", "social"]}
    grades = {sub: calculate_subject_grade(score) for sub, score in marks.items()}

    return render_template(
        "report.html",
        student_name=student_data.get("student_name"),
        roll_number=student_data.get("roll_number"),
        marks=marks,
        grades=grades,
        total_marks=student_data["total_marks_computed"],
        percentage=student_data["percentage_computed"],
        class_rank=student_data["class_rank"],
        final_grade=calculate_subject_grade(student_data["percentage_computed"])
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
