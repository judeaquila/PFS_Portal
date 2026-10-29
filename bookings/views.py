import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils.formats import date_format
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

from .models import AvailabilitySlot, Appointment, InAppNotification, ActionItem, NewClientProject, NewClientPackage, NewProjectActivity, AddOnService, BlueprintSubactivity
from .forms import AvailabilitySlotForm, BulkSlotForm, ClientBookingForm, AdminMeetingUpdateForm, ActionItemForm, InitiateProjectForm
from common.decorators import role_required
from accounts.models import UserRole, User


User = get_user_model()


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_availability_list(request):
    """
    FBV displaying all availability slots created by the admin, 
    separated into upcoming and past slots with client appointment details.
    """
    today = timezone.now().date()

    # Query all slots for this admin, prefetching appointment & client details
    base_slots = AvailabilitySlot.objects.filter(
        admin=request.user
    ).select_related('appointment__client')

    upcoming_slots = base_slots.filter(
        date__gte=today
    ).order_by('date', 'start_time')

    past_slots = base_slots.filter(
        date__lt=today
    ).order_by('-date', '-start_time')

    single_form = AvailabilitySlotForm()
    bulk_form = BulkSlotForm()

    context = {
        'upcoming_slots': upcoming_slots,
        'past_slots': past_slots,
        'single_form': single_form,
        'bulk_form': bulk_form,
        'today': today,
    }
    return render(request, 'bookings/associate_two_availability.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_create_slot(request):
    """
    FBV to create a single availability slot.
    """
    if request.method == 'POST':
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.admin = request.user
            try:
                slot.save()
                messages.success(request, f"Slot created for {slot.date.strftime('%A, %B %d %Y')} at {slot.start_time.strftime('%I:%M %p GMT')}")
            except Exception:
                messages.error(request, "A slot for this date and time already exists.")
        else:
            messages.error(request, "Failed to create slot. Check form inputs.")
            
    return redirect('bookings:associate-two-availability')


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_bulk_create_slots(request):
    """
    FBV generating consecutive slots between start and end times based on a interval duration.
    """
    if request.method == 'POST':
        form = BulkSlotForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            duration = timedelta(minutes=form.cleaned_data['slot_duration'])

            curr_dt = datetime.combine(date, start_time)
            end_dt = datetime.combine(date, end_time)

            created_count = 0
            while curr_dt + duration <= end_dt:
                slot_start = curr_dt.time()
                curr_dt += duration
                slot_end = curr_dt.time()

                slot, created = AvailabilitySlot.objects.get_or_create(
                    admin=request.user,
                    date=date,
                    start_time=slot_start,
                    defaults={'end_time': slot_end}
                )
                if created:
                    created_count += 1

            messages.success(request, f"Successfully created {created_count} slots for {date.strftime('%A, %B %d %Y')}.")
        else:
            messages.error(request, "Failed to generate bulk slots. Please check fields.")

    return redirect('bookings:associate-two-availability')


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_delete_slot(request, slot_id):
    """
    FBV to delete an unbooked slot.
    """
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, admin=request.user)
    
    if request.method == 'POST':
        if slot.is_booked:
            messages.error(request, "Cannot delete a slot that has already been booked by a client.")
        else:
            slot.delete()
            messages.success(request, "Slot removed successfully.")

    return redirect('bookings:associate-two-availability')



