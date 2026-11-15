from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SOURCE = Path('/Users/sreedhar/Documents/Sree-HVG/Sree_HVG_Resume/sree-resume.docx')
OUT = Path('/private/tmp/sree-resume-tailored.docx')
doc = Document(SOURCE)
original = list(doc.paragraphs)

# Retain the source document and its section order, replacing duplicated or
# less relevant wording and consolidating related engineering achievements.
summary = ('Senior engineer with 19+ years of experience in solution architecture and hands-on delivery of '
           'enterprise distributed systems, cloud-native platforms, and secure financial services. '
           'Designed payments, reconciliation, and user-management solutions at American Express, with '
           'strengths in RESTful API integration, platform modernization, reliability, and access governance. '
           'Partners with product teams, translates business requirements into technical solutions, and mentors engineers. '
           'Independent AI learning and personal proof-of-concept projects cover AI-assisted design documentation, '
           'API design, requirements analysis, and agentic systems.')

skills = [
    ('Architecture and integration', 'Solution architecture, distributed systems, RESTful APIs, microservices, event-driven systems, SaaS platforms, real-time services'),
    ('Hands-on engineering', 'Java, Spring Boot, Vert.x, Python, FastAPI, Pydantic, SQL/NoSQL, Redis'),
    ('AI learning and personal POCs', 'Google ADK, Vertex AI Agent Engine, Gemini, OpenAI SDK, Model Context Protocol (MCP), multi-agent orchestration, RAG, vector search, guardrails'),
    ('Security and governance', 'IAM, MFA, OAuth, RBAC, Microsoft Entra ID, SPIFFE/SPIRE, workload identity, policy-as-code, certificate lifecycle automation'),
    ('Cloud and operations', 'GCP, Docker, CI/CD, Splunk, Jaeger, distributed tracing, disaster recovery, production readiness; AWS and Azure familiarity'),
    ('Delivery and leadership', 'Agile, roadmap alignment, requirements analysis, code reviews, technical mentorship'),
]

experience = [
    'Led API strategy and implementation for application-to-application services on the Digital Servicing platform and technical architecture for payment-platform modernization.',
    'Partnered with the portfolio architect on a cross-platform architecture proposal that resulted in a $2.35M product-funded release strategy.',
    'Partnered with the product owner to define and execute the roadmap for migrating BTA-Connect clients to an in-house reconciliation platform.',
    'Designed and implemented enterprise-scale reconciliation, payments, and user-management platforms using Java, Vert.x, RESTful APIs, Redis, and microservices.',
    'Managed up to 30 contractors across four globally distributed scrum teams; oversaw code reviews, test automation, and operational-readiness assessments.',
    'Built self-service user-management capabilities that reduced corporate client onboarding time by 30%.',
    'Built IAM and MFA frameworks for regulated payment workflows; automated certificate renewal, reducing manual effort by 90% and preventing expiration-related incidents.',
    'Achieved $500K in one-time cost avoidance by aligning LAC market stakeholders and architects on adopting POA instead of modifying POD.',
]

calendar_project = [
    'Built a read-only calendar assistant using Python, Google ADK, Gemini, and FastAPI, with Google Calendar API tools for upcoming events and date-based availability queries.',
    'Implemented Microsoft Entra ID sign-in, delegated Google OAuth, token refresh, ADK conversation sessions, and browser chat that resumes pending questions after authentication.',
]

codeguard_project = [
    'Built a Python code-review risk assessment pipeline combining Git diff analysis, Tree-sitter structure metrics, secret detection, and OSV dependency vulnerability lookups.',
    'Integrated OpenAI and Claude triage with JSON Schema validation and retries to produce risk assessments, evidence references, and Markdown reports from extracted metadata.',
]

mcp_studio_project = [
    'Built FastAPI-hosted MCP clients and servers to explore Streamable HTTP sessions, tool discovery, invocation, and request inspection.',
    'Implemented MCP progress notifications and REST Server-Sent Events using shared streaming logic; configured Docker Compose and Nginx with buffering disabled.',
]

travel_project = [
    'Built an OpenAI-powered ReAct planner with planner, critic, executor, and summarizer roles, coordinating calendar, weather, and travel MCP services through a FastAPI JSON-RPC gateway.',
    'Implemented catalog-based tool authorization, Pydantic output contracts, bounded execution, evidence tracking, timeouts, and correlated logs using simulated domain data.',
]

verian = [
    'Led architecture and delivery of e-invoicing SaaS solutions and transformed an installer-based Purchase-to-Pay product into a cloud-hosted service.',
    'Reviewed requirements for gaps and dependencies, aligned designs with product managers, and mentored an offshore team of 10 contractors.',
]

harbor = [
    'Developed Java/J2EE SaaS solutions for accounts payable and receivable, including EDI and XML integrations and enterprise reference-architecture alignment.',
    'Led a $3M migration from Mercator to Informatica PowerCenter and Business Exchange to modernize enterprise data transformation.',
]

