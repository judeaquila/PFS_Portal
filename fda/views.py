from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Count
from django.utils.dateparse import parse_date

from common.decorators import role_required
from accounts.models import UserRole
from dashboard.models import ClientProject
from .models import FDAProjectTracker, FDAWorkflowStage, FDAProjectStageActivity, FDAPaymentGate, FDAActivityStatus, FDAPaymentGateStatus, FDAWorkClearance, PaymentScope
from django.contrib.auth.decorators import login_required
from .services import evaluate_project_stages_for_role



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
def associate_three_dashboard(request):
    return get_role_dashboard(request, 'ASSOCIATE_3', 'fda/associate_3.html')

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