from flask import Flask, render_template, request, redirect, url_for
import mysql.connector 
from mysql.connector import Error
from datetime import date, datetime


app = Flask(__name__)

# MySql db connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="sql9.freemysqlhosting.net",
            user="sql9656002",
            password="uRstyZdM6A",
            database="sql9656002"
        )
        if conn.is_connected():
            return conn

    except Error as e:
        return -1


def studentId_isValid(id):
    if id[0]=='U' and len(id[1:])==8 and id[1:].isdigit():
        return True
    else:
        return False


def date_isValid(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True  
    except ValueError:
        return False  


@app.route('/')
def attend_form():
    return render_template('attend_form.html')


@app.route('/manage_dashboard')
def manage_dashboard():
    return render_template('manage_dashboard.html')


@app.route('/add_student_form')
def add_student_form():
    return render_template('add_student.html')


@app.route('/search_date_attend_form')
def search_date_attend_form():
    return render_template('search_date_form.html')


@app.route('/submit_attend', methods=['POST'])
def attend():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        if not studentId_isValid(student_id):
            return render_template('attend_form.html', message="Student ID is invalid.")
            
        conn = get_db_connection()
        if conn==-1:
            return render_template('attend_form.html', message="DB connection error.")
        else:
            print("DB connect successfully.")
           
        cursor = conn.cursor()

        # check if student exist in table "Student"
        cursor.execute("SELECT * FROM Student WHERE Id = %s", (student_id,))
        student = cursor.fetchone()

        if student:
            # insert attendace into Attend
            today = date.today()
            cursor.execute("SELECT * FROM Attend WHERE Student_id = %s And Attend_date = %s", (student_id, today))
            attandence = cursor.fetchone()
            if attandence:
                conn.close()
                return render_template('attend_form.html', message="Student already attended today.")

            cursor.execute("INSERT INTO Attend (Student_id, Attend_date) VALUES (%s, %s)", (student_id, today))
            conn.commit()
            conn.close()
            return render_template('attend_form.html', message="Add student attendance successfully.")

        else:
            conn.close()
            return render_template('attend_form.html', message="Student does not exist.")
            
    return render_template('attend_form.html', message="Error request type.")


@app.route('/add_student', methods=['POST'])
def add_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        if not studentId_isValid(student_id):
            return render_template('add_student.html', message="Student ID is invalid.")
            
        conn = get_db_connection()
        if conn==-1:
            return render_template('add_student.html', message="DB connection error.")
        else:
            print("DB connect successfully.")
           
        cursor = conn.cursor()

        # check if student exist in table "Student"
        cursor.execute("SELECT * FROM Student WHERE Id = %s", (student_id,))
        student = cursor.fetchone()

        if student:
            conn.close()
            return render_template('add_student.html', message="Student is already exist.")

        else:
            cursor.execute("INSERT INTO Student (Id, FirstName, LastName) VALUES (%s, %s, %s)", (student_id, first_name, last_name))
            conn.commit()
            conn.close()
            return render_template('add_student.html', message="Add student successfully.")
            
    return render_template('add_student.html', message="Error request type.")


@app.route('/search_date_attend', methods=['POST'])
def search_date_attend():
    if request.method == 'POST':
        date = request.form.get('date')
      
        if not date_isValid(date):
            return render_template('search_date_form.html', message="Date is invalid.")
            
        conn = get_db_connection()
        if conn==-1:
            return render_template('search_date_form.html', message="DB connection error.")
        else:
            print("DB connect successfully.")
           
        cursor = conn.cursor()

        query = """
                SELECT s.Id, s.FirstName, s.LastName, IFNULL(a.Attend_date IS NOT NULL, 0) AS attend
                FROM Student s
                LEFT JOIN Attend a ON s.Id = a.Student_id AND a.Attend_date = %s
                """
        cursor.execute(query, (date,))
        date_attend = cursor.fetchall()

        if date_attend:
            conn.close()
            return render_template('date_attendance.html', results=date_attend, date=date)

        else:
            conn.close()
            return render_template('search_date_form.html', message="No date in {date}.")
            
    return render_template('search_date_form.html', message="Error request type.")

if __name__ == '__main__':
    app.run()
