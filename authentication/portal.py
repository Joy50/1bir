from django.urls import reverse


PORTAL_SECTIONS = {
    "admin": {
        "label": "Admin",
        "icon": "bi-shield-lock",
        "admin_only": True,
        "description": "User management, master data, logs, and system monitoring.",
        "items": [
            {
                "title": "User Management",
                "text": "View, update, and activate portal user accounts.",
                "url_name": "authentication:manage_users",
                "admin_only": True,
            },
            {
                "title": "Create User",
                "text": "Register new CO, officer, clerk, or admin accounts.",
                "url_name": "authentication:create_user",
                "admin_only": True,
            },
            {
                "title": "Duty Posts",
                "text": "Add sentry and duty posts with latitude and longitude.",
                "url_name": "duty:post_list",
                "admin_only": True,
            },
            {
                "title": "Create Rank",
                "text": "Add ranks used across personnel records.",
                "url_name": "common:create_rank",
                "admin_only": True,
            },
            {
                "title": "Create Organization",
                "text": "Add battalion, company, and other unit structures.",
                "url_name": "common:create_organization",
                "admin_only": True,
            },
            {
                "title": "Create Education Level",
                "text": "Add civil education levels for personnel records.",
                "url_name": "common:create_education_level",
                "admin_only": True,
            },
            {
                "title": "Activity Log",
                "text": "Review recent create, update, and delete actions.",
                "url_name": "common:activity_log",
                "admin_only": True,
            },
            {
                "title": "Statistics",
                "text": "Personnel, ranks, reports, and other unit counts.",
                "url_name": "common:statistics",
                "admin_only": True,
            },
        ],
    },
    "soldier": {
        "label": "Soldier",
        "icon": "bi-person-badge",
        "description": "Personnel records, enlistment, and soldier particulars.",
        "landing_url_name": "common:soldier_list",
        "path_prefixes": ("/soldiers",),
        "items": [
            {
                "title": "All Soldiers",
                "text": "View soldiers from your company and subunits.",
                "url_name": "common:soldier_list",
            },
            {
                "title": "Enlist Soldier",
                "text": "Add a new soldier to your company strength.",
                "url_name": "common:soldier_create",
            },
            {
                "title": "Service History",
                "text": "Record postings, ranks, and unit tenures.",
                "url_name": None,
            },
            {
                "title": "Medical Category",
                "text": "Maintain medical categories and validity dates.",
                "url_name": None,
            },
            {
                "title": "Performance Reports",
                "text": "Annual performance reports and scores.",
                "url_name": None,
            },
        ],
    },
    "training": {
        "label": "Training",
        "icon": "bi-journal-bookmark",
        "description": "Yearly plans, commitments, qualifications, leave, sports, IPFT, RET, and march courses.",
        "landing_url_name": "training:training_home",
        "path_prefixes": ("/training",),
        "items": [
            {
                "title": "Participation in Maj Training and Sports",
                "text": "Record sports and training competitions and achievements.",
                "url_name": "training:sports_list",
            },
            {
                "title": "Leave State",
                "text": "Clerks apply leave for soldiers. Officers approve or reject requests.",
                "url_name": "training:leave_list",
            },
            {
                "title": "Individual Qualification",
                "text": "Record multiple courses under multiple course levels for each soldier.",
                "url_name": "training:qual_list",
            },
            {
                "title": "Participation in Maj Commitment",
                "text": "Record GP Trg, ST, WT, FI, IHWF, and FF by soldier and year.",
                "url_name": "training:majcom_list",
            },
            {
                "title": "Yearly Career Plan",
                "text": "View soldiers with yearly cycle plans and unit coverage.",
                "url_name": "training:yearly_plan_list",
            },
            {
                "title": "IPFT",
                "text": "Record bi-annual IPFT type, chance, date, and result.",
                "url_name": "training:ipft_list",
            },
            {
                "title": "RET State",
                "text": "Open GP, SOSN, CAS Trophy, and Grenade firing records.",
                "url_name": "training:ret_list",
            },
            {
                "title": "Speed March & Assault Course",
                "text": "Record speed march and assault course practices and results.",
                "url_name": "training:march_course_list",
            },
        ],
    },
    "admin-logistics": {
        "label": "Admin & Logistics",
        "icon": "bi-box-seam",
        "description": "Soldier postings, duty posts, and the live OSM duty board.",
        "landing_url_name": "duty:home",
        "path_prefixes": ("/duty", "/postings"),
        "items": [
            {
                "title": "Daily Parade State",
                "text": "Authorized, posted, absent, and present strength with absence details.",
                "url_name": "duty:parade_state_list",
            },
            {
                "title": "Soldier Posting",
                "text": "CO posts a soldier. An officer of the receiving unit accepts him.",
                "url_name": "duty:posting_list",
                "roles": ("admin", "co", "officer"),
            },
            {
                "title": "Assign Duty",
                "text": "Officers assign a soldier to a duty post using the fair tour list.",
                "url_name": "duty:assign",
                "roles": ("admin", "co", "officer"),
            },
            {
                "title": "Duty Map",
                "text": "CO view of who is standing which post on OpenStreetMap.",
                "url_name": "duty:map",
                "roles": ("admin", "co"),
            },
            {
                "title": "Duty Posts",
                "text": "Admin-only register of posts with latitude and longitude.",
                "url_name": "duty:post_list",
                "admin_only": True,
            },
            {
                "title": "Stores & Inventory",
                "text": "Track equipment, stores, and issue registers.",
                "url_name": None,
            },
            {
                "title": "Vehicle & Movement",
                "text": "Manage transport and movement requests.",
                "url_name": None,
            },
        ],
    },
    "accounts": {
        "label": "Accounts",
        "icon": "bi-calculator",
        "description": "Financial records and account management.",
        "items": [
            {
                "title": "Pay & Allowances",
                "text": "Review pay-related records and statements.",
                "url_name": None,
            },
            {
                "title": "Unit Expenses",
                "text": "Record and monitor unit expenditure.",
                "url_name": None,
            },
            {
                "title": "Budget Summary",
                "text": "View consolidated financial summaries.",
                "url_name": None,
            },
        ],
    },
}


