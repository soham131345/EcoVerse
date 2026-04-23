EcoVerse README.txt

This document explains how to set up and how to use the EcoVerse app.

1. Installation
Before running the app, make sure all required Python packages are installed.
Run install.bat to automatically install ALL required pip libraries.
Make sure Python is installed and added to PATH.
After installation, start the app using python app.py.

2. Running the app
METHOD1:
-open terminal, then open the folder this is saved into. eg: cd D:\EcoVerse
-then run: python app.py
-visit localhost:5000

METHOD2:
-open python IDLE
-press CTRL+ O/ click open
-open app.py
-click F5/click run
-visit localhost:5000

3. Logging in
Two accounts  are already default: 
user: admin
pass: admin123
user: demo
pass: demo123
Apart from these accounts, you can also create your own accounts by clicking request access on the index page.

4. Testing Routes
The following routes are intended ONLY for testing and debugging during development.
 /points-debug --> Instantly grants 50,000 eco points to the logged-in user. This is used to skip
the normal user grind and unlock advanced features for testing such as repeated flights,
certifications, and high-level content.
/ultra --> Unlocks the ULTRA LEGEND certification for testing purposes only.

5. Reset database
To reset the database, quit the flask server then delete the folder: instance. Run app.py again to have a completely new system.

6. NOTE:
Please note that this application includes some unused HTML files. 