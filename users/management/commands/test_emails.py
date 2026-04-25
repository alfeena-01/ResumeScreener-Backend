from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from users.models import JobApplication, Job, CustomUser
from users.utils import send_application_confirmation_email, send_status_update_email


class Command(BaseCommand):
    help = 'Test email functionality'

    def handle(self, *args, **options):
        # Create test data if it doesn't exist
        hr_user, created = CustomUser.objects.get_or_create(
            email='hr@example.com',
            defaults={
                'username': 'test_hr',
                'user_type': 'hr'
            }
        )
        if created:
            hr_user.set_password('testpass123')
            hr_user.save()

        job_seeker, created = CustomUser.objects.get_or_create(
            email='jobseeker@example.com',
            defaults={
                'username': 'test_jobseeker',
                'user_type': 'job_seeker'
            }
        )
        if created:
            job_seeker.set_password('testpass123')
            job_seeker.save()

        job, created = Job.objects.get_or_create(
            title='Test Job',
            defaults={
                'description': 'Test job description',
                'location': 'Test Location',
                'company_name': 'Test Company',
                'requirements': 'Test requirements',
                'hr_user': hr_user
            }
        )

        # Create test application
        application, created = JobApplication.objects.get_or_create(
            job=job,
            applicant=job_seeker,
            defaults={'status': 'applied'}
        )

        if created:
            self.stdout.write('Created test application')
        else:
            self.stdout.write('Using existing test application')

        # Test application confirmation email
        self.stdout.write('Sending application confirmation email...')
        try:
            send_application_confirmation_email(application)
            self.stdout.write(self.style.SUCCESS('Application confirmation email sent successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send application confirmation email: {e}'))

        # Test status update email
        old_status = application.status
        application.status = 'reviewing'
        application.save()

        self.stdout.write('Sending status update email...')
        try:
            send_status_update_email(application, old_status)
            self.stdout.write(self.style.SUCCESS('Status update email sent successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send status update email: {e}'))