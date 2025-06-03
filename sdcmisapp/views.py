from django.shortcuts import render, redirect, get_object_or_404

from .forms import CreateUserForm, Loginform, IEC_AddForm, IEC_UpdateForm, RouteTaskForm, NoticePCISubmissionForm
from django.contrib.auth.models import auth, Group
from django.contrib.auth import authenticate

from django.contrib import messages
from datetime import timedelta, date # For due_date calculation
from django.db.models import Q # For complex lookups
from django.contrib.auth.decorators import login_required

from .models import iec_records, CustomUser, InitialEvaluationReport, PreChargeInvestigation
from .workflow_def import get_initial_status_key, CASE_WORKFLOW_STEPS, get_task_step_by_key


# home page

def home(request):
    
    return render(request, 'sdcmisapp/index.html')

# register

def register(request):
    registration_done = False
    form = CreateUserForm()
    
    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for registering! Your account is awaiting admin approval.")
            registration_done = True
            form = CreateUserForm() # Clear the form for the success page
        # If form is not valid, it will be re-rendered with errors
            
    context = {
        'form': form,
        'registration_done': registration_done
    }
    return render(request, 'sdcmisapp/register.html',context=context)

# user login

def login(request):  
    form = Loginform()
    
    if request.method == "POST":
        form = Loginform(request, data=request.POST)

        if form.is_valid():
            # form.is_valid() is True means authenticate() was successful via the form's clean method
            # and the user is active.
            user = form.get_user() # Get the authenticated user from the form
            auth.login(request, user)
            return redirect('dashboard')
        else:
            # Form is not valid. This means authenticate() called by the form's clean method returned None.
            # This could be due to:
            # 1. User is inactive (form.errors might contain "This account is inactive.")
            # 2. Credentials are wrong (form.errors might contain "Please enter a correct username and password...")
            # 3. User does not exist (form.errors would also indicate this)

            # The Loginform (AuthenticationForm) now has a custom error message for inactive users.
            # Its errors will be displayed by the template (e.g., via {{ form|crispy }} or {{ form.errors }}).
            # No need to add an additional message via django.contrib.messages for the inactive case here.
            pass # Form is invalid, template will display form.errors
    context = {'form':form}
    return render(request, 'sdcmisapp/login.html',context=context)

# USER LOGOUT

def logout(request):
    
    auth.logout(request)

    return redirect('login')

#  DASHBOARD

@login_required(login_url='login')

