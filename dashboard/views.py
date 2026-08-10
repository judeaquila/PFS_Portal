import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.models import UserRole
from common.decorators import role_required, mandatory_docs_required
from common.utils import get_required_document_types
from .forms import BaseUserProfileForm, ClientProfileForm, AmbassadorVerificationForm, ConsultantVerificationForm, AdminUserManagementForm, BusinessProfileForm, AvailabilityForm
from django.contrib import messages
from .models import ClientDocument, ClientRegion, DocumentType, DocumentStatus, ActivityLog, LogCategory, ProductCategory, ClientProject, ClientPackage as PackageChoices, ActivityStatus, PaymentStatus, ProjectActivity, ProjectGroup, ActivityNote, AmbassadorProfile, AmbassadorAssignment, ConsultantProfile, Availability, ConsultantAssignment
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max, F
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from .signals import get_activities_for_package
from collections import defaultdict



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
# @login_required
# @role_required([UserRole.SUPER_ADMIN])
# def superadmin_dashboard(request):
#     """Admin dashboard with combined unassigned/cancelled request queues & inline assignments."""

#     # ==========================================
#     # POST ACTIONS (INLINE ASSIGNMENTS)
#     # ==========================================
#     if request.method == "POST":
#         action = request.POST.get("action")

#         # --- ASSIGN / RE-ASSIGN FIELD ASSOCIATE ---
#         if action == "assign_associate_request":
#             assignment_id = request.POST.get("assignment_id")
#             associate_id = request.POST.get("associate_id")

#             if not associate_id:
#                 messages.error(request, "Please select an associate from the list before assigning.")
#                 return redirect("dashboard:super-admin-dashboard")

#             assignment = get_object_or_404(AmbassadorAssignment, pk=assignment_id)
#             ambassador_profile = get_object_or_404(AmbassadorProfile, user_id=associate_id)

#             assignment.ambassador = ambassador_profile
#             assignment.status = AmbassadorAssignment.TaskStatus.ASSIGNED
#             assignment.cancellation_reason = None  # Clear reason on reassignment
#             assignment.save(update_fields=['ambassador', 'status', 'cancellation_reason'])

#             client_name = assignment.client.business_name or assignment.client.get_full_name() or assignment.client.email
#             messages.success(
#                 request, 
#                 f"Successfully assigned Associate {ambassador_profile.user.get_full_name()} to {client_name}."
#             )
#             return redirect("dashboard:super-admin-dashboard")

#         # --- ASSIGN / RE-ASSIGN CONSULTANT ---
#         elif action == "assign_consultant_request":
#             assignment_id = request.POST.get("assignment_id")
#             consultant_id = request.POST.get("consultant_id")

#             if not consultant_id:
#                 messages.error(request, "Please select a consultant from the list before assigning.")
#                 return redirect("dashboard:super-admin-dashboard")

#             assignment = get_object_or_404(ConsultantAssignment, pk=assignment_id)
#             consultant_profile = get_object_or_404(ConsultantProfile, user_id=consultant_id)

#             assignment.consultant = consultant_profile
#             assignment.status = ConsultantAssignment.TaskStatus.ASSIGNED
#             assignment.cancellation_reason = None
#             assignment.save(update_fields=['consultant', 'status', 'cancellation_reason'])

#             client_name = assignment.client.business_name or assignment.client.get_full_name() or assignment.client.email
#             messages.success(
#                 request, 
#                 f"Successfully assigned Consultant {consultant_profile.user.get_full_name()} to {client_name}."
#             )
#             return redirect("dashboard:super-admin-dashboard")

#     # ==========================================
#     # COMBINED UNASSIGNED + CANCELLED QUEUES
#     # ==========================================
#     pending_associate_requests = AmbassadorAssignment.objects.filter(
#         status__in=[
#             AmbassadorAssignment.TaskStatus.UNASSIGNED,
#             AmbassadorAssignment.TaskStatus.CANCELLED
#         ]
#     ).select_related('client', 'project', 'ambassador__user').order_by('-updated_at')

#     pending_consultant_requests = ConsultantAssignment.objects.filter(
#         status__in=[
#             ConsultantAssignment.TaskStatus.UNASSIGNED,
#             ConsultantAssignment.TaskStatus.CANCELLED
#         ]
#     ).select_related('client', 'project', 'consultant__user').order_by('-updated_at')

