import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import UserRole
from common.decorators import role_required, mandatory_docs_required
from .forms import ClientProfileForm
from django.contrib import messages
from .models import ClientDocument, ClientRegion, DocumentType, DocumentStatus, ActivityLog, LogCategory, ProductCategory, ClientProject, ClientPackage as PackageChoices, ActivityStatus, PaymentStatus, ProjectActivity, ProjectGroup
from accounts.models import UserRole
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max, F
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction, models
from .signals import get_activities_for_package


User = get_user_model()


# Activity Log Helper Code
def create_activity_log(user, category, description):
    ActivityLog.objects.create(user=user, category=category, description=description)

# Dashboard Redirect
@login_required
def redirect_dashboard(request):
    user = request.user
    role = str(user.role)

    if role == UserRole.SUPER_ADMIN:
        return redirect("dashboard:super-admin-dashboard")
    
    elif role == UserRole.SUPERVISOR:
        return redirect("dashboard:supervisor-dashboard")
    
    elif role == UserRole.CONSULTANT:
        return redirect("dashboard:consultant-dashboard")
    
    elif role == UserRole.AMBASSADOR:
        return redirect("dashboard:ambassador-dashboard")
    
    elif role == UserRole.USER:
        return redirect("dashboard:user-dashboard")
    
    raise PermissionError("You do not have a valid role assigned!")


# SUPER ADMIN Dashboard
@login_required
@role_required([UserRole.SUPER_ADMIN])
def super_admin_dashboard(request):
    return render(request, "dashboards/super_admin.html")


# SUPERVISOR Dashboard
@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_dashboard(request):
    return render(request, "dashboards/supervisor.html")



# ****************************************************** CONSULTANT DASHBOARD ************************************************** #
# ****************************************************************************************************************************** #

