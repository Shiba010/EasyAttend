from flask import Flask, render_template, request, redirect, url_for
import redis
from datetime import date, datetime


app = Flask(__name__)

#MongoDB connetion
def get_StudentDB_connection():
    
    try:
        student_r = redis.Redis(
                host='redis-16585.c62.us-east-1-4.ec2.cloud.redislabs.com',
                port=16585,
                password='tEjCkoJ9QGw3MvTmPMiCd6HEIHKg8dLI')
        print("Successfully connected to StudentDB in Redis")
        return student_r
    except Exception as e:
        print(e)
        return -1

def get_AttendDB_connection():
    try:
        attend_r = redis.Redis(
                host='redis-16446.c244.us-east-1-2.ec2.cloud.redislabs.com',
                port=16446,
                password='5AlW694HRmn3JtBFx5lLgQR29ODHZYc9')
        print("Successfully connected to AttendDB in Redis")
        return attend_r
    except Exception as e:
        print(e)
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

#Redis OK
@app.route('/submit_attend', methods=['POST'])
def attend():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        if not studentId_isValid(student_id):
            return render_template('attend_form.html', message="Student ID is invalid.")
            
        student_r = get_StudentDB_connection()  
        if student_r==-1:
            return render_template('attend_form.html', message="StudentDB connection error.")

        # check if student exist in table "Student"
        if not student_r.exists(student_id):
            return render_template('attend_form.html', message="Student does not exist.")
        
        attend_r = get_AttendDB_connection()
        if attend_r==-1:
            return render_template('attend_form.html', message="AttendDB connection error.")

        today = str(date.today())
        # check if today is not a class day
        if not attend_r.sismember('AllDates', today):
            return render_template('attend_form.html', message="Today is not a class day.")

        # insert attendace into Attend
        if attend_r.sadd(student_id, today):
            return render_template('attend_form.html', message="Add student attendance successfully.")
        else:
            return render_template('attend_form.html', message="Add student attendance unsuccessfully.")


    return render_template('attend_form.html', message="Error request type.")


#Redis OK
# @app.route('/add_date', methods=['POST'])
# def add_date():
#     if request.method == 'POST':
#         date = request.form.get('date')

#         attend_r = get_AttendDB_connection()
#         if attend_r==-1:
#             return render_template('attend_form.html', message="AttendDB connection error.")


#     return render_template('add_student.html', message="Error request type.")
#Redis OK
@app.route('/add_student', methods=['POST'])
def add_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        if not studentId_isValid(student_id):
            return render_template('add_student.html', message="Student ID is invalid.")
            
        student_r = get_StudentDB_connection()  
        if student_r==-1:
            return render_template('add_student.html', message="StudentDB connection error.")

        # check if student exist in table "Student"
        if student_r.exists(student_id):
            return render_template('add_student.html', message="Student is already exist.")
           
        else:
            student_info1 = {"FirstName": first_name,  "LastName": last_name, "Enable": 1}
            if student_r.hmset(student_id, student_info1):       
                return render_template('add_student.html', message="Add student successfully.")
            else:
                return render_template('add_student.html', message="Add student unsuccessfully.")
            
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
