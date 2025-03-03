from flask import Flask, render_template, url_for, flash, redirect, request, send_file, session
from app.extensions import db
import pandas as pd
from io import BytesIO
import datetime
import openpyxl
from werkzeug.security import generate_password_hash, check_password_hash

def create_app():
    app = Flask(__name__)

    #configure the application
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'secret-key'

    #initialize the database
    db.init_app(app)

    # Pre-populate the database with three admin users (if they don't already exist)
    def create_admin_users():
        db.create_all()
        if not AdminUser.query.filter_by(username='admin1').first():
            admin1 = AdminUser(username='admin1', password=generate_password_hash('password'))
            admin2 = AdminUser(username='admin2', password=generate_password_hash('password'))
            admin3 = AdminUser(username='admin3', password=generate_password_hash('password'))
            db.session.add_all([admin1, admin2, admin3])
            db.session.commit()

    #create the database
    with app.app_context():
        from app.models import User, AdminUser
        db.create_all()
        create_admin_users()

    #routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Login route: renders a login form on GET, validates credentials on POST
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            admin = AdminUser.query.filter_by(username=username).first()
            if admin and check_password_hash(admin.password, password):
                session['user'] = admin.username
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid credentials. Please try again.', 'danger')
                return redirect(url_for('login'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        flash('You have been logged out.', 'info')
        return render_template('index.html')
    
    @app.route('/error')
    def error():
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('index'))
    
    @app.route('/download')
    def download():
        # Query all users from the database
        users = User.query.all()

        # Convert the query results to a list of dictionaries
        data = [{
            "ID": user.id,
            "Username": user.username,
            "Email": user.email,
            "Password": user.password
        } for user in users]

        # Create a DataFrame from the list
        df = pd.DataFrame(data)

        # Write the DataFrame to an in-memory Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Users')
        output.seek(0)

        # Generate a filename with the current timestamp
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"download_{now}.xlsx"

        # Send the file to the client
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    @app.route('/view')
    def view():
        users = User.query.all()
        return render_template('view.html', users=users)
    
    @app.route('/delete_record/<int:id>',methods=['GET','POST'])
    def delete_record(id):
            if session.get('user') is None:
                return redirect(url_for('login'))
            else:
                record = User.query.get(id)
                db.session.delete(record)
                db.session.commit()
                flash('Record deleted successfully', 'success')
                return redirect(url_for('view'))
    
    @app.route('/update_record/<int:id>',methods=['GET','POST'])
    def update_record(id):
        return {'message': id}
    
    @app.route('/create_manual')
    def create_manual():
        if session.get('user') is None:
            return redirect(url_for('login'))
        else:
            data = pd.read_csv('./app/data/raw_data/user_raw.csv')
            for i in range(len(data)):
                if User.query.filter_by(username=data['username'][i]).first():
                    pass
                else:
                    user = User(username=data['username'][i], email=data['email'][i], password=data['password'][i])
                    db.session.add(user)
            db.session.commit()
            flash('Users created successfully', 'success')
            return render_template('index.html')
    
    # Define allowed file extensions
    ALLOWED_EXTENSIONS = {'csv'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # Your function to add a user to the database
    def add_user_to_db(username, email, password):
        if User.query.filter_by(username=username).first():
            return '{username} already exists.'
        else:
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()
            return '{username} added successfully.'

    @app.route('/upload', methods=['GET', 'POST'])
    def upload():
        if session.get('user') is None:
            return redirect(url_for('login'))
        else:
            if request.method == 'POST':
                # Check if the POST request has the file part
                if 'file' not in request.files:
                    flash('No file part in the request.', 'danger')
                    return redirect(url_for('index'))
                file = request.files['file']
                if file.filename == '':
                    flash('No file selected.','danger')
                    return redirect(url_for('index'))
                if file and allowed_file(file.filename):
                    try:
                        # Read the CSV file using pandas
                        df = pd.read_csv(file)
                        # Check if the CSV has the expected columns in order
                        expected_columns = ['username', 'email', 'password']
                        if list(df.columns) != expected_columns:
                            flash('CSV file must have columns: username, email, password in that order.')
                            return redirect(request.url)
                        # Process each row in the CSV
                        for index, row in df.iterrows():
                            add_user_to_db(row['username'], row['email'], row['password'])
                        flash('Users uploaded and processed successfully.')
                    except Exception as e:
                        flash(f"Error processing file: {str(e)}")
                else:
                    flash('Invalid file type. Only CSV files are allowed.')
                flash('Users uploaded and processed successfully.','success')
                return redirect(url_for('index'))
            return render_template('index.html')
        

    return app