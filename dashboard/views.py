import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.models import UserRole
from common.decorators import role_required, mandatory_docs_required
from .forms import BaseUserProfileForm, ClientProfileForm, AmbassadorVerificationForm, ConsultantVerificationForm, AdminUserManagementForm
from django.contrib import messages
from .models import ClientDocument, ClientRegion, DocumentType, DocumentStatus, ActivityLog, LogCategory, ProductCategory, ClientProject, ClientPackage as PackageChoices, ActivityStatus, PaymentStatus, ProjectActivity, ProjectGroup, ActivityNote, AmbassadorProfile, AmbassadorAssignment, ConsultantProfile
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max, F
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
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
def superadmin_dashboard(request):
    """Provides a bird's-eye view of platform metrics and urgent administrative actions."""
    metrics = {
        'total_ambassadors': AmbassadorProfile.objects.count(),
        'pending_verifications': AmbassadorProfile.objects.filter(is_active_field_agent=False).count(),
        'active_assignments': AmbassadorAssignment.objects.filter(status='ASSIGNED').count(),
        'unclaimed_projects': ClientProject.objects.exclude(
            id__in=AmbassadorAssignment.objects.filter(status='ASSIGNED').values_list('project_id', flat=True)
        ).count(),
    }
    
    # Grab the 5 oldest unverified applications for a quick-action widget
    recent_signups = AmbassadorProfile.objects.filter(is_active_field_agent=False).select_related('user').order_by('id')[:5]

    context = {
        'metrics': metrics,
        'recent_signups': recent_signups,
    }

    return render(request, 'dashboards/super_admin.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def superadmin_ambassadors(request):
    """Renders comprehensive directory table managing all platform ambassador profiles."""
    ambassadors_users = User.objects.filter(role=UserRole.AMBASSADOR).select_related(
        'ambassador_profile'
    ).annotate(
        assignment_count=Count('ambassador_profile__assignments')
    ).order_by('-id')

    context = {
        'ambassadors': ambassadors_users
    }

    return render(request, 'dashboards/superadmin_ambassadors.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def superadmin_consultants(request):
    """Renders comprehensive directory table managing all platform consultant profiles."""
    consultants = User.objects.filter(role=UserRole.CONSULTANT).select_related(
        'ambassador_profile'
    ).annotate(
        assignment_count=Count('ambassador_profile__assignments')
    ).order_by('-id')

    context = {
        'consultants': consultants
    }

    return render(request, 'dashboards/superadmin_consultants.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def superadmin_process_verification(request, profile_id, action):
    """Processes verification assets against explicit design parameters."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=profile_id)
        profile = get_object_or_404(AmbassadorProfile, user=target_user)
        
        # Enforce that documents exist before letting action execute
        if not profile.id_card or not profile.verification_selfie:
            messages.error(request, f"Cannot process verification: Ambassador {target_user.email} hasn't uploaded all files.")
            return redirect('dashboard:superadmin-ambassadors')
            
        if action == 'verify':
            profile.verification_status = AmbassadorProfile.VerificationStatus.APPROVED
            profile.is_active_field_agent = True
            profile.save()
            messages.success(request, f"Successfully verified account and authorized Associate {target_user.email}.")
            
        elif action == 'decline':
            profile.verification_status = AmbassadorProfile.VerificationStatus.DECLINED
            profile.is_active_field_agent = False
            profile.save()
            messages.warning(request, f"Declined verification credentials for {target_user.email}.")
            
    return redirect('dashboard:superadmin-ambassadors')



@login_required
@role_required([UserRole.SUPER_ADMIN])
def superadmin_consultant_verification(request, profile_id, action):
    """Processes verification assets against explicit design parameters."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=profile_id)
        profile = get_object_or_404(ConsultantProfile, user=target_user)
        
        # Enforce that documents exist before letting action execute
        if not profile.id_card or not profile.verification_selfie:
            messages.error(request, f"Cannot process verification: Consultant {target_user.email} hasn't uploaded all files.")
            return redirect('dashboard:superadmin-consultants')
            
        if action == 'verify':
            profile.verification_status = ConsultantProfile.VerificationStatus.APPROVED
            profile.is_active_field_agent = True
            profile.save()
            messages.success(request, f"Successfully verified account and authorized Consultant {target_user.email}.")
            
        elif action == 'decline':
            profile.verification_status = ConsultantProfile.VerificationStatus.DECLINED
            profile.is_active_field_agent = False
            profile.save()
            messages.warning(request, f"Declined verification credentials for {target_user.email}.")
            
    return redirect('dashboard:superadmin-consultants')



@login_required
@role_required([UserRole.SUPER_ADMIN])
def admin_user_list(request):
    """Lists all users with search by name/email/phone and filter by role."""
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()

    users = User.objects.all().order_by('-id')

    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(whatsapp_number__icontains=query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    context = {
        'users': users,
        'query': query,
        'role_filter': role_filter,
    }
    return render(request, 'dashboards/superadmin_user_list.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def admin_user_detail(request, pk):
    """Shows full account profile including attached Consultant/Ambassador profiles."""
    target_user = get_object_or_404(User, pk=pk)
    
    context = {
        'target_user': target_user,
        'ambassador_profile': getattr(target_user, 'ambassadorprofile', None),
        'consultant_profile': getattr(target_user, 'consultantprofile', None),
    }
    return render(request, 'dashboards/superadmin_user_detail.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def admin_user_update(request, pk):
    """
    Dynamically loads and saves both the User model form 
    and the matching Role Profile form (Ambassador or Consultant).
    """
    target_user = get_object_or_404(User, pk=pk)
    
    user_form = AdminUserManagementForm(
        request.POST or None, 
        request.FILES or None, 
        instance=target_user
    )
    
    consultant_form = None
    ambassador_form = None
    profile_form = None

    # Load matching verification form based on user role
    if target_user.role == UserRole.AMBASSADOR:
        profile_instance, _ = AmbassadorProfile.objects.get_or_create(user=target_user)
        ambassador_form = AmbassadorVerificationForm(
            request.POST or None, 
            request.FILES or None, 
            instance=profile_instance
        )
        profile_form = ambassador_form

    elif target_user.role == UserRole.CONSULTANT:
        profile_instance, _ = ConsultantProfile.objects.get_or_create(user=target_user)
        consultant_form = ConsultantVerificationForm(
            request.POST or None, 
            request.FILES or None, 
            instance=profile_instance
        )
        profile_form = consultant_form

    if request.method == 'POST':
        user_valid = user_form.is_valid()
        profile_valid = profile_form.is_valid() if profile_form else True

        if user_valid and profile_valid:
            with transaction.atomic():
                saved_user = user_form.save()
                
                # Check if the admin changed the role during update and create missing profile
                if saved_user.role == UserRole.AMBASSADOR:
                    AmbassadorProfile.objects.get_or_create(user=saved_user)
                elif saved_user.role == UserRole.CONSULTANT:
                    ConsultantProfile.objects.get_or_create(user=saved_user)

                if profile_form:
                    profile_form.save()

            messages.success(request, f"Account details for {target_user.email} updated successfully.")
            return redirect('dashboard:admin-user-detail', pk=target_user.pk)

    context = {
        'target_user': target_user,
        'user_form': user_form,
        'consultant_form': consultant_form,
        'ambassador_form': ambassador_form,
    }
    return render(request, 'dashboards/superadmin_user_edit.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
@require_POST
def admin_user_toggle_active(request, pk):
    """Safely toggles active status to enable/disable user accounts without deleting records."""
    target_user = get_object_or_404(User, pk=pk)
    
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own administrative account.")
        return redirect('dashboard:admin-user-list')

    target_user.is_active = not target_user.is_active
    target_user.save()

    action = "activated" if target_user.is_active else "deactivated"
    messages.info(request, f"Account for {target_user.email} has been {action}.")
    return redirect('dashboard:admin-user-list')


@login_required
@role_required([UserRole.SUPER_ADMIN])
def admin_user_delete(request, pk):
    """Permanently deletes a user account and cascading profile media."""
    target_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        if target_user == request.user:
            messages.error(request, "You cannot delete your own administrative account.")
            return redirect('dashboard:admin-user-list')

        email = target_user.email
        target_user.delete()
        messages.success(request, f"User '{email}' permanently removed from system.")
        return redirect('dashboard:admin-user-list')

    return render(request, 'dashboards/superadmin_user_confirm_delete.html', {'target_user': target_user})



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
                description=f"Document '{display_name}' was verified and approved."
            )
            messages.success(request, f"Approved document: '{display_name}'.")

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
                description=f"Error flagged on '{display_name}'. Revision requested."
            )
            messages.warning(request, f"Uploaded document for '{display_name}' needs to be revised.")

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
@role_required([UserRole.CONSULTANT])
def initiate_client_project(request, client_id):
    """
    Audits and validates target account mandatory asset statuses, establishes the master 
    workspace model instance, and delegates task creation safely to the database layer.
    """
    client_user = get_object_or_404(User, id=client_id, role='USER')
    
    # Confirm mandatory onboarding compliance assets are approved
    required_types = [DocumentType.BUSINESS_CERT, DocumentType.HEALTH_CARD, DocumentType.FACILITY_SKETCH]
    approved_core_count = client_user.documents.filter(
        document_type__in=required_types,
        status=DocumentStatus.APPROVED
    ).count()
    
    if approved_core_count < len(required_types):
        messages.error(
            request, 
            f"Cannot initialize project board. This client has only completed {approved_core_count}/{len(required_types)} mandatory document approvals."
        )
        return redirect("dashboard:review-client", client_id=client_user.id)
    
    # Prevent duplicate active projects on a single user profile
    if hasattr(client_user, 'project_file'):
        messages.warning(request, "An active project workflow already exists for this client.")
        return redirect("dashboard:project-board", project_id=client_user.project_file.id)

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

            messages.success(request, f"Project workflow board activated successfully for {client_user.business_name or client_user.email}!")
            return redirect("dashboard:project-board", project_id=project.id)

        except Exception as e:
            messages.error(request, f"Project initiation failure: {str(e)}")
            return redirect("dashboard:initiate-client-project", client_id=client_user.id)

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
    return render(request, "dashboards/initiate_project.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
def project_service_board(request, project_id):
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

        return redirect('dashboard:project-board', project_id=project.id)
    
    context = {
        'project': project,
        'payment_choices': PaymentStatus.choices,
        'activity_choices': ActivityStatus.choices,
    }
    
    return render(request, 'dashboards/project_board.html', context)


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


@login_required
@role_required([UserRole.CONSULTANT])
def consultant_profile(request):
    """Displays and processes updates to contact info and verification uploads for Consultants."""
    profile, _ = ConsultantProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = BaseUserProfileForm(request.POST, instance=request.user)
        profile_form = ConsultantVerificationForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()

                profile_obj = profile_form.save(commit=False)
                
                # Reset verification status back to PENDING if CV, ID, or selfie is replaced
                if any(k in request.FILES for k in ['cv', 'id_card', 'verification_selfie']):
                    profile_obj.verification_status = ConsultantProfile.VerificationStatus.PENDING
                    profile_obj.is_active_field_agent = False

                profile_obj.save()

            create_activity_log(
                user=request.user,
                category=LogCategory.PROFILE,
                description="Updated consultant profile and verification documents."
            )
            messages.success(request, "Your profile details and credentials have been updated successfully.")
            return redirect('dashboard:consultant-profile')
    else:
        user_form = BaseUserProfileForm(instance=request.user)
        profile_form = ConsultantVerificationForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'dashboards/consultant_profile.html', context)


# @login_required
# @role_required([UserRole.CONSULTANT])
# def consultant_submit_verification(request):
#     """Allows Consultants to upload required assets for verification."""
#     profile, created = ConsultantProfile.objects.get_or_create(user=request.user)
    
#     if request.method == 'POST':
#         user_form = ConsultantBaseUserForm(request.POST, instance=request.user)
#         profile_form = ConsultantVerificationForm(request.POST, request.FILES, instance=profile)
        
#         if user_form.is_valid() and profile_form.is_valid():
#             user_form.save()
#             # Reset validation status back to pending upon resubmission
#             profile_obj = profile_form.save(commit=False)
#             profile_obj.verification_status = ConsultantProfile.VerificationStatus.PENDING
#             profile_obj.save()
            
#             messages.success(request, "Verification documentation uploaded successfully for evaluation.")
#             return redirect('accounts:consultant-dashboard')
#     else:
#         user_form = ConsultantBaseUserForm(instance=request.user)
#         profile_form = ConsultantVerificationForm(instance=profile)

#     context = {
#         'user_form': user_form,
#         'profile_form': profile_form,
#         'profile': profile
#     }
        
#     return render(request, 'dashboards/consultant_profile.html', context)



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


# # ADD PROJECT SUB-ITEMS
# @login_required
# def add_custom_project_subitem(request, project_id):
#     """
#     POST-only action endpoint allowing account consultants to instantly append 
#     ad-hoc project subitems to an active operational roadmap.
#     """
#     if request.method == "POST":
#         project = get_object_or_404(ClientProject, id=project_id)
#         activity_name = request.POST.get("activity_name", "").strip()
#         activity_deadline = request.POST.get("activity_deadline")
        
#         if not activity_name:
#             messages.error(request, "Operational subitem addition aborted. A valid task execution title must be provided.")
#             return redirect("dashboard:project-board", project_id=project.id)
            
#         ProjectActivity.objects.create(
#             project=project,
#             activity_name=activity_name,
#             activity_deadline=activity_deadline if activity_deadline else None,
#             payment_status=PaymentStatus.NOT_PAID,
#             activity_status=ActivityStatus.NOT_STARTED
#         )
        
#         messages.success(request, f"Successfully appended custom task subitem: '{activity_name}'.")
#         return redirect("dashboard:project-board", project_id=project.id)
        
#     return redirect("dashboard:global-boards")



#********************************************************** AMBASSADOR DASHBOARD **************************************************#
#******************************************************************************************************************************#
# AMBASSADOR Dashboard Overview
@login_required
@role_required([UserRole.AMBASSADOR])
def ambassador_dashboard(request):
    """
    Renders the operational hub for platform Ambassadors.
    Swaps presentation layers dynamically based on backend verification flags.
    """
    # 1. Safely evaluate profile instantiation states
    try:
        profile = request.user.ambassador_profile
        is_verified = profile.is_active_field_agent
    except AmbassadorProfile.DoesNotExist:
        profile = None
        is_verified = False

    # 2. Define standard fallback metrics variables
    active_assignments = []
    available_clients = []
    completed_payouts_total = "0.00"

    # 3. If verified, populate the operational datasets
    if is_verified:
        # Fetch client tracks currently managed by this ambassador agent
        active_assignments = AmbassadorAssignment.objects.filter(
            ambassador=profile, 
            status='ASSIGNED'
        ).select_related('client')

        # Calculate settled payouts ledger summary metrics
        payout_count = AmbassadorAssignment.objects.filter(
            ambassador=profile,
            status='COMPLETED',
            payout_processed=True
        ).count()
        completed_payouts_total = f"{payout_count * 150.00:.2f}"

        # Define documents that constitute a "Complete Profile Submission"
        required_types = [
            DocumentType.BUSINESS_CERT, 
            DocumentType.HEALTH_CARD, 
            DocumentType.FACILITY_SKETCH
        ]
        
        # 1. Gather all client IDs that are currently claimed by an active ambassador
        claimed_client_ids = AmbassadorAssignment.objects.filter(
            status='ASSIGNED'
        ).values_list('client_id', flat=True)

        # 2. Grab all users who are regular clients and NOT currently claimed
        open_clients = User.objects.filter(
            role=UserRole.USER
        ).exclude(
            id__in=claimed_client_ids
        ).order_by('-id')

        available_clients = []
        required_types = [DocumentType.BUSINESS_CERT, DocumentType.HEALTH_CARD, DocumentType.FACILITY_SKETCH]

        # 3. Process each client explicitly
        for client in open_clients:
            # Querying the ClientDocument directly using the client object avoids the relationship property naming issue completely
            client_docs = ClientDocument.objects.filter(client=client)
            uploaded_types = list(client_docs.values_list('document_type', flat=True))
            
            total_uploaded = sum(1 for t in uploaded_types if t in required_types)
            total_required = len(required_types)

            # If their uploads are incomplete, push them straight into the Ambassador pool
            if total_uploaded < total_required:
                # Safely capture their project record
                project = ClientProject.objects.filter(client=client).first()

                available_clients.append({
                    'client': client,
                    'project': project,
                    'total_uploaded': total_uploaded,
                    'total_required': total_required,
                    'has_business_cert': DocumentType.BUSINESS_CERT in uploaded_types,
                    'has_health_card': DocumentType.HEALTH_CARD in uploaded_types,
                    'has_facility_sketch': DocumentType.FACILITY_SKETCH in uploaded_types,
                })

    context = {
        'profile': profile,
        'is_verified': is_verified,
        'active_assignments': active_assignments,
        'available_clients': available_clients,
        'completed_payouts_total': completed_payouts_total,
    }
    return render(request, 'dashboards/ambassador.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
@login_required
def ambassador_claim_client(request):
    """Processes the claim request, creating an operational assignment block."""
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        modality = request.POST.get('modality', 'REMOTE')
        
        # 1. Grab or fail the target client user account
        target_client = get_object_or_404(User, id=client_id, role=UserRole.USER)
        
        # 2. Safety check: Ensure the ambassador has a verified active profile state
        profile = get_object_or_404(AmbassadorProfile, user=request.user)
        if not profile.is_active_field_agent:
            messages.error(request, "Access Denied. Your ambassador credentials are unverified.")
            return redirect('dashboard:ambassador-dashboard')
            
        # 3. Double-claim preventative safety lock check
        already_claimed = AmbassadorAssignment.objects.filter(client=target_client, status='ASSIGNED').exists()
        if already_claimed:
            messages.warning(request, "This client project has already been claimed by another Ambassador.")
            return redirect('dashboard:ambassador-dashboard')
            
        # 4. Initialize assignment pipeline structure records
        project = ClientProject.objects.filter(client=target_client).first()
        
        AmbassadorAssignment.objects.create(
            ambassador=profile,
            client=target_client,
            project=project,
            modality=modality,
            status='ASSIGNED'
        )
        
        messages.success(request, f"Successfully paired with {target_client.email}.")
        return redirect('dashboard:ambassador-client-workbench', client_id=target_client.id)
        
    return redirect('dashboard:ambassador-dashboard')



@login_required
@role_required([UserRole.AMBASSADOR])
@login_required
def ambassador_client_workbench(request, client_id):
    """Operational management workspace layout for a specific active assignment tracking node."""
    client_user = get_object_or_404(User, id=client_id)
    profile = get_object_or_404(AmbassadorProfile, user=request.user)
    
    # Secure validation check: Verify this assignment belongs to the active agent session
    assignment = get_object_or_404(
        AmbassadorAssignment, 
        ambassador=profile, 
        client=client_user, 
        status='ASSIGNED'
    )
    
    # Handle document uploads on behalf of the client
    if request.method == 'POST':
        doc_type = request.POST.get('document_type')
        uploaded_file = request.FILES.get('document_file')
        
        if doc_type and uploaded_file:
            ClientDocument.objects.create(
                client=client_user,
                uploaded_by=request.user,
                document_type=doc_type,
                file=uploaded_file
            )
            messages.success(request, f"Proxy document ({doc_type}) successfully uploaded.")
            return redirect('dashboard:ambassador-client-workbench', client_id=client_user.id)

    # Document state compilation for the workbench checklist UI
    client_docs = ClientDocument.objects.filter(client=client_user)
    uploaded_types = list(client_docs.values_list('document_type', flat=True))
    required_types = [DocumentType.BUSINESS_CERT, DocumentType.HEALTH_CARD, DocumentType.FACILITY_SKETCH]
    
    context = {
        'assignment': assignment,
        'client_user': client_user,
        'client_docs': client_docs,
        'required_types': required_types,
        'has_business_cert': DocumentType.BUSINESS_CERT in uploaded_types,
        'has_health_card': DocumentType.HEALTH_CARD in uploaded_types,
        'has_facility_sketch': DocumentType.FACILITY_SKETCH in uploaded_types,
    }
    return render(request, 'dashboards/ambassador_client_workbench.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
def ambassador_toggle_complete(request, assignment_id):
    """Toggles Ambassador sign-off status and checks if the payout can be executed."""
    assignment = get_object_or_404(AmbassadorAssignment, id=assignment_id, ambassador=request.user.ambassador_profile)
    
    assignment.ambassador_marked_complete = not assignment.ambassador_marked_complete
    assignment.ambassador_completed_at = timezone.now() if assignment.ambassador_marked_complete else None
    assignment.save()

    # Trigger dual-signoff gate evaluation engine execution rules
    assignment.check_and_finalize_payout()
    
    messages.success(request, "Verification status successfully updated.")
    return redirect('dashboard:ambassador-dashboard')


@login_required
@role_required([UserRole.AMBASSADOR])
def ambassador_clients(request):
    """
    Renders a dedicated directory of clients actively paired with the logged-in Ambassador.
    """
    # Safely evaluate active agent validation
    try:
        profile = request.user.ambassador_profile
        is_verified = profile.is_active_field_agent
    except AmbassadorProfile.DoesNotExist:
        profile = None
        is_verified = False

    clients = []

    # Only fetch active paired clients if the agent profile is verified active
    if is_verified:
        assignments = AmbassadorAssignment.objects.filter(
            ambassador=profile,
            status='ASSIGNED'
        ).select_related('client')
        
        # Extract the client User objects from the assignments
        clients = [assignment.client for assignment in assignments]

    context = {
        'profile': profile,
        'is_verified': is_verified,
        'clients': clients,
    }
    return render(request, 'dashboards/ambassador_clients.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
def ambassador_profile(request):
    """Displays and processes updates to contact info and verification uploads for Ambassadors."""
    profile, _ = AmbassadorProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = BaseUserProfileForm(request.POST, instance=request.user)
        profile_form = AmbassadorVerificationForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()

                profile_obj = profile_form.save(commit=False)
                
                # Reset verification status back to PENDING if any verification document is replaced
                if any(k in request.FILES for k in ['id_card', 'verification_selfie']):
                    profile_obj.verification_status = AmbassadorProfile.VerificationStatus.PENDING
                    profile_obj.is_active_field_agent = False

                profile_obj.save()

            create_activity_log(
                user=request.user,
                category=LogCategory.PROFILE,
                description="Updated ambassador profile and verification documents."
            )
            messages.success(request, "Your profile details and credentials have been updated successfully.")
            return redirect('dashboard:ambassador-profile')
    else:
        user_form = BaseUserProfileForm(instance=request.user)
        profile_form = AmbassadorVerificationForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'dashboards/ambassador_profile.html', context)




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

    # --- PROCESS INCOMING FILE UPLOADS ---
    if request.method == 'POST':
        files_saved = 0
        
        for doc_key in required_types:
            if doc_key in request.FILES:
                uploaded_file = request.FILES[doc_key]
                
                Document, created = ClientDocument.objects.update_or_create(
                    client=request.user,
                    document_type=doc_key,
                    defaults={
                        'file': uploaded_file,
                        'status': DocumentStatus.PENDING
                    }
                )
                files_saved += 1

        if files_saved > 0:
            messages.success(request, f"Successfully uploaded and saved {files_saved} file(s).")
        else:
            messages.error(request, "No files selected. Please choose a valid file to upload.")
            
        return redirect('dashboard:user-dashboard')

    # --- EVALUATE & RENDER CURRENT VIEW STATE ---
    client_docs = request.user.documents.all()
    
    # Generate an easy context map lookup
    uploaded_dict = {doc.document_type: doc for doc in client_docs}
    
    total_required = len(required_types)
    total_uploaded = client_docs.filter(document_type__in=required_types).count()
    
    # Safely query active tracking projects for summary presentation dashboards
    active_projects = request.user.projects.all()

    context = {
        'uploaded_dict': uploaded_dict,
        'total_uploaded': total_uploaded,
        'total_required': total_required,
        'active_projects': active_projects,
    }

    # If the user has fulfilled all baseline uploads, dynamically swap out the UI view template
    if total_uploaded >= total_required:
        recent_activities = request.user.activities.all()[:5]

        context = {
            "uploaded_dict": uploaded_dict,
            "recent_activities": recent_activities,
            "active_projects": active_projects,
        }

        return render(request, "dashboards/user_tracking.html", context)
        
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
            messages.success(request, f"Successfully uploaded and catalogued {saved_count} mandatory file(s) inside your portal.")
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
            messages.error(request, "Creating Supplmentary Document slot failed. You must provide a descriptive name.")
            return redirect('dashboard:user-documents')
        
        # Defensive Check: Does this client already have this exact custom slot?
        existing_slot = ClientDocument.objects.filter(
            client=request.user,
            document_type='SUPPLEMENTARY',
            custom_title__iexact=title
        ).exists()

        if existing_slot:
            messages.warning(request, f"A supplementary slot named '{title}' already exists in your portal.")
            return redirect('dashboard:user-documents')
        
        # If it passes the check, create it safely
        ClientDocument.objects.create(
            client=request.user,
            document_type='SUPPLEMENTARY',
            custom_title=title,
            status=DocumentStatus.PENDING
        )
        messages.success(request, f"New supplementary slot created for '{title}'.")

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
            messages.error(request, "This document is currently verified and locked.")
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
            description=f"Uploaded a document for: '{display_name}'."
        )
        
        messages.success(request, f"Document successfully uploaded for '{display_name}'.")
        
    return redirect('dashboard:user-documents')


@login_required
@role_required([UserRole.USER])
def client_project_dashboard(request, project_id):
    """
    Renders the read-only tracking and milestone overview matrix for the logged-in client.
    """
    # Enforce clear account level constraints by matching client=request.user
    project = get_object_or_404(
        ClientProject.objects.select_related('assigned_consultant')
        .prefetch_related('activities__notes_stream'),
        id=project_id,
        client=request.user
    )
    
    return render(request, 'dashboards/user_project_view.html', {
        'project': project
    })


# CLIENT Profile
@login_required
@role_required([UserRole.USER])
def user_profile(request):
    """Handles personal details update for regular client users."""
    if not getattr(request.user, 'is_regular_user', True):
        return redirect('dashboard:redirect-dashboard')

    if request.method == 'POST':
        form = ClientProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()

            create_activity_log(
                user=request.user, 
                category=LogCategory.PROFILE, 
                description="Updated profile details."
            )
            messages.success(request, "Your profile details have been saved successfully!")
            return redirect('dashboard:user-profile')
    else:
        form = ClientProfileForm(instance=request.user)

    context = {
        "form": form,
    }
    return render(request, "dashboards/user_profile.html", context)


@login_required
def client_confirm_verification(request):
    """Allows the client to sign off on the documents compiled for their file."""
    if request.method == 'POST':
        # Locate the active assignment for this specific logged-in client
        assignment = get_object_or_404(
            AmbassadorAssignment, 
            client=request.user, 
            status='ASSIGNED'
        )
        
        # Operational Check: Ensure all required documents actually exist before letting them confirm
        client_docs = ClientDocument.objects.filter(client=request.user)
        uploaded_types = list(client_docs.values_list('document_type', flat=True))
        required_types = [DocumentType.BUSINESS_CERT, DocumentType.HEALTH_CARD, DocumentType.FACILITY_SKETCH]
        
        all_uploaded = all(t in uploaded_types for t in required_types)
        
        if not all_uploaded:
            messages.error(request, "Cannot verify portfolio. Mandatory documents are still missing from your profile.")
            return redirect('dashboard:user-dashboard')
            
        # Flip the client confirmation switch
        assignment.client_marked_complete = True
        assignment.save()
        
        # Operational Trigger: If BOTH have signed off, shift the status to complete or notify systems
        if assignment.ambassador_marked_complete:
            # Optional: You can change the status here or leave it as ASSIGNED while both are True,
            # depending on how your consultant query reads 'readiness'.
            messages.success(request, "Dual Verification Achieved! Your profile has been forwarded to consultants to initiate project.")
        else:
            messages.success(request, "Your verification has been recorded. Awaiting final ambassador confirmation.")
            
        return redirect('dashboard:user-dashboard')

    return redirect('dashboard:user-dashboard')