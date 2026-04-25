from django.core.management.base import BaseCommand
from users.models import Job, CustomUser, JobApplication


class Command(BaseCommand):
    help = 'Test job deletion functionality'

    def handle(self, *args, **options):
        # Create test data
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

        # Create a job
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
        self.stdout.write(f'Job ID: {job.id}')

        # Create an application for the job
        application, created = JobApplication.objects.get_or_create(
            job=job,
            applicant=job_seeker,
            defaults={'status': 'applied'}
        )

        self.stdout.write(f'Application created: {created}')
        self.stdout.write(f'Applications before deletion: {JobApplication.objects.filter(job=job).count()}')

        # Delete the job
        job_id = job.id
        job.delete()

        self.stdout.write(f'Job deleted: {job_id}')
        self.stdout.write(f'Job exists: {Job.objects.filter(id=job_id).exists()}')
        self.stdout.write(f'Applications after deletion: {JobApplication.objects.filter(job_id=job_id).count()}')

        self.stdout.write('Job deletion test completed successfully!')