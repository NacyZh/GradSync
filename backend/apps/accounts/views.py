from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.middleware.csrf import get_token
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.permissions import IsAdministrator

from .locale_services import get_locale, set_locale
from .models import User
from .serializers import (
    AccountCreateSerializer,
    AccountUpdateSerializer,
    EmailVerificationSerializer,
    LocalePreferenceSerializer,
    LoginSerializer,
    NicknameUpdateSerializer,
    RegistrationSerializer,
    RoleActivationSerializer,
    RoleActivationUpdateSerializer,
    StudentOptionSerializer,
    UserSerializer,
)
from .models import RoleActivationRequest
from .services import (
    AccountsService,
    decide_role_activation,
    register_account,
    update_nickname,
    verify_email,
)


class LoginView(APIView):
    """Authenticate by email/password and establish a cookie session."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        get_token(request)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    """Clear the current session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = NicknameUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = update_nickname(user=request.user, nickname=serializer.validated_data["nickname"])
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(user).data)


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, _code = register_account(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
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

    def get(self, request):
        return Response({"locale": get_locale(request.user), "updatedAt": request.user.date_joined})

    def put(self, request):
        serializer = LocalePreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            locale = set_locale(request.user, serializer.validated_data["locale"])
        except ValidationError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"locale": locale, "updatedAt": request.user.date_joined})


# ── Admin account management ──


class AccountListCreateView(generics.ListCreateAPIView):
    """List all accounts (paginated) or create a new advisor/student account."""

    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = User.objects.order_by("-date_joined")
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AccountCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        try:
            user = AccountsService.create_account(
                email=serializer.validated_data["email"],
                name=serializer.validated_data["name"],
                global_role=serializer.validated_data["global_role"],
                created_by=self.request.user,
            )
        except ValidationError as e:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            raise DRFValidationError({"message": str(e)}) from e
        # Return the created user data.
        serializer._user = user

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(UserSerializer(serializer._user).data, status=status.HTTP_201_CREATED)


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
