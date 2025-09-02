from flask import Flask, render_template, request, url_for, redirect, flash, session
from sqlalchemy import text
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_session import Session

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False

Session(app)

# IMPORT THE SQALCHEMY LIBRARY's CREATE_ENGINE METHOD
from sqlalchemy import create_engine

# DEFINE THE DATABASE CREDENTIALS
user = 'root'
password = 'mitaly123'
host = '127.0.0.1'
port = 3306
database = 'todo'

# PYTHON FUNCTION TO CONNECT TO THE MYSQL DATABASE AND
# RETURN THE SQLACHEMY ENGINE OBJECT
def get_connection():
    return create_engine(
        url="mysql+pymysql://{0}:{1}@{2}:{3}/{4}".format(
            user, password, host, port, database
        )
    )


@app.route("/submit", methods=["GET", "POST"])
def submit():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    engine = get_connection()
    if request.method == 'POST':
        todotitle = request.form.get('todotitle')
        description = request.form.get('description')
        categories = request.form.get('categories')
        if todotitle and categories:
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            with engine.connect() as con:
                rs = con.execute(text(f'INSERT INTO todoitem (categories, title, description, user_id, created, lastUpdated) values ("{categories}", "{todotitle}", "{description}", {uid}, "{formatted_time}", "{formatted_time}");'))
                con.commit()
                flash('Successfully submit data!', 'green')
        else:
            flash('Invalid data!', 'red')
    return redirect(url_for("home"))


@app.route('/')
@app.route("/home")
def home():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    else:
        uid = session.get('user_id')
        category = request.args.get('category')
        title = request.args.get('title')

        if title or category:
            engine = get_connection()
            query = f"SELECT id,categories , title, description, created, lastUpdated FROM todoitem where user_id = {uid} and title like '%{title}%' "
            if category:
                query += f" and categories='{category}' "
            query += " order by id desc "
            with engine.connect() as con:
                con.commit()
                rs = con.execute(text(query) )
                row = rs.fetchall()        
        else:
            title = ''
            engine = get_connection()
            with engine.connect() as con:
                con.commit()
                rs = con.execute(text(f"SELECT id,categories , title, description, created, lastUpdated FROM todoitem where user_id = {uid} order by id desc") )
            row = rs.fetchall()
              
        return render_template('index.html', todos=row ,title=title, category=category ) 


@app.route('/delete/<id>')
def delete(id):
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    engine = get_connection()
    with engine.connect() as con:
        rs = con.execute(text(f'delete from todoitem where id={id} and user_id = {uid};'))
        con.commit()
        if rs.rowcount > 0:
            flash('Successfully deleted', "yellow")
        else:
            flash('You are not authorized to delete data!' , 'red')
        
    return redirect(url_for("home"))

@app.route('/update/<id>', methods = ['GET', 'POST'])
def update(id):
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    
    engine = get_connection()
    with engine.connect() as con:
            con.commit()
            rs = con.execute(text(f"SELECT id, categories, title,  description , user_id FROM todoitem where id={id} and user_id = {uid}") )
    row = rs.fetchall()
    if not row:
        flash('you are not updated')
        redirect(url_for('home'))
   
    return render_template('update.html', todo=row[0])

@app.route('/updateSubmit', methods=['GET', 'POST'])
def updatesubmit():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    engine = get_connection()
    
    if request.method == 'POST':
        id = request.form.get('id')
        todotitle = request.form.get('todotitle')
        description = request.form.get('description')
        categories = request.form.get('categories')
        if todotitle and categories:
            with engine.connect() as con:
                rs = con.execute(text(f'update todoitem set  categories = "{categories}", title = "{todotitle}", description = "{description}"  where id = {id} and user_id = {uid}'))
                con.commit()
            if rs.rowcount > 0:
                flash('Successfully updated data!', 'green')
            else:
                flash('You are not authorized to update data!  ', 'red')
            
    return redirect(url_for("home"))
           
  
@app.route("/register" , methods=['GET', 'POST'])
def register():
    engine = get_connection()
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        if not (name and  email and password):
            flash('All fields are required!', 'red')
        else:
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            hashed_password = generate_password_hash(password)
            
            with engine.connect() as con:
                rs = con.execute(text(f'select id from user where email= "{email}";')).fetchone()
                if rs:
                    flash('Email already exists.', 'red')

                else:
                    rs = con.execute(text(f'INSERT INTO user (name, email, password, created_at, updated_at) values ( "{name}", "{email}", "{hashed_password}", "{formatted_time}", "{formatted_time}");'))
                    con.commit()
                    flash('Successfully data register!', 'green')

                    rs = con.execute(text(f"SELECT id, name FROM user where email='{email}'") )
                    row = rs.fetchone()
                    session['user_id'] = row[0]
                    session['user_name'] = row[1]
                    return redirect(url_for('home'))
    return render_template('register.html' ) 
        

@app.route("/login" , methods=['GET', 'POST'])
def login():
    engine = get_connection()
    if request.method == 'POST':
        password = request.form.get('password')
        email = request.form.get('email')
        if password and email:
            with engine.connect() as con:
                rs = con.execute(text(f'select id,password,name from user where email= "{email}";'))
                rows = rs.fetchall()
                if len(rows) and check_password_hash(rows[0][1], password):
                    session['user_id'] = rows[0][0]
                    session['user_name'] = rows[0][2]
                    flash('Successfully login!', 'green')
                    return redirect(url_for('home'))
                else:
                    flash('Invalid Login Details', 'red')
        else:
            flash('Invalid Login Details', 'red')

    return render_template('login.html' )

@app.route("/logout" , methods=['GET', 'POST'])
def logout():
    
    session.clear()
    flash('Successfully logout Please login!', 'green')
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True, port=8001)