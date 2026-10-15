from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Count, F
from django.utils.dateparse import parse_date
from common.decorators import role_required
from accounts.models import UserRole
from dashboard.models import ClientProject, ActivityStatus, DocumentStatus, ClientDocument, DocumentType, ActivityLog, LogCategory, ProjectGroup, ClientRegion, ProductCategory, ClientPackage as PackageChoices, ProjectActivity, ActivityNote, PaymentStatus
from .models import FDAProjectTracker, FDAWorkflowStage, FDAProjectStageActivity, FDAPaymentGate, FDAActivityStatus, FDAPaymentGateStatus, FDAWorkClearance, PaymentScope
from django.contrib.auth.decorators import login_required
from .services import evaluate_project_stages_for_role

from django.contrib.auth import get_user_model
from common.decorators import get_required_document_types
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.db import transaction
from dashboard.signals import get_activities_for_package

User = get_user_model()



def get_role_dashboard(request, role_code, template_name):
    """
    Renders the dashboard for a given role (Associate 1..5, Consultant, etc.)
    """
    all_trackers = FDAProjectTracker.objects.all()
    
    all_active_tasks = []
    all_completed_tasks = []

    for tracker in all_trackers:
        active, completed = evaluate_project_stages_for_role(tracker, role_code)
        all_active_tasks.extend(active)
        all_completed_tasks.extend(completed)

    context = {
        'role_code': role_code,
        'active_tasks': all_active_tasks,
        'completed_tasks': all_completed_tasks,
    }
    return render(request, template_name, context)


@login_required
def associate_one_dashboard(request):
    return get_role_dashboard(request, 'ASSOCIATE_1', 'fda/associate_1.html')

@login_required
def associate_two_dashboard(request):
    return get_role_dashboard(request, 'ASSOCIATE_2', 'fda/associate_2.html')

@login_required
def associate_four_dashboard(request):
    return get_role_dashboard(request, 'ASSOCIATE_4', 'fda/associate_4.html')

@login_required
def associate_five_dashboard(request):
    return get_role_dashboard(request, 'ASSOCIATE_5', 'fda/associate_5.html')

@login_required
def consultant_dashboard(request):
    return get_role_dashboard(request, 'CONSULTANT', 'fda/consultant.html')



# ==========================================
# 1. PROJECT UPDATES (MASTER MATRIX VIEW)
# ==========================================

@role_required([UserRole.ASSOCIATE_1, UserRole.ASSOCIATE_2, UserRole.ASSOCIATE_3,
    UserRole.ASSOCIATE_4, UserRole.ASSOCIATE_5, UserRole.CONSULTANT,
    UserRole.SUPERVISOR, UserRole.SUPER_ADMIN
])
def tracker_list_view(request):
    """
    Renders the 'Project Updates' matrix matching Columns A through AB.
    """
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    stages = FDAWorkflowStage.objects.all().order_by('stage_number')
    trackers = FDAProjectTracker.objects.select_related(
        'project', 'project__client'
    ).prefetch_related(
        'stage_activities__stage',
        'payment_gates'
    ).order_by('project__client__business_name')

    # Filtering
    if search_query:
        trackers = trackers.filter(
            Q(project__client__business_name__icontains=search_query) |
            Q(project__client__email__icontains=search_query)
        )
    if status_filter:
        trackers = trackers.filter(project__group=status_filter)

    context = {
        'stages': stages,
        'trackers': trackers,
        'activity_statuses': FDAActivityStatus.choices,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'fda/tracker_list.html', context)