# The command presentation groups the portal under five staff branches. Keep
# feature definitions above close to their original modules, then compose the
# navigation here so each screen appears under the branch that owns it.
_MODULE_SECTIONS = PORTAL_SECTIONS


def _items(section, *titles):
    wanted = set(titles)
    return [item for item in _MODULE_SECTIONS[section]["items"] if item["title"] in wanted]


PORTAL_SECTIONS = {
    "dashboard": {
        "label": "Dashboard",
        "icon": "bi-flag",
        "description": "Unit identity, Commanding Officers, and achievements of 1 BIR.",
        "landing_url_name": "authentication:home",
        "items": [],
    },
    "a-matter": {
        "label": "A Matter",
        "icon": "bi-people",
        "description": "Personnel, leave, parade state, duty state, postings, and service particulars.",
        "path_prefixes": (
            "/soldiers", "/training/leave", "/parade-state", "/postings",
            "/duty/", "/duty/assign", "/duty/map",
        ),
        "items": [
            {
                "title": "Parade State",
                "text": "View authorized, posted, absent, and present battalion strength.",
                "url_name": "duty:parade_state_list",
            },
            {
                "title": "Leave State",
                "text": "View company leave state, individual leave plans, and approval status.",
                "url_name": "training:leave_list",
            },
            {
                "title": "Duty State",
                "text": "View current duty details, duty posts, and tour progress.",
                "url_name": "duty:home",
            },
            {
                "title": "Posting Record",
                "text": "View current and historical soldier posting records.",
                "url_name": "duty:posting_list",
            },
            {
                "title": "Svc Particulars",
                "text": "View soldiers and their complete service particulars.",
                "url_name": "common:soldier_list",
            },
        ],
    },
    "g-matter": {
        "label": "G Matter",
        "icon": "bi-journal-bookmark",
        "description": "Training plans, IPFT, RET, courses, qualifications, sports, and performance.",
        "landing_url_name": "training:training_home",
        "path_prefixes": ("/training",),
        "items": [
            item for item in _MODULE_SECTIONS["training"]["items"]
            if item["title"] != "Leave State"
        ],
    },
    "q-matter": {
        "label": "Q Matter",
        "icon": "bi-box-seam",
        "admin_only": True,
        "description": "Quartermaster stores, equipment, transport, and logistics administration.",
        "landing_url_name": "duty:post_list",
        "path_prefixes": ("/duty/posts",),
        "items": _items(
            "admin-logistics", "Duty Posts", "Stores & Inventory", "Vehicle & Movement"
        ),
    },
    "account-matter": {
        **_MODULE_SECTIONS["accounts"],
        "label": "Account Matter",
        "icon": "bi-calculator",
    },
    "misc": {
        **_MODULE_SECTIONS["admin"],
        "label": "Misc",
        "icon": "bi-grid",
        "description": "User administration, master data, logs, monitoring, and miscellaneous services.",
        "path_prefixes": ("/users", "/dashboard"),
        "items": [
            {
                "title": "Manage Dashboard",
                "text": "Update the home slider, Commanding Officer quotes, hall of fame, and unit achievements.",
                "url_name": "authentication:dashboard_manage",
                "admin_only": True,
            },
            *[
                item for item in _MODULE_SECTIONS["admin"]["items"]
                if item["title"] != "Duty Posts"
            ],
        ],
    },
}