# All content remains ordinary body text for straightforward reading and parsing.
# The original placed contact information in a header text box.
body = doc._element.body
for child in list(body):
    if child.tag != qn('w:sectPr'):
        body.remove(child)
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(.62)
section.bottom_margin = Inches(.62)
section.left_margin = Inches(.72)
section.right_margin = Inches(.72)
section.header_distance = Inches(.25)
section.footer_distance = Inches(.25)
section.different_first_page_header_footer = False
for part in (section.header, section.first_page_header, section.even_page_header,
             section.footer, section.first_page_footer, section.even_page_footer):
    for child in list(part._element):
        part._element.remove(child)
    part._element.append(OxmlElement('w:p'))

for style in doc.styles:
    if style.type == 1:
        style.font.name = 'Palatino'
        style.font.color.rgb = RGBColor(0, 0, 0)
        rp = style.element.find(qn('w:rPr'))
        if rp is not None:
            col = rp.find(qn('w:color'))
            if col is not None:
                for k in list(col.attrib):
                    if k != qn('w:val'): del col.attrib[k]
        pp = style.element.find(qn('w:pPr'))
        if pp is not None:
            for x in list(pp):
                if x.tag in (qn('w:pBdr'), qn('w:shd')): pp.remove(x)

normal = doc.styles['Normal']
normal.font.name = 'Palatino'
normal.font.size = Pt(11)
normal.font.bold = False
normal.font.italic = False
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.06
normal.paragraph_format.left_indent = Inches(0)
normal.paragraph_format.right_indent = Inches(0)
normal.paragraph_format.first_line_indent = Inches(0)

def paragraph(text='', *, style='Normal', size=11, bold=False, before=0, after=4, keep=False):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.left_indent = Inches(0)
    pf.right_indent = Inches(0)
    pf.first_line_indent = Inches(0)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.06
    pf.keep_with_next = keep
    pf.keep_together = True
    pf.widow_control = True
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.name = 'Palatino'
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = False
    r.font.color.rgb = RGBColor(0, 0, 0)
    return p

def heading(text, before=10):
    return paragraph(text, style='Heading 1', size=11.5, bold=True, before=before, after=5, keep=True)

def bullet(text):
    p = paragraph(text, after=5)
    pf = p.paragraph_format
    pf.left_indent = Inches(.16)
    pf.first_line_indent = Inches(-.16)
    numPr = OxmlElement('w:numPr')
    ilvl = OxmlElement('w:ilvl'); ilvl.set(qn('w:val'),'0')
    numId = OxmlElement('w:numId'); numId.set(qn('w:val'),'2')
    numPr.extend([ilvl,numId]); p._p.get_or_add_pPr().append(numPr)
    return p

paragraph('Sreedhar Suswaram', style='Title', size=24, bold=True, after=3, keep=True)
paragraph('Phoenix, AZ  |  (901) 283-7338  |  sreedhar.sr@gmail.com', size=10.5, after=8, keep=True)
paragraph('Solution Architecture and Enterprise Platforms', size=12, bold=True, after=8, keep=True)
heading('PROFESSIONAL SUMMARY', before=0)
paragraph(summary, after=6)
heading('TECHNICAL SKILLS', before=7)
for label, text in skills:
    p = paragraph('', after=3)
    p.add_run(label + ': ').bold = True
    p.add_run(text)
heading('PROFESSIONAL EXPERIENCE', before=9)
paragraph('American Express | 2013–Present', style='Heading 2', size=11.5, bold=True, after=3, keep=True)
paragraph('Senior Engineer, 2018–Present  |  Lead Developer, 2013–2018', size=11, after=6, keep=True)
for b in experience: bullet(b)

p = heading('EARLIER PROFESSIONAL EXPERIENCE', before=0)
p.paragraph_format.page_break_before = True
paragraph('Verian | Technical Delivery Manager | 2010–2013', style='Heading 2', size=11.5, bold=True, after=6, keep=True)
for b in verian: bullet(b)
paragraph('Harbor Payments | Engineering Roles | 2006–2010', style='Heading 2', size=11.5, bold=True, before=5, after=6, keep=True)
for b in harbor: bullet(b)
heading('INDEPENDENT AI LEARNING AND PERSONAL PROJECTS', before=11)
paragraph('Personal learning and proof-of-concept work completed outside employment.', after=6, keep=True)
for index, (name, bullets) in enumerate([
    ('Travel Planner MCP', travel_project),
    ('CodeGuard Code Review Assistant', codeguard_project),
    ('MCP Studio', mcp_studio_project),
    ('ADK Calendar Assistant', calendar_project),
]):
    paragraph(name, style='Heading 2', size=11.5, bold=True, before=5 if index else 0, after=5, keep=True)
    for b in bullets: bullet(b)
heading('EDUCATION AND CERTIFICATIONS', before=11)
paragraph('M.S., Electrical & Computer Engineering — University of Memphis', after=5)
paragraph('Harvard Certificate in Leadership Excellence', after=3)
paragraph('Certified Scrum Master  |  SAFe Scrum XP', after=0)

# Remove stale document metadata, retaining only the author's supplied identity.
props = doc.core_properties
props.author = 'Sreedhar Suswaram'
props.last_modified_by = 'Sreedhar Suswaram'
props.title = 'Sreedhar Suswaram Resume'
props.subject = 'American Express Sr Solutions Architect I'
props.comments = ''
props.keywords = ''
doc.save(OUT)
print(OUT)
print('Words:', sum(len(p.text.split()) for p in doc.paragraphs))