@require_POST
@role_required([
    UserRole.ASSOCIATE_1, UserRole.ASSOCIATE_2, UserRole.ASSOCIATE_3,
    UserRole.ASSOCIATE_4, UserRole.ASSOCIATE_5, UserRole.CONSULTANT,
    UserRole.SUPERVISOR, UserRole.SUPER_ADMIN
])
def update_stage_activity_status(request, tracker_id, stage_id):
    """
    AJAX / HTMX or form action to update an activity cell status in the matrix.
    """
    activity = get_object_or_404(
        FDAProjectStageActivity, 
        tracker_id=tracker_id, 
        stage_id=stage_id
    )
    new_status = request.POST.get('status')
    
    if new_status in dict(FDAActivityStatus.choices):
        activity.status = new_status
        activity.save()

        # Update Project Last Contacted / Update Note if provided
        tracker = activity.tracker
        last_contacted = request.POST.get('last_contacted')
        latest_update = request.POST.get('latest_update')

        if last_contacted:
            tracker.last_contacted = parse_date(last_contacted)
        if latest_update is not None:
            tracker.latest_update_blocker = latest_update
        
        tracker.save()
        messages.success(request, f"Updated {activity.stage.short_stage_name} for {tracker.project.client.business_name or tracker.project.client.email}")

    return redirect('fda:tracker_list')


