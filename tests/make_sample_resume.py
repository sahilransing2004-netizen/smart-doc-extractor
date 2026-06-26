"""Generates a synthetic born-digital resume PDF for testing the
direct-text-extraction path (i.e. a PDF with a real text layer,
the way Word/Canva/LaTeX would produce one)."""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUTPUT_PATH = "/home/sahilransing/smart-doc-extractor/sample_resumes/digital_resume.pdf"

lines = [
    "Sahil Ransing",
    "Email: sahil.ransing@example.com | Phone: +91-9876543210",
    "Location: Ahmedabad, India",
    "",
    "SUMMARY",
    "Aspiring DevOps and MLOps engineer with hands-on experience building",
    "end-to-end ML pipelines, CI/CD workflows, and cloud deployments.",
    "",
    "SKILLS",
    "Python, Bash, Docker, Git, FastAPI, Linux, AWS, Kubernetes (learning)",
    "",
    "EXPERIENCE",
    "Personal Projects - 2025 to present",
    "Built and deployed an expense tracking system using Flask and Supabase.",
    "Consolidated multiple ML projects into a unified GitHub portfolio.",
    "",
    "EDUCATION",
    "B.Tech, Computer Science - 2022 to 2026",
]

c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
text_obj = c.beginText(50, 800)
text_obj.setFont("Helvetica", 11)
for line in lines:
    text_obj.textLine(line)
c.drawText(text_obj)
c.save()

print(f"Sample digital resume written to {OUTPUT_PATH}")
