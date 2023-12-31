import redis
from datetime import date, datetime, timedelta
import pandas as pd
import atexit
from wtforms import StringField, PasswordField, SubmitField
import pytz

from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager
from flask_login import UserMixin
from flask_wtf import FlaskForm
from flask_login import login_user
from flask_login import logout_user
from flask_login import login_required


app = Flask(__name__)

#OK
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
#OK
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
#OK
def get_CourseDB_connection():
    try:
        course_r = redis.Redis(
                host='redis-13449.c73.us-east-1-2.ec2.cloud.redislabs.com',
                port=13449,
                password='nRxWiqiWKZuoEG2QZHCEeklwweYxvvsg')
        print("Successfully connected to CourseDB in Redis")
        return course_r
    except Exception as e:
        print(e)
        return -1

#Global variable of db connection
attend_r = get_AttendDB_connection()
student_r = get_StudentDB_connection()
course_r = get_CourseDB_connection()

def close_redis_connection():
    global attend_r, student_r, course_r
    attend_r.close()
    student_r.close()
    course_r.close()

#Close the db connections if the application stop
atexit.register(close_redis_connection)

# login OK
app.secret_key = 'your_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'sign_in'  # redirect


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

users = {'admin@bu.edu': User('1', 'admin@bu.edu', 'admin')}


#OK
def studentId_isValid(id):
    if id[0]=='U' and len(id[1:])==8 and id[1:].isdigit():
        return True
    else:
        return False


#OK function for adding course
def all_matching_weekdays_between(days, start_date, end_date):
    # Parsing the input dates to datetime objects
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if end<start:
        return -1

    day_to_ix = {'MON':0, 'TUE':1, 'WED':2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN':6}   
    weekday =  day_to_ix[days]

    # Finding the weekday of the start date
    # weekday = start.weekday()

    # Adjusting the start date to the next same weekday
    if start.weekday() != weekday:
        start += timedelta(days=(weekday - start.weekday() + 7) % 7)

    # Finding all matching weekdays between the start and end dates
    current = start
    matching_days = []
    while current <= end:
        matching_days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=7)

    return matching_days


@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if user.id == user_id:
            return user
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():

    username = request.form.get("email")
    password = request.form.get("password")
    user = users.get(username)
        
    if user and user.password == password:
        login_user(user)
        return redirect(url_for('manage_dashboard')) 
    else: 
        return render_template('sign_in.html', message='Invalid user or wrong passwaord.')
   
    return render_template('sign_in.html', message='Invalid submit!')

