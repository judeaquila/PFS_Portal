from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from .forms import LoginForm, RegistrationForm, AmbassadorRegistrationForm, ConsultantRegistrationForm, CustomPasswordResetForm, CustomSetPasswordForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from payments.models import Payment
from common.decorators import anonymous_required
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode



User = get_user_model()

@anonymous_required
def register_view(request):
    """
    Handles user registration for paid users.
    Enforces that a valid payment session exists prior to account creation.
    """
    if request.user.is_authenticated:
        return redirect("dashboard:redirect-dashboard")

    # Enforce access restriction via session payment reference
    payment_ref = request.session.get("paid_payment_ref")

    if not payment_ref:
        messages.error(
            request,
            "Access restricted. Please select a service package and complete payment to register.",
        )
        return redirect("core:pricing")

    # Retrieve verified payment record awaiting account link
    payment = Payment.objects.filter(
        ref=payment_ref, verified=True, user__isnull=True
    ).first()

    if not payment:
        # If session holds an invalid or already linked payment
        request.session.pop("paid_payment_ref", None)
        messages.error(
            request, "Invalid or expired payment link. Please select a package."
        )
        return redirect("core:pricing")

    # Handle Form Submission
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Link payment record to newly created user
            payment.user = user
            payment.save()

            # Clean up session
            request.session.pop("paid_payment_ref", None)

            # Auto log-in new user
            login(request, user, backend="accounts.backends.EmailBackend")
            messages.success(
                request, "Account created successfully! Welcome to your portal."
            )
            return redirect("dashboard:redirect-dashboard")
    else:
        # Pre-fill email and business name from payment record
        form = RegistrationForm(
            initial={
                "email": payment.email,
                "business_name": payment.business_name,
            }
        )

    if payment:
        for field in ["email", "business_name"]:
            form.fields[field].widget.attrs["readonly"] = True
            existing_css = form.fields[field].widget.attrs.get("class", "")
            form.fields[field].widget.attrs["class"] = f"{existing_css} bg-slate-100 text-slate-500 cursor-not-allowed"

    context = {
        "form": form,
        "payment": payment,
    }

    return render(request, "registration/register.html", context)


@anonymous_required
def login_view(request):
    """
    Handles secure client and staff login using the custom LoginForm.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:redirect-dashboard')

    error_message = None

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Retrieve the authenticated user attached during form cleaning
            user = form.cleaned_data.get('user')
            login(request, user, backend='accounts.backends.EmailBackend')
            next_url = request.GET.get('next') or 'dashboard:redirect-dashboard'
            return redirect(next_url)
        else:
            # Safely grab the validation error string
            error_message = form.non_field_errors().as_text() or "Invalid email or password."
    else:
        form = LoginForm()

    context = {
        "form": form,
        "error_message": error_message,
    }

    return render(request, "registration/login.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Logs out the user and safely drops them back at the home landing page.
    """
    logout(request)
    return redirect("core:home")


@anonymous_required
def ambassador_register(request):
    """
    Handles Ambassador registration. Automatically enforces the 'AMBASSADOR' role
    and redirects to the appropriate dashboard workspace.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:ambassador-dashboard')

    if request.method == 'POST':
        form = AmbassadorRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmailBackend')
            return redirect('dashboard:ambassador-dashboard')
    else:
        form = AmbassadorRegistrationForm()

    context = {
        "form": form,
    }

    return render(request, 'registration/ambassador_register.html', context)


@anonymous_required
def consultant_register(request):
    """
    Handles Consultant registration. Automatically maps the secure 
    CONSULTANT role via the model form save architecture.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:consultant-dashboard')

    if request.method == 'POST':
        form = ConsultantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            login(request, user, backend='accounts.backends.EmailBackend')
            return redirect('dashboard:consultant-dashboard')
    else:
        form = ConsultantRegistrationForm()

    return render(request, 'registration/consultant_register.html', {"form": form})



@anonymous_required
def password_reset_request_view(request):
    """Handles the initial password reset email request."""
    if request.method == "POST":
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="accounts/password_reset_email.html",
                subject_template_name="accounts/password_reset_subject.txt",
                from_email=None,
                extra_email_context={"extra_url_name": "accounts:password_reset_confirm"},
            )
            return redirect("accounts:password_reset_done")
    else:
        form = CustomPasswordResetForm()

    return render(request, "accounts/password_reset_form.html", {"form": form})


@anonymous_required
def password_reset_done_view(request):
    """Displays confirmation that a password reset email was dispatched."""
    return render(request, "accounts/password_reset_done.html")


@anonymous_required
def password_reset_confirm_view(request, uidb64, token):
    """Validates the reset token and accepts the new password."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        if request.method == "POST":
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect("accounts:password_reset_complete")
        else:
            form = CustomSetPasswordForm(user)
    else:
        validlink = False
        form = None

    context = {
        "form": form,
        "validlink": validlink,
    }
    return render(request, "accounts/password_reset_confirm.html", context)


@anonymous_required
def password_reset_complete_view(request):
    """Informs the user that their password reset was successful."""
    return render(request, "accounts/password_reset_complete.html")