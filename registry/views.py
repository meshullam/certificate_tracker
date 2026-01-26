import logging
import pandas as pd
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta

from .models import CertificateRecord, ActivityLog, DashboardStats
from .forms import ExcelUploadForm

# ==================================================================
# LOGGING CONFIGURATION
# ==================================================================
logger = logging.getLogger(__name__)


# ==================================================================
# HELPER FUNCTION - Get Client IP
# ==================================================================
def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ==================================================================
# DASHBOARD
# ==================================================================
@login_required
def dashboard(request):
    """
    Main dashboard showing statistics and recent activities.
    """
    # Get or create today's stats
    stats = DashboardStats.get_or_create_today_stats()
    
    # Get recent activities (last 20)
    recent_activities = ActivityLog.get_recent_activities(limit=20)
    
    # Get user's recent activities
    user_activities = ActivityLog.get_user_activities(request.user, limit=10)
    
    # Department breakdown
    department_stats = CertificateRecord.objects.values('department').annotate(
        total=Count('id'),
        collected=Count('id', filter=Q(status='Collected')),
        pending=Count('id', filter=Q(status='Not Collected'))
    ).order_by('-total')[:5]
    
    # Weekly trend (last 7 days)
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    daily_uploads = []
    daily_collections = []
    labels = []
    
    for i in range(7):
        date = week_ago + timedelta(days=i)
        labels.append(date.strftime('%a'))
        
        uploads = ActivityLog.objects.filter(
            timestamp__date=date,
            action='UPLOAD'
        ).count()
        daily_uploads.append(uploads)
        
        collections = ActivityLog.objects.filter(
            timestamp__date=date,
            action='COLLECT'
        ).count()
        daily_collections.append(collections)
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'user_activities': user_activities,
        'department_stats': department_stats,
        'chart_labels': labels,
        'chart_uploads': daily_uploads,
        'chart_collections': daily_collections,
        'current_year': timezone.now().year,
    }
    
    # Log dashboard view
    ActivityLog.log_activity(
        user=request.user,
        action='SEARCH',
        description='Viewed dashboard',
        ip_address=get_client_ip(request)
    )
    
    return render(request, 'registry/dashboard.html', context)


