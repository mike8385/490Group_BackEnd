-- Drop database if it exists and create a new one
DROP DATABASE IF EXISTS clinic_db;
CREATE DATABASE clinic_db;
USE clinic_db;

-- Drop tables if they exist before creating new ones
DROP TABLE IF EXISTS LIKED_POSTS;
DROP TABLE IF EXISTS POST_COMMENTS;
DROP TABLE IF EXISTS COMMUNITY_POST;
DROP TABLE IF EXISTS AUDIT_LOG;
DROP TABLE IF EXISTS LOG_TABLE;
DROP TABLE IF EXISTS CHAT;
DROP TABLE IF EXISTS USER;
DROP TABLE IF EXISTS PATIENT_BILL;
DROP TABLE IF EXISTS PATIENT_APPOINTMENT;
DROP TABLE IF EXISTS MEAL_PLAN;
DROP TABLE IF EXISTS MEAL;
DROP TABLE IF EXISTS MEAL_PLAN_ENTRY;
DROP TABLE IF EXISTS PATIENT_PRESCRIPTION;
DROP TABLE IF EXISTS PATIENT_WEEKLY;
DROP TABLE IF EXISTS PATIENT_DAILY_SURVEY;
DROP TABLE IF EXISTS PATIENT_INIT_SURVEY;
DROP TABLE IF EXISTS PATIENT;
DROP TABLE IF EXISTS MEDICINE_STOCK;
DROP TABLE IF EXISTS MEDICINE;
DROP TABLE IF EXISTS PHARMACY;
DROP TABLE IF EXISTS DOCTOR;
DROP TABLE IF EXISTS CHAT;
DROP TABLE IF EXISTS CHAT_MESSAGE;

