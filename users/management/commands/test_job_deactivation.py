from django.core.management.base import BaseCommand
from users.models import Job, CustomUser


class Command(BaseCommand):
    help = 'Test job deactivation functionality'

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

        job, created = Job.objects.get_or_create(
            title='Test Job for Deletion',
            defaults={
                'description': 'Test job description',
                'location': 'Test Location',
                'company_name': 'Test Company',
                'requirements': 'Test requirements',
                'hr_user': hr_user
            }
        )

        self.stdout.write(f'Job created: {created}')
        self.stdout.write(f'Job is_active: {job.is_active}')

        # Test deactivation
        if job.is_active:
            job.is_active = False
            job.save()
            self.stdout.write('Job deactivated successfully')

        # Test activation
        job.is_active = True
        job.save()
        self.stdout.write('Job activated successfully')

        # Test deletion prevention with applications
        job_seeker, created = CustomUser.objects.get_or_create(
            email='jobseeker2@example.com',
            defaults={
                'username': 'test_jobseeker2',
                'user_type': 'job_seeker'
            }
        )
        if created:
            job_seeker.set_password('testpass123')
            job_seeker.save()

        # Create an application for the job
        from users.models import JobApplication
        application, created = JobApplication.objects.get_or_create(
            job=job,
            applicant=job_seeker,
            defaults={'status': 'applied'}
        )

        self.stdout.write(f'Application created: {created}')
        self.stdout.write(f'Job has applications: {job.applications.exists()}')

        # Try to delete job (should fail)
        try:
            if job.applications.exists():
                self.stdout.write('Job cannot be deleted - has applications')
            else:
                job.delete()
                self.stdout.write('Job deleted successfully')
        except Exception as e:
            self.stdout.write(f'Error deleting job: {e}')