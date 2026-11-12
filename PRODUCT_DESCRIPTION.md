# PFS Online Portal - Product Description Report

**Prepared from:** rbac codebase (Django web application), live domain https://portal.pfsgh.com
**Organization:** Pneuma Food Scientifcs (PFS) - food science and regulatory compliance consultancy, Ghana
**Currency:** Ghana Cedis (GHS) | **Payment gateway:** Paystack | **Auth:** Email-based login
**Status:** Live, under active development section by section

---

## 1. Executive Summary

The PFS Online Portal is an end-to-end client management and certification platform for Pneuma Food Scientifcs, a Ghana-based food science consultancy. It takes a client from first discovering PFS services on the public website, through package selection and payment, account setup, compliance document upload and review, project initiation, staged service delivery, and ongoing support, while giving PFS staff (field associates, consultants, supervisors, and administrators) role-specific dashboards to manage their workload.

In plain terms: it is a client onboarding, compliance tracking, and service delivery portal for a food regulatory consulting business. Clients pay for a service package, upload the documents PFS needs to assess their facility or product, and then work with an assigned PFS team through every step until their registration or certification is complete.

## 2. What the App Does (in Plain Language)

### A public-facing service website
Visitors can learn about PFS, browse service packages and pricing, see the client journey, read about the team (ambassadors/associates and consultants), find FAQs, terms of service, and privacy policy, and get in touch. Once a visitor becomes a paying client and logs in, they are redirected to their own private client dashboard instead of the public pages.

### Package selection and payment
There are two overarching package families - Assessment Packages and Implementation Packages - each with a defined scope and sub-specific packages for different client needs. A prospective client chooses a package, provides their business name and email, and pays online through Paystack (accepting card, mobile money, bank transfer, etc.). Prices are listed in Ghana Cedis and are current. Payment is verified automatically with Paystack before an account is created, so only paying customers can register.

### Client registration and profile setup
After payment is verified, the client creates an account using their email (no username required) and completes a business profile: business name, WhatsApp and alternative phone numbers, emergency contact, company logo, sector (food, cosmetics, pharmaceuticals, supplements, etc.), and Ghana region (all 16 regions plus Diaspora).

### Compliance document upload and review
Clients provide compliance documents to PFS to facilitate their FDA approval process. PFS assists with some documents (for example, the Business Registration Certificate), while other documents must be obtained by the clients themselves (for example, a Food Handlers Certificate). Required documents vary by sector and package and may include:
- Business Registration Certificate
- Facility Floor Sketch Plan
- Company Logo / Brand Logo
- Proposed Product Labels
- Pictures of Product (With Label)
- Laboratory Results
- Medical Fitness Certificate (Health Card)
- Water Analysis Report
- Menu, Recipe Steps, Pest Control Certificate, SOPs (for food service clients)

Clients upload these files through a document vault. PFS staff review each document and mark it Approved, Pending, or Rejected (with a written rejection reason and optional attachment). Until the mandatory documents are approved, the client cannot move forward to project initiation.

### Project initiation and case management
Once documents are approved, PFS staff initiate a client project. Each project is categorized (e.g., FDA Active Clients, Product Development, Quality Systems Setup, Internal) and assigned to a consultant. The project contains a checklist of activities with statuses (Not Started, In Progress, Completed, Paused, Client Task), deadlines, notes, and per-activity payment status. Both staff and the client can track overall project completion as a percentage.


### FDA 20-stage regulatory workflow
For clients going through Ghana Food and Drugs Authority (FDA) registration, PFS uses a structured 20-stage workflow (from 5% up to 100% completion). This 20-stage workflow is an internal PFS process. Each stage is assigned to a specific staff role (Associate 1 through 5), and stages unlock one after another in sequence. Each stage tracks:
- Activity status (Complete, Ongoing, Waiting Internal/External, On Hold, Discontinued, Not Applicable)
- Payment gate status (To Confirm, Pending, Part Paid, Paid, Waived, Not Required)
- Work clearance (Cleared to Proceed, Payment Pending - Do Not Start, Follow-Up, On Hold)

This gives PFS a clear stage-by-stage view of where every client stands and what must happen before work can continue.