@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_appointments_list(request):
    """
    FBV listing client appointments separated by status/timeline for administrative review.
    """
    now = timezone.now()
    today = now.date()
    
    # Base queryset with optimization
    base_qs = Appointment.objects.select_related('slot', 'client').order_by('slot__date', 'slot__start_time')
    
    # Categorize appointments
    context = {
        # Imminent / Upcoming (Scheduled and date is today or in the future)
        'upcoming_appointments': base_qs.filter(status=Appointment.StatusChoices.SCHEDULED, slot__date__gte=today),
        
        # Past / Completed (Either marked completed, or scheduled dates that have passed)
        'past_appointments': base_qs.filter(
            Q(status=Appointment.StatusChoices.COMPLETED) | Q(status=Appointment.StatusChoices.SCHEDULED, slot__date__lt=today)
        ),
        
        # Cancelled
        'cancelled_appointments': base_qs.filter(status=Appointment.StatusChoices.CANCELLED),
    }
    
    return render(request, 'bookings/associate_two_appointments.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_appointment_detail(request, appointment_id):
    """
    FBV allowing Associate 2 to independently manage:
    1. Appointment Status / Schedule
    2. Virtual Meeting Link
    3. Meeting Summary & PDF/Word Document
    4. Action Items (via separate forms)
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    action_items = appointment.action_items.all()
    formatted_date = date_format(appointment.slot.date, "l, F jS Y")

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # Update Status
        if action_type == 'update_status':
            status = request.POST.get('status')
            if status in dict(Appointment.StatusChoices.choices):
                appointment.status = status
                appointment.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Appointment status updated to '{appointment.get_status_display()}'.")
            else:
                messages.error(request, "Invalid status selected.")

        # Update Meeting Link
        elif action_type == 'update_link':
            old_link = appointment.meeting_link
            new_link = request.POST.get('meeting_link', '').strip()
            appointment.meeting_link = new_link
            appointment.save(update_fields=['meeting_link', 'updated_at'])

            if new_link and old_link != new_link:
                InAppNotification.objects.create(
                    recipient=appointment.client,
                    appointment=appointment,
                    title="Meeting Link Updated",
                    message = f"The meeting link for '{appointment.title}' on {formatted_date} has been added/updated.",
                    notification_type=InAppNotification.NotificationTypes.LINK_ADDED
                )
            messages.success(request, "Virtual meeting link saved successfully.")

        # Upload Summary Document & Notes
        elif action_type == 'update_summary':
            meeting_notes = request.POST.get('meeting_notes', '').strip()
            appointment.meeting_notes = meeting_notes

            if 'summary_document' in request.FILES:
                appointment.summary_document = request.FILES['summary_document']
                InAppNotification.objects.create(
                    recipient=appointment.client,
                    appointment=appointment,
                    title="Meeting Summary Available",
                    message=f"A summary document for '{appointment.title}' has been uploaded.",
                    notification_type=InAppNotification.NotificationTypes.SUMMARY_READY
                )

            appointment.save()
            messages.success(request, "Meeting summary and notes updated successfully.")

        return redirect('bookings:associate-two-appointment-detail', appointment_id=appointment.id)

    # Initial form instances for GET render
    form = AdminMeetingUpdateForm(instance=appointment)
    action_form = ActionItemForm()

    context = {
        'appointment': appointment,
        'action_items': action_items,
        'form': form,
        'action_form': action_form,
    }
    return render(request, 'bookings/associate_two_appointment_detail.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_add_action_item(request, appointment_id):
    """FBV to attach a new action item To-Do to an appointment."""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        form = ActionItemForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.appointment = appointment
            action.save()
            messages.success(request, "Action item added.")
    return redirect('bookings:associate-two-appointment-detail', appointment_id=appointment.id)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_toggle_action_item(request, item_id):
    """FBV to toggle completion state of an action item."""
    item = get_object_or_404(ActionItem, id=item_id)
    item.is_completed = not item.is_completed
    item.save()
    return redirect('bookings:associate-two-appointment-detail', appointment_id=item.appointment.id)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_delete_action_item(request, item_id):
    """FBV to delete an action item."""
    item = get_object_or_404(ActionItem, id=item_id)
    appointment_id = item.appointment.id
    item.delete()
    messages.success(request, "Action item removed.")
    return redirect('bookings:associate-two-appointment-detail', appointment_id=appointment_id)


# --- Notifications View logic ---

@login_required
@role_required([UserRole.ASSOCIATE_2])
def unread_notifications_count(request):
    """AJAX FBV returning unread count and latest 5 notifications."""
    notifications = InAppNotification.objects.filter(recipient=request.user)
    unread_count = notifications.filter(is_read=False).count()
    latest_notifications = notifications[:5]

    items = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime("%b %d, %H:%M")
        } for n in latest_notifications
    ]

    context = {
        'unread_count': unread_count,
        'notifications': items,
    }
    return JsonResponse(context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def mark_notifications_as_read(request):
    """FBV to mark all user notifications as read."""
    if request.method == 'POST':
        InAppNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid method'}, status=400)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_projects_list(request):
    """List all client projects with their progress and active package."""
    projects = NewClientProject.objects.select_related('client', 'client_package')\
        .prefetch_related('activities').all().order_by('-created_at')

    context = {
        'projects': projects,
    }
    
    return render(request, 'bookings/associate_two_projects_list.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_initiate_project(request, client_id=None):
    """
    Initiates a new project for a specific client profile.
    Automatically assigns the target client, restricts staff selections to Associate 2 roles,
    and feeds package subactivities to Alpine.js.
    """
    client_obj = None
    if client_id:
        client_obj = get_object_or_404(User, id=client_id, role=UserRole.USER)

    if request.method == 'POST':
        form = InitiateProjectForm(request.POST, client_obj=client_obj)
        if form.is_valid():
            with transaction.atomic():
                project = form.save(commit=False)
                
                # Assign target client from URL if set
                if client_obj:
                    project.client = client_obj

                # Default assigned staff to logged-in user if left unselected
                if not project.assigned_staff:
                    project.assigned_staff = request.user

                project.save()

                messages.success(
                    request, 
                    f"Project '{project.title}' successfully initiated! Milestone activities generated."
                )
                return redirect('bookings:associate-two-project-detail', project_id=project.id)
        else:
            print("FORM ERRORS:", form.errors)
            messages.error(request, f"Form validation failed: {form.errors}")
    else:
        initial_data = {'assigned_staff': request.user.id}
        if client_obj:
            initial_data['client'] = client_obj.id

        form = InitiateProjectForm(initial=initial_data, client_obj=client_obj)

    # Serialize blueprints for Alpine.js dynamic preview
    blueprints_dict = {}
    packages = NewClientPackage.objects.prefetch_related('blueprint_subactivities').all()
    for pkg in packages:
        blueprints_dict[str(pkg.id)] = [
            f"{sub.activity_name} ({sub.scope})" if getattr(sub, 'scope', None) else sub.activity_name
            for sub in pkg.blueprint_subactivities.all().order_by('sort_order')
        ]

    context = {
        'form': form,
        'client_obj': client_obj,
        'blueprints_json': json.dumps(blueprints_dict),
    }

    return render(request, 'bookings/associate_two_initiate_project.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_project_detail(request, project_id):
    """Detail view showing project activity tracking, completion rates, and add-ons."""
    project = get_object_or_404(
        NewClientProject.objects.select_related('client', 'client_package'), 
        id=project_id
    )
    activities = project.activities.all().order_by('id')
    
    total_activities = activities.count()
    completed_activities = activities.filter(activity_status=NewProjectActivity.ActivityStatus.COMPLETED).count()
    progress_percentage = int((completed_activities / total_activities * 100)) if total_activities > 0 else 0

    context = {
        'project': project,
        'activities': activities,
        'total_activities': total_activities,
        'completed_activities': completed_activities,
        'progress_percentage': progress_percentage,
        'add_ons': AddOnService.objects.all(),
    }

    return render(request, 'bookings/associate_two_project_detail.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
@require_POST
def update_project_activity_status(request, activity_id):
    """API/HTMX-ready view to update an individual project activity status and payment."""
    activity = get_object_or_404(NewProjectActivity, id=activity_id)
    
    new_status = request.POST.get('activity_status')
    new_payment = request.POST.get('payment_status')

    if new_status in NewProjectActivity.ActivityStatus.values:
        activity.activity_status = new_status

    if new_payment in NewProjectActivity.PaymentStatus.values:
        activity.payment_status = new_payment

    activity.save()
    messages.success(request, f"Updated activity: {activity.activity_name}")

    return redirect('bookings:associate-two-project-detail', project_id=activity.project.id)


@login_required
@role_required([UserRole.ASSOCIATE_2])
def associate_two_edit_project(request, project_id):
    """
    Allows Associate 2 to update an existing client project's details,
    package selection, assigned staff, and financial payment tracking.
    """
    project = get_object_or_404(NewClientProject.objects.select_related('client', 'client_package', 'assigned_staff'), id=project_id)
    client_obj = project.client

    if request.method == 'POST':
        form = InitiateProjectForm(request.POST, instance=project, client_obj=client_obj)
        if form.is_valid():
            with transaction.atomic():
                updated_project = form.save()
                messages.success(request, f"Project '{updated_project.title}' successfully updated!")
                return redirect('bookings:associate-two-project-detail', project_id=updated_project.id)
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        form = InitiateProjectForm(instance=project, client_obj=client_obj)

    # Serialize blueprints for Alpine.js dynamic preview
    blueprints_dict = {}
    packages = NewClientPackage.objects.prefetch_related('blueprint_subactivities').all()
    for pkg in packages:
        blueprints_dict[str(pkg.code)] = [
            f"{sub.activity_name} ({sub.scope})" if getattr(sub, 'scope', None) else sub.activity_name
            for sub in pkg.blueprint_subactivities.all().order_by('sort_order')
        ]

    context = {
        'form': form,
        'project': project,
        'client_obj': client_obj,
        'blueprints_json': json.dumps(blueprints_dict),
    }

    return render(request, 'bookings/associate_two_edit_project.html', context)


@login_required
@role_required([UserRole.ASSOCIATE_2])
@require_POST
def associate_two_delete_project(request, project_id):
    """
    Deletes or archives an active client project workspace.
    """
    project = get_object_or_404(NewClientProject, id=project_id)
    project_title = project.title
    
    with transaction.atomic():
        project.delete()
        messages.success(request, f"Project '{project_title}' has been successfully deleted.")

    return redirect('bookings:associate-two-projects-list')


@login_required
@role_required([UserRole.ASSOCIATE_2])
def package_comparison_matrix_view(request):
    """
    Public / Internal matrix view comparing all packages, scopes, and inclusions side-by-side.
    """
    packages = NewClientPackage.objects.prefetch_related('blueprint_subactivities').all()
    add_ons = AddOnService.objects.all()

    # Collect distinct activity definitions and their scopes across packages
    all_blueprint_activities = BlueprintSubactivity.objects.values(
        'activity_name', 'scope'
    ).distinct()

    # Build inclusion lookup grid: matrix_grid[activity_name][package_code] = True/False
    matrix_grid = []
    
    # Standard 14 matrix activities list to preserve display sequence
    activity_order = [
        ("Review of product documentation", "1 Product"),
        ("Review of product label", "1 Label"),
        ("FDA online portal account creation", "1 Account"),
        ("FDA online product registration", "1 Product"),
        ("FDA online facility registration", "1 Facility"),
        ("Sample submission to the FDA", "1 Product"),
        ("Application follow ups", "1 Product"),
        ("Audit scheduling follow ups", "1 Facility"),
        ("Lab sample preparation training", "1 Product"),
        ("Sample submission to a laboratory", "1 Product"),
        ("Laboratory test results follow up", "1 Product"),
        ("Facility setup and audit training", "1 Facility"),
        ("Drafting of forms", "10 Forms"),
        ("Drafting of SOPs", "10 SOPs"),
    ]

    for act_name, default_scope in activity_order:
        row = {
            'activity_name': act_name,
            'scope': default_scope,
            'inclusions': {}
        }
        for pkg in packages:
            is_included = pkg.blueprint_subactivities.filter(activity_name=act_name).exists()
            row['inclusions'][pkg.code] = is_included
        matrix_grid.append(row)

    context = {
        'packages': packages,
        'matrix_grid': matrix_grid,
        'add_ons': add_ons,
    }

    return render(request, 'bookings/package_comparison_matrix.html', context)


##################################################################################################
############################## CLIENT BOOKING VIEW ###############################################
##################################################################################################

@login_required
@role_required([UserRole.USER])
def client_booking_view(request):
    """
    FBV displaying all available slots grouped by date for clients to browse and select.
    """
    today = timezone.now().date()
    
    # Fetch all available future slots
    available_slots = AvailabilitySlot.objects.filter(
        date__gte=today,
        is_booked=False
    ).order_by('date', 'start_time')

    # Group slots by date for intuitive UI rendering
    grouped_slots = {}
    for slot in available_slots:
        grouped_slots.setdefault(slot.date, []).append(slot)

    booking_form = ClientBookingForm()

    context = {
        'grouped_slots': grouped_slots,
        'booking_form': booking_form,
        'today': today,
    }
    return render(request, 'bookings/client_book_slot.html', context)


@login_required
@role_required([UserRole.USER])
def client_confirm_booking(request, slot_id):
    """
    FBV to process slot reservation, create the appointment, and trigger admin notification.
    """
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, is_booked=False)

    if request.method == 'POST':
        form = ClientBookingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Lock slot and create appointment
                slot.is_booked = True
                slot.save()

                appointment = form.save(commit=False)
                appointment.slot = slot
                appointment.client = request.user
                appointment.save()

                # Notify the administrator in-app
                InAppNotification.objects.create(
                    recipient=slot.admin,
                    appointment=appointment,
                    title="New Booking Received",
                    message=f"{request.user.get_full_name() or request.user.business_name} booked a meeting on {slot.date.strftime('%A, %B %d %Y')} at {slot.start_time.strftime('%I:%M %p')}.",
                    notification_type='BOOKING_CONFIRMED'
                )

                # Notify client confirmation
                InAppNotification.objects.create(
                    recipient=request.user,
                    appointment=appointment,
                    title="Booking Confirmed",
                    message=f"Your appointment is set for {slot.date.strftime('%A, %B %d %Y')} at {slot.start_time.strftime('%I:%M %p')}.",
                    notification_type='BOOKING_CONFIRMED'
                )

            messages.success(request, "Your meeting has been successfully booked!")
            return redirect('bookings:client-booking-dashboard')
        else:
            messages.error(request, "Invalid booking details. Please try again.")

    return redirect('bookings:client-booking')


@login_required
@role_required([UserRole.USER])
def client_booking_dashboard(request):
    """
    FBV for client appointment overview separated by status/timeline tabs.
    """
    now = timezone.now()
    today = now.date()
    
    # Base queryset for the logged-in client
    base_qs = Appointment.objects.filter(
        client=request.user
    ).select_related('slot').prefetch_related('action_items').order_by('slot__date', 'slot__start_time')

    context = {
        # Imminent / Upcoming (Scheduled and date is today or in the future)
        'upcoming_appointments': base_qs.filter(status=Appointment.StatusChoices.SCHEDULED, slot__date__gte=today),
        
        # Past / Completed (Marked completed or past scheduled dates)
        'past_appointments': base_qs.filter(
            Q(status=Appointment.StatusChoices.COMPLETED) | Q(status=Appointment.StatusChoices.SCHEDULED, slot__date__lt=today)
        ),
        
        # Cancelled
        'cancelled_appointments': base_qs.filter(status=Appointment.StatusChoices.CANCELLED),
        
        'now': now,
    }
    return render(request, 'bookings/client_booking.html', context)


@login_required
@role_required([UserRole.USER])
def client_appointment_detail(request, appointment_id):
    """
    FBV allowing clients to view specific details, meeting links, summaries, and action items for a single appointment.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)
    action_items = appointment.action_items.all()

    context = {
        'appointment': appointment,
        'action_items': action_items,
    }
    return render(request, 'bookings/client_appointment_detail.html', context)