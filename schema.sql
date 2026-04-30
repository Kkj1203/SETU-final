-- schema.sql
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS ambulances;
DROP TABLE IF EXISTS hospitals;
DROP TABLE IF EXISTS requests;

-- ── Auth / identity ───────────────────────────────────────────────────────────
CREATE TABLE users (
  user_id    TEXT PRIMARY KEY,
  name       TEXT NOT NULL,
  email      TEXT UNIQUE NOT NULL,
  password   TEXT NOT NULL,        -- bcrypt hashed
  role       TEXT NOT NULL,        -- admin | patient | hospital_staff | first_responder
  linked_id  TEXT,                 -- patient_id | hosp_id | amb_id
  created_at TEXT
);

-- ── Patients ──────────────────────────────────────────────────────────────────
CREATE TABLE patients (
  patient_id         TEXT PRIMARY KEY,
  name               TEXT,
  dob                TEXT,
  gender             TEXT,
  blood_group        TEXT,
  allergies          TEXT,
  conditions         TEXT,
  medications        TEXT,
  biometric_template TEXT
);

-- ── Ambulances ────────────────────────────────────────────────────────────────
CREATE TABLE ambulances (
  amb_id       TEXT PRIMARY KEY,
  vehicle_no   TEXT,
  driver_name  TEXT,
  current_lat  REAL,
  current_lng  REAL,
  status       TEXT
);

-- ── Hospitals ─────────────────────────────────────────────────────────────────
CREATE TABLE hospitals (
  hosp_id TEXT PRIMARY KEY,
  name    TEXT,
  address TEXT,
  lat     REAL,
  lng     REAL,
  beds    INTEGER,
  icu     INTEGER,
  status  TEXT
);

-- ── Requests ──────────────────────────────────────────────────────────────────
CREATE TABLE requests (
  req_id            TEXT PRIMARY KEY,
  batch_id          TEXT,
  patient_id        TEXT,
  amb_id            TEXT,
  hosp_id           TEXT,
  created_at        TEXT,
  urgency           TEXT,
  status            TEXT,   -- pending | assigned | closed | declined
  assigned_hosp     TEXT,
  response_ts       TEXT,
  eta_minutes       INTEGER,
  current_situation TEXT
);

-- ── Seed: default admin ───────────────────────────────────────────────────────
-- password = "admin123"  (bcrypt hash generated at first run — placeholder here)
-- actual hash is inserted by app.py on init_db()

-- ── Seed: Ambulances ──────────────────────────────────────────────────────────
INSERT INTO ambulances VALUES('AMB1','MH12AB1234','Rahul',18.5204,73.8567,'idle');
INSERT INTO ambulances VALUES('AMB2','MH12XY7890','Vikas',18.5312,73.8499,'idle');

-- ── Seed: Hospitals ───────────────────────────────────────────────────────────
INSERT INTO hospitals VALUES('H001','City General Hospital','MG Road',18.5220,73.8560,50,10,'open');
INSERT INTO hospitals VALUES('H002','St. Marys Hospital','Camp Area',18.5180,73.8590,30,5,'open');
INSERT INTO hospitals VALUES('H003','Trauma Care Centre','Pune Road',18.5300,73.8500,20,8,'open');
INSERT INTO hospitals VALUES('H004','Fallback Govt Hospital','Outer Area',18.5400,73.8450,40,12,'open');
INSERT INTO hospitals VALUES('H005','Ruby Hall Clinic','Sassoon Road',18.5308,73.8780,80,15,'open');
INSERT INTO hospitals VALUES('H006','Jehangir Hospital','Bund Garden',18.5340,73.8785,60,12,'open');
INSERT INTO hospitals VALUES('H007','Sancheti Hospital','Shivaji Nagar',18.5285,73.8472,45,10,'open');
INSERT INTO hospitals VALUES('H008','Deenanath Mangeshkar Hospital','Erandwane',18.5105,73.8293,100,20,'open');
INSERT INTO hospitals VALUES('H009','Inlaks Budhrani Hospital','Koregaon Park',18.5370,73.8850,70,14,'open');
INSERT INTO hospitals VALUES('H010','Lokmanya Hospital','Nigdi',18.6420,73.7600,55,11,'open');
INSERT INTO hospitals VALUES('H011','Sahyadri Hospital','Karve Road',18.5030,73.8130,90,25,'open');
INSERT INTO hospitals VALUES('H012','Aditya Birla Hospital','Chinchwad',18.6280,73.8030,85,20,'open');
INSERT INTO hospitals VALUES('H013','Noble Hospital','Hadapsar',18.4960,73.9330,65,18,'open');
INSERT INTO hospitals VALUES('H014','KEM Hospital','Rasta Peth',18.5195,73.8700,75,22,'open');
INSERT INTO hospitals VALUES('H015','Bharati Hospital','Dhankawadi',18.4690,73.8570,80,18,'open');
