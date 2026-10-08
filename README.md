
# ZEIL CareerConnect

## Project Overview

ZEIL CareerConnect helps job seekers prepare for their
target jobs through personalised AI-generated preparation
roadmaps, intelligent industry mentor matching, and
mock interview bookings.

## Core Feature

### AI-Powered Job Preparation Roadmap

Candidates enter a target job description, their existing
skills, and preparation time.

Google Gemini analyses job requirements and generates
a personalised weekly learning and interview preparation
roadmap.

## Nice-to-Have Features

### 1. Intelligent Mentor Recommendations
Matches candidate preparation priorities with fictional
industry mentor profiles based on relevant technical skills.

### 2. Mock Interview Booking
Allows candidates to select an industry mentor and
reserve an available mock interview session in demo mode.

## AI Technologies

- Google Gemini Flash: roadmap generation
- Pydantic: structured AI output validation
- Skill-based matching: mentor recommendations
- Python and Streamlit: application implementation

## Hackathon Bonus Challenges

- Built for Hiring (+20)
- Strict Shapes (+5), subject to demonstrating invalid-output handling

## Project Scope

The hackathon prototype focuses on generating useful
career preparation plans and connecting candidates with
relevant industry expertise.

Real payments, mentor verification, authentication and
video conferencing are future development opportunities.

## Run Locally

1. Create and activate a Python virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Create a .env file containing GEMINI_API_KEY.
4. Run:
   streamlit run app.py

## Demo Data

Mentor profiles and availability are fictional.
No actual payments or interviews are processed.