def dashboard(request):
    user = request.user
    records_qs = iec_records.objects.all()

    # Filter records based on user role
    if user.role in ['ier_inv', 'pci_inv']:
        records_qs = records_qs.filter(
            Q(created_by=user) | Q(assigned_to=user)
        ).distinct() # Use distinct() if a record could be created by and assigned to the same user
    # Add more role-based filters here if needed for other roles (e.g., admin, dir)

    records_qs = records_qs.order_by('-id') # Apply ordering after filtering
    today = date.today()
    
    # Get the initial status key from the workflow definition
    initial_status_key = get_initial_status_key()
    # print(f"\nDEBUG: Overall Initial Workflow Status Key: '{initial_status_key}'") # DEBUG REMOVED

    # Calculate days remaining for each record
    processed_records = []
    for record in records_qs:
        if record.due_date:
            delta = record.due_date - today
            record.days_remaining = delta.days
            if record.days_remaining < 0:
                record.overdue_days_count = abs(record.days_remaining)  # Store positive overdue days
            # No need for an else for overdue_days_count if not overdue, template will handle
        else:
            # Ensure days_remaining is set if due_date is None
            record.days_remaining = None # Handle cases where due_date might be null
        
        # --- DETAILED DEBUGGING FOR acknowledge_and_route BUTTON ---
        # print(f"\n--- DEBUG: Processing Record ID: {record.id} (Ref: {record.iec_ref}) ---") # DEBUG REMOVED
        # print(f"DEBUG: Current Logged-in User: '{user}' (ID: {user.id})") # DEBUG REMOVED
        # print(f"DEBUG: Record Status: '{record.status}'") # DEBUG REMOVED
        # print(f"DEBUG: Record Created By: '{record.created_by}' (ID: {record.created_by.id if record.created_by else 'N/A'})") # DEBUG REMOVED
        
        condition1_initial_key_exists = bool(initial_status_key)
        condition2_status_matches = initial_status_key and record.status == initial_status_key
        condition3_user_is_creator = record.created_by == user

        # print(f"DEBUG: Condition 1 (Initial key exists?): {condition1_initial_key_exists}") # DEBUG REMOVED
        # print(f"DEBUG: Condition 2 (Record status ('{record.status}') == Initial key ('{initial_status_key}')?): {condition2_status_matches}") # DEBUG REMOVED
        # print(f"DEBUG: Condition 3 (Record created_by ('{record.created_by}') == Current user ('{user}')?): {condition3_user_is_creator}") # DEBUG REMOVED
        
        # Determine if the current user can acknowledge and route this record
        record.can_acknowledge_and_route = False # Default to False
        if condition1_initial_key_exists and condition2_status_matches and condition3_user_is_creator:
            record.can_acknowledge_and_route = True
        
        # Determine if the current user can submit the Notice of PCI
        record.can_submit_notice_pci = False
        if len(CASE_WORKFLOW_STEPS) > 1 and \
           record.status == CASE_WORKFLOW_STEPS[1].key and \
           record.assigned_to == user: # Assuming index 1 is 'notice_pci'
            record.can_submit_notice_pci = True

        # print(f"DEBUG: Result -> record.can_acknowledge_and_route: {record.can_acknowledge_and_route}") # DEBUG REMOVED
        # print(f"--- END DEBUG Record ID: {record.id} ---\n") # DEBUG REMOVED
        # --- END DETAILED DEBUGGING ---
        processed_records.append(record)
    
    # --- Calculate Summary Card Data ---
    total_ier_count = records_qs.count()
    completed_ier_count = records_qs.filter(status='resolved').count() # Assuming 'resolved' is your final completed status
    
    # Active tasks: assigned to the user and not yet resolved
    active_tasks_count = records_qs.filter(assigned_to=user).exclude(status='resolved').count()
    
    # Pending requests: created by the user and in the initial state, awaiting routing
    pending_routing_count = 0
    if initial_status_key: # Ensure initial_status_key is available
        pending_routing_count = records_qs.filter(created_by=user, status=initial_status_key).count()

    context = {
        'records': processed_records,
        'current_date': today, # Add today's date to the context
        'total_ier_count': total_ier_count,
        'completed_ier_count': completed_ier_count,
        'active_tasks_count': active_tasks_count,
        'pending_routing_count': pending_routing_count,
    }

    return render(request, 'sdcmisapp/dashboard.html', context=context) 

# create record

@login_required(login_url='login')

def  iec_addrecord(request):
    record_created_successfully = False
    new_record_ref = None
    form = IEC_AddForm()
    
    if request.method == "POST":

        form = IEC_AddForm(request.POST)

        if form.is_valid():

            record = form.save(commit=False) # Don't save to DB yet
            record.created_by = request.user
            record.assigned_to = request.user # Initially assign to the creator for the first step

            initial_status_key = get_initial_status_key()
            if initial_status_key:
                record.status = initial_status_key
                initial_step_config = get_task_step_by_key(initial_status_key)
                if initial_step_config and record.date_received:
                    record.due_date = record.date_received + timedelta(days=initial_step_config.days_to_complete)
                elif record.date_received: # Fallback if step details not found (should ideally not happen)
                    # Consider logging a warning here
                    record.due_date = record.date_received + timedelta(days=2) # Original fallback
            else:
                # This case should ideally be prevented by ensuring CASE_WORKFLOW_STEPS is not empty
                messages.error(request, "Workflow is not configured correctly (no initial step).")
                # record.status will use model default, or handle as error

            record.save() # Now save with all fields
            
            messages.success(request, f"Record '{record.iec_ref}' has been created.") # General message for base.html
            record_created_successfully = True
            new_record_ref = record.iec_ref
            form = IEC_AddForm() # Clear the form for the success page or next entry
        
    context = {
        'form': form,
        'record_created_successfully': record_created_successfully,
        'new_record_ref': new_record_ref
    }
    return render(request, 'sdcmisapp/create-iec.html', context=context)  


