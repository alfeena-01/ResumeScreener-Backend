from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import JobApplication, Notification


@receiver(post_save, sender=JobApplication)
def create_notification_on_status_change(sender, instance, created, **kwargs):
    """
    Signal handler to create a notification when JobApplication status is updated
    """
    # Skip notification on initial creation (when status is 'applied')
    if created:
        return
    
    # Get the previous status
    old_status = None
    try:
        old_instance = JobApplication.objects.get(pk=instance.pk)
        # Since we can't easily get the old status from post_save signal,
        # we'll check if it's different from 'applied'
    except JobApplication.DoesNotExist:
        pass
    
    # Create notification for status changes
    status_display = {
        'reviewing': 'Your application is being reviewed',
        'interview': 'You have been invited for an interview',
        'rejected': 'Your application has been rejected',
        'accepted': 'Congratulations! Your application has been accepted',
    }
    
    if instance.status in status_display:
        notification = Notification.objects.create(
            user=instance.applicant,
            job_application=instance,
            notification_type='application_update',
            title=f"{instance.job.title} - {instance.get_status_display()}",
            message=f"Your application for {instance.job.title} at {instance.job.company_name} status has been updated to: {status_display[instance.status]}"
        )
