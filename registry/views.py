import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import CertificateRecord
from .forms import ExcelUploadForm
from django.shortcuts import render, redirect, get_object_or_404
import openpyxl
from django.http import HttpResponse
from django.utils import timezone


@login_required
def upload_excel(request):
    """
    Upload an Excel file and create/update CertificateRecord rows.
    Accepts several common header variants and maps them to canonical fields.
    """
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Please upload a valid Excel file.")
            return redirect('upload_excel')

        excel_file = form.cleaned_data['excel_file']

        try:
            df = pd.read_excel(excel_file)
            original_columns = df.columns.tolist()
            lowered_map = {col: col.strip().lower() for col in original_columns}

            messages.info(request, f"Columns found: {original_columns}")

            possible_names = {
                'name': ['name', 'student name', 'full name'],
                'index_number': ['index number', 'index no', 'index_no', 'index', 'admission number', 'admission_no', 'admission no'],
                'programme': ['programme', 'program', 'course', 'course name'],
                'slip_number': ['slip no', 'slip_number', 'slip', 'slip no.', 'slipno'],
                'department': ['department', 'dept'],
            }

            col_map = {}
            for canonical, variants in possible_names.items():
                for actual_col, lowered in lowered_map.items():
                    if lowered in variants:
                        col_map[canonical] = actual_col
                        break

            required = ['name', 'index_number', 'programme', 'department']
            missing = [r for r in required if r not in col_map]
            if missing:
                messages.error(request, f"Missing required columns: {missing}. Found columns: {original_columns}")
                return redirect('upload_excel')

            created_count = updated_count = skipped_count = 0

            for _, row in df.iterrows():
                name = str(row.get(col_map.get('name'), '')).strip()
                index_number = str(row.get(col_map.get('index_number'), '')).strip()
                programme = str(row.get(col_map.get('programme'), '')).strip()
                department = str(row.get(col_map.get('department'), '')).strip()
                slip_number = str(row.get(col_map.get('slip_number'), '')).strip() if 'slip_number' in col_map else ''

                if not index_number:
                    skipped_count += 1
                    continue

                obj, created = CertificateRecord.objects.update_or_create(
                    index_number=index_number,
                    defaults={
                        'name': name,
                        'programme': programme,
                        'department': department,
                        'slip_number': slip_number,
                        'status': 'Not Collected',
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            messages.success(
                request,
                f"Upload complete: {created_count} created, {updated_count} updated, {skipped_count} skipped."
            )
            return redirect('upload_excel')

        except Exception as e:
            print("Error processing uploaded Excel:", repr(e))
            messages.error(request, f"Error processing file: {e}")
            return redirect('upload_excel')

    else:
        form = ExcelUploadForm()

    # ✅ ADDED SECTION: Search + Pagination + Hide list if no search
        # ✅ ADDED SECTION: Search + Pagination + Hide list if no search
    search_query = request.GET.get('q', '').strip()

    records = CertificateRecord.objects.all()
    if search_query:
        records = records.filter(
            Q(name__icontains=search_query) | Q(index_number__icontains=search_query)
        )
    else:
        records = CertificateRecord.objects.none()  # hide list if no search

    records = records.order_by('-upload_date')

    paginator = Paginator(records, 10)  # show 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    # ✅ FIXED TEMPLATE NAME BELOW
    return render(request, 'registry/upload_certificates.html', context)


    return render(request, 'registry/upload.html', context)

def collect_certificate(request, pk):
    record = get_object_or_404(CertificateRecord, pk=pk)
    record.status = "Collected"
    record.collected_at = timezone.now()
    record.save()
    messages.success(request, f"{record.name}'s certificate marked as collected.")

    # Preserve search query so the same student remains visible
    search_query = request.GET.get("q", "")

    # Redirect back to upload page with search if present
    if search_query:
        return redirect(f"/registry/upload/?q={search_query}")
    else:
        return redirect("upload_excel")


@login_required
def generate_report(request):
    status = request.GET.get('status')
    if not status:
        messages.error(request, "Please select a report type.")
        return redirect('upload_excel')

    records = CertificateRecord.objects.filter(status=status)

    import openpyxl
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{status} Certificates"

    headers = ['Index Number', 'Name', 'Programme', 'Department', 'Slip Number', 'Status', 'Upload Date', 'Collected At']
    ws.append(headers)

    for rec in records:
        ws.append([
            rec.index_number,
            rec.name,
            rec.programme,
            rec.department,
            rec.slip_number,
            rec.status,
            rec.upload_date.strftime("%Y-%m-%d %H:%M") if rec.upload_date else '',
            rec.collected_at.strftime("%Y-%m-%d %H:%M") if rec.collected_at else ''
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{status}_Certificates_Report.xlsx"'

    wb.save(response)
    return response