#     # ==========================================
#     # AVAILABLE AGENTS WITH ACTIVE TASK COUNTS
#     # ==========================================
#     available_associates = User.objects.filter(
#         role=UserRole.AMBASSADOR,
#         ambassador_profile__is_active_field_agent=True
#     ).annotate(
#         active_task_count=Count(
#             'ambassador_profile__assignments',
#             filter=Q(ambassador_profile__assignments__status=AmbassadorAssignment.TaskStatus.ASSIGNED)
#         )
#     ).order_by('first_name')

#     available_consultants = User.objects.filter(
#         role=UserRole.CONSULTANT,
#         consultant_profile__is_active_consultant=True
#     ).annotate(
#         active_task_count=Count(
#             'consultant_profile__consultant_assignments',
#             filter=Q(consultant_profile__consultant_assignments__status=ConsultantAssignment.TaskStatus.ASSIGNED)
#         )
#     ).order_by('first_name')

#     # ==========================================
#     # ACTIVE ASSIGNMENTS
#     # ==========================================
#     active_associate_assignments = AmbassadorAssignment.objects.filter(
#         ambassador__isnull=False,
#         status=AmbassadorAssignment.TaskStatus.ASSIGNED
#     ).select_related('ambassador__user', 'client', 'project').order_by('-created_at')

#     active_consultant_assignments = ConsultantAssignment.objects.filter(
#         consultant__isnull=False,
#         status=ConsultantAssignment.TaskStatus.ASSIGNED
#     ).select_related('consultant__user', 'client', 'project').order_by('-created_at')

#     # ==========================================
#     # PROJECTS, LOGS & KPI METRICS
#     # ==========================================
#     recent_projects = ClientProject.objects.select_related(
#         'client', 'assigned_consultant'
#     ).prefetch_related('activities').order_by('-updated_at')[:8]

#     recent_activity_logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:6]
#     today = timezone.now().date()

#     metrics = {
#         'active_clients': User.objects.filter(role=UserRole.USER, is_active=True).count(),
#         'active_projects': ClientProject.objects.count(),
#         'total_ambassadors': AmbassadorProfile.objects.filter(is_active_field_agent=True).count(),
#         'total_consultants': ConsultantProfile.objects.filter(is_active_consultant=True).count(),
#         'pending_verifications': (
#             AmbassadorProfile.objects.filter(verification_status=AmbassadorProfile.VerificationStatus.PENDING).count() +
#             ConsultantProfile.objects.filter(verification_status=ConsultantProfile.VerificationStatus.PENDING).count()
#         ),
#         'pending_documents': ClientDocument.objects.filter(status=DocumentStatus.PENDING).count(),
#         'delayed_activities': ProjectActivity.objects.filter(
#             Q(activity_status=ActivityStatus.PAUSED) | 
#             Q(activity_deadline__lt=today, activity_status__in=[ActivityStatus.ONGOING, ActivityStatus.NOT_STARTED])
#         ).count(),
#         'active_assignments': active_associate_assignments.count(),
#         'active_consultant_assignments': active_consultant_assignments.count(),
#         'pending_requests_count': pending_associate_requests.count(),
#         'pending_consultant_requests_count': pending_consultant_requests.count(),
#     }

#     recent_signups = AmbassadorProfile.objects.filter(
#         verification_status=AmbassadorProfile.VerificationStatus.PENDING
#     ).select_related('user').order_by('-id')[:5]

#     context = {
#         'metrics': metrics,
#         'recent_signups': recent_signups,
#         'recent_projects': recent_projects,
#         'recent_activity_logs': recent_activity_logs,
        
#         # Combined Unassigned/Cancelled Queues
#         'pending_associate_requests': pending_associate_requests,
#         'pending_consultant_requests': pending_consultant_requests,
        
#         # Agent Lists for Inline Action Dropdowns
#         'available_associates': available_associates,
#         'available_consultants': available_consultants,
        
#         'active_associate_assignments': active_associate_assignments,
#         'active_consultant_assignments': active_consultant_assignments,
#     }