### Staff and field assistance (Associates / Ambassadors)
PFS field staff (called Associates or Ambassadors) are assigned to help individual clients. Assistance can be remote or in-person. Each assignment tracks status (Unassigned, Assigned/In Progress, Completed, Cancelled), and both the client and the associate can mark the assignment complete. Payout to the associate is triggered only once both sides confirm completion; payout integration is planned for a later release and will be done via in-app verification.

### Consultants
Verified consultants (subject-matter experts) undergo ID, CV, and selfie verification before approval. Approved consultants review client portfolios, audit documents, manage project boards, add activity notes, update activity statuses, and track their own availability.

### Appointments and meetings
PFS administrators set up availability slots (days and times they are available to meet). Clients can book an appointment in an open slot, specify a meeting topic and initial notes, and later receive a meeting link (e.g., Zoom, Google Meet, Teams) plus a meeting summary document. Staff can attach action items (to-dos) to each appointment.

### Staff certification and examinations
PFS runs internal exams for its associates and staff to certify their knowledge. Examinations are mandatory for all associates. Exam topics include PFS Company Knowledge, PFS Services, Client Management, Communication, Professionalism, Product Development, FDA, GMP, Sales, and PFS Culture. Exams are multiple choice, timed, and require a passing score. If a staff member fails, they are locked out for a short cooling-off period before retaking; repeated failures require revisiting the must-know materials, learning again, and sitting for the exams again. Supervisors and administrators create and manage exams and question banks (including bulk CSV upload).

### Payments and billing
Beyond the initial package payment, the platform supports:
- Payment requests raised by staff for a client (e.g., top-up fees), tracked as Pending/Paid/Cancelled
- Historical/offline payments recorded manually (cash, cheque, bank transfer, mobile money)
- Per-project and per-activity payment tracking (Paid, Part Paid, Not Paid, Included in Package)
- Full payment history visible to clients and administrators

### Administration and oversight
Super Administrators have full control: create and manage all users, reset roles, activate/deactivate or delete accounts, verify or decline associate and consultant applications, review and approve/reject client documents, initiate projects, raise payment requests, record historical payments, and view a global operations board grouping all client projects by category. Supervisors have a scoped version of these powers for their teams.

### Platform operations and security
- Login is by email and password; password reset emails are supported.
- Sessions expire after 30 minutes of inactivity and when the browser closes.
- Every user action that matters (document uploads, profile updates, payments) is logged in an activity feed.
- Maintenance mode is used during deployments (superadmin access is preserved).


## 3. Who the App Is For (Target Users)

Based on the features in the code, the platform serves five distinct user groups:

| User type | Who they are | What they use the portal for |
|---|---|---|
| **Clients / Food businesses** | Entrepreneurs and companies across Ghana and in the Diaspora (food, cosmetics, pharma, supplements, herbal, household chemicals, food service) seeking FDA registration, facility registration, product development, QMS setup, or business planning support | Browse services, pay for a package, register, upload compliance documents, track project progress, book appointments, view payment history, confirm assignment completion |
| **Associates / Ambassadors** | PFS field staff who work directly with clients, either remotely or through in-person visits | View assigned clients, manage assignments, mark tasks complete, review client documents, use role-specific FDA workflow dashboards (Associate 1-5), take mandatory certification exams, log availability |
| **Consultants** | Verified external or internal subject-matter experts | Complete identity/CV/selfie verification before approval; review client portfolios, audit documents, manage project activities and notes, update activity status, set weekly availability |
| **Supervisors** | PFS team leads who oversee associates and consultants | Verify team members, view client and payment details for their team, manage staff schedules, view verification queues, reassign work, view supervisor-scoped dashboards |
| **Super Administrators** | PFS platform operators and office management | Full user and role management, document approval/rejection, project initiation, payment requests and historical payments, global operations oversight, system maintenance |

**Primary target market:** Food and allied-product businesses nationwide in Ghana and in the Diaspora that need regulatory compliance support (especially Ghana FDA registration) and are comfortable paying online and managing paperwork through a web portal.

## 4. Core User-Facing Capabilities

### For the public / prospective clients
- Browse service packages and transparent GHS pricing on a public website
- Learn about the PFS client journey, team, services, and FAQs
- Contact PFS through a contact form
- Pay online via Paystack and instantly create an account after verification