del _MODULE_SECTIONS


def get_portal_context(request):
    is_admin = bool(
        request.user.is_authenticated
        and getattr(request.user, "is_admin", False)
    )

    if is_admin:
        visible_sections = PORTAL_SECTIONS
    else:
        visible_sections = {
            key: data
            for key, data in PORTAL_SECTIONS.items()
            if not data.get("admin_only")
        }

    default_section = "a-matter"
    section_key = request.GET.get("section")
    home_path = reverse("authentication:home")

    if not section_key:
        if request.path == home_path:
            section_key = "dashboard"
        else:
            for key, data in visible_sections.items():
                prefixes = data.get("path_prefixes") or ()
                if any(
                    request.path == prefix or request.path.startswith(prefix + "/")
                    for prefix in prefixes
                ):
                    section_key = key
                    break

    if section_key not in visible_sections:
        section_key = default_section

    user_role = getattr(request.user, "role", "")
    user_is_co = bool(getattr(request.user, "is_co", False))

    def visible_items_for(data):
        result = []
        for item in data["items"]:
            if not item.get("url_name"):
                continue
            if item.get("admin_only") and not is_admin:
                continue
            allowed_roles = item.get("roles")
            if allowed_roles and not is_admin:
                if user_role not in allowed_roles and not (
                    user_is_co and "co" in allowed_roles
                ):
                    continue
            result.append(
                {
                    "title": item["title"],
                    "text": item["text"],
                    "url": reverse(item["url_name"]),
                }
            )
        return result

    section = visible_sections[section_key]
    items = visible_items_for(section)
    if not items and section_key != "dashboard":
        section_key = "a-matter" if "a-matter" in visible_sections else next(iter(visible_sections))
        section = visible_sections[section_key]
        items = visible_items_for(section)

    sidebar = []

    for key, data in visible_sections.items():
        preview_items = visible_items_for(data)
        if not preview_items and key != "dashboard":
            continue
        landing_url_name = data.get("landing_url_name")
        if landing_url_name:
            section_url = reverse(landing_url_name)
        else:
            section_url = f"{reverse('authentication:home')}?section={key}"

        sidebar.append(
            {
                "key": key,
                "label": data["label"],
                "icon": data["icon"],
                "url": section_url,
                "active": key == section_key,
            }
        )

    context = {
        "show_sidebar": True,
        "sidebar_sections": sidebar,
        "active_section_key": section_key,
        "active_section_label": section["label"],
        "active_section_description": section["description"],
        "section_items": items,
    }

    if is_admin and section_key == "misc":
        from common.services import get_admin_statistics

        context["admin_stats"] = get_admin_statistics()

    return context