#     return render(request, 'dashboards/super_admin.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def superadmin_dashboard(request):
    """Admin dashboard featuring inline associate dispatches and client-consultant management."""

    # ==========================================
    # POST ACTIONS (INLINE ASSIGNMENTS)
    # ==========================================
    if request.method == "POST":
        action = request.POST.get("action")

        # --- ASSIGN / RE-ASSIGN FIELD ASSOCIATE ---
        if action == "assign_associate_request":
            assignment_id = request.POST.get("assignment_id")
            associate_id = request.POST.get("associate_id")

            if not associate_id:
                messages.error(request, "Please select an associate from the list before assigning.")
                return redirect("dashboard:super-admin-dashboard")

            assignment = get_object_or_404(AmbassadorAssignment, pk=assignment_id)
            ambassador_profile = get_object_or_404(AmbassadorProfile, user_id=associate_id)

            assignment.ambassador = ambassador_profile
            assignment.status = AmbassadorAssignment.TaskStatus.ASSIGNED
            assignment.cancellation_reason = None  # Reset cancellation flag
            assignment.save(update_fields=['ambassador', 'status', 'cancellation_reason'])

            client_name = assignment.client.business_name or assignment.client.get_full_name() or assignment.client.email
            messages.success(
                request, 
                f"Successfully assigned Associate {ambassador_profile.user.get_full_name()} to {client_name}."
            )
            return redirect("dashboard:super-admin-dashboard")

        # --- ASSIGN / CHANGE CONSULTANT ON CLIENT PROJECT ---
        elif action == "assign_project_consultant":
            project_id = request.POST.get("project_id")
            consultant_user_id = request.POST.get("consultant_user_id")

            project = get_object_or_404(ClientProject, pk=project_id)

            if consultant_user_id:
                consultant_user = get_object_or_404(User, pk=consultant_user_id, role=UserRole.CONSULTANT)
                project.assigned_consultant = consultant_user
                project.save(update_fields=['assigned_consultant'])

                client_name = project.client.business_name or project.client.get_full_name() or project.client.email
                messages.success(
                    request, 
                    f"Successfully assigned Consultant {consultant_user.get_full_name()} to project for {client_name}."
                )
            else:
                # Handle clearing consultant assignment
                project.assigned_consultant = None
                project.save(update_fields=['assigned_consultant'])
                messages.info(request, "Removed consultant assignment from project.")

            return redirect("dashboard:super-admin-dashboard")

    # ==========================================
    # FIELD ASSOCIATE REQUEST QUEUE (UNASSIGNED + CANCELLED)
    # ==========================================
    pending_associate_requests = AmbassadorAssignment.objects.filter(
        status__in=[
            AmbassadorAssignment.TaskStatus.UNASSIGNED,
            AmbassadorAssignment.TaskStatus.CANCELLED
        ]
    ).select_related('client', 'project', 'ambassador__user').order_by('-updated_at')

    # ==========================================
    # AVAILABLE AGENTS WITH ACTIVE WORKLOADS
    # ==========================================
    available_associates = User.objects.filter(
        role=UserRole.AMBASSADOR,
        ambassador_profile__is_active_field_agent=True
    ).annotate(
        active_task_count=Count(
            'ambassador_profile__assignments',
            filter=Q(ambassador_profile__assignments__status=AmbassadorAssignment.TaskStatus.ASSIGNED)
        )
    ).order_by('first_name')

    available_consultants = User.objects.filter(
        role=UserRole.CONSULTANT,
        consultant_profile__is_active_consultant=True
    ).annotate(
        active_case_count=Count('assigned_projects')
    ).order_by('first_name')

    # ==========================================
    # ACTIVE ASSIGNMENTS & CLIENT PROJECTS
    # ==========================================
    active_associate_assignments = AmbassadorAssignment.objects.filter(
        ambassador__isnull=False,
        status=AmbassadorAssignment.TaskStatus.ASSIGNED
    ).select_related('ambassador__user', 'client', 'project').order_by('-created_at')

    client_projects_list = ClientProject.objects.select_related(
        'client', 'assigned_consultant'
    ).prefetch_related('activities').order_by('-updated_at')

    # ==========================================
    # KPI METRICS & RECENT LOGS
    # ==========================================
    recent_activity_logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:6]
    today = timezone.now().date()

    metrics = {
        'active_clients': User.objects.filter(role=UserRole.USER, is_active=True).count(),
        'active_projects': client_projects_list.count(),
        'unassigned_consultant_projects': client_projects_list.filter(assigned_consultant__isnull=True).count(),
        'total_ambassadors': AmbassadorProfile.objects.filter(is_active_field_agent=True).count(),
        'total_consultants': ConsultantProfile.objects.filter(is_active_consultant=True).count(),
        'pending_verifications': (
            AmbassadorProfile.objects.filter(verification_status=AmbassadorProfile.VerificationStatus.PENDING).count() +
            ConsultantProfile.objects.filter(verification_status=ConsultantProfile.VerificationStatus.PENDING).count()
        ),
        'pending_documents': ClientDocument.objects.filter(status=DocumentStatus.PENDING).count(),
        'delayed_activities': ProjectActivity.objects.filter(
            Q(activity_status=ActivityStatus.PAUSED) | 
            Q(activity_deadline__lt=today, activity_status__in=[ActivityStatus.ONGOING, ActivityStatus.NOT_STARTED])
        ).count(),
        'active_assignments': active_associate_assignments.count(),
        'pending_associate_requests_count': pending_associate_requests.count(),
    }

    recent_signups = AmbassadorProfile.objects.filter(
        verification_status=AmbassadorProfile.VerificationStatus.PENDING
    ).select_related('user').order_by('-id')[:5]

    # ==========================================
    # STAFF SCHEDULES & AVAILABILITY SLOTS
    # ==========================================
    consult_available = Availability.objects.filter(
        user__role=UserRole.CONSULTANT
    ).select_related('user').order_by('weekday', 'start_time')

    associate_available = Availability.objects.filter(
        user__role=UserRole.AMBASSADOR
    ).select_related('user').order_by('weekday', 'start_time')

    consultants_availability = defaultdict(list)
    for slot in consult_available:
        consultants_availability[slot.user].append(slot)

    associates_availability = defaultdict(list)
    for slot in associate_available:
        associates_availability[slot.user].append(slot)

    context = {
        'metrics': metrics,
        'recent_signups': recent_signups,
        'client_projects_list': client_projects_list,
        'recent_projects': client_projects_list[:8],
        'recent_activity_logs': recent_activity_logs,

        # Staff Availability
        'consultants_availability': dict(consultants_availability),
        'associates_availability': dict(associates_availability),
        
        # Queues & Lists
        'pending_associate_requests': pending_associate_requests,
        'available_associates': available_associates,
        'available_consultants': available_consultants,
        'active_associate_assignments': active_associate_assignments,
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
            messages.error(request, f"Cannot process verification: Associate {target_user.email} hasn't uploaded all files.")
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
            profile.is_active_consultant = True
            profile.save()
            messages.success(request, f"Successfully verified account and authorized Consultant {target_user.email}.")
            
        elif action == 'decline':
            profile.verification_status = ConsultantProfile.VerificationStatus.DECLINED
            profile.is_active_consultant = False
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
def consultant_availability(request):
    if request.method == "POST":
        form = AvailabilityForm(request.POST)

        if form.is_valid():
            availability = form.save(commit=False)
            availability.user = request.user
            availability.save()

            messages.success(request, "Availability added successfully.")
            return redirect("dashboard:consultant-availability")
    else:
        form = AvailabilityForm()

    grouped = {}

    for day, label in Availability.WeekDay.choices:

        grouped[label] = Availability.objects.filter(
            user=request.user,
            weekday=day
        ).order_by("start_time")

    context = {
        "form": form,
        "grouped": grouped,
    }
    return render(request, "dashboards/consultant_availability.html", context)


@login_required
@role_required([UserRole.CONSULTANT])
@require_POST
def edit_availability(request, pk):
    availability = get_object_or_404(Availability, pk=pk, user=request.user)

    form = AvailabilityForm(request.POST, instance=availability)
    if form.is_valid():
        form.save()
        messages.success(request, "Availability updated.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Update failed: {error}")

    return redirect("dashboard:consultant-availability")


@login_required
@role_required([UserRole.CONSULTANT])
@require_POST
def delete_availability(request, pk):
    availability = get_object_or_404(Availability, pk=pk, user=request.user)

    availability.delete()
    messages.success(request, "Availability removed.")

    return redirect("dashboard:consultant-availability")


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



#********************************************************** ASSOCIATE DASHBOARD **************************************************#
#******************************************************************************************************************************#
# ASSOCIATE Dashboard Overview
@login_required
@role_required([UserRole.AMBASSADOR])
def ambassador_dashboard(request):
    """
    Renders the operational hub for PFS Associates.
    Swaps presentation layers dynamically based on backend verification flags.
    """
    try:
        profile = request.user.ambassador_profile
        is_verified = profile.is_active_field_agent
    except AmbassadorProfile.DoesNotExist:
        profile = None
        is_verified = False

    active_assignments = []
    available_clients = []
    completed_payouts_total = "0.00"

    if is_verified:
        # Fetch client tracks currently managed by this ambassador agent
        raw_assignments = AmbassadorAssignment.objects.filter(
            ambassador=profile, 
            status='ASSIGNED'
        ).select_related('client').prefetch_related('client__documents')

        # Calculate settled payouts ledger summary metrics
        payout_count = AmbassadorAssignment.objects.filter(
            ambassador=profile,
            status='COMPLETED',
            payout_processed=True
        ).count()
        completed_payouts_total = f"{payout_count * 150.00:.2f}"

        # Enrich active assignments with document progress metadata
        for assignment in raw_assignments:
            client = assignment.client
            client_required_types = get_required_document_types(client)
            
            # Exclude rejected documents from valid count
            valid_docs = client.documents.exclude(status=DocumentStatus.REJECTED)
            uploaded_types = set(valid_docs.values_list('document_type', flat=True))

            missing_docs = []
            for doc_type in client_required_types:
                if doc_type not in uploaded_types:
                    try:
                        label = DocumentType(doc_type).label
                    except ValueError:
                        label = doc_type
                    missing_docs.append({'code': doc_type, 'label': label})

            total_required = len(client_required_types)
            matching_uploaded = [dt for dt in client_required_types if dt in uploaded_types]
            total_uploaded = len(matching_uploaded)

            active_assignments.append({
                'id': assignment.id,
                'client': client,
                'modality': getattr(assignment, 'modality', None),
                'get_modality_display': assignment.get_modality_display() if hasattr(assignment, 'get_modality_display') else '',
                'ambassador_marked_complete': getattr(assignment, 'ambassador_marked_complete', False),
                'client_marked_complete': getattr(assignment, 'client_marked_complete', False),
                'total_uploaded': total_uploaded,
                'total_required': total_required,
                'missing_types': missing_docs,
            })

        # Gather all client IDs currently claimed by an active ambassador
        claimed_client_ids = AmbassadorAssignment.objects.filter(
            status='ASSIGNED'
        ).values_list('client_id', flat=True)

        # Prefetch ONLY documents to eliminate N+1 queries
        open_clients = User.objects.filter(
            role=UserRole.USER
        ).exclude(
            id__in=claimed_client_ids
        ).prefetch_related(
            'documents'
        ).order_by('-id')

        for client in open_clients:
            client_required_types = get_required_document_types(client)
            
            valid_docs = client.documents.exclude(status=DocumentStatus.REJECTED)
            uploaded_types = set(valid_docs.values_list('document_type', flat=True))

            missing_docs = []
            for doc_type in client_required_types:
                if doc_type not in uploaded_types:
                    try:
                        label = DocumentType(doc_type).label
                    except ValueError:
                        label = doc_type
                    missing_docs.append({'code': doc_type, 'label': label})

            total_required = len(client_required_types)
            matching_uploaded = [doc_type for doc_type in client_required_types if doc_type in uploaded_types]
            total_uploaded = len(matching_uploaded)

            if total_uploaded < total_required or total_required == 0:
                available_clients.append({
                    'client': client,
                    'total_uploaded': total_uploaded,
                    'total_required': total_required,
                    'required_types': client_required_types,
                    'uploaded_types': uploaded_types,
                    'missing_types': missing_docs,
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
def associate_availability(request):
    if request.method == "POST":
        form = AvailabilityForm(request.POST)

        if form.is_valid():
            availability = form.save(commit=False)
            availability.user = request.user
            availability.save()

            messages.success(request, "Availability added successfully.")
            return redirect("dashboard:associate-availability")
    else:
        form = AvailabilityForm()

    grouped = {}

    for day, label in Availability.WeekDay.choices:

        grouped[label] = Availability.objects.filter(
            user=request.user,
            weekday=day
        ).order_by("start_time")

    context = {
        "form": form,
        "grouped": grouped,
    }
    return render(request, "dashboards/associate_availability.html", context)


@login_required
@role_required([UserRole.AMBASSADOR])
@require_POST
def associate_edit_availability(request, pk):
    availability = get_object_or_404(Availability, pk=pk, user=request.user)

    form = AvailabilityForm(request.POST, instance=availability)
    if form.is_valid():
        form.save()
        messages.success(request, "Availability updated.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Update failed: {error}")

    return redirect("dashboard:associate-availability")


@login_required
@role_required([UserRole.AMBASSADOR])
@require_POST
def associate_delete_availability(request, pk):
    availability = get_object_or_404(Availability, pk=pk, user=request.user)

    availability.delete()
    messages.success(request, "Availability removed.")

    return redirect("dashboard:associate-availability")


@login_required
@role_required([UserRole.AMBASSADOR])
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
            doc, created = ClientDocument.objects.update_or_create(
                client=client_user,
                document_type=doc_type,
                defaults={
                    'uploaded_by': request.user,
                    'file': uploaded_file,
                    'status': DocumentStatus.PENDING,
                    'cancellation_reason': '',
                }
            )
            action_text = "uploaded" if created else "re-uploaded"
            messages.success(request, f"Proxy document ({doc.get_document_type_display()}) successfully {action_text}.")
            return redirect('dashboard:ambassador-client-workbench', client_id=client_user.id)

    # Dynamic document state compilation
    client_docs = ClientDocument.objects.filter(client=client_user).order_by('-uploaded_at')
    
    # Fetch dynamically required document codes based on client sector/package
    required_type_codes = get_required_document_types(client_user)
    
    # Filter out rejected documents for requirements evaluation
    valid_uploaded_docs = client_docs.exclude(status=DocumentStatus.REJECTED)
    uploaded_type_codes = set(valid_uploaded_docs.values_list('document_type', flat=True))
    
    # Build dropdown options and progress counters dynamically
    missing_types = []
    for code in required_type_codes:
        if code not in uploaded_type_codes:
            try:
                label = DocumentType(code).label
            except ValueError:
                label = code
            missing_types.append({'code': code, 'label': label})
            
    total_required = len(required_type_codes)
    total_uploaded = len([code for code in required_type_codes if code in uploaded_type_codes])
    
    context = {
        'assignment': assignment,
        'client_user': client_user,
        'client_docs': client_docs,
        'missing_types': missing_types,
        'total_uploaded': total_uploaded,
        'total_required': total_required,
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
    Handles multi-file onboarding uploads, associate assistance requests,
    and automatically transitions the view state when baseline docs are complete.
    """
    required_types = get_required_document_types(request.user)

    # --- PROCESS INCOMING FORM SUBMISSION ---
    if request.method == 'POST':
        files_saved = 0
        
        # Process File Uploads
        for doc_key in required_types:
            if doc_key in request.FILES:
                uploaded_file = request.FILES[doc_key]
                
                ClientDocument.objects.update_or_create(
                    client=request.user,
                    document_type=doc_key,
                    defaults={
                        'file': uploaded_file,
                        'status': DocumentStatus.PENDING,
                        'uploaded_by': request.user
                    }
                )
                files_saved += 1

        # Process Associate Assistance Request
        requires_associate = request.POST.get('requires_associate') == 'on'
        modality = request.POST.get('associate_modality', AmbassadorAssignment.AssistanceModality.REMOTE)

        if requires_associate:
            # Check if an active or unassigned/pending request already exists
            existing_assignment = AmbassadorAssignment.objects.filter(
                client=request.user,
                status__in=[
                    AmbassadorAssignment.TaskStatus.UNASSIGNED,
                    AmbassadorAssignment.TaskStatus.ASSIGNED,
                    AmbassadorAssignment.TaskStatus.COMPLETED,
                    AmbassadorAssignment.TaskStatus.CANCELLED,
                ]
            ).first()

            if not existing_assignment:
                # Get client's primary project if available
                primary_project = request.user.projects.first()
                
                # Create an UNASSIGNED request so it routes to Superadmin for assignment
                AmbassadorAssignment.objects.create(
                    client=request.user,
                    project=primary_project,
                    status=AmbassadorAssignment.TaskStatus.UNASSIGNED,
                    modality=modality,
                )
        
        if files_saved > 0 or requires_associate:
            messages.success(request, "Your onboarding details and documents have been updated.")
        else:
            messages.error(request, "No changes or files were selected.")
            
        return redirect('dashboard:user-dashboard')

    # --- EVALUATE & RENDER CURRENT VIEW STATE ---
    client_docs = request.user.documents.all()
    uploaded_dict = {doc.document_type: doc for doc in client_docs}
    
    total_required = len(required_types)
    total_uploaded = client_docs.filter(
        document_type__in=required_types,
        status__in=[DocumentStatus.PENDING, DocumentStatus.APPROVED]
    ).exclude(file="").count()
    
    active_projects = request.user.projects.all()

    # Fetch any current associate assistance request (pending or assigned)
    existing_associate_request = AmbassadorAssignment.objects.filter(
        client=request.user,
        status__in=[
            AmbassadorAssignment.TaskStatus.UNASSIGNED,
            AmbassadorAssignment.TaskStatus.ASSIGNED,
            AmbassadorAssignment.TaskStatus.COMPLETED,
            AmbassadorAssignment.TaskStatus.CANCELLED,
        ]
    ).first()

    # Fetch assigned associate
    assignment = AmbassadorAssignment.objects.filter(
        client=request.user,
        status=AmbassadorAssignment.TaskStatus.ASSIGNED
    ).select_related('ambassador').first()

    context = {
        'uploaded_dict': uploaded_dict,
        'total_uploaded': total_uploaded,
        'total_required': total_required,
        'active_projects': active_projects,
        'required_types': required_types,
        'existing_associate_request': existing_associate_request,
        'assignment': assignment,
    }

    # If all baseline uploads are complete, swap out the template
    if total_uploaded >= total_required:
        recent_activities = request.user.activities.all()[:5]

        context = {
            "uploaded_dict": uploaded_dict,
            "recent_activities": recent_activities,
            "active_projects": active_projects,
            "existing_associate_request": existing_associate_request,
        }

        return render(request, "dashboards/user_tracking.html", context)
        
    return render(request, "dashboards/user.html", context)



@login_required
@role_required([UserRole.USER])
@mandatory_docs_required
def user_documents_vault(request):
    """
    Manages explicit standalone updates for baseline FDA document types.
    Supports sector switching by maintaining visibility for non-mandatory uploaded assets.
    """
    # Fetch current sector's required document types
    required_doc_types = get_required_document_types(request.user)

    # Convert required doc types into clean upper-case string keys
    required_keys = [
        dt.value for dt in required_doc_types
    ]

    # Fetch all client documents
    client_docs = request.user.documents.all()

    # Map uploaded non-supplementary documents into a lookup dictionary
    uploaded_dict = {
        str(doc.document_type.value if hasattr(doc.document_type, 'value') else doc.document_type).upper(): doc
        for doc in client_docs
        if str(doc.document_type).upper() != DocumentType.SUPPLEMENTARY
    }

    # Helper function to extract human-readable labels
    def get_label_for_key(raw_key):
        if hasattr(DocumentType, 'choices'):
            choices_dict = dict(DocumentType.choices)
            if raw_key in choices_dict:
                return choices_dict[raw_key]
        return raw_key.replace('_', ' ').title()

    # Handle Document Upload POST Requests
    if request.method == 'POST':
        saved_count = 0

        # Process any uploaded file key present in request.FILES
        for doc_key, uploaded_file in request.FILES.items():
            if doc_key == 'attached_file':  # Skip supplementary form input
                continue

            doc_key_clean = str(doc_key).upper()
            existing_doc = uploaded_dict.get(doc_key_clean)

            # Block editing if document is already approved
            if existing_doc and existing_doc.status == DocumentStatus.APPROVED:
                doc_label = existing_doc.get_document_type_display() if hasattr(existing_doc, 'get_document_type_display') else doc_key_clean
                messages.error(
                    request, 
                    f"Modifications blocked: Your {doc_label} is already approved and cannot be altered."
                )
                return redirect('dashboard:user-documents')

            # Create or update document asset
            doc, created = ClientDocument.objects.update_or_create(
                client=request.user,
                document_type=doc_key_clean,
                defaults={
                    'file': uploaded_file,
                    'status': DocumentStatus.PENDING,
                    'uploaded_by': request.user
                }
            )
            saved_count += 1

            doc_label = doc.get_document_type_display() if hasattr(doc, 'get_document_type_display') else doc_key_clean
            action = "Submitted initial draft of" if created else "Uploaded a new version of"
            
            create_activity_log(
                user=request.user,
                category=LogCategory.DOCUMENT,
                description=f"{action} {doc_label}."
            )

        if saved_count > 0:
            messages.success(
                request, 
                f"Successfully uploaded and catalogued {saved_count} file(s) inside your portal."
            )
        return redirect('dashboard:user-documents')

    # Categorize Documents for Rendering
    
    # Active Sector Required Documents
    active_required_documents = []
    for raw_key in required_keys:
        active_required_documents.append({
            'key': raw_key,
            'label': get_label_for_key(raw_key),
            'doc': uploaded_dict.get(raw_key),
            'is_required': True
        })

    # Other Uploaded Documents (Uploaded files NOT in the current sector's required list)
    other_uploaded_documents = []
    for key_str, doc in uploaded_dict.items():
        if key_str not in required_keys and doc.file:
            other_uploaded_documents.append({
                'key': key_str,
                'label': doc.get_document_type_display() if hasattr(doc, 'get_document_type_display') else get_label_for_key(key_str),
                'doc': doc,
                'is_required': False
            })

    # Supplementary Custom Request Docs
    supplementary_documents = client_docs.filter(document_type=DocumentType.SUPPLEMENTARY).order_by('id')

    context = {
        'active_required_documents': active_required_documents,
        'other_uploaded_documents': other_uploaded_documents,
        'supplementary_documents': supplementary_documents,
        'total_uploaded': client_docs.filter(file__isnull=False).exclude(file="").count(),
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
            document_type=DocumentType.SUPPLEMENTARY,
            custom_title__iexact=title
        ).exists()

        if existing_slot:
            messages.warning(request, f"A supplementary slot named '{title}' already exists in your portal.")
            return redirect('dashboard:user-documents')
        
        # If it passes the check, create it safely
        ClientDocument.objects.create(
            client=request.user,
            document_type=DocumentType.SUPPLEMENTARY,
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
        
        display_name = document.custom_title if document.document_type == DocumentType.SUPPLEMENTARY else document.get_document_type_display()
        
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


@login_required
@role_required([UserRole.USER])
def assigned_associate_detail(request):
    """
    Displays the details of the associate assigned to the logged-in client.
    """
    # Fetch the active or assigned request for the logged-in client
    associate_request = AmbassadorAssignment.objects.filter(
        client=request.user
    ).select_related('ambassador', 'project').order_by('-created_at').first()

    # If no request exists or no associate has been assigned yet
    if not associate_request:
        messages.info(request, "You have not requested associate assistance.")
        return redirect('dashboard:user-dashboard') # Update with your client dashboard URL name

    if not associate_request.ambassador:
        messages.warning(request, "Your assistance request is currently pending assignment.")
        return redirect('dashboard:user-dashboard')

    context = {
        'assignment': associate_request,
        'associate': associate_request.ambassador,
    }
    return render(request, 'dashboards/user_assigned_associate.html', context)


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
@role_required([UserRole.USER])
def user_toggle_assignment_completion(request, assignment_id):
    """Allows client to mark the current associate assignment as complete."""
    if request.method == 'POST':
        assignment = get_object_or_404(AmbassadorAssignment, id=assignment_id, client=request.user)
        
        # Toggle completion status
        if not assignment.client_marked_complete:
            assignment.client_marked_complete = True
            assignment.client_completed_at = timezone.now()
            messages.success(request, "You have marked this assignment as complete. Thank you!")
        else:
            assignment.client_marked_complete = False
            assignment.client_completed_at = None
            messages.info(request, "Completion status reopened.")

        assignment.save()

        assignment.check_and_finalize_payout()

    return redirect('dashboard:assigned-associate-detail')


@login_required
@role_required([UserRole.USER])
def user_request_change_associate(request, assignment_id):
    """Allows client to cancel current associate assignment with a reason and flag for admin reassignment."""
    if request.method == 'POST':
        assignment = get_object_or_404(AmbassadorAssignment, id=assignment_id, client=request.user)
        
        # Prevent cancelling if already marked complete by client
        if assignment.client_marked_complete:
            messages.error(request, "Completed assignments cannot be re-assigned.")
            return redirect('dashboard:my-associate')

        reason = request.POST.get('cancellation_reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for requesting a change.")
            return redirect('dashboard:assigned-associate-detail')

        # Update assignment state
        assignment.status = AmbassadorAssignment.TaskStatus.CANCELLED
        assignment.cancellation_reason = reason
        assignment.ambassador = None
        assignment.save()

        messages.success(request, "Your request has been submitted to the admin team for reassignment.")

    return redirect('dashboard:assigned-associate-detail')


@login_required
@role_required([UserRole.USER])
def business_profile_view(request):
    """View to display and edit client business profile metrics."""
    user = request.user

    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your business profile has been updated successfully.")
            return redirect('dashboard:business-profile')
        else:
            messages.error(request, "Please correct the errors below to update your profile.")
    else:
        form = BusinessProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'dashboards/user_business_profile.html', context)