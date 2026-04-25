from django.core.management.base import BaseCommand
from users.models import Job, CustomUser


class Command(BaseCommand):
    help = 'Clean up job data - keep only jobs currently visible in HR posted jobs list'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--delete-test-jobs',
            action='store_true',
            help='Delete jobs with test-related titles',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_test_jobs = options['delete_test_jobs']

        self.stdout.write('=== JOB CLEANUP ANALYSIS ===')

        # Get all jobs
        all_jobs = Job.objects.all()
        total_jobs = all_jobs.count()

        # Get active jobs (visible to job seekers)
        active_jobs = Job.objects.filter(is_active=True)
        active_count = active_jobs.count()

        # Get jobs visible in HR posted jobs list (active jobs owned by HR users)
        hr_users = CustomUser.objects.filter(user_type='hr')
        hr_posted_jobs = Job.objects.filter(
            is_active=True,
            hr_user__in=hr_users
        )
        hr_posted_count = hr_posted_jobs.count()

        # Find jobs that are not in HR posted jobs list
        orphaned_jobs = active_jobs.exclude(hr_user__in=hr_users)
        orphaned_count = orphaned_jobs.count()

        self.stdout.write(f'Total jobs in database: {total_jobs}')
        self.stdout.write(f'Active jobs: {active_count}')
        self.stdout.write(f'Jobs in HR posted list: {hr_posted_count}')
        self.stdout.write(f'Orphaned active jobs: {orphaned_count}')

        # Identify test jobs
        test_keywords = ['test', 'Test', 'TEST', 'sample', 'Sample', 'demo', 'Demo']
        test_jobs = Job.objects.filter(
            title__icontains='test'
        ).exclude(
            title__icontains='tester'  # Don't delete legitimate tester positions
        )

        for keyword in test_keywords[1:]:  # Skip 'test' since we already did it
            test_jobs = test_jobs | Job.objects.filter(title__icontains=keyword)

        test_jobs = test_jobs.distinct()
        test_count = test_jobs.count()

        self.stdout.write(f'\\nPotential test jobs: {test_count}')

        if test_count > 0:
            self.stdout.write('\\nTest jobs found:')
            for job in test_jobs:
                self.stdout.write(f'  - ID {job.id}: "{job.title}" by {job.hr_user.username}')

        # Jobs to potentially delete
        jobs_to_delete = Job.objects.none()

        if orphaned_count > 0:
            jobs_to_delete = jobs_to_delete | orphaned_jobs
            self.stdout.write(f'\\nOrphaned jobs to delete: {orphaned_count}')
            for job in orphaned_jobs:
                self.stdout.write(f'  - ID {job.id}: "{job.title}" (no HR owner)')

        if delete_test_jobs and test_count > 0:
            jobs_to_delete = jobs_to_delete | test_jobs
            self.stdout.write(f'\\nTest jobs to delete: {test_count}')

        jobs_to_delete = jobs_to_delete.distinct()
        delete_count = jobs_to_delete.count()

        if delete_count == 0:
            self.stdout.write('\\n✅ No jobs need to be deleted. All jobs are properly in HR posted jobs list.')
            return

        self.stdout.write(f'\\n⚠️  Total jobs to delete: {delete_count}')

        if dry_run:
            self.stdout.write('\\n🔍 DRY RUN - No changes made')
            self.stdout.write('Run without --dry-run to actually delete these jobs')
        else:
            # Confirm deletion
            self.stdout.write('\\n❌ DELETING JOBS...')
            deleted_count = 0
            for job in jobs_to_delete:
                try:
                    job_title = job.title
                    job_id = job.id
                    job.delete()
                    deleted_count += 1
                    self.stdout.write(f'  ✅ Deleted: ID {job_id} - "{job_title}"')
                except Exception as e:
                    self.stdout.write(f'  ❌ Failed to delete job ID {job.id}: {e}')

            self.stdout.write(f'\\n✅ Successfully deleted {deleted_count} jobs')
            self.stdout.write(f'Remaining jobs: {Job.objects.count()}')