@app.route('/sign_in')
def sign_in():
    return render_template('sign_in.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return render_template('sign_in.html', message='Log out successfully!')


#OK
@app.route('/')
def attend_form():
    return render_template('attend_form.html')

#OK
@login_required
@app.route('/update_students_form', methods=['POST'])
def update_students_from():
    if request.method == 'POST':
        course_section = request.form.get("course_section")
        return render_template('update_students_form.html', course_section = course_section)
    return redirect(url_for('manage_dashboard'))


#OK
@app.route('/update_students', methods=['POST'])
@login_required
def update_students():
    if request.method == 'POST':
        if 'student_info' not in request.files:
            return render_template('update_students_form.html', message='No file part')
        file = request.files['student_info']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return render_template('update_students_form.html', message='No selected file')
        if not file.filename.lower().endswith('.csv'):
            return render_template('update_students_form.html', message='File is not a CSV')
    
        course_name = request.form.get("course_section")
        
        df = pd.read_csv(file)
        for i in range(df.shape[0]):
            if not studentId_isValid(df.iloc[i]['Student Id']):
                return render_template('update_students_form.html', message=f"Fail to update students in {course_name}! Detect invalid student id.")

        course_r.hset(course_name, "Student Count", df.shape[0])

        course_dates = course_r.smembers(f"{course_name}_date")
        course_dates = [datetime.strptime(d.decode(), '%Y-%m-%d').date() for d in list(course_dates)]
        today = datetime.today().date()
        count_after_today = sum(d >= today for d in course_dates)

        # all the student in the csv file
        update_student = {}
        for i in range(df.shape[0]):
            update_student[df.iloc[i]['Student Id']] = {'FirstName': df.iloc[i]['First Name'], 
                                                        'LastName': df.iloc[i]['Last Name'],
                                                        'Enable': '1',
                                                        'Course_Section': course_name,
                                                        'Total_course': count_after_today}
        selected_student = []
        old_student = set()
        for BuId in student_r.scan_iter("*"):
            data_type = student_r.type(BuId).decode('utf-8')
            if data_type == 'hash':
                info = student_r.hgetall(BuId) 
                old_student.add(BuId.decode())      

                #student in this class dropped before but return to this class again
                if info[b'Enable']==b'0' and info[b'Course_Section']==course_name.encode() and BuId in update_student:  
                    student_r.hset(BuId, 'Enable', '1')
                    continue

                #student in other class or Student in this csv
                if info[b'Course_Section']!=course_name.encode() or BuId.decode() in update_student:
                    continue  

                #disable the student in this class but drop this time
                student_r.hset(BuId, 'Enable', '0')

        #add new student to DB        
        for BuId in update_student:
            if BuId in old_student:
                continue     
            student_r.hmset(BuId, update_student[BuId]) 

        return render_template('update_students_form.html', message=f'Update students in {course_name} successfully')
    return render_template('update_students_form.html', message='Error request type')




#Ok
@app.route('/manage_dashboard')
@login_required
def manage_dashboard():

    course_info = []
    for key in course_r.scan_iter("*"):
        # Determine the type of the key-value pair
        data_type = course_r.type(key).decode('utf-8')
        course = [key.decode('utf-8')]
        if data_type == 'hash':
            value = course_r.hgetall(key)
            for k,v in value.items():
                if k.decode('utf-8') == 'Start_time' or k.decode('utf-8') == 'End_time':
                    continue
                course.append(v.decode('utf-8'))
            course_info.append(course)

    return render_template('manage_dashboard.html', array=course_info)


@app.route('/delete_course', methods=['POST'])
@login_required
def delete_course():
    if request.method == 'POST':
        course_section = request.form.get("course_section")
        
        students_to_del = []
        #find the student in that course
        for BuId in student_r.scan_iter("*"):
            data_type = student_r.type(BuId).decode('utf-8')
            if data_type == 'hash':
                info = student_r.hgetall(BuId) 
                #student not in this class or already dropped   
                if info[b'Course_Section']==course_section.encode():
                    students_to_del.append(BuId)
      
        # delete the students from student and attendence db
        for BuId in students_to_del:
            attend_r.delete(BuId)
            student_r.delete(BuId)

        #delete that course    
        course_r.delete(course_section)
        course_r.delete(course_section+"_date")
        return redirect(url_for('manage_dashboard'))

    return redirect(url_for('manage_dashboard'))

#OK
@app.route('/student_list', methods=['POST'])
@login_required
def student_list():
    if request.method == 'POST':
        course_section = request.form.get("course_section")

        student_info = []
        for BuId in student_r.scan_iter("*"):

            data_type = student_r.type(BuId).decode('utf-8')
            if data_type == 'hash':
                info = student_r.hgetall(BuId) 
                if info[b'Enable']==b'0' or info[b'Course_Section']!=course_section.encode():
                    continue
                attend_count = len(attend_r.smembers(BuId))
                course_count = course_r.hget(course_section.encode(), "total_course").decode('utf-8')
                total_course = int(info[b"Total_course"].decode("utf-8"))
                attend_rate = round(attend_count/total_course*100) #%
                attendence = f'{attend_rate}% ({attend_count}/{total_course})'

                arr = [BuId.decode('utf-8'), info[b'FirstName'].decode('utf-8'), info[b'LastName'].decode('utf-8'), attendence]
        
            student_info.append(arr)

        return render_template('student_list.html', course_section=course_section, array=student_info)

    return redirect(url_for('manage_dashboard'))


@app.route('/add_course_form')
@login_required
def add_course_form():
    return render_template('add_course_form.html')


#Ok, need error detection
@app.route('/add_course', methods=['POST'])
@login_required
def add_course():
    if request.method == 'POST':
        if 'student_info' not in request.files:
            return render_template('add_course_form.html', message='No file part')
        file = request.files['student_info']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return render_template('add_course_form.html', message='No selected file')
        if not file.filename.lower().endswith('.csv'):
            return render_template('add_course_form.html', message='File is not a CSV')
    
        course_name = request.form.get("course_section")
        days = request.form.get("days")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        time = f"{start_time} - {end_time}"
        start_date= request.form.get("start_date")
        end_date= request.form.get("end_date")
        courses = request.form.get("courses")

        all_dates = all_matching_weekdays_between(days, start_date, end_date) #list
        if all_dates == -1:
            return render_template('add_course_form.html', message=f"Error! End date is earlier than start date!")
        
        for date in all_dates:
            course_r.sadd(course_name+"_date", date)
            
        #add course info to Course db
        df = pd.read_csv(file)

        #if some student id is invalid in csv file, then stop
        for i in range(df.shape[0]):
            if not studentId_isValid(df.iloc[i]['Student Id']):
                return render_template('add_course_form.html', message=f"Fail to create {course_name}! Detect invalid student ids.")

    
        course_r.hset(course_name, "Days", days)
        course_r.hset(course_name, "Times", time)
        course_r.hset(course_name, "Start_time", start_time)
        course_r.hset(course_name, "End_time", end_time)
        course_r.hset(course_name, "Student Count", df.shape[0])
        course_r.hset(course_name, "total_course", len(all_dates))

        #add the student of this course
        update_student = {}
        for i in range(df.shape[0]):
            update_student[df.iloc[i]['Student Id']] = {'FirstName': df.iloc[i]['First Name'], 
                                                        'LastName': df.iloc[i]['Last Name'],
                                                        'Enable': '1',
                                                        'Course_Section': course_name,
                                                        'Total_course': len(all_dates)}
                                                        
        for BuId in update_student:
            student_r.hmset(BuId, update_student[BuId]) 

        return render_template('add_course_form.html', message=f'Create {course_name} successfully')

    return render_template('add_course_form.html', message='Error request type')



#OK
@app.route('/submit_attend', methods=['POST'])
def attend():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        if not studentId_isValid(student_id):
            return render_template('attend_form.html', message="Student ID is invalid.")
            
        # check if student exists in "Student db"
        if not student_r.exists(student_id):
            return render_template('attend_form.html', message="Student does not exist.")
        
        course_section = student_r.hget(student_id, 'Course_Section').decode() # b'CS633-E1' => 'CS633-E1'
        today = str(date.today())

        start_time = course_r.hget(course_section, 'Start_time').decode()
        end_time = course_r.hget(course_section, 'End_time').decode()
        start_time = datetime.strptime(start_time, "%H:%M").time()
        end_time = datetime.strptime(end_time, "%H:%M").time()

        # Record the current time
        eastern = pytz.timezone('America/New_York')
        current_time = datetime.now(eastern)
        
        # Check if the current time is within the range
        is_within_range = start_time <= current_time.time() <= end_time

        if course_r.sismember(course_section+'_date', today):
            if not is_within_range:
                return render_template('attend_form.html', message=f"Not in the class time.")

            if attend_r.sismember(student_id, today):
                return render_template('attend_form.html', message=f"{student_id} already signed-in today.")
            elif attend_r.sadd(student_id, today):
                return render_template('attend_form.html', message=f"{student_id} sign-in successfully.")
            else:
                return render_template('attend_form.html', message="Add student attendance unsuccessfully.")
        else:
            return render_template('attend_form.html', message="Not a class day.")

    return render_template('attend_form.html', message="Wrong request type.")

# @app.route('/get_course_section', methods=['GET'])
# @login_required
# def get_course_section():
#     course_section = {}
#     index = 0
#     for key in course_r.scan_iter("*"):
#         course_section[index] = key.decode('utf-8')

#     return jsonify(course_section)


if __name__ == '__main__':
    app.run()
