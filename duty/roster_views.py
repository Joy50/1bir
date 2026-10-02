from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from authentication.views import DutyRosterMixin
from common.scoping import get_accessible_companies
from common.views import SoldierAccessMixin

from .pdf import build_daily_roster_pdf, build_monthly_roster_pdf
from .services import (
    daily_roster,
    month_bounds,
    monthly_roster_summary,
    parse_report_date,
    parse_report_month,
    roster_organization_ids,
)


class RosterContextMixin(DutyRosterMixin, SoldierAccessMixin):
    def get_form_kwargs(self):
        return {}

    def selected_company(self):
        companies = get_accessible_companies(self.request.user)
        value = self.request.GET.get("company", "")
        if value.isdigit():
            return companies.filter(pk=int(value)).first()
        return None

    def roster_scope(self):
        company = self.selected_company()
        return company, roster_organization_ids(self.request.user, company)


class DutyRosterDailyView(RosterContextMixin, TemplateView):
    template_name = "duty/roster_daily.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company, organization_ids = self.roster_scope()
        report_date = parse_report_date(self.request.GET.get("date"))
        roster = daily_roster(report_date, organization_ids, company)
        context.update({
            "organizations": get_accessible_companies(self.request.user),
            "selected_organization": company,
            "report_date": report_date,
            "previous_date": report_date - timedelta(days=1),
            "next_date": report_date + timedelta(days=1),
            **roster,
        })
        return context


class DutyRosterDailyPDFView(RosterContextMixin, View):
    def get(self, request, *args, **kwargs):
        company, organization_ids = self.roster_scope()
        report_date = parse_report_date(request.GET.get("date"))
        roster = daily_roster(report_date, organization_ids, company)
        pdf_file = build_daily_roster_pdf(report_date, roster, company)
        scope = company.organization_name if company else "1-BIR"
        filename = f"daily-duty-roster-{scope}-{report_date:%Y-%m-%d}.pdf"
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DutyRosterMonthlyView(RosterContextMixin, TemplateView):
    template_name = "duty/roster_monthly.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company, organization_ids = self.roster_scope()
        month_start = parse_report_month(self.request.GET.get("month"))
        previous_month, next_month, month_end = month_bounds(month_start)
        summary = monthly_roster_summary(month_start, organization_ids, company)
        context.update({
            "organizations": get_accessible_companies(self.request.user),
            "selected_organization": company,
            "month_start": month_start,
            "month_end": month_end,
            "previous_month": previous_month,
            "next_month": next_month,
            "today": timezone.localdate(),
            **summary,
        })
        return context


class DutyRosterMonthlyPDFView(RosterContextMixin, View):
    def get(self, request, *args, **kwargs):
        company, organization_ids = self.roster_scope()
        month_start = parse_report_month(request.GET.get("month"))
        summary = monthly_roster_summary(month_start, organization_ids, company)
        pdf_file = build_monthly_roster_pdf(month_start, summary, company)
        scope = company.organization_name if company else "1-BIR"
        filename = f"monthly-duty-roster-{scope}-{month_start:%Y-%m}.pdf"
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
