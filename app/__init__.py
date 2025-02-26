from flask import Flask, render_template, url_for
from app.extensions import db
import pandas as pd

def create_app():
    app = Flask(__name__)

    #configure the application
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    #initialize the database
    db.init_app(app)

    #create the database
    with app.app_context():
        from app.models import User
        db.create_all()

    #routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/upload')
    def upload():
        return {'message':"render_template('upload.html')"}
    
    @app.route('/download')
    def download():
        return {'message':"render_template('download.html')"}
    
    @app.route('/view')
    def view():
        users = User.query.all()
        return render_template('view.html', users=users)
    
    @app.route('/create_manual')
    def create_manual():
        data = pd.read_csv('./app/data/raw_data/user_raw.csv')
        for i in range(len(data)):
            user = User(username=data['username'][i], email=data['email'][i], password=data['password'][i])
            db.session.add(user)
        db.session.commit()
        return {'message':'Data has been added successfully'}
        

    return app