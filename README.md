# Air-Ticket-Booking-System (BACKUP BRANCH)
this is just a backup branch that contains all the documentation and code for ML and old code before deployment and dockerisation.

Repository for building the suyati project for the airport ticket booking system

The program will assume the password of the localhost mysql server to be 'mysql'

### Features
1. Users can create their user account.
2. Users can book both one-way as well as round-trip tickets.
3. Webpages are mobile responsive.
4. Users can cancel their booked tickets.
5. Users can view their previously booked tickets (Both confirmed and cancelled tickets).
6. Tickets are downloadable as pdf document.
7. As-you-type Search
8. Per-Airplane Arrival Delay Predicted by Machine Learning based on Historical Data
   
### Installation

- Install Python from [here](https://www.python.org/downloads/) manually.
- Install project dependencies by running `python -m pip install -r requirements.txt`.
- Run the commands `python manage.py makemigrations` and `python manage.py migrate` in the project directory to make and apply migrations.
- Create superuser with `python manage.py createsuperuser`. (This step is optional.)
- Run the command `python manage.py runserver` to run the web server.
- Open web browser and goto `127.0.0.1:8000` url to start using the web application.