# update record

@login_required(login_url='login')

def update_iec(request,pk):

    record = iec_records.objects.get(id=pk)

    form = IEC_UpdateForm(instance=record)
    
    if request.method == "POST":

        form = IEC_UpdateForm(request.POST, instance=record)

        if form.is_valid():

            form.save()

            messages.success(request, "Record Updated")

            return redirect('dashboard')
        
    context = {'form': form}

    return render(request, 'sdcmisapp/update_iec.html', context=context)



# read view single record

@login_required(login_url='login')

def view_iec(request,pk):

    all_records = iec_records.objects.get(id=pk)

    context = {'iec_records': all_records}

    return render(request, 'sdcmisapp/view_iec.html', context=context)


# Delete record

@login_required(login_url='login')

def delete_iec(request,pk):
    
   record = iec_records.objects.get(id=pk)

   record.delete()

   return redirect('dashboard')


# defining the steps

@login_required(login_url='login')
def acknowledge_and_route(request, pk):
    record = get_object_or_404(iec_records, id=pk)
    user = request.user
    initial_status_key = get_initial_status_key()

    # --- Authorization and State Check ---
    if record.created_by != user:
        messages.error(request, "Only the creator of the record can perform this initial routing.")
        return redirect('dashboard')

    if not initial_status_key: # Should not happen if workflow is configured
        messages.error(request, "Workflow initial step is not configured. Cannot proceed.")
        return redirect('dashboard')
        
    if record.status != initial_status_key:
        current_status_display = record.get_status_display()
        expected_initial_step = get_task_step_by_key(initial_status_key)
        expected_status_display = expected_initial_step.description if expected_initial_step else "the initial state"
        messages.error(request, f"Record {record.iec_ref} (current status: '{current_status_display}') is not in the expected state ('{expected_status_display}') for this routing action.")
        return redirect('dashboard')

    # --- Determine eligible users for routing ---
    # Eligible users are active, in the same location as the current user (creator), with specific roles, excluding the current user.
    user_location = user.location if hasattr(user, 'location') else None
    eligible_roles = ['ier_inv', 'pci_inv'] # Define the roles for routing
    eligible_users_qs = CustomUser.objects.none()
    if user_location:
        eligible_users_qs = CustomUser.objects.filter(
            Q(role__in=eligible_roles), # Filter by specified roles
            is_active=True,
            location=user_location
        ).exclude(pk=user.pk).order_by('username')

    if request.method == "POST":
        form = RouteTaskForm(request.POST, eligible_users_queryset=eligible_users_qs)
        if form.is_valid():
            # Status check already done above.
            if len(CASE_WORKFLOW_STEPS) > 1:
                next_workflow_step = CASE_WORKFLOW_STEPS[1] # The step after initial (index 1)

                # Create the InitialEvaluationReport instance
                try:
                    InitialEvaluationReport.objects.create(
                        iec_record=record,
                        submitted_by=request.user,
                        # submitted_on is auto_now_add
                        director_approval_date=form.cleaned_data.get('director_approval_date'),
                        remarks=form.cleaned_data.get('submission_remarks')
                    )
                except Exception as e: # Catch potential integrity errors if trying to create a duplicate for OneToOneField
                    # This might also catch if iec_record already has an IER.
                    # Consider using get_or_create or updating if exists, if that's the desired behavior.
                    # For OneToOne, create should typically only happen once.
                    existing_ier = InitialEvaluationReport.objects.filter(iec_record=record).first()
                    if existing_ier:
                         messages.warning(request, f"Initial Evaluation Report for {record.iec_ref} already exists. Proceeding with routing.")
                    else:
                        messages.error(request, f"Could not save Initial Evaluation Report details. Error: {e}")
                        return redirect('dashboard') # Or back to the form

                # If transitioning to a PCI step, ensure PreChargeInvestigation record exists
                if next_workflow_step.key == CASE_WORKFLOW_STEPS[1].key: # 'notice_pci'
                    pci_obj, created = PreChargeInvestigation.objects.get_or_create(
                        iec_record=record
                        # You can add defaults here if other fields in PreChargeInvestigation
                        # need specific values upon creation, e.g.,
                        # defaults={'some_other_field': 'initial_value'}
                    )
                    # Defaults for precharge_no etc., will be handled by model or later forms
                    # --- DEBUG: Confirm PreChargeInvestigation creation/retrieval ---
                    # print(f"DEBUG (acknowledge_and_route): PreChargeInvestigation for IEC ID {record.id} (iec_ref: {record.iec_ref}): {'Created' if created else 'Retrieved'}.")
                    # print(f"DEBUG (acknowledge_and_route): PCI Object details: PK={pci_obj.pk if pci_obj else 'N/A'}, iec_record_id={pci_obj.iec_record_id if pci_obj else 'N/A'}, precharge_no='{pci_obj.precharge_no if pci_obj else 'N/A'}'")
                    # --- END DEBUG ---

                
                # Existing logic for routing the iec_record
                next_assignee = form.cleaned_data['assign_to']
                record.status = next_workflow_step.key
                record.assigned_to = next_assignee
                record.due_date = date.today() + timedelta(days=next_workflow_step.days_to_complete)
                record.save()

                # --- DEBUG: Confirm state after save in acknowledge_and_route ---
                # print(f"DEBUG (acknowledge_and_route): IEC Record {record.iec_ref} saved. Status: {record.status}, Assigned To: {record.assigned_to.username if record.assigned_to else 'N/A'}")
                # --- END DEBUG ---

                messages.success(request, f"Initial Evaluation Report for {record.iec_ref} submitted and task routed to {next_assignee.username} for '{next_workflow_step.description}'.")
                return redirect('dashboard')
            else:
                messages.error(request, f"No subsequent step defined in the workflow to route record {record.iec_ref} to.")
                return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
            # eligible_users_exist will be set before rendering
            # Fall through to render template with form errors
    else: # GET request
        form = RouteTaskForm(eligible_users_queryset=eligible_users_qs)

    eligible_users_exist = eligible_users_qs.exists()
    if request.method == 'GET' and not eligible_users_exist: # Show warning only on initial load if no users
        messages.warning(request, "There are no other active IER or PCI Investigators in your location to route this task to.")

    context = {
        'record': record,
        'form': form,
        'eligible_users_exist': eligible_users_exist
    }
    return render(request, 'sdcmisapp/acknowledge_route_confirm.html', context)


