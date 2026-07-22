from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.permissions import IsAdministrator

from .locale_services import get_locale, set_locale
from .models import RoleActivationRequest, User
from .serializers import (
    AccessTokenSerializer,
    AccountUpdateSerializer,
    AuthenticatedUserSerializer,
    EmailVerificationSerializer,
    LocalePreferenceSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
    RegistrationSerializer,
    RoleActivationSerializer,
    RoleActivationUpdateSerializer,
    StudentOptionSerializer,
    UserSerializer,
    VerificationResendSerializer,
)
from .services import (
    AccountsService,
    change_password,
    decide_role_activation,
    register_account,
    resend_verification_code,
    update_profile,
    verify_email,
)
from .tokens import (
    clear_refresh_cookie,
    issue_token_pair,
    refresh_cookie,
    revoke_refresh_token,
    rotate_refresh_token,
    set_refresh_cookie,
)


class LoginView(APIView):
    """Authenticate and establish both a session and a refreshable access token."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: AuthenticatedUserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        get_token(request)
        token_payload, refresh = issue_token_pair(user)
        response = Response({**UserSerializer(user).data, **token_payload})
        set_refresh_cookie(response, refresh)
        response["Cache-Control"] = "no-store"
        return response


class LogoutView(APIView):
    """Clear the current session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: OpenApiResponse(description="Logged out")})
    def post(self, request):
        revoke_refresh_token(refresh_cookie(request))
        logout(request)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        response["Cache-Control"] = "no-store"
        return response


@method_decorator(csrf_protect, name="dispatch")
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=None,
        responses={
            200: AccessTokenSerializer,
            401: OpenApiResponse(description="Refresh token invalid or expired"),
        },
    )
    def post(self, request):
        raw_refresh = refresh_cookie(request)
        if not raw_refresh:
            return Response(
                {"message": "Refresh token is required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            token_payload, replacement = rotate_refresh_token(raw_refresh)
        except AuthenticationFailed as exc:
            return Response({"message": str(exc.detail)}, status=status.HTTP_401_UNAUTHORIZED)
        response = Response(token_payload)
        set_refresh_cookie(response, replacement)
        response["Cache-Control"] = "no-store"
        return response


@method_decorator(csrf_protect, name="dispatch")
class TokenRevokeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses={204: OpenApiResponse(description="Token revoked")})
    def post(self, request):
        revoke_refresh_token(refresh_cookie(request))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        response["Cache-Control"] = "no-store"
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(request=ProfileUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = update_profile(
                user=request.user,
                name=serializer.validated_data["name"],
                nickname=serializer.validated_data["nickname"],
                degree_type=serializer.validated_data.get("degreeType"),
            )
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(user).data)


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegistrationSerializer,
        responses={
            202: OpenApiResponse(description="Registration accepted"),
            422: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, _code = register_account(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                name=serializer.validated_data["name"],
                nickname=serializer.validated_data["nickname"],
                requested_role=serializer.validated_data["requestedRole"],
                degree_type=serializer.validated_data.get("degreeType"),
            )
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"email": user.email, "status": user.status, "requestedRole": user.requested_role},
            status=status.HTTP_202_ACCEPTED,
        )


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={200: UserSerializer, 422: OpenApiResponse(description="Validation error")},
    )
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_email(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
            )
        except (ValidationError, User.DoesNotExist) as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(user).data)


class VerificationResendView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration"

    @extend_schema(
        request=VerificationResendSerializer,
        responses={202: OpenApiResponse(description="Verification email queued")},
    )
    def post(self, request):
        serializer = VerificationResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resend_verification_code(email=serializer.validated_data["email"])
        return Response(
            {"message": "If the account is awaiting verification, a new code has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={204: OpenApiResponse(description="Password changed")},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = change_password(
                user=request.user,
                current_password=serializer.validated_data["currentPassword"],
                new_password=serializer.validated_data["newPassword"],
            )
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        update_session_auth_hash(request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleActivationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdministrator]
    serializer_class = RoleActivationSerializer

    def get_queryset(self):
        return RoleActivationRequest.objects.select_related("user").order_by("-created_at")


class RoleActivationDetailView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = RoleActivationRequest.objects.select_related("user")
    serializer_class = RoleActivationSerializer
    lookup_url_kwarg = "pk"

    def patch(self, request, *args, **kwargs):
        serializer = RoleActivationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            activation = decide_role_activation(
                activation=self.get_object(),
                reviewer=request.user,
                action=serializer.validated_data["action"],
            )
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RoleActivationSerializer(activation).data)


class StudentSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentOptionSerializer
    pagination_class = None

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY),
            OpenApiParameter("projectId", int, OpenApiParameter.QUERY),
        ],
        responses={
            200: StudentOptionSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["project_id"] = self.request.query_params.get("projectId")
        return context

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        queryset = User.objects.filter(
            global_role=User.GlobalRole.STUDENT,
            status=User.Status.ACTIVE,
            active_role="student",
        ).select_related("student_profile")
        if query:
            queryset = queryset.filter(Q(nickname__icontains=query) | Q(email__icontains=query))
        return queryset.order_by("nickname", "email")[:25]


class LocalePreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: LocalePreferenceSerializer})
    def get(self, request):
        return Response({"locale": get_locale(request.user), "updatedAt": request.user.date_joined})

    @extend_schema(request=LocalePreferenceSerializer, responses={200: LocalePreferenceSerializer})
    def put(self, request):
        serializer = LocalePreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            locale = set_locale(request.user, serializer.validated_data["locale"])
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"locale": locale, "updatedAt": request.user.date_joined})


# ── Admin account management ──


class AccountListView(generics.ListAPIView):
    """List accounts for governance; account creation is self-service."""

    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = User.objects.order_by("-date_joined")
    serializer_class = UserSerializer


class AccountDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve, update, suspend, reactivate, or archive a single account."""

    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return AccountUpdateSerializer
        return UserSerializer

    def perform_update(self, serializer):
        try:
            AccountsService.edit_account(
                user=self.get_object(),
                name=serializer.validated_data.get("name"),
                global_role=serializer.validated_data.get("global_role"),
            )
        except ValidationError as e:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"message": str(e)}) from e

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(UserSerializer(self.get_object()).data)

    def post(self, request, pk=None):
        """Dispatch action: suspend, reactivate, or archive."""
        instance = self.get_object()
        action = request.data.get("action")
        try:
            if action == "suspend":
                AccountsService.suspend_account(user=instance, actor=request.user)
            elif action == "reactivate":
                AccountsService.reactivate_account(user=instance)
            elif action == "archive":
                AccountsService.archive_account(user=instance, actor=request.user)
            else:
                return Response(
                    {"message": "Invalid action. Use suspend, reactivate, or archive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValidationError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(instance).data)