-- Tables changed (need new mock data): Doctor, Patient, PATIENT_INIT_SURVEY
-- Basically new tables: MEAL, MEAL_PLAN, MEAL_PLAN_ENTRY
-- DOCTOR RELATED TABLES
CREATE TABLE DOCTOR ( -- the doctor related registration info
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL, -- doctor's login email
	password VARCHAR(255) NOT NULL,     -- hashed password
    description TEXT, -- a description of the doctor for the patient page
    license_num VARCHAR(9) UNIQUE NOT NULL, -- doctor must be a unique license num
    license_exp_date DATE NOT NULL,
    dob DATE NOT NULL,
    med_school VARCHAR (255) NOT NULL,
    years_of_practice INT CHECK (years_of_practice >= 0), 
    specialty VARCHAR(255) NOT NULL,
    payment_fee DECIMAL(6,2) CHECK (payment_fee >= 0), -- fixed fee for appointments
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    address TEXT NOT NULL,
    zipcode VARCHAR(5) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    doctor_picture BLOB,  -- Stores profile picture
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------

-- PHARMACY RELATED TABLES
CREATE TABLE PHARMACY ( -- pharmacy registration info
    pharmacy_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    address TEXT NOT NULL,
	zipcode VARCHAR(10) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    pharmacy_name VARCHAR(255) NOT NULL,  -- Name of the pharmacy
    store_hours VARCHAR(255),  -- Example: "Mon-Fri: 9 AM - 9 PM"
    password VARCHAR(255) NOT NULL,  -- Hashed password for authentication
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE MEDICINE ( -- the 5 medicines the user can choose from
    medicine_id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(255) UNIQUE NOT NULL,
    medicine_price DECIMAL(4, 2) NOT NULL, -- price per pill
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE MEDICINE_STOCK ( -- the inventory
    stock_id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_id INT NOT NULL,
    pharmacy_id INT NOT NULL,
    stock_count INT CHECK (stock_count >= 0),  -- Ensures stock is non-negative
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (medicine_id) REFERENCES MEDICINE(medicine_id) ON DELETE CASCADE,
    FOREIGN KEY (pharmacy_id) REFERENCES PHARMACY(pharmacy_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- MEAL PLAN TABLES

CREATE TABLE MEAL ( -- the meal information
    meal_id INT AUTO_INCREMENT PRIMARY KEY,
    meal_name VARCHAR(255) NOT NULL,
    meal_description TEXT,
    meal_calories INT CHECK (meal_calories >= 0),
    meal_picture BLOB,  -- To store meal images
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE MEAL_PLAN (
    meal_plan_id INT AUTO_INCREMENT PRIMARY KEY,
    meal_plan_name ENUM('Low Carb', 'Keto', 'Paleo', 'Mediterranean', 'Vegan', 'Vegetarian', 'Gluten-Free', 'Dairy-Free') NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE MEAL_PLAN_ENTRY (
    entry_id INT AUTO_INCREMENT PRIMARY KEY,
    meal_plan_id INT NOT NULL,
    meal_id INT NOT NULL,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
    meal_time ENUM('Breakfast', 'Lunch', 'Dinner') NOT NULL,
    FOREIGN KEY (meal_plan_id) REFERENCES MEAL_PLAN(meal_plan_id) ON DELETE CASCADE,
    FOREIGN KEY (meal_id) REFERENCES MEAL(meal_id) ON DELETE CASCADE,
    UNIQUE(meal_plan_id, day_of_week, meal_time), -- Prevents duplicate meals in same slot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- PATIENT RELATED TABLES
CREATE TABLE PATIENT ( -- patient registration info
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT,  -- Foreign key referencing a doctor table
    patient_email VARCHAR(255) UNIQUE NOT NULL,
    patient_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    doctor_rating DECIMAL(3,2) CHECK (doctor_rating BETWEEN 0 AND 5), -- rating for doctor and appointment
    pharmacy_id INT,  -- Foreign key referencing a pharmacy table
    profile_pic VARCHAR(255),  -- Storing profile picture path or URL
    insurance_provider VARCHAR(255),  -- Storing insurance provider name
    insurance_policy_number VARCHAR(255),  -- Storing insurance policy number
    insurance_expiration_date DATE,  -- Storing the insurance policy expiration date
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES DOCTOR(doctor_id),  -- Assuming a DOCTOR table exists
    FOREIGN KEY (pharmacy_id) REFERENCES PHARMACY(pharmacy_id)  -- Assuming a PHARMACY table exists
);

CREATE TABLE PATIENT_INIT_SURVEY ( -- what will be in what is initially asked for the survey
    is_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT,
    mobile_number VARCHAR(15) NOT NULL,  -- Storing phone number
    dob DATE NOT NULL,  -- Date of Birth, age can be calculated from DOB
    gender ENUM('Male', 'Female', 'Other'),
    height DECIMAL(5,2),  -- Storing height in cm or inches
    weight DECIMAL(5,2),  -- Storing weight in kg or lbs
    activity DECIMAL(5,2),
    health_goals VARCHAR(800),
    dietary_restrictions TEXT,  -- Storing multiple dietary restrictions
    blood_type VARCHAR(10) NOT NULL,
    patient_address TEXT NOT NULL,
	patient_zipcode VARCHAR(10) NOT NULL,
    patient_city VARCHAR(100) NOT NULL,
    patient_state VARCHAR(50) NOT NULL,
    medical_conditions TEXT,  -- Storing medical conditions
    family_history TEXT,  -- Storing family history
    past_procedures TEXT,  -- Storing previous procedures
    favorite_meal VARCHAR(255),  -- Storing favorite meal -- random dummy question for about me
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE CASCADE
);

CREATE TABLE PATIENT_DAILY_SURVEY ( -- the everyday survey info
    ds_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    date DATE NOT NULL,
    water_intake INT NOT NULL,  -- In glasses of water, user must enter 0 if they have not drank water
    calories_consumed INT CHECK (calories_consumed >= 0),
    heart_rate INT CHECK (heart_rate >= 0),  -- BPM
    exercise INT NOT NULL,  -- Minutes of exercise, user must enter 0 if they have not exercised
    mood VARCHAR(50),  -- Mood description
    follow_plan TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE CASCADE
);
 
CREATE TABLE PATIENT_WEEKLY ( -- weekly survey info
    ws_id INT AUTO_INCREMENT PRIMARY KEY,  -- Unique ID for the weekly record
    patient_id INT NOT NULL,  -- References patient
    week_start DATE NOT NULL,  -- Start of the weekly range
    blood_pressure VARCHAR(20) NOT NULL,  -- Example format: '120/80'
    weight_change DECIMAL(5,2) NOT NULL,  -- Weight change in lbs, BMI will be inserted based on height from PATIENT_INIT_SURVEY, calculate on application layer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,  -- Record update timestamp
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE CASCADE
);


CREATE TABLE PATIENT_PRESCRIPTION ( -- defines patient prescription from appointment with quantity of medication
    prescription_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    medicine_id INT NOT NULL,
    quantity INT NOT NULL, -- number of pills
    picked_up TINYINT DEFAULT 0,  -- 0 = false, 1 = true
    filled TINYINT DEFAULT 0,  -- 0 = false, 1 = true
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES MEDICINE(medicine_id)  
);

CREATE TABLE PATIENT_APPOINTMENT (
    patient_appt_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_datetime DATETIME NOT NULL, -- for when the appt is
    reason_for_visit TEXT NOT NULL, -- why the appt
    current_medications TEXT, -- what meds the patient is on
    exercise_frequency VARCHAR(255), -- how much the patient exercises
    doctor_appointment_note TEXT,  -- NULL until completed
    accepted TINYINT default 0,
    meal_prescribed ENUM('Low Carb', 'Keto', 'Paleo', 'Mediterranean', 'Vegan', 'Vegetarian', 'Gluten-Free', 'Dairy-Free', 'Whole30', 'Flexitarian'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES PATIENT(doctor_id) ON DELETE CASCADE
);


CREATE TABLE PATIENT_BILL ( -- the patient's bill
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    appt_id INT NOT NULL, -- what appointment it is for
    unit_price DECIMAL(10,2) CHECK (unit_price >= 0), -- the normal price
    charge DECIMAL(10,2) CHECK (charge >= 0), -- how much they are getting charged
    credit DECIMAL(10,2) CHECK (credit >= 0), -- how much credit they have
    current_bill DECIMAL(10,2) GENERATED ALWAYS AS (charge - credit) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (appt_id) REFERENCES PATIENT_APPOINTMENT(patient_appt_id) ON DELETE CASCADE
);
-- ---------------------------------------------------------------------
-- GENERAL TABLES
CREATE TABLE USER ( -- a general table to reference the users
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT UNIQUE,  
    doctor_id INT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE SET NULL,
    FOREIGN KEY (doctor_id) REFERENCES DOCTOR(doctor_id) ON DELETE SET NULL
);

CREATE TABLE LOG_TABLE (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    logged_in TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logged_out TIMESTAMP NULL,  -- Will be NULL until the user logs out
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE
);

CREATE TABLE AUDIT_LOG ( -- audit of what goes on within the app
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,  -- NULL if event is system-generated
    event_type VARCHAR(255) NOT NULL, -- e.g., 'Prescription Created', 'Login Failed'
    table_name VARCHAR(255) NOT NULL, -- table that was affected 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE SET NULL
);
-- ----------------------------------------------------------------------
-- COMMUNITY RELATED TABLES
CREATE TABLE COMMUNITY_POST ( -- a post a user makes
    post_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL, -- the user who made the post
    category VARCHAR(100) NOT NULL,
    description TEXT,
    picture BLOB,  -- Storing images
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE
);

CREATE TABLE POST_COMMENTS ( -- comments that a specific post has
    comment_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES COMMUNITY_POST(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE
);

CREATE TABLE LIKED_POSTS ( -- posts that are liked from a user
    liked_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES COMMUNITY_POST(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    UNIQUE (post_id, user_id)  -- Ensures a user can like a post only once
);

-- ----------------------------------------------------------------------
-- Chat related tables
CREATE TABLE CHAT (
    chat_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL, -- Foreign key referencing patient who is chatting
    doctor_id INT NOT NULL,  -- Foreign key referencing the doctor in the chat
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Chat start date
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- Last update timestamp
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES DOCTOR(doctor_id) ON DELETE CASCADE
);

CREATE TABLE CHAT_MESSAGE (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    chat_id INT NOT NULL, -- Foreign key to CHAT table
    sender_id INT NOT NULL, -- Either patient or doctor (can be inferred by sender_id)
    receiver_id INT NOT NULL, -- Either doctor or patient (the other party)
    message TEXT NOT NULL, -- Message content
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Message sent timestamp
    FOREIGN KEY (chat_id) REFERENCES CHAT(chat_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES USER(user_id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES USER(user_id) ON DELETE CASCADE
);
