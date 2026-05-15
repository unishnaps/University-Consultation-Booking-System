# University-Consultation-Booking-System
A web-based system for managing university consultation bookings between students and administrators.

# Requirements
Before running the project locally, make sure you have the following installed:
1.	Git
2.	VSCode or any other IDE
3.	Xampp
4.	MySQL
5.	Git Bash
6.	Python 3.x

# Setup Instructions
1.	Clone the repository
In git Bash
git clone https://github.com/unishnaps/University-Consultation-Booking-System.git
cd University-Consultation-Booking-System

2.	Create and activate a virtual environment
In powershell
python -m venv venv
Windows:
venv\Scripts\activate
macOS/Linux:
source venv/bin/activate

3.	Install dependencies
In powershell
pip install -r requirements.txt

4.	Open the Xampp and Start the following services.
•	Apache
•	MySQL
•	FileZilla

5.	Configure the environment
Create a .env file
Example of .env file structure:
SECRET_KEY=
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=uniconsult_db
DB_PORT=3306

6.	Initialize the database
In powershell
mysql -u root -p < database.sql

7.	Run the application
In powershell
python app.py
Open http://localhost:5000 in your browser.

# Default Accounts
| Role | Email | Password |
|------|------|------|
| Admin | admin@university.edu | Admin@1234 |
| Student | j.smith@university.edu | Student@1234 |