@login_required
def update_stage_status(request, tracker_id, activity_id):
    if request.method == 'POST':
        activity = get_object_or_404(FDAProjectStageActivity, id=activity_id, tracker_id=tracker_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(FDAProjectStageActivity.STATUS_CHOICES):
            activity.status = new_status
            activity.save()
            
            # Recalculate highest stage % achieved for tracker
            tracker = activity.tracker
            completed_percentages = tracker.stage_activities.filter(
                status='COMPLETE'
            ).values_list('stage__stage_percentage', flat=True)
            
            tracker.highest_stage_percentage = max(completed_percentages, default=0)
            tracker.save()

    return redirect(request.META.get('HTTP_REFERER', 'fda:tracker_list'))


# ==========================================
# 2. TEAM TASKS (OPERATIONAL QUEUE)
# ==========================================

@role_required([
    UserRole.ASSOCIATE_1, UserRole.ASSOCIATE_2, UserRole.ASSOCIATE_3,
    UserRole.ASSOCIATE_4, UserRole.ASSOCIATE_5, UserRole.CONSULTANT,
    UserRole.SUPERVISOR, UserRole.SUPER_ADMIN
])
def team_tasks_view(request):
    """
    Renders the 'Team Tasks' sheet: Filterable by handler role, displays dynamic work clearance.
    """
    handler_role = request.GET.get('handler_role', 'ALL').strip()
    status_filter = request.GET.get('status', 'ALL').strip()

    # Query active/ongoing/waiting stage activities
    activities = FDAProjectStageActivity.objects.select_related(
        'tracker', 
        'tracker__project', 
        'tracker__project__client', 
        'stage'
    ).prefetch_related(
        'tracker__payment_gates'
    ).filter(
        status__in=[
            FDAActivityStatus.ONGOING, 
            FDAActivityStatus.WAITING_EXTERNAL, 
            FDAActivityStatus.WAITING_INTERNAL,
            FDAActivityStatus.ON_HOLD
        ]
    )

    if handler_role != 'ALL':
        activities = activities.filter(
            Q(handler_override__role=handler_role) | 
            Q(handler_override__isnull=True, stage__assigned_role=handler_role)
        )

    if status_filter != 'ALL':
        activities = activities.filter(status=status_filter)

    # Attach computed Work Clearance dynamically to each item
    task_items = []
    for act in activities:
        # Find matching stage-level payment gate or fall back to project-level gate
        p_gate = act.tracker.payment_gates.filter(
            Q(scope=PaymentScope.STAGE_LEVEL, stage=act.stage) |
            Q(scope=PaymentScope.PROJECT_LEVEL)
        ).first()

        if p_gate:
            clearance = p_gate.compute_work_clearance(act.status)
            payment_required = "Yes" if p_gate.payment_required else "No"
            payment_status_display = p_gate.get_status_display()
        else:
            clearance = FDAWorkClearance.CLEARED if act.status != FDAActivityStatus.ON_HOLD else FDAWorkClearance.ON_HOLD
            payment_required = "No"
            payment_status_display = "Not Required"

        task_items.append({
            'activity': act,
            'tracker': act.tracker,
            'client': act.tracker.project.client,
            'stage': act.stage,
            'handler_role': act.handler_override.get_role_display() if act.handler_override else act.stage.get_assigned_role_display(),
            'payment_required': payment_required,
            'payment_status': payment_status_display,
            'work_clearance': clearance,
            'work_clearance_display': clearance.label,
        })

    # Header counter summary metrics
    summary_counters = {
        'ongoing': activities.filter(status=FDAActivityStatus.ONGOING).count(),
        'waiting_external': activities.filter(status=FDAActivityStatus.WAITING_EXTERNAL).count(),
        'waiting_internal': activities.filter(status=FDAActivityStatus.WAITING_INTERNAL).count(),
        'on_hold': activities.filter(status=FDAActivityStatus.ON_HOLD).count(),
    }

    context = {
        'task_items': task_items,
        'summary_counters': summary_counters,
        'user_roles': UserRole.choices,
        'selected_handler': handler_role,
        'selected_status': status_filter,
    }
    return render(request, 'fda/team_tasks.html', context)


# ==========================================
# 3. PAYMENT REGISTER (FINANCIAL GATE)
# ==========================================

@role_required([UserRole.ASSOCIATE_5, UserRole.SUPERVISOR, UserRole.SUPER_ADMIN])
def payment_register_view(request):
    """
    Renders the 'Payment Register' sheet controlling stage/project clearances.
    """
    status_filter = request.GET.get('status', 'ALL')
    
    gates = FDAPaymentGate.objects.select_related(
        'tracker', 
        'tracker__project', 
        'tracker__project__client', 
        'stage', 
        'payment_request', 
        'verified_payment'
    ).order_by('-created_at')

    if status_filter != 'ALL':
        gates = gates.filter(status=status_filter)

    context = {
        'payment_gates': gates,
        'gate_statuses': FDAPaymentGateStatus.choices,
        'selected_status': status_filter,
    }
    return render(request, 'fda/payment_register.html', context)


@require_POST
@role_required([UserRole.ASSOCIATE_5, UserRole.SUPERVISOR, UserRole.SUPER_ADMIN])
def update_payment_gate_status(request, gate_id):
    """
    Updates status, amounts, and dates for payment gates.
    """
    gate = get_object_or_404(FDAPaymentGate, id=gate_id)
    
    status = request.POST.get('status')
    amount_paid = request.POST.get('amount_paid')
    date_paid = request.POST.get('date_paid')
    remarks = request.POST.get('remarks')

    if status in dict(FDAPaymentGateStatus.choices):
        gate.status = status
    if amount_paid:
        gate.amount_paid = amount_paid
    if date_paid:
        gate.date_paid = parse_date(date_paid)
    if remarks is not None:
        gate.remarks = remarks
        
    gate.save()
    messages.success(request, f"Payment gate for {gate.tracker.project.client.business_name or gate.tracker.project.client.email} updated.")
    
    return redirect('fda:payment_register')


# ==========================================
# 4. DASHBOARD & ANALYTICS VIEW
# ==========================================

@role_required([
    UserRole.ASSOCIATE_1, UserRole.ASSOCIATE_2, UserRole.ASSOCIATE_3,
    UserRole.ASSOCIATE_4, UserRole.ASSOCIATE_5, UserRole.CONSULTANT,
    UserRole.SUPERVISOR, UserRole.SUPER_ADMIN
])
def dashboard_view(request):
    """
    Renders the executive 'Dashboard' view with aggregate counts and stage volume breakdowns.
    """
    total_projects = FDAProjectTracker.objects.count()
    
    # Portfolio breakdown by project group
    status_counts = ClientProject.objects.values('group').annotate(total=Count('id'))
    
    # Global Activity Status distribution across all cells in matrix
    activity_totals = FDAProjectStageActivity.objects.values('status').annotate(total=Count('id'))
    activity_dict = {item['status']: item['total'] for item in activity_totals}

    # Ongoing projects grouped per stage (for chart rendering)
    stage_breakdown = FDAWorkflowStage.objects.annotate(
        ongoing_count=Count(
            'fdaprojectstageactivity',
            filter=Q(fdaprojectstageactivity__status=FDAActivityStatus.ONGOING)
        )
    ).order_by('stage_number')

    # Payment totals
    payment_gates_count = FDAPaymentGate.objects.count()
    pending_payments_count = FDAPaymentGate.objects.filter(status=FDAPaymentGateStatus.PENDING).count()
    alerts_count = FDAProjectTracker.objects.filter(
        payment_gates__status__in=[FDAPaymentGateStatus.PENDING, FDAPaymentGateStatus.TO_CONFIRM]
    ).distinct().count()

    context = {
        'total_projects': total_projects,
        'status_counts': status_counts,
        'activity_dict': activity_dict,
        'stage_breakdown': stage_breakdown,
        'payment_gates_count': payment_gates_count,
        'pending_payments_count': pending_payments_count,
        'alerts_count': alerts_count,
    }
    return render(request, 'fda/dashboard.html', context)


####################################################################################
########################## ASSOCIATE 3 DASHBOARD ###################################
####################################################################################
@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_dashboard(request):
    """
    High-level operational overview desk for Associate 3 role.
    Computes system-wide performance metrics, project phase distribution,
    and pending document action queues across all clients globally.
    """

    # System-wide Client Project Footprint using ORM Annotations
    annotated_projects = ClientProject.objects.annotate(
        total_activities=Count('activities'),
        completed_activities=Count('activities', filter=Q(activities__activity_status=ActivityStatus.COMPLETED))
    )

    # Derive System-Wide Progress Metrics
    completed_projects_qs = annotated_projects.filter(
        total_activities__gt=0, 
        total_activities=F('completed_activities')
    )
    completed_vaults_count = completed_projects_qs.count()

    active_projects_qs = annotated_projects.exclude(
        total_activities__gt=0, 
        total_activities=F('completed_activities')
    )
    total_active_projects_count = active_projects_qs.count()

    active_onboarding_count = active_projects_qs.filter(completed_activities=0).count()

    # Step Phase Routing Counts
    facility_phase_count = active_projects_qs.filter(
        activities__activity_name__icontains="Facility",
        activities__activity_status__in=[
            ActivityStatus.ONGOING, 
            ActivityStatus.NOT_STARTED, 
            ActivityStatus.CLIENT_TASK
        ]
    ).distinct().count()

    label_phase_count = active_projects_qs.filter(
        activities__activity_name__icontains="Label",
        activities__activity_status__in=[
            ActivityStatus.ONGOING, 
            ActivityStatus.NOT_STARTED, 
            ActivityStatus.CLIENT_TASK
        ]
    ).distinct().count()

    # Global Pending Documents Query across all clients
    pending_documents = ClientDocument.objects.filter(
        status=DocumentStatus.PENDING
    ).distinct()

    # Assembled Context Architecture
    context = {
        "metrics": {
            "total_clients": User.objects.filter(role=UserRole.USER).distinct().count(),
            "total_active_projects": total_active_projects_count,
            "active_onboarding": active_onboarding_count,
            "urgent_attention": pending_documents.count(),
            "completed_vaults": completed_vaults_count,
            "facility_phase_count": facility_phase_count,
            "label_phase_count": label_phase_count,
        },
        "recent_pending_uploads": (
            pending_documents.select_related('client')
            .order_by("-updated_at")[:5]
        )
    }

    return render(request, "fda/associate_3.html", context)


@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_client_submissions(request):
    """
    Master queue view for PFS consultants.
    Fetches all accounts matching UserRole.USER with database-level pagination.
    """
    clients_queryset = (
        User.objects.filter(role=UserRole.USER)
        .prefetch_related('documents')
        .order_by('-id')
    )

    # Server-Side Pagination Extraction
    page = request.GET.get('page', 1)
    paginator = Paginator(clients_queryset, 10)

    try:
        paginated_clients = paginator.page(page)
    except PageNotAnInteger:
        paginated_clients = paginator.page(1)
    except EmptyPage:
        paginated_clients = paginator.page(paginator.num_pages)

    # Compile the operational dashboard data matrix
    clients_data = []
    for client in paginated_clients:
        # Dynamically fetch required types & count per individual client
        required_types = get_required_document_types(client)
        required_count = len(required_types)

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
    return render(request, "fda/associate3_client_submissions.html", context)


@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_review_client_documents(request, client_id):
    """
    Renders an exclusive review audit workspace tracking single client assets
    coupled with contextual sequential pagination indexing fields.
    """

    client = get_object_or_404(User, id=client_id, role=UserRole.USER)
    client_docs = client.documents.all()

    active_projects = client.projects.all().order_by("-id")
    
    # Map uploaded documents into a dictionary mapping document types to lists of documents
    uploaded_dict = {}
    for doc in client_docs:
        if str(doc.document_type).upper() != str(DocumentType.SUPPLEMENTARY):
            key_clean = str(doc.document_type.value if hasattr(doc.document_type, 'value') else doc.document_type).upper()
            uploaded_dict.setdefault(key_clean, []).append(doc)
    
    # Dynamically resolve mandatory document keys for this specific client
    required_keys = [dt.value for dt in get_required_document_types(client)] if hasattr(get_required_document_types(client)[0], 'value') else get_required_document_types(client)
    doc_choices_dict = dict(DocumentType.choices) if hasattr(DocumentType, 'choices') else {}

    def get_label_for_key(raw_key):
        if raw_key in doc_choices_dict:
            return doc_choices_dict[raw_key]
        return str(raw_key).replace('_', ' ').title()

    documents_data = []
    for type_key in required_keys:
        type_key_clean = str(type_key).upper()
        documents_data.append({
            'type_key': type_key_clean,
            'type_label': get_label_for_key(type_key_clean),
            'docs': uploaded_dict.get(type_key_clean, [])
        })

    # Fetch supplementary documents separately
    supplementary_documents = client_docs.filter(document_type=DocumentType.SUPPLEMENTARY).order_by('id')

    context = {
        'client': client,
        'documents_data': documents_data,
        'supplementary_documents': supplementary_documents,
        'active_projects': active_projects,
    }
    return render(request, "fda/review_client_documents.html", context)


@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_document_review_action(request, doc_id):
    """
    POST route handling immediate validation switches targeting a ClientDocument row.
    """
    if request.method == 'POST':
        document = get_object_or_404(ClientDocument, id=doc_id)
        action_type = request.POST.get('action_type')

        display_name = document.custom_title if document.document_type == DocumentType.SUPPLEMENTARY else document.get_document_type_display()

        if document.status == DocumentStatus.APPROVED:
            messages.error(request, "This action cannot be performed. This document has already been verified and locked.")
            return redirect('fda:associate-three-review-client-documents', client_id=document.client.id)

        if action_type == 'APPROVE':
            document.status = DocumentStatus.APPROVED
            document.rejection_reason = ""
            document.rejection_file = None  # Clear previous rejection files if approved now
            document.save()
            
            ActivityLog.objects.create(
                user=document.client,
                category=LogCategory.SYSTEM,
                description=f"{display_name} document has been verified and approved."
            )
            messages.success(request, f"Approved document: '{display_name}'.")

        elif action_type == 'REJECT':
            reason = request.POST.get('rejection_reason', '').strip()
            rejection_file = request.FILES.get('rejection_file') # Capture uploaded rejection file
            
            if not reason:
                messages.error(request, f"You must provide a rejection reason to flag '{display_name}' as rejected.")
                return redirect('fda:associate-three-review-client-documents', client_id=document.client.id)
                
            document.status = DocumentStatus.REJECTED
            document.rejection_reason = reason
            
            if rejection_file:
                document.rejection_file = rejection_file
                
            document.save()
            
            ActivityLog.objects.create(
                user=document.client,
                category=LogCategory.SYSTEM,
                description=f"Error flagged on '{display_name}'. Revision requested with notes/attachment."
            )
            messages.warning(request, f"{display_name} document rejected. Client has been notified with the rejection notes and attachment provided.")

        return redirect('fda:associate-three-review-client-documents', client_id=document.client.id)
        
    return redirect('fda:associate-three-dashboard')


@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_initiate_client_project(request, client_id):
    """
    Audits and validates target account mandatory asset statuses, establishes the master 
    workspace model instance, and delegates task creation safely to the database layer.
    """
    client_user = get_object_or_404(User, id=client_id, role=UserRole.USER)

    # Confirm mandatory onboarding compliance assets are approved
    required_types = get_required_document_types(client_user)
    approved_core_count = client_user.documents.filter(
        document_type__in=required_types,
        status=DocumentStatus.APPROVED
    ).count()
    
    if approved_core_count < len(required_types):
        messages.error(
            request, 
            f"Cannot initialize project. This client has only {approved_core_count}/{len(required_types)} approved mandatory documents."
        )
        return redirect("fda:associate-three-review-client-documents", client_id=client_user.id)
    
    # Prevent duplicate active projects on a single user profile
    if hasattr(client_user, 'project_file'):
        messages.warning(request, "An active project already exists for this client.")
        return redirect("fda:associate-three-project-board", project_id=client_user.project_file.id)

    # FORM OPERATIONS HANDLER
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

            messages.success(request, f"Project board activated successfully for {client_user.business_name or client_user.email}!")
            return redirect("fda:associate-three-project-board", project_id=project.id)

        except Exception as e:
            messages.error(request, f"Project initiation failure: {str(e)}")
            return redirect("fda:associate-three-initiate-client-project", client_id=client_user.id)

    # DATA PRESENTATION PROCESSING
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
    return render(request, "fda/associate3_initiate_client_project.html", context)


@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_project_board(request, project_id):
    """
    Renders the dedicated consultant workflow control engine for a single client project file.
    """
    project = get_object_or_404(
        ClientProject.objects.select_related('client', 'assigned_consultant').prefetch_related('activities'),
        id=project_id
    )

    if request.method == "POST":
        action = request.POST.get('action')

        # Add new subitem
        if action == "add_subitem":
            name = request.POST.get('activity_name')
            if name:
                ProjectActivity.objects.create(
                    project=project,
                    activity_name=name
                )
        
        # Add a note
        elif action == "add_note":
            activity_id = request.POST.get('activity_id')
            text = request.POST.get('note_text')
            if activity_id and text:
                activity = ProjectActivity.objects.get(id=activity_id, project=project)
                ActivityNote.objects.create(activity=activity, note_text=text)

        # Update Payment Status
        elif action == "update_payment":
            activity_id = request.POST.get('activity_id')
            val = request.POST.get('status_value')
            if activity_id and val:
                act = ProjectActivity.objects.get(id=activity_id, project=project)
                act.payment_status = val
                act.save()

        # Update Activity Status
        elif action == "update_activity_status":
            activity_id = request.POST.get('activity_id')
            val = request.POST.get('status_value')
            if activity_id and val:
                act = ProjectActivity.objects.get(id=activity_id, project=project)
                act.activity_status = val
                act.save()

        return redirect('fda:associate-three-project-board', project_id=project.id)
    
    context = {
        'project': project,
        'payment_choices': PaymentStatus.choices,
        'activity_choices': ActivityStatus.choices,
    }
    
    return render(request, 'fda/associate3_project_board.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_3, UserRole.SUPERVISOR])
def associate_three_global_projects_board(request):
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
    return render(request, "fda/associate3_global_project_board.html", context)