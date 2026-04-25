from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from users.models import Job, CustomUser
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Automated job data maintenance - clean up old inactive jobs and send reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-old',
            type=int,
            default=30,
            help='Remove inactive jobs older than this many days (default: 30)',
        )
        parser.add_argument(
            '--send-report',
            action='store_true',
            help='Send cleanup report via email',
        )

    def handle(self, *args, **options):
        days_old = options['days_old']
        send_report = options['send_report']

        cutoff_date = datetime.now() - timedelta(days=days_old)

        self.stdout.write(f'=== AUTOMATED JOB MAINTENANCE ===')
        self.stdout.write(f'Cleaning up inactive jobs older than {days_old} days ({cutoff_date.date()})')

        # Find old inactive jobs
        old_inactive_jobs = Job.objects.filter(
            is_active=False,
            posted_date__lt=cutoff_date
        )

        old_count = old_inactive_jobs.count()

        # Clean up old inactive jobs
        if old_count > 0:
            self.stdout.write(f'Found {old_count} old inactive jobs to remove')
            deleted_count = 0
            for job in old_inactive_jobs:
                try:
                    job.delete()
                    deleted_count += 1
                except Exception as e:
                    self.stdout.write(f'Failed to delete job {job.id}: {e}')

            self.stdout.write(f'✅ Removed {deleted_count} old inactive jobs')
        else:
            self.stdout.write('✅ No old inactive jobs to clean up')

        # Current status
        total_jobs = Job.objects.count()
        active_jobs = Job.objects.filter(is_active=True).count()
        inactive_jobs = Job.objects.filter(is_active=False).count()

        hr_users = CustomUser.objects.filter(user_type='hr').count()
        hr_with_jobs = CustomUser.objects.filter(
            user_type='hr',
            jobs_posted__is_active=True
        ).distinct().count()

        report = f"""
=== JOB DATABASE MAINTENANCE REPORT ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total jobs: {total_jobs}
- Active jobs: {active_jobs}
- Inactive jobs: {inactive_jobs}
- Total HR users: {hr_users}
- HR users with active jobs: {hr_with_jobs}

MAINTENANCE ACTIONS:
- Cleaned up old inactive jobs (> {days_old} days): {old_count} removed

CURRENT ACTIVE JOBS BY HR:
"""

        hr_stats = {}
        for hr in CustomUser.objects.filter(user_type='hr'):
            job_count = Job.objects.filter(hr_user=hr, is_active=True).count()
            if job_count > 0:
                hr_stats[hr.username] = job_count
                report += f"- {hr.username}: {job_count} jobs\n"

        report += "\n✅ Database maintenance completed successfully"

        self.stdout.write(report)

        # Send email report if requested
        if send_report:
            try:
                send_mail(
                    subject='Job Database Maintenance Report',
                    message=report,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],  # Send to admin
                    fail_silently=False,
                )
                self.stdout.write('📧 Maintenance report sent via email')
            except Exception as e:
                self.stdout.write(f'❌ Failed to send email report: {e}')

        self.stdout.write('✅ Job data maintenance completed!')