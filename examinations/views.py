import random
import csv
import io
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import Question, ExamAttempt, QuestionCategory, Exam
from .forms import QuestionForm, SupervisorQuestionForm, ExamForm
from common.decorators import role_required
from accounts.models import UserRole


# ---------------------------------------------------------------------------------------- #
# -------------------------------- SUPERADMIN DASHBOARD ---------------------------------- #
# ---------------------------------------------------------------------------------------- #

@login_required
@role_required([UserRole.SUPER_ADMIN])
def question_list(request):
    category_filter = request.GET.get('category', '')
    questions = Question.objects.select_related('created_by', 'exam').all()

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

    context = {'question': question}
    return render(request, 'examinations/superadmin_question_confirm_delete.html', context)


@login_required
@role_required([UserRole.SUPER_ADMIN])
def question_bulk_upload(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid .csv file.")
            return redirect('examination:question_bulk_upload')

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
        except Exception as e:
            messages.error(request, f"Error reading file: {str(e)}")
            return redirect('examination:question_bulk_upload')

        valid_categories = dict(QuestionCategory.choices)
        valid_options = dict(Question.OPTION_CHOICES)

        questions_to_create = []
        errors = []

        for row_idx, row in enumerate(reader, start=2):
            category = row.get('category', '').strip()
            text = row.get('text', '').strip()
            option_a = row.get('option_a', '').strip()
            option_b = row.get('option_b', '').strip()
            option_c = row.get('option_c', '').strip()
            option_d = row.get('option_d', '').strip()
            correct_answer = row.get('correct_answer', '').strip().upper()

            if not all([category, text, option_a, option_b, option_c, option_d, correct_answer]):
                errors.append(f"Row {row_idx}: Missing required fields.")
                continue

            if category not in valid_categories:
                errors.append(f"Row {row_idx}: Invalid category '{category}'.")
                continue

            if correct_answer not in valid_options:
                errors.append(f"Row {row_idx}: Invalid correct answer '{correct_answer}'. Must be A, B, C, or D.")
                continue

            questions_to_create.append(Question(
                category=category,
                text=text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer,
                created_by=request.user,
                is_active=True
            ))

        if questions_to_create:
            Question.objects.bulk_create(questions_to_create)
            messages.success(request, f"Successfully imported {len(questions_to_create)} question(s)!")

        if errors:
            for err in errors[:5]:
                messages.warning(request, err)
            if len(errors) > 5:
                messages.warning(request, f"...and {len(errors) - 5} more errors.")

        return redirect('examination:question_list')

    return render(request, 'examinations/superadmin_question_bulk_upload.html')


@login_required
@role_required([UserRole.SUPER_ADMIN, UserRole.SUPERVISOR])
def download_sample_question_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="question_import_sample.csv"'

    writer = csv.writer(response)
    writer.writerow(['category', 'text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'])
    writer.writerow([
        'COMPANY_KNOWLEDGE', 
        'What year was PFS founded?', 
        '2010', '2015', '2018', '2020', 
        'B'
    ])
    return response


# ---------------------------------------------------------------------------------------- #
# -------------------------------- SUPERVISOR DASHBOARD ---------------------------------- #
# ---------------------------------------------------------------------------------------- #

@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_exam_list(request):
    exams = Exam.objects.prefetch_related('questions').all()

    context = {
        'exams': exams,
    }
    return render(request, 'examinations/supervisor_exam_list.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_exam_create(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            messages.success(request, f'Exam "{exam.title}" created successfully!')
            return redirect('examination:supervisor_exam_list')
    else:
        form = ExamForm()

    context = {
        'form': form,
        'title': 'Create Exam',
    }
    return render(request, 'examinations/supervisor_exam_form.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_exam_toggle_lock(request, exam_id):
    """Toggle the lock state of an exam."""
    if request.method == 'POST':
        exam = get_object_or_404(Exam, pk=exam_id)
        exam.is_active = not exam.is_active
        exam.save()

        status = "locked" if exam.is_active else "unlocked"
        messages.success(request, f'Exam "{exam.title}" has been successfully {status}.')
    
    redirect_url = request.META.get('HTTP_REFERER', 'examination:supervisor_exam_list')
    return redirect(redirect_url)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_list(request):
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        exam_id = request.POST.get('exam_id')
        
        question = get_object_or_404(Question, pk=question_id)
        
        if exam_id:
            exam = get_object_or_404(Exam, pk=exam_id)
            question.exam = exam
            messages.success(request, f'Question assigned to exam "{exam.title}".')
        else:
            question.exam = None
            messages.info(request, 'Question unassigned from exam.')
            
        question.save()
        
        redirect_url = request.META.get('HTTP_REFERER', 'examination:supervisor_question_list')
        return redirect(redirect_url)

    # Filtering Logic
    category_filter = request.GET.get('category', '')
    exam_filter = request.GET.get('exam', '')

    questions = Question.objects.select_related('created_by', 'exam').all().order_by('-created_at')

    if category_filter:
        questions = questions.filter(category=category_filter)
    if exam_filter:
        if exam_filter == 'unassigned':
            questions = questions.filter(exam__isnull=True)
        else:
            questions = questions.filter(exam_id=exam_filter)

    paginator = Paginator(questions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    all_exams = Exam.objects.all().order_by('title')

    context = {
        'page_obj': page_obj,
        'categories': QuestionCategory.choices,
        'exams': all_exams,
        'selected_category': category_filter,
        'selected_exam': exam_filter,
    }
    return render(request, 'examinations/supervisor_question_list.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_exam_question_list(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id)
    questions = exam.questions.select_related('created_by').all().order_by('-created_at')

    context = {
        'exam': exam,
        'questions': questions,
    }
    return render(request, 'examinations/supervisor_exam_question_list.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_general_question_create(request):
    """Creates a question directly into the global pool without binding to a specific exam."""
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
        'title': 'Add Question to Bank',
    }
    return render(request, 'examinations/supervisor_question_form.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_create(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id)

    if request.method == 'POST':
        form = SupervisorQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.created_by = request.user
            question.save()
            messages.success(request, f'Question added successfully to "{exam.title}".')
            return redirect('examination:supervisor_exam_question_list', exam_id=exam.id)
    else:
        form = SupervisorQuestionForm()

    context = {
        'form': form,
        'exam': exam,
        'title': f'Add Question to "{exam.title}"',
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

    context = {'question': question}
    return render(request, 'examinations/supervisor_question_confirm_delete.html', context)


@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_question_bulk_upload(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id)

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid .csv file.")
            return redirect('examination:supervisor_question_bulk_upload', exam_id=exam.id)

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            reader = csv.DictReader(io_string)
        except Exception as e:
            messages.error(request, f"Error reading file: {str(e)}")
            return redirect('examination:supervisor_question_bulk_upload', exam_id=exam.id)

        valid_categories = dict(QuestionCategory.choices)
        valid_options = dict(Question.OPTION_CHOICES)

        questions_to_create = []
        errors = []

        for row_idx, row in enumerate(reader, start=2):
            category = row.get('category', '').strip()
            text = row.get('text', '').strip()
            option_a = row.get('option_a', '').strip()
            option_b = row.get('option_b', '').strip()
            option_c = row.get('option_c', '').strip()
            option_d = row.get('option_d', '').strip()
            correct_answer = row.get('correct_answer', '').strip().upper()

            if not all([category, text, option_a, option_b, option_c, option_d, correct_answer]):
                errors.append(f"Row {row_idx}: Missing required fields.")
                continue

            if category not in valid_categories:
                errors.append(f"Row {row_idx}: Invalid category '{category}'.")
                continue

            if correct_answer not in valid_options:
                errors.append(f"Row {row_idx}: Invalid correct answer '{correct_answer}'. Must be A, B, C, or D.")
                continue

            questions_to_create.append(Question(
                exam=exam,
                category=category,
                text=text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer,
                created_by=request.user,
                is_active=True
            ))

        if questions_to_create:
            Question.objects.bulk_create(questions_to_create)
            messages.success(request, f"Successfully imported {len(questions_to_create)} question(s) into '{exam.title}'!")

        if errors:
            for err in errors[:5]:
                messages.warning(request, err)
            if len(errors) > 5:
                messages.warning(request, f"...and {len(errors) - 5} more errors.")

        return redirect('examination:supervisor_exam_question_list', exam_id=exam.id)

    return render(request, 'examinations/supervisor_question_bulk_upload.html', {'exam': exam})



# ---------------------------------------------------------------------------------------- #
# -------------------------------- ASSOCIATE DASHBOARD ---------------------------------- #
# ---------------------------------------------------------------------------------------- #

@login_required
@role_required([UserRole.AMBASSADOR])
def exam_landing(request):
    exams = Exam.objects.all().prefetch_related('questions')
    
    # Get all previous attempts by this associate indexed by exam_id
    user_attempts = ExamAttempt.objects.filter(user=request.user).order_by('-attempt_date')
    
    # Process exam status metadata per exam
    exam_cards = []
    for exam in exams:
        attempts_for_exam = user_attempts.filter(exam=exam)
        latest_attempt = attempts_for_exam.first()
        
        is_locked = False
        time_remaining = None

        if latest_attempt:
            if latest_attempt.passed:
                is_locked = True
            elif latest_attempt.next_attempt_allowed_at and timezone.now() < latest_attempt.next_attempt_allowed_at:
                is_locked = True
                time_remaining = latest_attempt.next_attempt_allowed_at - timezone.now()

        exam_cards.append({
            'exam': exam,
            'latest_attempt': latest_attempt,
            'total_attempts': attempts_for_exam.count(),
            'is_locked': is_locked,
            'time_remaining': time_remaining,
            'active_questions_count': exam.questions.filter(is_active=True).count(),
        })

    context = {
        'exam_cards': exam_cards,
        'user_attempts': user_attempts,
    }
    return render(request, 'examinations/landing.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id)

    # Check whether exams is locked
    if exam.is_active:
        messages.error(request, f"'{exam.title}' is currently locked by administrators and unavailable for testing.")
        return redirect('examination:ambassador_landing')
    
    latest_attempt = ExamAttempt.objects.filter(user=request.user, exam=exam).first()

    if latest_attempt:
        if latest_attempt.passed:
            messages.info(request, f"You have already passed the '{exam.title}' examination.")
            return redirect('examination:ambassador_landing')
        if latest_attempt.next_attempt_allowed_at and timezone.now() < latest_attempt.next_attempt_allowed_at:
            messages.warning(request, "This examination is currently locked. Please wait for the cooldown period to end.")
            return redirect('examination:ambassador_landing')

    # Fetch active questions specific to THIS exam
    questions = list(exam.questions.filter(is_active=True))
    random.shuffle(questions)

    if not questions:
        messages.error(request, f"No active questions available for '{exam.title}'. Please contact support.")
        return redirect('examination:ambassador_landing')

    context = {
        'exam': exam,
        'questions': questions,
    }
    return render(request, 'examinations/take_exam.html', context)


@login_required
@role_required([UserRole.AMBASSADOR])
def submit_exam(request, exam_id):
    if request.method != 'POST':
        return redirect('examination:ambassador_landing')

    exam = get_object_or_404(Exam, pk=exam_id)

    # Re-verify if exams is locked
    if exam.is_active:
        messages.error(request, f"Submission failed: '{exam.title}' has been locked by supervisors.")
        return redirect('examination:ambassador_landing')
    
    latest_attempt = ExamAttempt.objects.filter(user=request.user, exam=exam).first()
    
    if latest_attempt and latest_attempt.is_locked:
        messages.error(request, "Submission rejected. Cooldown active for this exam.")
        return redirect('examination:ambassador_landing')

    questions = exam.questions.filter(is_active=True)
    total_questions = questions.count()
    correct_count = 0

    if total_questions == 0:
        messages.error(request, "Exam system error: No active questions were found at submission time.")
        return redirect('examination:ambassador_landing')

    for q in questions:
        selected_option = request.POST.get(f'question_{q.id}')
        if selected_option and selected_option.upper() == q.correct_answer.upper():
            correct_count += 1

    attempt = ExamAttempt.objects.create(
        user=request.user,
        exam=exam,
        total_questions=total_questions,
        correct_answers=correct_count,
    )

    if attempt.passed:
        messages.success(request, f"Congratulations! You passed '{exam.title}' with a score of {attempt.score_percentage}%!")
    else:
        messages.warning(request, f"You scored {attempt.score_percentage}% on '{exam.title}'. Retake unlocked in 5 minutes.")

    return redirect('examination:ambassador_landing')