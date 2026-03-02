import logging
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone

from .models import CertificateRecord

logger = logging.getLogger(__name__)


# ==================================================================
# RATE LIMITING HELPER
# ==================================================================

def is_rate_limited(ip_address, limit=20, window=60):
    """
    Simple IP-based rate limiter using Django's cache framework.
    Allows 'limit' requests per 'window' seconds per IP.
    Returns True if the IP has exceeded the limit.
    """
    cache_key = f"rate_limit:public_search:{ip_address}"
    request_count = cache.get(cache_key, 0)

    if request_count >= limit:
        return True

    # Increment count; set expiry only on first request
    if request_count == 0:
        cache.set(cache_key, 1, timeout=window)
    else:
        cache.incr(cache_key)

    return False


def get_client_ip(request):
    """Extract the real client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ==================================================================
# PUBLIC SEARCH VIEW
# ==================================================================

@csrf_exempt          # Public endpoint — no CSRF token needed
@require_GET          # Only allow GET requests
def public_certificate_search(request):
    """
    Public read-only API endpoint for students to search for their
    certificate collection status.

    URL: /api/certificate-search/?query=<name_or_index_number>

    Returns ONLY:
      - name, index_number, programme, department, status
    Never returns: slip_number, uploaded_by, collected_by, upload_date, etc.

    Rate limited to 20 requests per minute per IP address.
    """

    # ── 1. RATE LIMITING ──────────────────────────────────────────
    client_ip = get_client_ip(request)

    if is_rate_limited(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JsonResponse(
            {"found": False, "error": "Too many requests. Please wait a moment and try again."},
            status=429
        )

    # ── 2. INPUT VALIDATION ───────────────────────────────────────
    query = request.GET.get('query', '').strip()

    if not query:
        return JsonResponse(
            {"found": False, "error": "Please provide a name or index number to search."},
            status=400
        )

    if len(query) < 3:
        return JsonResponse(
            {"found": False, "error": "Search query must be at least 3 characters."},
            status=400
        )

    if len(query) > 100:
        return JsonResponse(
            {"found": False, "error": "Search query is too long."},
            status=400
        )

    # ── 3. DATABASE SEARCH ────────────────────────────────────────
    try:
        # Search by name (case-insensitive) OR exact index number match
        # Index number is matched exactly to prevent partial leaks.
        # Name is matched partially (contains) for usability.
        records = CertificateRecord.objects.filter(
            Q(name__icontains=query) |
            Q(index_number__iexact=query)
        ).only(
            # Explicitly select ONLY public-safe fields
            'name', 'index_number', 'programme', 'department', 'status'
        ).order_by('name')[:10]  # Limit to 10 results maximum

        if not records.exists():
            logger.info(f"Public search — no results for query '{query}' from IP {client_ip}")
            return JsonResponse({
                "found": False,
                "message": "No certificate record found. Please check your name or index number and try again."
            })

        # ── 4. BUILD SAFE RESPONSE ────────────────────────────────
        results = []
        for record in records:
            results.append({
                "name": record.name,
                "index_number": record.index_number,
                "programme": record.programme,
                "department": record.department,
                "status": record.status,
                # Human-friendly status label
                "status_label": "✅ Ready for Collection" if record.status == "Not Collected" else "✔ Already Collected",
            })

        logger.info(f"Public search — {len(results)} result(s) for query '{query}' from IP {client_ip}")

        return JsonResponse({
            "found": True,
            "count": len(results),
            "results": results
        })

    except Exception as e:
        # Never expose internal errors to the public
        logger.exception(f"Error in public_certificate_search for query '{query}': {e}")
        return JsonResponse(
            {"found": False, "error": "A server error occurred. Please try again later."},
            status=500
        )
