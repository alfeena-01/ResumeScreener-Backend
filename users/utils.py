from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import os
from dotenv import load_dotenv
load_dotenv(override=True)

import json
import PyPDF2
from .models import JobApplication

try:
    import google.generativeai as genai
except ImportError:
    pass

def setup_gemini():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def extract_text_from_pdf(file_obj):
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return ""

def generate_job_description(title, level, skills):
    try:
        if not title or not skills:
            return {
                "description": "Title and skills are required.",
                "requirements": "Please provide both title and skills."
            }
        
        if not setup_gemini():
            return {
                "description": "API Key not configured.",
                "requirements": "Configure GEMINI_API_KEY in your environment."
            }
        
        prompt = f"""You are an expert HR Manager. The user is asking you to write a professional Job Description for a {level} {title}.
The key skills required are: {skills}.
Please generate a cohesive, professional job description and a bulleted list of requirements.
Return ONLY a raw JSON object (no markdown formatting, no backticks) with the keys:
{{
  "description": "...",
  "requirements": "..."
}}"""
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        if not response or not hasattr(response, 'text'):
            return {
                "description": "No response from API.",
                "requirements": "The API did not return a valid response."
            }
        
        text = response.text
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        
        data = json.loads(text)
        return data
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in generate_job_description: {e}")
        return {
            "description": "Failed to parse API response as JSON.",
            "requirements": f"JSON Error: {str(e)}"
        }
    except Exception as e:
        print(f"Error generating JD: {type(e).__name__}: {e}")
        return {
            "description": "Failed to generate job description.",
            "requirements": f"{type(e).__name__}: {str(e)}"
        }

def calculate_match_score(resume_text, job_desc, job_reqs):
    try:
        if not setup_gemini():
            return 0, "AI not configured."
        if not resume_text:
            return 0, "Resume text could not be extracted."

        prompt = f"""You are an expert ATS (Applicant Tracking System).
Here is a candidate's resume text:
---
{resume_text}
---

Here is the Job Description:
---
{job_desc}
---

Here are the Job Requirements:
---
{job_reqs}
---

Evaluate the candidate against the job. Calculate a match percentage from 0 to 100 based on how well their skills and experience align with the job requirements. Also list the key missing skills.
Return ONLY a raw JSON object (no markdown formatting, no backticks) with the keys:
{{
  "match_percentage": integer,
  "missing_skills": ["skill1", "skill2..."]
}}"""
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        if not response or not hasattr(response, 'text'):
            return 0, "No response from API"
        
        text = response.text
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()
        data = json.loads(text)
        
        perc = data.get("match_percentage", 0)
        missing = data.get("missing_skills", [])
        return perc, ", ".join(missing) if missing else "All required skills present"
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in calculate_match_score: {e}")
        return 0, f"Error parsing response: {str(e)}"
    except Exception as e:
        print(f"Error calculating match score: {type(e).__name__}: {e}")
        return 0, f"Error generating match score: {str(e)}"


def send_application_confirmation_email(application):
    subject = f'Application Submitted - {application.job.title}'
    context = {
        'applicant_name': application.applicant.get_full_name() or application.applicant.username,
        'job_title': application.job.title,
        'company_name': application.job.company_name,
        'job_location': application.job.location,
        'applied_date': application.applied_date.strftime('%B %d, %Y'),
    }

    html_message = render_to_string('emails/application_confirmation.html', context)

    send_mail(
        subject=subject,
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.applicant.email],
        fail_silently=False,
    )


def send_status_update_email(application, old_status):
    if application.status == old_status:
        return

    subject = f'Application Status Update - {application.job.title}'

    context = {
        'applicant_name': application.applicant.get_full_name() or application.applicant.username,
        'job_title': application.job.title,
        'company_name': application.job.company_name,
        'job_location': application.job.location,
        'applied_date': application.applied_date.strftime('%B %d, %Y'),
        'status': application.status,
    }

    html_message = render_to_string('emails/status_update.html', context)

    send_mail(
        subject=subject,
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.applicant.email],
        fail_silently=False,
    )