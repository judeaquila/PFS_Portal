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
        if request.user.is_authenticated:
            email = request.user.email
            # Fetch company name from past payment or user business attribute
            last_payment = Payment.objects.filter(user=request.user).last()
            business_name = (
                last_payment.business_name
                if last_payment
                else getattr(
                    request.user,
                    "business_name",
                    getattr(request.user, "business_name", ""),
                )
            )
        else:
            email = request.POST.get("email", "").strip()
            business_name = request.POST.get("business_name", "").strip()

        if not email or not business_name:
            messages.error(
                request, "Please provide both Email and Business Name."
            )
            return redirect("core:pricing")

        package, _ = AssessmentPackage.objects.get_or_create(
            package_type=package_code
        )
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

    # 1. Define package-specific redirection URLs or views
    STANDARD_BOOKING_URL = getattr(
        settings, "STANDARD_PACKAGE_BOOKING_URL", "https://calendar.app.google/uMsT9pQZG86KmfSR6"
    )

    # Helper function to evaluate standard package check
    is_standard_package = (
        payment.package and payment.package.package_type == PackageType.STANDARD
    )

    # 2. Handle already verified payment edge case
    if payment.verified:
        messages.info(request, "This payment has already been verified.")
        if request.user.is_authenticated:
            return redirect("payments:booking-success")

        # Guest user re-accessing an already verified payment link
        if is_standard_package:
            return redirect(STANDARD_BOOKING_URL)

        return redirect("accounts:register")

    # 3. Verify payment with Paystack
    paystack = Paystack()
    status, result = paystack.verify_payment(ref)

    if status and result.get("status") == "success":
        amount_paid = result.get("amount")

        if amount_paid == payment.amount_value():
            payment.verified = True

            # Flow A: User is already logged in
            if request.user.is_authenticated:
                payment.user = request.user
                payment.save()
                messages.success(
                    request, "Payment successful! Your booking is confirmed."
                )

                # If logged in standard user also goes to booking or success page:
                if is_standard_package:
                    return redirect(STANDARD_BOOKING_URL)

                return redirect("payments:booking-success")

            # Flow B: Guest User (Not Authenticated)
            payment.save()

            # Special Flow for STANDARD (GHS 200) Package
            if is_standard_package:
                messages.success(
                    request,
                    "Payment verified! Please pick a time slot for your assessment session.",
                )
                return redirect(STANDARD_BOOKING_URL)

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

    error_message = result.get("message", "Payment verification failed.")
    messages.error(request, f"Verification failed: {error_message}")
    return redirect("core:pricing")


def booking_success(request):
    payment_id = request.GET.get("payment_id") or request.resolver_match.kwargs.get(
        "payment_id"
    )
    payment = None

    if payment_id and request.user.is_authenticated:
        payment = Payment.objects.filter(
            id=payment_id, user=request.user
        ).first()

    return render(request, "core/booking_success.html", {"payment": payment})