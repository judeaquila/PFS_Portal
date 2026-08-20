from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import AssessmentPackage, PackageType, Payment
from .paystack import Paystack


def initiate_package_payment(request, package_code):
    """Initializes payment directly from pricing page without intermediate template."""
    valid_codes = [choice[0] for choice in PackageType.choices]
    if package_code not in valid_codes:
        messages.error(request, "Invalid package selection.")
        return redirect("core:pricing")

    if request.method == "POST":
        posted_business_name = request.POST.get("business_name", "").strip()

        if request.user.is_authenticated:
            email = request.user.email
            # Check last payment, then user model, then fallback to POST field
            last_payment = Payment.objects.filter(user=request.user).exclude(business_name="").last()
            business_name = (
                (last_payment.business_name if last_payment else None)
                or getattr(request.user, "business_name", None)
                or posted_business_name
            )
        else:
            email = request.POST.get("email", "").strip()
            business_name = posted_business_name

        if not email or not business_name:
            messages.error(
                request, "Please provide both Email and Business Name."
            )
            return redirect("core:pricing")

        # FIX: Query standard packages filtered by null custom fields to prevent MultipleObjectsReturned
        package = AssessmentPackage.objects.filter(
            package_type=package_code,
            custom_price__isnull=True,
            custom_title__isnull=True
        ).order_by('created_at').first()

        # If no standard package exists in the database yet, initialize it
        if not package:
            package = AssessmentPackage.objects.create(package_type=package_code)

        user = request.user if request.user.is_authenticated else None

        # Create pending payment record
        payment = Payment.objects.create(
            user=user,
            package=package,
            business_name=business_name,
            amount=package.price,
            email=email,
        )

        # Pass payment info back to pricing page so JS popup opens
        context = {
            "payment": payment,
            "paystack_pub_key": settings.PAYSTACK_PUBLIC_KEY,
            "trigger_paystack": True,
            "amount_value": payment.amount_value(),
        }
        return render(request, "core/pricing.html", context)

    return redirect("core:pricing")


def verify_payment(request, ref):
    """Verifies payment with Paystack and handles redirect flows for guest vs logged-in users."""
    payment = get_object_or_404(Payment, ref=ref)

    STANDARD_BOOKING_URL = getattr(
        settings, "STANDARD_PACKAGE_BOOKING_URL", "https://calendar.app.google/uMsT9pQZG86KmfSR6"
    )

    PROD_DEV_BOOKING_URL = getattr(
        settings, "PROD_DEV_PACKAGE_BOOKING_URL", "https://calendar.app.google/uMsT9pQZG86KmfSR6"
    )

    is_standard_package = (
        payment.package and payment.package.package_type == PackageType.STANDARD
    )

    is_prod_dev_package = (
        payment.package and payment.package.package_type == PackageType.PROD_DEV
    )

    # Handle already verified payment edge case
    if payment.verified:
        messages.info(request, "This payment has already been verified.")
        if request.user.is_authenticated:
            return redirect("payments:booking-success")

        # Guest user re-accessing an already verified payment link
        if is_standard_package:
            return redirect(STANDARD_BOOKING_URL)
        elif is_prod_dev_package:
            return redirect(PROD_DEV_BOOKING_URL)

        return redirect("accounts:register")

    # Verify payment with Paystack
    paystack = Paystack()
    status, result = paystack.verify_payment(ref)

    if status and result.get("status") == "success":
        amount_paid = result.get("amount")

        # Safely cast both sides to integer (subunits / kobo / pesewas) for comparison
        if amount_paid is not None and int(amount_paid) == int(payment.amount_value()):
            payment.verified = True

            # User is already logged in
            if request.user.is_authenticated:
                payment.user = request.user
                payment.save()
                messages.success(
                    request, "Payment successful! Please confirm your booking."
                )

                if is_standard_package:
                    return redirect(STANDARD_BOOKING_URL)
                elif is_prod_dev_package:
                    return redirect(PROD_DEV_BOOKING_URL)

                return redirect("payments:booking-success")

            # Guest User (Not Authenticated)
            payment.save()

            if is_standard_package:
                messages.success(
                    request,
                    "Payment verified! Please pick a time slot for your assessment session.",
                )
                return redirect(STANDARD_BOOKING_URL)

            if is_prod_dev_package:
                messages.success(
                    request,
                    "Payment verified! Please pick a time slot for your assessment session.",
                )
                return redirect(PROD_DEV_BOOKING_URL)

            # Standard Guest Flow for higher tier packages -> Registration
            request.session["paid_payment_ref"] = payment.ref
            messages.success(
                request,
                "Payment verified! Please complete your account setup below to access your portal.",
            )
            return redirect("accounts:register")

        else:
            messages.error(
                request, "Payment amount mismatch. Please contact support."
            )
            return redirect("core:pricing")

    error_message = result.get("message", "Payment verification failed.") if isinstance(result, dict) else "Payment verification failed."
    messages.error(request, f"Verification failed: {error_message}")
    return redirect("core:pricing")


def booking_success(request):
    payment_id = request.GET.get("payment_id") or request.resolver_match.kwargs.get(
        "payment_id"
    )
    payment = None

    if payment_id and str(payment_id).isdigit() and request.user.is_authenticated:
        payment = Payment.objects.filter(
            id=int(payment_id), user=request.user
        ).first()

    return render(request, "core/booking_success.html", {"payment": payment})