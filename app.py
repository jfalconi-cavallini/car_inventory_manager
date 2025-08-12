from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import json
import scraper  # your scraper.py module
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cars.db'
app.config['SECRET_KEY'] = 'your-secret-key'
db = SQLAlchemy(app)


# Car model with VIN, image_url, and listing link added
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # e.g. 'available', 'sold'
    vin = db.Column(db.String(100), unique=True, nullable=True)  # VIN field
    image_url = db.Column(db.String(255), nullable=True)         # Image URL field
    link = db.Column(db.String(500), nullable=True)              # Listing link


#routes 
@app.route('/', methods=['GET', 'POST'])
def home():
    search = request.args.get('search')
    if search:
        cars = Car.query.filter(
            (Car.make.ilike(f'%{search}%')) | 
            (Car.model.ilike(f'%{search}%')) |
            (Car.status.ilike(f'%{search}%'))
        ).all()
    else:
        cars = Car.query.all()
    return render_template('home.html', cars=cars, search=search)

@app.route('/add', methods=['GET', 'POST'])
def add_car():
    if request.method == 'POST':
        car = Car(
            make=request.form['make'],
            model=request.form['model'],
            year=int(request.form['year']),
            price=float(request.form['price']),
            mileage=int(request.form['mileage']),
            status=request.form['status'],
            vin=request.form.get('vin'),
            image_url=request.form.get('image_url'),
            link=request.form.get('link')
        )
        db.session.add(car)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_car.html')

@app.route('/delete/<int:car_id>')
def delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/edit/<int:car_id>', methods=['GET', 'POST'])
def edit_car(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        car.make = request.form['make']
        car.model = request.form['model']
        car.year = int(request.form['year'])
        car.price = float(request.form['price'])
        car.mileage = int(request.form['mileage'])
        car.status = request.form['status']
        car.vin = request.form.get('vin')
        car.image_url = request.form.get('image_url')
        car.link = request.form.get('link')
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit_car.html', car=car)



def scheduled_scrape():
    with app.app_context():
        print("Running scheduled scraper...")
        base_url = 'https://www.claycooley.com/inventory/new-cars/'
        cars = scraper.scrape_all_new_cars(base_url)
        count_added = 0

        for car_data in cars:
            vin = car_data.get('vin')
            if vin:
                existing_car = Car.query.filter_by(vin=vin).first()
            else:
                existing_car = Car.query.filter_by(
                    make=car_data['make'],
                    model=car_data['model'],
                    year=int(car_data['year']) if str(car_data['year']).isdigit() else 0
                ).first()

            if existing_car:
                continue

            price = float(car_data.get('price', 0.0))
            mileage = int(car_data.get('mileage', 0))

            new_car = Car(
                make=car_data['make'],
                model=car_data['model'],
                year=int(car_data['year']) if str(car_data['year']).isdigit() else 0,
                price=price,
                mileage=mileage,
                status='available',
                vin=vin,
                image_url=car_data.get('image_url'),
                link=car_data.get('link')
            )
            db.session.add(new_car)
            count_added += 1

        db.session.commit()
        print(f"Scheduled scraping complete: {count_added} new cars added.")


#main code
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    #initialize scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()

    # Add the job to run scheduled_scrape every 1 hour (you can adjust this)
    scheduler.add_job(
        func=scheduled_scrape,
        trigger=IntervalTrigger(hours=24),  # every 1 hour
        id='scrape_job',
        name='Scrape car data every hour',
        replace_existing=True
    )

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


    app.run(host="0.0.0.0", port=8080)
