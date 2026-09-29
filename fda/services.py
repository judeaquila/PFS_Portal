def evaluate_project_stages_for_role(project_tracker, user_role):
    """
    Evaluates stages in sequential order.
    Returns active stages assigned to the user, and prior completed stages (marked as DONE).
    """
    activities = project_tracker.stage_activities.select_related('stage').order_by('stage__stage_percentage')
    
    chain_unlocked = True  # Stage 1 (5%) starts unlocked
    active_tasks = []
    completed_tasks = []

    for activity in activities:
        assigned_role = activity.stage.assigned_role # e.g. ASSOCIATE_1, ASSOCIATE_2
        is_user_role = (assigned_role == user_role or user_role in ['SUPERVISOR', 'SUPER_ADMIN'])

        if activity.status == 'COMPLETE':
            if is_user_role:
                completed_tasks.append({
                    'tracker': project_tracker,
                    'activity': activity,
                    'status_label': 'DONE',
                    'is_actionable': False
                })
            # Prior stage complete -> Next stage in sequence is allowed to unlock
            chain_unlocked = True

        elif chain_unlocked:
            # First incomplete stage in sequence becomes ACTIVE
            if is_user_role:
                active_tasks.append({
                    'tracker': project_tracker,
                    'activity': activity,
                    'status_label': 'ACTION REQUIRED',
                    'is_actionable': True
                })
            # Lock all downstream stages until this one is marked COMPLETE
            chain_unlocked = False

        else:
            # Stage is downstream and locked
            chain_unlocked = False

    return active_tasks, completed_tasks