@login_required
@role_required([UserRole.CONSULTANT])
def consultant_dashboard(request):
    """
    High-level operational overview desk for PFS consultants.
    Computes accurate performance metrics dynamically without relying on static
    project status fields, and isolates urgent document action queues.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    consultant = request.user

    # 1. Optimize Client Project Footprint using ORM Annotations
    # Evaluates total activities vs. completed activities at the database level.
    annotated_projects = ClientProject.objects.filter(
        assigned_consultant=consultant
    ).annotate(
        total_activities=Count('activities'),
        completed_activities=Count('activities', filter=Q(activities__activity_status=ActivityStatus.COMPLETED))
    )

    # 2. Derive Progress Metrics on ClientProject via Automated Progress Logic
    # Completed Vaults: Total activities > 0 and total equals completed counts
    completed_projects_qs = annotated_projects.filter(
        total_activities__gt=0, 
        total_activities=F('completed_activities')
    )
    completed_vaults_count = completed_projects_qs.count()

    # Active Projects: The inversion of completed workflows
    active_projects_qs = annotated_projects.exclude(
        total_activities__gt=0, 
        total_activities=F('completed_activities')
    )
    total_active_projects_count = active_projects_qs.count()

    # Onboarding Files: Active projects where absolutely no tasks are done yet
    active_onboarding_count = active_projects_qs.filter(completed_activities=0).count()

    # 3. Handle Step Phase Routing Counts based on Activity Names
    # Counts active projects containing specific critical milestone descriptors
    facility_phase_count = active_projects_qs.filter(
        activities__activity_name__icontains="Facility",
        activities__activity_status__in=[ActivityStatus.ONGOING, ActivityStatus.NOT_STARTED, ActivityStatus.CLIENT_TASK]
    ).distinct().count()

    label_phase_count = active_projects_qs.filter(
        activities__activity_name__icontains="Label",
        activities__activity_status__in=[ActivityStatus.ONGOING, ActivityStatus.NOT_STARTED, ActivityStatus.CLIENT_TASK]
    ).distinct().count()

    # 4. Assembled Corrected Context Architecture
    context = {
        "metrics": {
            "total_clients": User.objects.filter(role="USER").count(),
            "total_active_projects": total_active_projects_count,
            "active_onboarding": active_onboarding_count,
            "urgent_attention": ClientDocument.objects.filter(
            # Captures documents if assigned to you OR if the file hasn't been locked to a project setup yet
            Q(client__projects__assigned_consultant=consultant) | Q(client__projects__isnull=True),
            status=DocumentStatus.PENDING
            ).distinct().count(),
            "completed_vaults": completed_vaults_count,
            "facility_phase_count": facility_phase_count,
            "label_phase_count": label_phase_count,
        },
        "recent_pending_uploads": ClientDocument.objects.filter(
        Q(client__projects__assigned_consultant=consultant) | Q(client__projects__isnull=True),
        status=DocumentStatus.PENDING
        ).select_related('client').order_by("-updated_at").distinct()[:5]
    }

    return render(request, "dashboards/consultant.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def consultant_client_submissions(request):
    """
    Master queue view for PFS consultants.
    Fetches all accounts matching UserRole.USER with database-level pagination.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    clients_queryset = User.objects.filter(role='USER').order_by('-id')
    
    required_types = [
        DocumentType.BUSINESS_CERT,
        DocumentType.HEALTH_CARD,
        DocumentType.FACILITY_SKETCH,
    ]
    required_count = len(required_types)

    # 1. Server-Side Pagination Extraction
    page = request.GET.get('page', 1)
    paginator = Paginator(clients_queryset, 10)  # Standardizes on 10 records per page

    try:
        paginated_clients = paginator.page(page)
    except PageNotAnInteger:
        paginated_clients = paginator.page(1)
    except EmptyPage:
        paginated_clients = paginator.page(paginator.num_pages)

    # 2. Compile the operational dashboard data matrix
    clients_data = []
    for client in paginated_clients:
        uploaded_count = client.documents.filter(
            document_type__in=required_types
        ).exclude(file="").count()
        
        percentage = int((uploaded_count / required_count) * 100) if required_count > 0 else 0
        is_complete = uploaded_count >= required_count

        clients_data.append({
            'client': client,
            'uploaded_count': uploaded_count,
            'required_count': required_count,
            'percentage': percentage,
            'is_complete': is_complete
        })

    context = {
        'clients_data': clients_data,
        'page_obj': paginated_clients,
    }
    return render(request, "dashboards/consultant_client_submissions.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def review_client_portfolio(request, client_id):
    """
    Renders an exclusive review audit workspace tracking single client assets
    coupled with contextual sequential pagination indexing fields.
    """

    client = get_object_or_404(User, id=client_id, role='USER')
    client_docs = client.documents.all()

    active_projects = client.projects.all().order_by("-id")
    
    uploaded_dict = {
        doc.document_type: doc for doc in client_docs 
        if doc.document_type != DocumentType.SUPPLEMENTARY
    }
    
    documents_data = []
    for type_key, type_label in DocumentType.choices:
        if type_key == DocumentType.SUPPLEMENTARY:
            continue
        documents_data.append({
            'type_key': type_key,
            'type_label': type_label,
            'doc': uploaded_dict.get(type_key, None)
        })

    supplementary_documents = client_docs.filter(document_type=DocumentType.SUPPLEMENTARY).order_by('id')

    # 3. Queue Switcher Calculation Pipeline
    master_queue_ids = list(
        User.objects.filter(role='USER').order_by('-id').values_list('id', flat=True)
    )
    
    try:
        current_idx = master_queue_ids.index(client.id)
        prev_client_id = master_queue_ids[current_idx - 1] if current_idx > 0 else None
        next_client_id = master_queue_ids[current_idx + 1] if current_idx < len(master_queue_ids) - 1 else None
        queue_position = current_idx + 1
    except ValueError:
        prev_client_id = None
        next_client_id = None
        queue_position = 1

    context = {
        'client': client,
        'documents_data': documents_data,
        'supplementary_documents': supplementary_documents,
        'active_projects': active_projects,
        'prev_client_id': prev_client_id,
        'next_client_id': next_client_id,
        'queue_position': queue_position,
        'total_queue_count': len(master_queue_ids),
    }
    return render(request, "dashboards/audit_client.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def process_audit_action(request, doc_id):
    """
    POST route handling immediate validation switches targeting a ClientDocument row.
    """
    if request.method == 'POST':
        document = get_object_or_404(ClientDocument, id=doc_id)
        action_type = request.POST.get('action_type')

        display_name = document.custom_title if document.document_type == DocumentType.SUPPLEMENTARY else document.get_document_type_display()

        if document.status == DocumentStatus.APPROVED:
            messages.error(request, "This action cannot be performed. This document has already been verified and locked.")
            return redirect('dashboard:review-client', client_id=document.client.id)

        if action_type == 'APPROVE':
            document.status = DocumentStatus.APPROVED
            document.rejection_reason = ""
            document.save()
            
            ActivityLog.objects.create(
                user=document.client,
                category=LogCategory.SYSTEM,
                description=f"Compliance asset '{display_name}' was verified and approved."
            )
            messages.success(request, f"Approved compliance asset: '{display_name}'.")

        elif action_type == 'REJECT':
            reason = request.POST.get('rejection_reason', '').strip()
            
            if not reason:
                messages.error(request, f"You must provide a rejection reason to flag '{display_name}' as rejected.")
                return redirect('dashboard:review-client', client_id=document.client.id)
                
            document.status = DocumentStatus.REJECTED
            document.rejection_reason = reason
            document.save()
            
            ActivityLog.objects.create(
                user=document.client,
                category=LogCategory.SYSTEM,
                description=f"Deficiency flagged on '{display_name}'. Revision requested."
            )
            messages.warning(request, f"Flagged deficiency feedback note for '{display_name}'.")

        return redirect('dashboard:review-client', client_id=document.client.id)
        
    return redirect('dashboard:consultant-dashboard')


@login_required
@role_required([UserRole.CONSULTANT])
def consultant_companies_list(request):
    """
    Master searchable directory of all registered client companies.
    """
    search_query = request.GET.get('search', '').strip()
    clients_qs = User.objects.filter(role='USER')
    
    if search_query:
        clients_qs = clients_qs.filter(
            Q(business_name__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
    
    clients_qs = clients_qs.annotate(
        total_docs=Count('documents'),
        latest_upload=Max('documents__updated_at')
    ).order_by('business_name', '-id')

    required_types = [DocumentType.BUSINESS_CERT, DocumentType.HEALTH_CARD, DocumentType.FACILITY_SKETCH]
    required_count = len(required_types)
    
    companies_data = []
    for client in clients_qs:
        approved_core = client.documents.filter(
            document_type__in=required_types,
            status=DocumentStatus.APPROVED
        ).count()
        
        submitted_core = client.documents.filter(
            document_type__in=required_types
        ).exclude(file="").count()
        
        has_pending = client.documents.filter(status=DocumentStatus.PENDING).exists()
        completion_rate = int((approved_core / required_count) * 100) if required_count > 0 else 0
        
        companies_data.append({
            'client': client,
            'completion_rate': completion_rate,
            'approved_count': approved_core,
            'required_count': required_count,
            'submitted_count': submitted_core,
            'has_pending': has_pending,
            'latest_upload': client.latest_upload
        })

    context = {
        'companies_data': companies_data,
        'search_query': search_query,
    }
    return render(request, "dashboards/consultant_companies_list.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def consultant_company_overview(request, client_id):
    """
    360 degree snapshot profile for a specific client company.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    client = get_object_or_404(User, id=client_id, role='USER')
    
    docs = client.documents.all()
    approved_count = docs.filter(status=DocumentStatus.APPROVED).count()
    pending_count = docs.filter(status=DocumentStatus.PENDING).count()
    rejected_count = docs.filter(status=DocumentStatus.REJECTED).count()
    
    recent_logs = ActivityLog.objects.filter(user=client).order_by('-timestamp')[:6]
    
    if rejected_count > 0:
        account_status = "Action Required"
        status_color = "amber"
    elif pending_count > 0:
        account_status = "Under Review"
        status_color = "indigo"
    elif approved_count >= 3:
        account_status = "Fully Compliant"
        status_color = "emerald"
    else:
        account_status = "Incomplete Setup"
        status_color = "slate"

    context = {
        'client': client,
        'stats': {
            'approved': approved_count,
            'pending': pending_count,
            'rejected': rejected_count,
            'total': docs.count()
        },
        'account_status': account_status,
        'status_color': status_color,
        'recent_logs': recent_logs,
    }
    return render(request, "dashboards/consultant_company_overview.html", context)


@login_required
@role_required(['CONSULTANT'])
def initiate_client_project(request, client_id):
    """
    Audits and validates target account mandatory asset statuses, establishes the master 
    workspace model instance, and delegates task creation safely to the database layer.
    """
    client_user = get_object_or_404(User, id=client_id, role='USER')
    
    # 1. GATEKEEPER VALIDATION: Confirm mandatory onboarding compliance assets are approved
    required_types = [DocumentType.BUSINESS_CERT, DocumentType.HEALTH_CARD, DocumentType.FACILITY_SKETCH]
    approved_core_count = client_user.documents.filter(
        document_type__in=required_types,
        status=DocumentStatus.APPROVED
    ).count()
    
    if approved_core_count < len(required_types):
        messages.error(
            request, 
            f"Cannot initialize board. This client has only completed {approved_core_count}/{len(required_types)} mandatory document approvals."
        )
        return redirect("dashboard:review-client", client_id=client_user.id)
    
    # 2. BOUNDARY VALIDATION: Prevent duplicate active projects on a single user profile
    if hasattr(client_user, 'project_file'):
        messages.warning(request, "An active operational workflow file already exists for this portfolio.")
        return redirect("dashboard:project-board", project_id=client_user.project_file.id)

    # 3. FORM OPERATIONS HANDLER (POST)
    if request.method == "POST":
        group = request.POST.get("group")
        client_package = request.POST.get("client_package")
        category = request.POST.get("category")
        region = request.POST.get("region")
        project_start_date = request.POST.get("project_start_date")
        product_names = request.POST.get("product_names", "")
        overall_project_notes = request.POST.get("overall_project_notes", "")
        
        try:
            with transaction.atomic():
                # Writing the project to the database triggers the post_save receiver cleanly
                project = ClientProject.objects.create(
                    client=client_user,
                    group=group,
                    client_package=client_package,
                    category=category,
                    region=region,
                    project_start_date=project_start_date,
                    product_names=product_names,
                    overall_project_notes=overall_project_notes,
                    assigned_consultant=request.user
                )

            messages.success(request, f"Operational workflow board activated successfully for {client_user.business_name or client_user.email}!")
            return redirect("dashboard:project-board", project_id=project.id)

        except Exception as e:
            messages.error(request, f"Operational submission failure: {str(e)}")
            return redirect("dashboard:initiate-client-project", client_id=client_user.id)

    # 4. DATA PRESENTATION PROCESSING (GET)
    # Dynamically extract lists directly out of the helper for your template's Alpine preview engine
    frontend_blueprints = {
        choice_key: get_activities_for_package(choice_key)
        for choice_key, _ in PackageChoices.choices
    }

    context = {
        "target_client": client_user,
        "groups": ProjectGroup.choices,
        "packages": PackageChoices.choices,
        "categories": ProductCategory.choices,
        "regions": ClientRegion.choices,
        "blueprints_json": json.dumps(frontend_blueprints),
    }
    return render(request, "dashboards/initiate_project.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def project_service_board(request, project_id):
    """
    Renders the unified operational tracking workspace interface.
    """
    project = get_object_or_404(ClientProject.objects.prefetch_related('activities'), id=project_id)
    
    context = {
        "project": project,
        "completion_percentage": project.automated_progress,
        "payment_choices": PaymentStatus.choices,
        "activity_choices": ActivityStatus.choices,
    }
    return render(request, "dashboards/project_board.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def update_activity_status(request, activity_id):
    """
    Processes seamless inline dropdown choices straight from the board grid.
    """
    if request.method == "POST":
        activity = get_object_or_404(ProjectActivity, id=activity_id)
        update_type = request.POST.get("update_type")
        status_value = request.POST.get("status_value")
        
        if update_type == "PAYMENT":
            activity.payment_status = status_value
        elif update_type == "ACTIVITY":
            activity.activity_status = status_value
            
        activity.save()
        return redirect("dashboard:project-board", project_id=activity.project.id)
        
    return redirect("dashboard:consultant-dashboard")



# GLOBAL PROJECTS BOARD
@login_required
@role_required([UserRole.CONSULTANT])
def global_operations_boards(request):
    """
    Renders a top-level macro overview of the operational ecosystem.
    Gathers all active initialized client projects and buckets them tightly 
    by their overarching ProjectGroup category boards.
    """
    # Grab all active projects with prefetched records for dynamic performance tracking
    projects = ClientProject.objects.select_related('client', 'assigned_consultant').prefetch_related('activities').all()
    
    # Initialize an empty matrix mapped directly to your model's ProjectGroup choices
    boards_matrix = {
        group_key: {
            "label": group_label,
            "projects": [],
            "total_subitems_count": 0
        }
        for group_key, group_label in ProjectGroup.choices
    }
    
    # Map, bucket, and tally subactivities across categories cleanly
    for proj in projects:
        group_key = proj.group
        if group_key in boards_matrix:
            subitems_count = proj.activities.count()
            boards_matrix[group_key]["projects"].append(proj)
            boards_matrix[group_key]["total_subitems_count"] += subitems_count

    context = {
        "boards_matrix": boards_matrix,
    }
    return render(request, "dashboards/global_boards.html", context)


# ADD PROJECT SUB-ITEMS
@login_required
def add_custom_project_subitem(request, project_id):
    """
    POST-only action endpoint allowing account consultants to instantly append 
    ad-hoc project subitems to an active operational roadmap.
    """
    if request.method == "POST":
        project = get_object_or_404(ClientProject, id=project_id)
        activity_name = request.POST.get("activity_name", "").strip()
        activity_deadline = request.POST.get("activity_deadline")
        
        if not activity_name:
            messages.error(request, "Operational subitem addition aborted. A valid task execution title must be provided.")
            return redirect("dashboard:project-board", project_id=project.id)
            
        ProjectActivity.objects.create(
            project=project,
            activity_name=activity_name,
            activity_deadline=activity_deadline if activity_deadline else None,
            payment_status=PaymentStatus.NOT_PAID,
            activity_status=ActivityStatus.NOT_STARTED
        )
        
        messages.success(request, f"Successfully appended custom task subitem: '{activity_name}'.")
        return redirect("dashboard:project-board", project_id=project.id)
        
    return redirect("dashboard:global-boards")



# AMBASSADOR Dashboard
@login_required
@role_required([UserRole.AMBASSADOR])
def ambassador_dashboard(request):
    return render(request, "dashboards/ambassador.html")



#********************************************************** CLIENT DASHBOARD **************************************************#
#******************************************************************************************************************************#
# CLIENT Dashboard Overview
@login_required
@role_required([UserRole.USER])
def user_dashboard(request):
    """
    Manages the regular client dashboard workspace state.
    Handles multi-file onboarding uploads and automatically transitions
    the view state when the initial baseline is completed.
    """

    # Define our list of mandatory baseline document keys
    required_types = [
        DocumentType.BUSINESS_CERT,
        DocumentType.HEALTH_CARD,
        DocumentType.FACILITY_SKETCH
    ]

    # --- HTTP POST: PROCESS INCOMING FILE UPLOADS ---
    if request.method == 'POST':
        files_saved = 0
        
        # Iterate over every possible file slot we expect from the template form
        for doc_key in required_types:
            if doc_key in request.FILES:
                uploaded_file = request.FILES[doc_key]
                
                # update_or_create overrides an existing row or provisions a new one.
                # It prevents database IntegrityErrors due to the unique_together constraint.
                
                document, created = ClientDocument.objects.update_or_create(
                    client=request.user,
                    document_type=doc_key,
                    defaults={
                        'file': uploaded_file,
                        'status': DocumentStatus.PENDING  # Reset status back to pending upon re-upload
                    }
                )
                files_saved += 1

        if files_saved > 0:
            messages.success(request, f"Successfully uploaded and saved {files_saved} file(s).")
        else:
            messages.error(request, "No files selected. Please choose a valid file to upload.")
            
        return redirect('dashboard:user-dashboard')

    # --- HTTP GET: EVALUATE & RENDER CURRENT VIEW STATE ---
    client_docs = request.user.documents.all()
    
    # Generate an easy context map lookup: { 'BUSINESS_CERT': DocumentObject, ... }
    uploaded_dict = {doc.document_type: doc for doc in client_docs}
    
    # Count how many of our *required keys* exist in the client's asset pool
    total_required = len(required_types)
    total_uploaded = client_docs.filter(document_type__in=required_types).count()
    
    context = {
        'uploaded_dict': uploaded_dict,
        'total_uploaded': total_uploaded,
        'total_required': total_required,
    }

    # If the user has fulfilled all baseline uploads, dynamically swap out the UI view template
    if total_uploaded >= total_required:
        recent_activities = request.user.activities.all()[:5]

        context = {
            "recent_activities": recent_activities,
        }

        return render(request, "dashboards/user_tracking.html", context)
        
    # Default State: Still missing some baseline elements
    return render(request, "dashboards/user.html", context)


# Client Documents
@login_required
@role_required([UserRole.USER])
@mandatory_docs_required
def user_documents_vault(request):
    """
    Manages explicit standalone updates for all static required baseline FDA document types.
    """
    # Extract only standard statutory keys
    all_document_keys = [
        choice[0] for choice in DocumentType.choices 
        if choice[0] != 'SUPPLEMENTARY'
    ]

    # Fetch existing core documents into a dictionary mapping for quick lookup
    client_docs = request.user.documents.all()
    uploaded_dict = {
        doc.document_type: doc for doc in client_docs 
        if doc.document_type != 'SUPPLEMENTARY'
    }

    if request.method == 'POST':
        saved_count = 0
        
        for doc_key in all_document_keys:
            if doc_key in request.FILES:
                
                # Check if this specific document key is already approved
                existing_doc = uploaded_dict.get(doc_key)
                if existing_doc and existing_doc.status == DocumentStatus.APPROVED:
                    messages.error(request, f"Modifications blocked: Your {existing_doc.get_document_type_display()} is already approved and cannot be altered.")
                    return redirect('dashboard:user-documents')

                # Proceed safely if it's new or not yet approved
                doc, created = ClientDocument.objects.update_or_create(
                    client=request.user,
                    document_type=doc_key,
                    defaults={
                        'file': request.FILES[doc_key],
                        'status': DocumentStatus.PENDING  # Require re-review on update
                    }
                )
                saved_count += 1

                # Log Activity Stream
                action = "Uploaded a new version of" if not created else "Submitted initial draft of"
                create_activity_log(
                    user=request.user,
                    category=LogCategory.DOCUMENT,
                    description=f"{action} {doc.get_document_type_display()}."
                )
        
        if saved_count > 0:
            messages.success(request, f"Successfully uploaded and cataloged {saved_count} core file(s) inside your vault.")
        return redirect('dashboard:user-documents')

    # Grab all custom requests in insertion order
    supplementary_documents = client_docs.filter(document_type='SUPPLEMENTARY').order_by('id')
    
    context = {
        'uploaded_dict': uploaded_dict,
        'supplementary_documents': supplementary_documents,
        'total_uploaded': client_docs.exclude(file="").count(),
    }
    return render(request, "dashboards/user_documents.html", context)



# CLIENT Supplementary Documents Slot
@login_required
@role_required([UserRole.USER])
@mandatory_docs_required
def create_supplementary_slot(request):
    if request.method == 'POST':
        title = request.POST.get('custom_title', '').strip()

        if not title:
            messages.error(request, "Asset tracking generation failed. You must provide a descriptive name.")
            return redirect('dashboard:user-documents')
        
        # Defensive Check: Does this client already have this exact custom slot?
        existing_slot = ClientDocument.objects.filter(
            client=request.user,
            document_type='SUPPLEMENTARY',
            custom_title__iexact=title # Case-insensitive match check
        ).exists()

        if existing_slot:
            messages.warning(request, f"A requirement slot named '{title}' already exists in your vault.")
            return redirect('dashboard:user-documents')
        
        # If it passes the check, create it safely
        ClientDocument.objects.create(
            client=request.user,
            document_type='SUPPLEMENTARY',
            custom_title=title,
            status=DocumentStatus.PENDING
        )
        messages.success(request, f"New dynamic slot created for '{title}'.")

    return redirect('dashboard:user-documents')


# CLIENT Supplementary Documents Upload
@login_required
@role_required([UserRole.USER])
@mandatory_docs_required
def upload_document_asset(request, doc_id):
    """
    Processes the raw file multi-part file upload form binding for a targeted slot.
    Handles both traditional core entries and dynamically generated slots uniformly.
    """
    if request.method == 'POST' and request.FILES.get('attached_file'):
        # Secure catch boundary targeting strictly the active user context scope
        document = get_object_or_404(ClientDocument, id=doc_id, client=request.user)
        
        # Enforce validation locks on audited materials
        if document.status == DocumentStatus.APPROVED:
            messages.error(request, "This tracking item is currently verified and locked.")
            return redirect('dashboard:user-documents')

        # Attach multi-part binary payload stream directly
        document.file = request.FILES['attached_file']
        document.status = DocumentStatus.PENDING  # Reset workflow routing state flags
        document.save()
        
        display_name = document.custom_title if document.document_type == 'SUPPLEMENTARY' else document.get_document_type_display()
        
        # Log Custom Supplementary Submission activity record
        create_activity_log(
            user=request.user,
            category=LogCategory.DOCUMENT,
            description=f"Attached file asset payload to supplementary slot: '{display_name}'."
        )
        
        messages.success(request, f"Document binary successfully uploaded for '{display_name}'.")
        
    return redirect('dashboard:user-documents')


# CLIENT Profile
@login_required
@role_required([UserRole.USER])
def user_profile(request):
    # Only let regular users see this view
    if not request.user.is_regular_user:
         return redirect('dashboard:redirect-dashboard')
         
    if request.method == 'POST':
        # Pass instance=request.user to target the active logged-in user directly
        form = ClientProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()

            # Log Activity
            create_activity_log(
                user=request.user, 
                category=LogCategory.PROFILE, 
                description="Updated authorized representative details."
            )
            messages.success(request, "Your contact metrics have been saved successfully!")
            return redirect('dashboard:user-profile')
    else:
        form = ClientProfileForm(instance=request.user)

    context = {
        "form": form,
    }

    return render(request, "dashboards/user_profile.html", context)
