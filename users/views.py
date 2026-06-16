from django.shortcuts import render
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from .serializers import CustomUserSerializer, SignUpSerializer, LoginSerializer, JobSerializer, ResumeSerializer, JobApplicationSerializer, NotificationSerializer
from .models import CustomUser, Job, Resume, JobApplication, Notification
from .utils import send_application_confirmation_email, send_status_update_email, extract_text_from_pdf, calculate_match_score, generate_job_description


class IsHRUserOrReadOnly(BasePermission):
    """
    Custom permission to allow HR users to create jobs,
    and allow all users to read jobs.
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.is_authenticated and request.user.user_type == 'hr'

# Create your views here.
class UserInfoView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CustomUserSerializer

    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            self.object = self.get_object()
            serializer = self.get_serializer(self.object, data=request.data, partial=partial)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
    # Allow unauthenticated access for viewing jobs
    permission_classes = (AllowAny,)
    serializer_class = JobSerializer
    
    def get_queryset(self):
        # Only show active jobs that are currently visible in HR's posted jobs list
        queryset = Job.objects.filter(is_active=True)
        own = self.request.query_params.get('own')
        if self.request.user.is_authenticated and self.request.user.user_type == 'hr' and own in ['1', 'true', 'True']:
            return queryset.filter(hr_user=self.request.user)
        return queryset
    
    def create(self, request, *args, **kwargs):
        # Only HR users can create jobs
        if not request.user or not request.user.is_authenticated or request.user.user_type != 'hr':
            return Response({'error': 'Only HR users can post jobs'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(hr_user=self.request.user)

class JobDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = JobSerializer
    permission_classes = (AllowAny,)
    
    def get_queryset(self):
        # Regular users can only see active jobs
        return Job.objects.filter(is_active=True)
    
    def update(self, request, *args, **kwargs):
        job = self.get_object()
        if request.user.is_authenticated and (job.hr_user == request.user or request.user.is_staff):
            return super().update(request, *args, **kwargs)
        return Response({'error': 'You do not have permission to update this job'}, status=status.HTTP_403_FORBIDDEN)
    
    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if request.user.is_authenticated and (job.hr_user == request.user or request.user.is_staff):
            # Send notification emails to all applicants before deleting the job
            applications = job.applications.all()
            for application in applications:
                try:
                    # Send a notification that the job has been removed
                    subject = f'Job Posting Removed - {job.title}'
                    context = {
                        'applicant_name': application.applicant.get_full_name() or application.applicant.username,
                        'job_title': job.title,
                        'company_name': job.company_name,
                        'removal_reason': 'The job posting has been removed by the employer.',
                    }
                    
                    html_message = render_to_string('emails/job_removed.html', context)
                    
                    send_mail(
                        subject=subject,
                        message='',
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[application.applicant.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to send job removal email to {application.applicant.email}: {e}")
            
            # Delete the job - this will cascade and delete all applications
            return super().destroy(request, *args, **kwargs)
        return Response({'error': 'You do not have permission to delete this job'}, status=status.HTTP_403_FORBIDDEN)

class ResumeUploadView(APIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request):
        if request.user.user_type != 'job_seeker':
            return Response(
                {'error': 'Only job seekers can upload resumes'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        resume_file = request.FILES.get('resume_file')
        
        if not resume_file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not resume_file.name.endswith('.pdf'):
            return Response(
                {'error': 'Only PDF files are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            parsed_text = extract_text_from_pdf(resume_file)
            resume_file.seek(0)
            
            resume, created = Resume.objects.update_or_create(
                user=request.user,
                defaults={'resume_file': resume_file, 'parsed_text': parsed_text}
            )
            
            return Response({
                'message': 'User resume uploaded successfully.',
                'resume': ResumeSerializer(resume).data
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    
    def get(self, request):
        try:
            resume = Resume.objects.get(user=request.user)
            return Response(
                ResumeSerializer(resume).data,
                status=status.HTTP_200_OK
            )
        except Resume.DoesNotExist:
            return Response(
                {'error': 'No resume found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )

class JobApplicationCreateView(CreateAPIView):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        if request.user.user_type != 'job_seeker':
            return Response({'error': 'Only job seekers can apply for jobs'}, status=status.HTTP_403_FORBIDDEN)
        
        job_id = request.data.get('job')
        if not job_id:
            return Response({'error': 'Job ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if JobApplication.objects.filter(job=job, applicant=request.user).exists():
            return Response({'error': 'You have already applied for this job'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        resume = getattr(request.user, 'resume', None)
        resume_text = resume.parsed_text if resume else ""
        
        perc, missing = calculate_match_score(resume_text, job.description, job.requirements)
        
        application = serializer.save(applicant=request.user, job=job, match_percentage=perc, missing_skills=missing)
        
        # Send confirmation email to job seeker
        try:
            send_application_confirmation_email(application)
        except Exception as e:
            # Log the error but don't fail the application creation
            print(f"Failed to send confirmation email: {e}")
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class JobApplicationListView(ListCreateAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if self.request.user.user_type == 'hr':
            return JobApplication.objects.filter(job__hr_user=self.request.user)
        return JobApplication.objects.filter(applicant=self.request.user)


class JobApplicationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer
    permission_classes = (IsAuthenticated,)
    
    def update(self, request, *args, **kwargs):
        application = self.get_object()
        # Only HR can update application status
        if request.user.user_type == 'hr' and application.job.hr_user == request.user:
            old_status = application.status
            response = super().update(request, *args, **kwargs)
            
            # Send status update email to job seeker
            try:
                send_status_update_email(application, old_status)
            except Exception as e:
                # Log the error but don't fail the status update
                print(f"Failed to send status update email: {e}")
            
            return response
        return Response(
            {'error': 'You do not have permission to update this application'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def destroy(self, request, *args, **kwargs):
        application = self.get_object()
        # Only HR or applicant can delete
        if request.user == application.job.hr_user or request.user == application.applicant:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {'error': 'You do not have permission to delete this application'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def get_queryset(self):
        # Users can only see their own applications or applications for their posted jobs
        if self.request.user.user_type == 'hr':
            return JobApplication.objects.filter(job__hr_user=self.request.user)
        return JobApplication.objects.filter(applicant=self.request.user)


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.user == request.user:
            return super().update(request, *args, **kwargs)
        return Response(
            {'error': 'You do not have permission to update this notification'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def destroy(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.user == request.user:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {'error': 'You do not have permission to delete this notification'},
            status=status.HTTP_403_FORBIDDEN
        )

class AIGenerateJDView(APIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request):
        try:
            if request.user.user_type != 'hr':
                return Response({'error': 'Only HR users can generate JDs'}, status=status.HTTP_403_FORBIDDEN)
            
            title = request.data.get('title', '').strip()
            level = request.data.get('level', '').strip()
            skills = request.data.get('skills', '').strip()
            
            if not title:
                return Response({'error': 'Job title is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not skills:
                return Response({'error': 'Key skills are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            data = generate_job_description(title, level, skills)
            
            # Check if generation failed (error fields in response)
            if "API Key not configured" in str(data.get('requirements', '')):
                return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if "Failed to" in str(data.get('description', '')):
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Unhandled error in AIGenerateJDView: {type(e).__name__}: {e}")
            return Response(
                {'error': f'Server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