# ==================================================================
# CERTIFICATE UPLOAD & MANAGEMENT
# ==================================================================
@login_required
def upload_excel(request):
    """
    Upload an Excel file and create/update CertificateRecord rows.
    Supports search and pagination of uploaded records.
    """
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        
        if not form.is_valid():
            messages.error(request, "Please upload a valid Excel file.")
            return redirect('upload_excel')

        excel_file = request.FILES['excel_file']

        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Check if file is empty
            if df.empty:
                messages.error(request, "The uploaded file is empty.")
                return redirect('upload_excel')
            
            original_columns = df.columns.tolist()
            logger.info(f"Processing Excel file: {excel_file.name} with {len(df)} rows")
            
            # Create lowercase mapping for case-insensitive column matching
            columns_map = {col.strip().lower(): col for col in original_columns}
            
            # Find required columns using flexible matching
            name_col = None
            index_col = None
            programme_col = None
            department_col = None
            slip_col = None
            
            # Match name column
            for variant in ['name', 'student name', 'full name', 'student_name', 'fullname']:
                if variant in columns_map:
                    name_col = columns_map[variant]
                    break
            
            # Match index number column
            for variant in ['index number', 'index no', 'index_no', 'index', 'admission number', 'admission no', 'admission_no']:
                if variant in columns_map:
                    index_col = columns_map[variant]
                    break
            
            # Match programme column
            for variant in ['programme', 'program', 'course', 'course name', 'course_name']:
                if variant in columns_map:
                    programme_col = columns_map[variant]
                    break
            
            # Match department column
            for variant in ['department', 'dept', 'faculty']:
                if variant in columns_map:
                    department_col = columns_map[variant]
                    break
            
            # Match slip number column (optional)
            for variant in ['slip no', 'slip number', 'slip_no', 'slip_number', 'slip', 'certificate no', 'cert_no']:
                if variant in columns_map:
                    slip_col = columns_map[variant]
                    break
            
            # Validate required columns exist
            missing_columns = []
            if not name_col:
                missing_columns.append('Name')
            if not index_col:
                missing_columns.append('Index Number')
            if not programme_col:
                missing_columns.append('Programme')
            if not department_col:
                missing_columns.append('Department')
            
            if missing_columns:
                error_msg = f"Missing required columns: {', '.join(missing_columns)}. Found: {', '.join(original_columns)}"
                logger.error(error_msg)
                messages.error(request, error_msg)
                return redirect('upload_excel')

            # Process rows
            created_count = 0
            updated_count = 0
            skipped_count = 0

            for index, row in df.iterrows():
                try:
                    # Extract and clean data
                    name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ''
                    index_number = str(row[index_col]).strip() if pd.notna(row[index_col]) else ''
                    programme = str(row[programme_col]).strip() if pd.notna(row[programme_col]) else ''
                    department = str(row[department_col]).strip() if pd.notna(row[department_col]) else ''
                    slip_number = str(row[slip_col]).strip() if slip_col and pd.notna(row[slip_col]) else ''

                    # Skip rows with missing critical data
                    if not index_number or index_number.lower() in ['nan', 'none', '']:
                        skipped_count += 1
                        continue

                    if not name or not programme or not department:
                        skipped_count += 1
                        continue

                    # Create or update record
                    obj, created = CertificateRecord.objects.update_or_create(
                        index_number=index_number,
                        defaults={
                            'name': name,
                            'programme': programme,
                            'department': department,
                            'slip_number': slip_number,
                            'status': 'Not Collected',
                            'uploaded_by': request.user,  # Track who uploaded
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as row_error:
                    logger.error(f"Error processing row {index + 2}: {row_error}")
                    skipped_count += 1

            # Log activity
            ActivityLog.log_activity(
                user=request.user,
                action='UPLOAD',
                description=f"Uploaded {excel_file.name}: {created_count} created, {updated_count} updated, {skipped_count} skipped",
                ip_address=get_client_ip(request)
            )

            # Provide feedback
            success_msg = f"Upload complete! Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}"
            messages.success(request, success_msg)
            logger.info(success_msg)
            return redirect('upload_excel')

        except Exception as e:
            error_msg = "An error occurred while processing the file. Please check the file format and try again."
            logger.exception(f"Error processing Excel file {excel_file.name}: {e}")
            messages.error(request, error_msg)
            return redirect('upload_excel')

    else:
        form = ExcelUploadForm()

    # ==================================================================
    # DISPLAY RECORDS WITH SEARCH & PAGINATION
    # ==================================================================
    search_query = request.GET.get('q', '').strip()

    # Get all records, apply search filter if query exists
    records = CertificateRecord.objects.all().order_by('-upload_date')
    
    if search_query:
        records = records.filter(
            Q(name__icontains=search_query) | 
            Q(index_number__icontains=search_query)
        )
        
        # Log search activity
        ActivityLog.log_activity(
            user=request.user,
            action='SEARCH',
            description=f"Searched for: {search_query}",
            ip_address=get_client_ip(request)
        )

    # Pagination - 10 records per page
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'page_obj': page_obj,
        'search_query': search_query,
        'current_year': timezone.now().year,
    }

    return render(request, 'registry/upload_certificates.html', context)


# ==================================================================
# CERTIFICATE COLLECTION
# ==================================================================
@login_required
def collect_certificate(request, pk):
    """
    Mark a certificate as collected and record the timestamp.
    """
    record = get_object_or_404(CertificateRecord, pk=pk)
    
    if request.method == 'POST':
        # Mark as collected
        record.mark_collected(request.user)  # Using model method
        
        # Log activity
        ActivityLog.log_activity(
            user=request.user,
            action='COLLECT',
            description=f"Collected certificate for {record.name} ({record.index_number})",
            certificate=record,
            ip_address=get_client_ip(request)
        )
        
        logger.info(f"Certificate collected: {record.index_number} - {record.name} by {request.user.username}")
        messages.success(request, f"{record.name}'s certificate marked as collected.")

        # Preserve search query in redirect
        search_query = request.GET.get("q", "")
        if search_query:
            return redirect(f"/registry/upload/?q={search_query}")
        else:
            return redirect("upload_excel")
    
    return redirect("upload_excel")


# ==================================================================
# REPORT GENERATION
# ==================================================================
@login_required
def generate_report(request):
    """
    Generate Excel report of certificates filtered by status.
    """
    status = request.GET.get('status', '').strip()
    
    if not status:
        messages.error(request, "Please select a report type.")
        return redirect('upload_excel')

    # Fetch records with selected status
    records = CertificateRecord.objects.filter(status=status).order_by('-upload_date')

    if not records.exists():
        messages.warning(request, f"No {status} certificates found.")
        return redirect('upload_excel')

    try:
        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{status} Certificates"

        # Add headers
        headers = [
            'Index Number', 
            'Name', 
            'Programme', 
            'Department', 
            'Slip Number', 
            'Status', 
            'Upload Date',
            'Uploaded By',
            'Collected At',
            'Collected By'
        ]
        ws.append(headers)

        # Add data rows
        for rec in records:
            ws.append([
                rec.index_number,
                rec.name,
                rec.programme,
                rec.department,
                rec.slip_number or '',
                rec.status,
                rec.upload_date.strftime("%Y-%m-%d %H:%M") if rec.upload_date else '',
                rec.uploaded_by.username if rec.uploaded_by else '',
                rec.collected_at.strftime("%Y-%m-%d %H:%M") if rec.collected_at else '',
                rec.collected_by.username if rec.collected_by else ''
            ])

        # Prepare HTTP response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"{status.replace(' ', '_')}_Certificates_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Save workbook to response
        wb.save(response)
        
        # Log activity
        ActivityLog.log_activity(
            user=request.user,
            action='DOWNLOAD_REPORT',
            description=f"Downloaded {status} certificates report ({records.count()} records)",
            ip_address=get_client_ip(request)
        )
        
        logger.info(f"Report generated: {filename} with {records.count()} records by {request.user.username}")
        return response

    except Exception as e:
        logger.exception(f"Error generating report: {e}")
        messages.error(request, "An error occurred while generating the report. Please try again.")
        return redirect('upload_excel')