@login_required(login_url='login')
def submit_notice_pci(request, pk):
    iec_record = get_object_or_404(iec_records, id=pk)
    user = request.user

    # --- DEBUG: State check at start of submit_notice_pci ---
    # print(f"DEBUG (submit_notice_pci): Checking Record {iec_record.iec_ref} (ID: {pk})")
    # print(f"DEBUG (submit_notice_pci): IEC Current Status: {iec_record.status}, IEC Assigned To: {iec_record.assigned_to.username if iec_record.assigned_to else 'N/A'}")
    # --- END DEBUG ---

    try:
        pci_record = PreChargeInvestigation.objects.get(iec_record=iec_record)
    except PreChargeInvestigation.DoesNotExist:
        messages.error(request, f"Pre-Charge Investigation details not found for {iec_record.iec_ref}. This record should have been created when the case was assigned for PCI. Please contact admin.")
        return redirect('view_iec', pk=iec_record.id)

    # Expected status for this action: 'notice_pci' (index 1 of CASE_WORKFLOW_STEPS)
    expected_status_key = CASE_WORKFLOW_STEPS[1].key if len(CASE_WORKFLOW_STEPS) > 1 else None
    current_step_config = get_task_step_by_key(expected_status_key) if expected_status_key else None

    if not current_step_config:
        messages.error(request, "Workflow 'Notice of PCI' step is not configured. Cannot proceed.")
        return redirect('view_iec', pk=iec_record.id)

    # --- DEBUG: Check if PCI record was found ---
    # print(f"DEBUG (submit_notice_pci): PreChargeInvestigation record found in DB: {pci_record is not None}. PCI PK: {pci_record.pk if pci_record else 'N/A'}")
    # --- END DEBUG ---

    if iec_record.status != expected_status_key:
        # print(f"DEBUG (submit_notice_pci): IEC Status check failed. Expected: '{expected_status_key}', Got: '{iec_record.status}'")
        messages.error(request, f"Record {iec_record.iec_ref} (current status: '{iec_record.get_status_display()}') is not in the expected state ('{current_step_config.description}') for submitting the Notice of PCI.")
        return redirect('view_iec', pk=iec_record.id)

    if iec_record.assigned_to != user:
        # print(f"DEBUG (submit_notice_pci): IEC Assignment check failed. Expected: '{user.username}', Got: '{iec_record.assigned_to.username if iec_record.assigned_to else 'N/A'}'")
        messages.error(request, f"This task ('{current_step_config.description}') for {iec_record.iec_ref} is not assigned to you. It is assigned to {iec_record.assigned_to.username if iec_record.assigned_to else 'N/A'}.")
        return redirect('view_iec', pk=iec_record.id)

    if request.method == "POST":
        form = NoticePCISubmissionForm(request.POST, instance=pci_record)
        if form.is_valid():
            updated_pci_record = form.save(commit=False)
            updated_pci_record.notice_pci_submitted_by = user
            updated_pci_record.notice_pci_submitted_on = date.today() # System date of submission
            # precharge_no is handled by the form if it's editable.
            updated_pci_record.save()

            # Transition to the next step: 'comment_counter_affidavit' (index 2)
            if len(CASE_WORKFLOW_STEPS) > 2:
                next_workflow_step = CASE_WORKFLOW_STEPS[2]
                iec_record.status = next_workflow_step.key
                # Due date for the next step. Assigned_to likely remains the same PCI investigator.
                if updated_pci_record.notice_pci_respondent_received_on:
                    # Base due date on when respondent received notice, if available
                    iec_record.due_date = updated_pci_record.notice_pci_respondent_received_on + timedelta(days=next_workflow_step.days_to_complete)
                else:
                    # Fallback to today if respondent received date is not set
                    iec_record.due_date = date.today() + timedelta(days=next_workflow_step.days_to_complete)
                
                # iec_record.assigned_to remains the same for now for the PCI investigator.
                iec_record.save()
                messages.success(request, f"Notice of Pre-Charge Investigation for {iec_record.iec_ref} submitted. Case moved to '{next_workflow_step.description}'.")
                return redirect('view_iec', pk=iec_record.id)
            else:
                messages.error(request, "Workflow next step ('Comment/Counter Affidavit') is not configured.")
                return redirect('view_iec', pk=iec_record.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else: # GET request
        form = NoticePCISubmissionForm(instance=pci_record)

    context = {
        'form': form,
        'iec_record': iec_record,
        'pci_record': pci_record,
        'current_step_description': current_step_config.description
    }
    return render(request, 'sdcmisapp/submit_notice_pci.html', context)
