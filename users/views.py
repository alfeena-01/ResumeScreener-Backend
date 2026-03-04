from django.shortcuts import render
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CustomUserSerializer, SignUpSerializer, LoginSerializer, JobSerializer
from .models import CustomUser, Job

# Create your views here.
class UserInfoView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CustomUserSerializer

    def get_object(self):
        return self.request.user

class SignUpView(CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = (AllowAny,)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': CustomUserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User created successfully'
        }, status=status.HTTP_201_CREATED)

class LoginView(CreateAPIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': CustomUserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

class JobListView(ListCreateAPIView):
    queryset = Job.objects.filter(is_active=True)
    serializer_class = JobSerializer
    permission_classes = (AllowAny,)
    
    def perform_create(self, serializer):
        serializer.save(hr_user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'hr':
            return super().create(request, *args, **kwargs)
        return Response({'error': 'Only HR users can post jobs'}, status=status.HTTP_403_FORBIDDEN)

class JobDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = (AllowAny,)
    
    def update(self, request, *args, **kwargs):
        job = self.get_object()
        if request.user.is_authenticated and (job.hr_user == request.user or request.user.is_staff):
            return super().update(request, *args, **kwargs)
        return Response({'error': 'You do not have permission to update this job'}, status=status.HTTP_403_FORBIDDEN)
    
    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if request.user.is_authenticated and (job.hr_user == request.user or request.user.is_staff):
            return super().destroy(request, *args, **kwargs)
        return Response({'error': 'You do not have permission to delete this job'}, status=status.HTTP_403_FORBIDDEN)
