from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import CustomUser, Job, Resume, JobApplication, Notification
from django.contrib.auth import authenticate

class CustomUserSerializer(ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = ("id", "email", "username", "user_type", "first_name", "last_name", "profile_picture")
        read_only_fields = ("id", "email", "username", "user_type")

class JobSerializer(ModelSerializer):
    hr_user_name = serializers.CharField(source='hr_user.username', read_only=True)
    
    class Meta:
        model = Job
        fields = ("id", "title", "description", "location", "job_type", "company_name", "salary_min", "salary_max", "salary_currency", "requirements", "hr_user", "hr_user_name", "posted_date", "is_active")
        read_only_fields = ("id", "hr_user", "posted_date")

class SignUpSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    user_type = serializers.ChoiceField(choices=['job_seeker', 'hr'])
    
    class Meta:
        model = CustomUser
        fields = ("email", "username", "password", "password_confirm", "user_type")
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data, password=password)
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "Invalid email or password."})
        
        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Invalid email or password."})
        
        data['user'] = user
        return data


class ResumeSerializer(ModelSerializer):
    class Meta:
        model = Resume
        fields = ("id", "user", "resume_file", "uploaded_at", "updated_at")
        read_only_fields = ("id", "user", "uploaded_at", "updated_at")
    
    def validate_resume_file(self, value):
        if not value.name.endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value

class JobApplicationSerializer(ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.username', read_only=True)
    applicant_email = serializers.CharField(source='applicant.email', read_only=True)
    resume_url = serializers.SerializerMethodField(read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)

    class Meta:
        model = JobApplication
        fields = ("id", "job", "job_title", "applicant", "applicant_name", "applicant_email", "resume_url", "status", "match_percentage", "missing_skills", "applied_date", "updated_at")
        read_only_fields = ("id", "applicant", "applied_date", "updated_at")

    def get_resume_url(self, obj):
        request = self.context.get('request')
        resume = getattr(obj.applicant, 'resume', None)
        if resume and resume.resume_file:
            if request is not None:
                return request.build_absolute_uri(resume.resume_file.url)
            return resume.resume_file.url
        return None


class NotificationSerializer(ModelSerializer):
    job_title = serializers.CharField(source='job_application.job.title', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='job_application.job.company_name', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = ("id", "user", "job_application", "notification_type", "title", "message", "is_read", "job_title", "company_name", "created_at")
        read_only_fields = ("id", "user", "created_at")
