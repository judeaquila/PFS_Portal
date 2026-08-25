import random
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Question, ExamAttempt, QuestionCategory
from .forms import QuestionForm, SupervisorQuestionForm
from common.decorators import role_required
from accounts.models import UserRole


# ---------------------------------------------------------------------------------------- #
# -------------------------------- SUPERADMIN DASHBOARD ---------------------------------- #
# ---------------------------------------------------------------------------------------- #
@login_required
@role_required([UserRole.SUPER_ADMIN])
def question_list(request):
    category_filter = request.GET.get('category', '')
        
    # Pre-fetch creator to avoid N+1 queries in the template
    questions = Question.objects.select_related('created_by').all()

    if category_filter:
        questions = questions.filter(category=category_filter)

    paginator = Paginator(questions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': QuestionCategory.choices,
        'selected_category': category_filter,
    }
    return render(request, 'examinations/superadmin_question_list.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def question_create(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            messages.success(request, 'Question added successfully.')
            return redirect('examination:question_list')
    else:
        form = QuestionForm()

    context = {
        'form': form,
        'title': 'Create Question',
    }

    return render(request, 'examinations/superadmin_question_form.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def question_update(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated successfully.')
            return redirect('examination:question_list')
    else:
        form = QuestionForm(instance=question)

    context = {
        'form': form,
        'title': 'Edit Question',
    }

    return render(request, 'examinations/superadmin_question_form.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted successfully.')
        return redirect('examination:question_list')

    context = {
        'question': question,
    }
    
    return render(request, 'examinations/superadmin_question_confirm_delete.html', context)



# ---------------------------------------------------------------------------------------- #
# -------------------------------- SUPERVISOR DASHBOARD ---------------------------------- #
# ---------------------------------------------------------------------------------------- #
@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_list(request):
    category_filter = request.GET.get('category', '')
    
    # Pre-fetch creator to avoid N+1 queries in the template
    questions = Question.objects.select_related('created_by').all()

    if category_filter:
        questions = questions.filter(category=category_filter)

    paginator = Paginator(questions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': QuestionCategory.choices,
        'selected_category': category_filter,
    }
    return render(request, 'examinations/supervisor_question_list.html', context)
    


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_create(request):
    if request.method == 'POST':
        form = SupervisorQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            messages.success(request, 'Question added successfully.')
            return redirect('examination:supervisor_question_list')
    else:
        form = SupervisorQuestionForm()

    context = {
        'form': form,
        'title': 'Create Question',
    }

    return render(request, 'examinations/supervisor_question_form.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_update(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        form = SupervisorQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated successfully.')
            return redirect('examination:supervisor_question_list')
    else:
        form = SupervisorQuestionForm(instance=question)

    context = {
        'form': form,
        'title': 'Edit Question',
    }

    return render(request, 'examinations/supervisor_question_form.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted successfully.')
        return redirect('examination:supervisor_question_list')

    context = {
        'question': question,
    }
    
    return render(request, 'examinations/supervisor_question_confirm_delete.html', context)



# ---------------------------------------------------------------------------------------- #
# -------------------------------- ASSOCIATE DASHBOARD ---------------------------------- #
# ---------------------------------------------------------------------------------------- #

@login_required
@role_required([UserRole.AMBASSADOR])
def exam_landing(request):
    """Landing page displaying attempt history, current status, and start button."""
    latest_attempt = ExamAttempt.objects.filter(user=request.user).first()
    attempts = ExamAttempt.objects.filter(user=request.user)

    is_locked = False
    time_remaining = None

    if latest_attempt:
        if latest_attempt.passed:
            is_locked = True
        elif latest_attempt.next_attempt_allowed_at and timezone.now() < latest_attempt.next_attempt_allowed_at:
            is_locked = True
            time_remaining = latest_attempt.next_attempt_allowed_at - timezone.now()

    context = {
        'latest_attempt': latest_attempt,
        'attempts': attempts,
        'is_locked': is_locked,
        'time_remaining': time_remaining,
    }
    return render(request, 'examinations/landing.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
def take_exam(request):
    """Renders the examination interface if not locked."""
    latest_attempt = ExamAttempt.objects.filter(user=request.user).first()

    # Lock Security Check
    if latest_attempt:
        if latest_attempt.passed:
            messages.info(request, "You have already passed the examination.")
            return redirect('examination:ambassador_landing')
        if latest_attempt.next_attempt_allowed_at and timezone.now() < latest_attempt.next_attempt_allowed_at:
            messages.warning(request, "Your examination is currently locked. Please wait for the cooldown period to end.")
            return redirect('examination:ambassador_landing')

    # Fetch active questions (shuffled for dynamic ordering)
    questions = list(Question.objects.filter(is_active=True))
    random.shuffle(questions)

    if not questions:
        messages.error(request, "No active questions available for the examination. Please contact support.")
        return redirect('examination:ambassador_landing')

    context = {
        'questions': questions,
    }

    return render(request, 'examinations/take_exam.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
def submit_exam(request):
    """Processes submitted answers, calculates total score, and applies pass/fail logic."""
    if request.method != 'POST':
        return redirect('examination:ambassador_landing')

    latest_attempt = ExamAttempt.objects.filter(user=request.user).first()
    if latest_attempt and latest_attempt.is_locked:
        messages.error(request, "Submission rejected. Your account is currently locked from taking the exam.")
        return redirect('examination:ambassador_landing')

    questions = Question.objects.filter(is_active=True)
    total_questions = questions.count()
    correct_count = 0

    if total_questions == 0:
        messages.error(request, "Exam system error: No questions were active at submission time.")
        return redirect('examination:ambassador_landing')

    for q in questions:
        selected_option = request.POST.get(f'question_{q.id}')
        if selected_option and selected_option.upper() == q.correct_answer.upper():
            correct_count += 1

    # Record the attempt
    attempt = ExamAttempt.objects.create(
        user=request.user,
        total_questions=total_questions,
        correct_answers=correct_count,
    )

    if attempt.passed:
        messages.success(request, f"Congratulations! You passed with a score of {attempt.score_percentage}%!")
    else:
        messages.warning(request, f"You scored {attempt.score_percentage}%. Passing threshold is 80%. Retake unlocked in 5 minutes.")

    return redirect('examination:ambassador_landing')