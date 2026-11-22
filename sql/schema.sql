-- ============================================================================
-- Hospital Emergency and Patient Priority Management System
-- Database Schema & Seed Data
-- ============================================================================

CREATE DATABASE IF NOT EXISTS hospital_db;
USE hospital_db;

-- Drop tables in reverse foreign key order for clean resets
DROP TABLE IF EXISTS treatment_log;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;

-- ----------------------------------------------------------------------------
-- 1. Doctors Table
-- ----------------------------------------------------------------------------
CREATE TABLE doctors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    current_patient_id INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- 2. Patients Table
-- ----------------------------------------------------------------------------
CREATE TABLE patients (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(10) NOT NULL,
    contact VARCHAR(20) NOT NULL,
    complaint TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority TINYINT NOT NULL COMMENT '1=Critical, 2=Urgent, 3=Moderate, 4=Minor',
    status ENUM('WAITING', 'IN_TREATMENT', 'DISCHARGED') DEFAULT 'WAITING',
    arrival_time DATETIME NOT NULL,
    treatment_start DATETIME NULL,
    discharge_time DATETIME NULL,
    assigned_doctor_id INT NULL,
    CONSTRAINT fk_patients_doctor FOREIGN KEY (assigned_doctor_id) 
        REFERENCES doctors(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- 3. Treatment Log Table (Timeline / Linked List history persistence)
-- ----------------------------------------------------------------------------
CREATE TABLE treatment_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    note TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_patient FOREIGN KEY (patient_id) 
        REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------------------------
-- Indexes for Performance
-- ----------------------------------------------------------------------------
CREATE INDEX idx_patients_status_priority ON patients(status, priority);
CREATE INDEX idx_treatment_log_patient_id ON treatment_log(patient_id);

-- ============================================================================
-- Seed Data
-- ============================================================================

-- 1. Insert 5 Initial Doctors
INSERT INTO doctors (id, name, specialization, is_available, current_patient_id) VALUES
(1, 'Dr. Robert Chase', 'Emergency Medicine', TRUE, NULL),
(2, 'Dr. Allison Cameron', 'Trauma Surgery', TRUE, NULL),
(3, 'Dr. Gregory House', 'Diagnostic Medicine & Cardiology', TRUE, NULL),
(4, 'Dr. Eric Foreman', 'Neurology', TRUE, NULL),
(5, 'Dr. Lisa Cuddy', 'Internal Medicine & Pediatrics', TRUE, NULL);

-- 2. Insert 8 Initial Patients with Mixed Priorities and Arrival Timestamps
-- Demonstrates priority ordering and FIFO tie-breaking within the Min-Heap.
INSERT INTO patients (id, name, age, gender, contact, complaint, category, priority, status, arrival_time, treatment_start, discharge_time, assigned_doctor_id) VALUES
(1, 'Johnathan Miller', 58, 'Male', '+1-555-0101', 'Acute retrosternal chest pain radiating to left arm (suspected STEMI)', 'Cardiac', 1, 'WAITING', '2026-11-22 10:00:00', NULL, NULL, NULL),
(2, 'Sarah Connor', 34, 'Female', '+1-555-0102', 'High-speed motor vehicle collision, blunt head trauma with altered sensorium', 'Trauma', 1, 'WAITING', '2026-11-22 10:08:00', NULL, NULL, NULL),
(3, 'Michael Scott', 45, 'Male', '+1-555-0103', 'Severe acute right lower quadrant abdominal pain, nausea, rebound tenderness', 'Surgery', 2, 'WAITING', '2026-11-22 09:55:00', NULL, NULL, NULL),
(4, 'Emma Watson', 28, 'Female', '+1-555-0104', 'Acute severe asthma exacerbation with audible wheezing and low SpO2 (91%)', 'Respiratory', 2, 'WAITING', '2026-11-22 10:12:00', NULL, NULL, NULL),
(5, 'David Chen', 52, 'Male', '+1-555-0105', 'Open fracture of left forearm from fall, bleeding controlled', 'Orthopedics', 3, 'WAITING', '2026-11-22 09:40:00', NULL, NULL, NULL),
(6, 'Olivia Taylor', 22, 'Female', '+1-555-0106', 'Deep kitchen knife laceration on palm, requires exploration and sutures', 'Trauma', 3, 'WAITING', '2026-11-22 10:15:00', NULL, NULL, NULL),
(7, 'James Wilson', 31, 'Male', '+1-555-0107', 'Inversion injury to right ankle during basketball, moderate swelling', 'Orthopedics', 4, 'WAITING', '2026-11-22 09:30:00', NULL, NULL, NULL),
(8, 'Sophia Garcia', 19, 'Female', '+1-555-0108', 'Mild seasonal viral fever (38C), sore throat, and nasal congestion', 'General', 4, 'WAITING', '2026-11-22 09:50:00', NULL, NULL, NULL);

-- 3. Initial Treatment Logs for Seed Patients
INSERT INTO treatment_log (patient_id, status, note, created_at) VALUES
(1, 'WAITING', 'Triage assessment complete: Severe chest pain, Priority 1 (Critical). Placed in Min-Heap waiting queue.', '2026-11-22 10:00:00'),
(2, 'WAITING', 'Triage assessment complete: Traumatic head injury, Priority 1 (Critical). Placed in Min-Heap waiting queue.', '2026-11-22 10:08:00'),
(3, 'WAITING', 'Triage assessment complete: Suspected appendicitis, Priority 2 (Urgent). Placed in Min-Heap waiting queue.', '2026-11-22 09:55:00'),
(4, 'WAITING', 'Triage assessment complete: Acute respiratory distress, Priority 2 (Urgent). Placed in Min-Heap waiting queue.', '2026-11-22 10:12:00'),
(5, 'WAITING', 'Triage assessment complete: Left forearm fracture, Priority 3 (Moderate). Placed in Min-Heap waiting queue.', '2026-11-22 09:40:00'),
(6, 'WAITING', 'Triage assessment complete: Palmar laceration, Priority 3 (Moderate). Placed in Min-Heap waiting queue.', '2026-11-22 10:15:00'),
(7, 'WAITING', 'Triage assessment complete: Ankle sprain, Priority 4 (Minor). Placed in Min-Heap waiting queue.', '2026-11-22 09:30:00'),
(8, 'WAITING', 'Triage assessment complete: Viral syndrome, Priority 4 (Minor). Placed in Min-Heap waiting queue.', '2026-11-22 09:50:00');
