# knight_hacks_8
knighthacks VIII project
💊 Digital Prescription Verification System
📖 Overview

The Digital Prescription Verification System is a secure web application built with Flask, SQLite, and OCR/QR technology to authenticate and manage medical prescriptions. It allows verified medical professionals (issuers) to create digital prescriptions and authorized officials (verifiers) to confirm their legitimacy using either a unique code or an uploaded image.

This project was designed to combat prescription fraud by creating a trustworthy, digital-first platform that streamlines verification and ensures prescription authenticity.

🚀 Key Features

Two User Roles

🧑‍⚕️ Issuer: Doctors and pharmacists can securely create and sign prescriptions, which are automatically assigned a unique code and a scannable QR tag.

🕵️ Verifier: Authorized personnel (e.g., police, medical authorities) can verify prescriptions using an image, QR code, or manual code entry.

Smart Verification System

Built-in OCR (Optical Character Recognition) using the OCR.Space API for reading prescription details from uploaded images.

Integrated QR Code Scanning for instant digital verification.

Secure PDF Generation

Each prescription can be downloaded as a PDF containing the doctor’s details, patient info, medications (with quantity), and the verification QR code.

Role-Based Access Control

Users have access only to features specific to their roles.

Login sessions are secured using Flask’s session management.

Centralized dashboard for easy access to Issuer and Verifier functions.

🧠 Tech Stack

Frontend: HTML, CSS (inline styling, responsive layout)

Backend: Flask (Python)

Database: SQLite

APIs & Libraries:

OCR.Space API for text extraction

ReportLab for PDF generation

Pyzbar & Pillow for QR code handling

qrcode for generating QR tags