### For clients (logged-in portal users)
- Create and manage a business profile (logo, contact numbers, sector, region)
- Upload mandatory compliance documents required for their sector
- View document review status (approved, pending, or rejected with reasons)
- Upload supplementary documents as needed
- View assigned project, activity checklist, and overall completion percentage
- View assigned associate/consultant and confirm when an assignment is complete
- Request a change of associate if needed
- Book appointments in available staff time slots
- View meeting links and summary documents after appointments
- View payment history and payment requests
- Reset password via email

### For associates / field staff
- View a role-specific dashboard showing active and completed FDA workflow stages for their clients
- Review client document submissions and approve/reject with notes
- Initiate client projects and manage project boards (add activities, notes, update status and payment)
- See a global board of all projects grouped by category
- Mark assignments complete (remote or in-person) and trigger payout
- Set and manage weekly availability
- Take mandatory internal certification exams

### For consultants
- Submit CV, government ID, and selfie for identity verification
- Once approved, review assigned client portfolios and documents
- Audit documents and record audit actions
- Manage project activity boards: add activities and notes, update statuses and payment status
- Manage weekly availability for meetings

### For supervisors
- Verify or decline associate and consultant applications
- View client and payment details for team members
- Manage staff schedules and availability
- View verification queues and reassign associates to different clients
- Record historical payments and view payment history

### For super administrators
- Create, edit, activate or deactivate, and delete any user account; manage roles
- Verify or decline all associate and consultant applications
- Approve or reject client compliance documents (with rejection reasons or files)
- Initiate client projects once mandatory documents are approved
- Raise custom payment requests for clients and record offline/historical payments
- View a global operations board of every client project grouped by category
- Place the platform in maintenance mode (used during deployments)


## 5. Business Value

- **Faster client onboarding:** Payment-gated registration means only serious, paying prospects enter the portal, and document requirements are clear and sector-specific.
- **Reduced paperwork and back-and-forth:** Clients upload documents once; staff approve or reject them in one place with reasons, eliminating lost files and unclear feedback.
- **Standardized service delivery:** The 20-stage FDA workflow ensures every registration project follows the same proven steps, with clear gatekeeping (no work starts until payment is cleared).
- **Accountability:** Every assignment, document review, payment, and user action is tracked and time-stamped, so managers always know who did what and where each client stands.
- **Revenue capture:** Online payments via Paystack, plus support for offline methods (cash, mobile money, bank transfer, cheque), ensure no payment goes unrecorded.
- **Staff quality control:** Internal exams and ID/CV/selfie verification ensure associates and consultants are qualified before they represent PFS to clients. Exams are mandatory for all associates.
- **Scalable operations:** Role-based access lets PFS add more staff and clients without giving everyone access to everything.

## 6. Confirmed Business Details

The following business details were confirmed with the product team:

1. **Package model:** Prices are current. There are two overarching package families - Assessment Packages and Implementation Packages - each with a defined scope and sub-specific packages for different client needs.
2. **FDA scope:** FDA refers to the Ghana Food and Drugs Authority. The 20-stage workflow is an internal PFS process used to manage client registration projects.
3. **Payouts:** Payout integration is planned for a later release and will be done via in-app verification.
4. **Examinations:** Exams are mandatory for all associates. Repeated failures require revisiting the must-know materials, learning again, and sitting for the exams again.
5. **Deployment:** The portal is live but still under development section by section.
6. **Coverage:** PFS offers services to clients nationwide and in the Diaspora (all 16 Ghana regions plus Diaspora).
7. **Document ownership:** Clients provide compliance documents to PFS to facilitate their FDA approval process. PFS assists with some documents (e.g., Business Registration Certificate), while other documents must be obtained by clients themselves (e.g., Food Handlers Certificate / Health Card).
8. **Maintenance mode:** Used during deployments (superadmin access preserved).

## 7. Technical Snapshot (for reference only)

- **Framework:** Django 6.0.5 (Python), SQLite database
- **Authentication:** Custom email-based user model with role-based access control (@role_required decorators)
- **Payments:** Paystack API integration
- **Email:** Gmail SMTP for password resets and notifications
- **Document storage:** Local/media file uploads (Pillow for image handling; ReportLab available for PDF generation)
- **Deployment:** Django admin included; error pages (400/403/404/500) and maintenance mode configured

---

*Report generated by scanning the rbac codebase at C:\Users\bbsab\OneDrive\Documents\HOLOGRAM DIGITAL\PNEUMA FOOD SCIENTIFICS\CERTIFICATIONS EMPIRE\rbac and confirmed with the product team.*

