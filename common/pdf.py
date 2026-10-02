from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import legal
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from common.bangla_render import (
    FONT_NAME,
    BanglaText,
    bangla_paragraph,
    draw_centred_bangla_text,
    register_bangla_font,
)
from common.models import Family, Organization

FONT = register_bangla_font()
BLACK = colors.black
NA = "নাই।"
BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = {
    1: "জানুয়ারি",
    2: "ফেব্রুয়ারি",
    3: "মার্চ",
    4: "এপ্রিল",
    5: "মে",
    6: "জুন",
    7: "জুলাই",
    8: "আগস্ট",
    9: "সেপ্টেম্বর",
    10: "অক্টোবর",
    11: "নভেম্বর",
    12: "ডিসেম্বর",
}
RANK_BN = {
    "snk": "সৈনিক",
    "sainik": "সৈনিক",
    "sepoy": "সৈনিক",
    "lcpl": "ল্যান্স নায়েক",
    "l/cpl": "ল্যান্স নায়েক",
    "cpl": "নায়েক",
    "sgt": "হাবিলদার",
    "hav": "হাবিলদার",
    "wo": "ওয়ারেন্ট অফিসার",
}
TRADE_BN = {
    "COOK": "কুক",
    "CLK": "ক্লার্ক",
    "GD": "জিডি",
}


def _bn(value):
    return str(value).translate(BN_DIGITS)


def _text(value):
    if value in (None, ""):
        return "—"
    return str(value)


def _na(value):
    if value in (None, ""):
        return NA
    return str(value)


def _dari(value):
    if value in (None, ""):
        return NA
    return str(value).rstrip(" ।.") + "।"


def _recorded(*parts):
    values = []
    for part in parts:
        text = str(part).strip() if part not in (None, "") else ""
        if text and text.lower() not in {"none", "null", "-"}:
            values.append(text)
    return " ".join(values)


def _result_bn(value):
    if value in (None, "", "-"):
        return "-"
    mapping = {
        "pass": "পাস",
        "fail": "ফেল",
        "a": "এ",
        "b+": "বি+",
        "b": "বি",
    }
    return mapping.get(str(value).strip().lower(), str(value))


def _org_label(organization):
    name = str(organization or "").strip()
    compact = name.lower().replace(" ", "")
    if compact in {"1bir", "1stbir"} or name.lower() in {"1 bir", "1st bir"}:
        return "১ বীর"
    return name


def _p(text, size=10, leading=14, align=TA_LEFT, bold=False):
    return bangla_paragraph(
        escape(str(text)).replace("\n", "<br/>"),
        font_size=size,
        leading=leading,
        align=align,
    )


def _date_long(value):
    if not value:
        return NA
    return f"{_bn(value.day)} {BN_MONTHS[value.month]} {_bn(value.year)}।"


def _date_short(value):
    if not value:
        return "অদ্যাবধি"
    return f"{_bn(value.strftime('%d-%m-%Y'))}"


def _service_length(doe):
    if not doe:
        return NA
    today = date.today()
    months = (today.year - doe.year) * 12 + today.month - doe.month
    if today.day < doe.day:
        months -= 1
    months = max(months, 0)
    years, leftover = divmod(months, 12)
    return f"{_bn(years)} বছর {_bn(leftover)} মাস"


def _rank_bn(rank):
    name = str(rank or "").strip()
    return RANK_BN.get(name.lower(), name)


def _trade_bn(trade):
    if not trade:
        return ""
    return TRADE_BN.get(trade, trade)


def _members(soldier, relation):
    return [item for item in soldier.family_members.all() if item.relation == relation]


def _member_line(member):
    if member is None:
        return NA
    detail = member.name
    extras = [part for part in (member.occupation, member.remarks) if part]
    if extras:
        detail = f"{detail}, {', '.join(extras)}"
    return f"{detail}।"


def _mobile(soldier):
    numbers = [item.mobile_number for item in soldier.mobile_numbers.all() if item.mobile_number]
    if numbers:
        return numbers[0]
    for member in soldier.family_members.all():
        if member.mobile_number:
            return member.mobile_number
    return ""


def _mother_unit(organization):
    current = organization
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if current.unit_kind == Organization.KIND_UNIT:
            return _org_label(current)
        current = current.parent_organization
    return "১ বীর"


def _current_trade(soldier):
    for item in soldier.service_histories.all():
        if item.end_date is None and item.trade:
            return item.trade
    current = next(
        (item for item in soldier.service_histories.all() if item.end_date is None),
        None,
    )
    if current and current.trade:
        return current.trade
    histories = list(soldier.service_histories.all())
    if histories and histories[0].trade:
        return histories[0].trade
    return ""


def _qual_rows(soldier, kind):
    rows = []
    for qualification in soldier.qualifications.all():
        for course in qualification.courses.all():
            level = getattr(getattr(course.course_name, "level", None), "name", "") or ""
            is_cadre = "cadre" in level.lower()
            if kind == "cadre" and not is_cadre:
                continue
            if kind == "course" and is_cadre:
                continue
            rows.append(
                [
                    course.course_name.name,
                    _result_bn(course.result) if course.result else "",
                    "",
                    "",
                ]
            )
    return rows


def _inset(table, indent, width):
    wrapper = Table([["", table]], colWidths=[indent, width - indent])
    wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrapper


def _grid(data, col_widths, has_header=True):
    table = Table(data, colWidths=col_widths, repeatRows=1 if has_header else 0)
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    table.setStyle(TableStyle(commands))
    return table


def _line_table(cells, widths):
    table = Table([cells], colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 2),
                ("RIGHTPADDING", (1, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return table


def _item_row(serial, label, value, widths, empty=NA):
    display = value if value not in (None, "") else empty
    third = f"ঃ {display}" if display != "" else ""
    return _line_table(
        [_p(f"{serial}।", 10, 13), _p(label, 10, 13), _p(third, 10, 13)],
        widths,
    )


def _sub_row(mark, label, value, widths, empty=NA):
    display = value if value not in (None, "") else empty
    third = f"ঃ {display}" if display != "" else "ঃ"
    return _line_table(
        [_p(""), _p(f"{mark}. {label}", 10, 13), _p(third, 10, 13)],
        widths,
    )


PHOTO_WIDTH = 32 * mm
PHOTO_HEIGHT = 40 * mm


def _photo_stream(soldier):
    photo = getattr(soldier, "photo", None)
    if not photo or not getattr(photo, "name", None):
        return None
    try:
        photo.open("rb")
        try:
            data = photo.read()
        finally:
            photo.close()
    except (OSError, ValueError, FileNotFoundError):
        return None
    return BytesIO(data) if data else None


def _fit_image(width, height, max_width, max_height):
    if not width or not height:
        return max_width, max_height
    scale = min(max_width / width, max_height / height)
    return width * scale, height * scale


class _TitleWithPhoto(Flowable):
    """Centered dossier title with the soldier photo pinned to the top-right."""

    def __init__(self, photo_stream=None):
        super().__init__()
        self.title = BanglaText("সংক্ষিপ্ত জীবন বৃত্তান্ত", 14, 18, TA_CENTER)
        self.unit = BanglaText("১ বীর", 13, 17, TA_CENTER)
        self.photo_stream = photo_stream

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        _title_w, title_h = self.title.wrap(availWidth, availHeight)
        _unit_w, unit_h = self.unit.wrap(availWidth, availHeight)
        self._unit_h = unit_h
        self._text_h = title_h + unit_h
        self.height = max(self._text_h, PHOTO_HEIGHT if self.photo_stream else 0)
        return self.width, self.height

    def draw(self):
        text_bottom = (self.height - self._text_h) / 2
        self.title.drawOn(self.canv, 0, text_bottom + self._unit_h)
        self.unit.drawOn(self.canv, 0, text_bottom)
        if not self.photo_stream:
            return
        self.photo_stream.seek(0)
        try:
            reader = ImageReader(self.photo_stream)
            image_w, image_h = reader.getSize()
        except Exception:
            return
        draw_w, draw_h = _fit_image(image_w, image_h, PHOTO_WIDTH, PHOTO_HEIGHT)
        x = self.width - draw_w
        y = self.height - draw_h
        self.canv.drawImage(
            reader,
            x,
            y,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        self.canv.setStrokeColor(BLACK)
        self.canv.setLineWidth(0.6)
        self.canv.rect(x, y, draw_w, draw_h)


def _header_footer(canvas, document):
    canvas.saveState()
    canvas.setFillColor(BLACK)
    centre_x = document.pagesize[0] / 2
    draw_centred_bangla_text(
        canvas,
        centre_x,
        document.pagesize[1] - 14 * mm,
        "সীমিত",
        11,
    )
    draw_centred_bangla_text(canvas, centre_x, 12 * mm, _bn(document.page), 9)
    draw_centred_bangla_text(canvas, centre_x, 8 * mm, "সীমিত", 9)
    canvas.restoreState()


def build_soldier_pdf(soldier):
    buffer = BytesIO()
    page_width, _page_height = legal
    left = 14 * mm
    right = 14 * mm
    usable = page_width - left - right
    serial_w = 12 * mm
    label_w = 68 * mm
    value_w = usable - serial_w - label_w
    item_widths = [serial_w, label_w, value_w]
    inner_w = usable - serial_w

    document = SimpleDocTemplate(
        buffer,
        pagesize=legal,
        leftMargin=left,
        rightMargin=right,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"সংক্ষিপ্ত জীবন বৃত্তান্ত — {soldier.army_number} {soldier.name}",
    )

    trade = _trade_bn(_current_trade(soldier))
    identity = f"{_bn(soldier.army_number)} {_rank_bn(soldier.rank)}"
    if trade:
        identity += f" ({trade})"
    identity += f" {soldier.name}"

    father = next(iter(_members(soldier, Family.RELATION_FATHER)), None)
    mother = next(iter(_members(soldier, Family.RELATION_MOTHER)), None)
    wife = next(iter(_members(soldier, Family.RELATION_WIFE)), None)
    if wife is None:
        wife = next(iter(_members(soldier, Family.RELATION_HUSBAND)), None)
    children = _members(soldier, Family.RELATION_SON) + _members(
        soldier, Family.RELATION_DAUGHTER
    )
    siblings = _members(soldier, Family.RELATION_BROTHER) + _members(
        soldier, Family.RELATION_SISTER
    )
    brothers = _members(soldier, Family.RELATION_BROTHER)
    sisters = _members(soldier, Family.RELATION_SISTER)
    married = wife is not None
    mobile = _mobile(soldier)
    present = soldier.present_address or ""
    if mobile:
        present = f"{present}\nমোবাইলঃ {_bn(mobile)}".strip()
    permanent = soldier.permanent_address or (
        "বর্তমান ঠিকানার অনুরূপ" if soldier.present_address else ""
    )

    courses = _qual_rows(soldier, "course")
    cadres = _qual_rows(soldier, "cadre")
    sports = list(soldier.sports_trainings.all())
    medical = next(iter(soldier.medical_categories.all()), None)
    aprs = list(soldier.annual_performance_reports.all())[:3]
    histories = list(soldier.service_histories.all())
    histories.sort(key=lambda item: item.start_date or date.min)
    civil = "; ".join(
        f"{item.level}" + (f" ({item.grade})" if item.grade else "")
        for item in soldier.civil_educations.all()
    )
    special = soldier.specialist_cadre or ""
    year = date.today().year
    ipft = [row for row in soldier.ipft_records.all() if row.date.year == year]
    first_ipft = next(
        (row.result for row in ipft if row.type_of_ipft.startswith("1st")),
        "",
    )
    second_ipft = next(
        (row.result for row in ipft if row.type_of_ipft.startswith("2nd")),
        "",
    )
    ret = next(iter(soldier.ret_states.all()), None)
    march = next(iter(soldier.speed_marches.all()), None)

    story = [
        _TitleWithPhoto(_photo_stream(soldier)),
        Spacer(1, 8),
        _item_row("১", "নং, পদবী এবং নাম", identity, item_widths),
        _item_row("২", "জন্ম তারিখ", _date_long(soldier.dob), item_widths),
        _item_row("৩", "রক্তের গ্রুপ", "", item_widths),
        _item_row("৪", "বর্তমান ঠিকানা (ইউনিট ব্যতীত)", present, item_widths),
        _item_row("৫", "স্থায়ী ঠিকানা (মোবাইল নম্বর সহ)", permanent, item_widths),
        _item_row("৬", "মাতৃ ইউনিট", _mother_unit(soldier.organization), item_widths),
        _item_row("৭", "বৈবাহিক অবস্থা", "বিবাহিত" if married else "অবিবাহিত", item_widths),
        _item_row("৮", "পিতার নাম, বয়স ও পেশার বিবরণ", _member_line(father), item_widths),
        _item_row("৯", "মাতার নাম, বয়স ও পেশার বিবরণ", _member_line(mother), item_widths),
        _item_row("১০", "স্ত্রীর নাম, বয়স ও পেশার বিবরণ", _member_line(wife), item_widths),
        _item_row("১১", "শ্বশুরের নাম, বয়স ও পেশার বিবরণ", "", item_widths),
        _item_row("১২", "শাশুড়ির নাম, বয়স ও পেশার বিবরণ", "", item_widths),
        _item_row("১৩", "সন্তানাদির নাম বয়সসহ", "" if children else NA, item_widths, empty=""),
        Spacer(1, 4),
        _inset(
            _grid(
                [
                    [
                        _p("নাম", 9, 12, TA_CENTER),
                        _p("বয়স", 9, 12, TA_CENTER),
                        _p("পেশা (স্কুল/কলেজ/কর্মরত প্রতিষ্ঠানের নাম উল্লেখ করুন)", 9, 12, TA_CENTER),
                        _p("মন্তব্য", 9, 12, TA_CENTER),
                    ]
                ]
                + (
                    [
                        [
                            _p(child.name, 9),
                            _p(child.remarks or "", 9),
                            _p(child.occupation or "", 9),
                            _p("", 9),
                        ]
                        for child in children
                    ]
                    or [[_p("", 9), _p("", 9), _p("", 9), _p("", 9)]]
                ),
                [inner_w * 0.28, inner_w * 0.12, inner_w * 0.42, inner_w * 0.18],
            ),
            serial_w,
            usable,
        ),
        Spacer(1, 6),
        _item_row(
            "১৪",
            "ভাই ও বোনের নাম ও পেশা",
            f"{_bn(f'{len(brothers):02d}')} ভাই, {_bn(f'{len(sisters):02d}')} বোন"
            if siblings
            else NA,
            item_widths,
        ),
        Spacer(1, 4),
        _inset(
            _grid(
                [
                    [
                        _p("নাম এবং বয়স", 9, 12, TA_CENTER),
                        _p("সম্পর্ক", 9, 12, TA_CENTER),
                        _p("পেশা (স্কুল/কলেজ/কর্মরত প্রতিষ্ঠানের নাম উল্লেখ করুন)", 9, 12, TA_CENTER),
                        _p("মন্তব্য", 9, 12, TA_CENTER),
                    ]
                ]
                + (
                    [
                        [
                            _p(item.name, 9),
                            _p("ভাই" if item.relation == Family.RELATION_BROTHER else "বোন", 9),
                            _p(item.occupation or "", 9),
                            _p(item.remarks or "", 9),
                        ]
                        for item in siblings
                    ]
                    or [[_p("", 9), _p("", 9), _p("", 9), _p("", 9)]]
                ),
                [inner_w * 0.28, inner_w * 0.14, inner_w * 0.40, inner_w * 0.18],
            ),
            serial_w,
            usable,
        ),
        Spacer(1, 8),
        _item_row("১৫", "চাকুরীর সংক্ষিপ্ত বিবরণ", "", item_widths, empty=""),
        _sub_row("ক", "চাকুরীতে যোগদানের তারিখ", _date_long(soldier.doe), item_widths),
        _sub_row("খ", "সর্বমোট চাকুরী", _service_length(soldier.doe), item_widths),
        _sub_row(
            "গ",
            "বর্তমান পদে পদোন্নতির তারিখ",
            (
                "অপ্রয়োজনীয়।"
                if _rank_bn(soldier.rank) == "সৈনিক" or not soldier.present_rank_date
                else _date_long(soldier.present_rank_date)
            ),
            item_widths,
        ),
        _sub_row("ঘ", "পূর্ববর্তী ইউনিটে চাকুরীর বিবরণ", "", item_widths, empty=""),
        Spacer(1, 4),
    ]

    history_header = [
        [
            _p("ক্রমিক", 9, 12, TA_CENTER),
            _p("ইউনিট", 9, 12, TA_CENTER),
            _p("সময়কাল", 9, 12, TA_CENTER),
            _p("", 9),
            _p("নিয়োগ", 9, 12, TA_CENTER),
            _p("মন্তব্য", 9, 12, TA_CENTER),
        ],
        [
            _p("", 9),
            _p("", 9),
            _p("হইতে", 9, 12, TA_CENTER),
            _p("পর্যন্ত", 9, 12, TA_CENTER),
            _p("", 9),
            _p("", 9),
        ],
    ]
    history_rows = []
    for index, item in enumerate(histories, start=1):
        posting = _trade_bn(item.trade)
        history_rows.append(
            [
                _p(_bn(index) + "।", 9, 12, TA_CENTER),
                _p(_org_label(item.organization), 9),
                _p(_date_short(item.start_date), 9, 12, TA_CENTER),
                _p(_date_short(item.end_date), 9, 12, TA_CENTER),
                _p(posting, 9),
                _p("", 9),
            ]
        )
    if not history_rows:
        history_rows = [[_p("১।", 9, 12, TA_CENTER), _p("", 9), _p("", 9), _p("", 9), _p("", 9), _p("", 9)]]
    inner_history = _grid(
        history_header + history_rows,
        [inner_w * 0.10, inner_w * 0.22, inner_w * 0.16, inner_w * 0.16, inner_w * 0.20, inner_w * 0.16],
    )
    inner_history.setStyle(
        TableStyle(
            [
                ("SPAN", (2, 0), (3, 0)),
                ("SPAN", (0, 0), (0, 1)),
                ("SPAN", (1, 0), (1, 1)),
                ("SPAN", (4, 0), (4, 1)),
                ("SPAN", (5, 0), (5, 1)),
                ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ]
        )
    )
    story.extend([_inset(inner_history, serial_w, usable), Spacer(1, 8)])

    story.append(_item_row("১৬", "সামরিক শিক্ষাগত যোগ্যতা (ফলাফল সহ)।", "", item_widths, empty=""))
    story.append(_sub_row("ক", "কোর্স", "" if courses else NA, item_widths, empty="" if courses else NA))
    story.append(Spacer(1, 4))
    course_table_rows = [
        [
            _p("ক্রমিক", 9, 12, TA_CENTER),
            _p("কোর্সের নাম", 9, 12, TA_CENTER),
            _p("ফলাফল", 9, 12, TA_CENTER),
            _p("অবস্থান", 9, 12, TA_CENTER),
            _p("মন্তব্য", 9, 12, TA_CENTER),
        ]
    ]
    source = courses or [("", "", "", "")]
    for index, row in enumerate(source, start=1):
        course_table_rows.append(
            [
                _p(_bn(index) + "।", 9, 12, TA_CENTER),
                _p(row[0], 9),
                _p(row[1], 9, 12, TA_CENTER),
                _p(row[2] or "", 9, 12, TA_CENTER),
                _p(row[3], 9),
            ]
        )
    story.append(
        _inset(
            _grid(
                course_table_rows,
                [inner_w * 0.10, inner_w * 0.34, inner_w * 0.16, inner_w * 0.20, inner_w * 0.20],
            ),
            serial_w,
            usable,
        )
    )
    story.extend(
        [
            Spacer(1, 6),
            _sub_row("খ", "ক্যাডার", "" if cadres else NA, item_widths, empty="" if cadres else NA),
            Spacer(1, 4),
        ]
    )
    cadre_table_rows = [
        [
            _p("ক্রমিক", 9, 12, TA_CENTER),
            _p("ক্যাডারের নাম", 9, 12, TA_CENTER),
            _p("ফলাফল", 9, 12, TA_CENTER),
            _p("অবস্থান", 9, 12, TA_CENTER),
            _p("মন্তব্য", 9, 12, TA_CENTER),
        ]
    ]
    source = cadres or [("", "", "", "")]
    for index, row in enumerate(source, start=1):
        cadre_table_rows.append(
            [
                _p(_bn(index) + "।", 9, 12, TA_CENTER),
                _p(row[0], 9),
                _p(row[1], 9, 12, TA_CENTER),
                _p(row[2] or "-", 9, 12, TA_CENTER),
                _p(row[3], 9),
            ]
        )
    story.append(
        _inset(
            _grid(
                cadre_table_rows,
                [inner_w * 0.10, inner_w * 0.34, inner_w * 0.16, inner_w * 0.20, inner_w * 0.20],
            ),
            serial_w,
            usable,
        )
    )

    story.extend(
        [
            Spacer(1, 8),
            _item_row("১৭", "সর্বশেষ ০৩ বছরের এপিআর (গ্রেডিং সহ)", "", item_widths, empty=""),
            Spacer(1, 4),
        ]
    )
    apr_rows = [
        [
            _p("ক্রমিক", 9, 12, TA_CENTER),
            _p("বছর", 9, 12, TA_CENTER),
            _p("প্লাটুন কমাডার", 9, 12, TA_CENTER),
            _p("কোম্পানি কমাডার", 9, 12, TA_CENTER),
            _p("মন্তব্য", 9, 12, TA_CENTER),
        ]
    ]
    apr_source = (list(aprs) + [None, None, None])[:3]
    for index, item in enumerate(apr_source, start=1):
        grade = ""
        year_value = ""
        if item is not None:
            year_value = _bn(item.year)
            grade = item.report or (str(item.score) if item.score is not None else "")
        apr_rows.append(
            [
                _p(_bn(index) + "।", 9, 12, TA_CENTER),
                _p(year_value, 9, 12, TA_CENTER),
                _p(grade, 9, 12, TA_CENTER),
                _p(grade, 9, 12, TA_CENTER),
                _p("", 9),
            ]
        )
    story.append(
        _inset(
            _grid(
                apr_rows,
                [inner_w * 0.10, inner_w * 0.14, inner_w * 0.28, inner_w * 0.28, inner_w * 0.20],
            ),
            serial_w,
            usable,
        )
    )

    sports_text = "; ".join(
        f"{item.name_of_comp}"
        + (f" ({item.significant_achievement})" if item.significant_achievement else "")
        for item in sports
    )
    height_parts = []
    if soldier.height_feet is not None:
        height_parts.append(f"{_bn(soldier.height_feet)} ফুট")
    if soldier.height_inches is not None:
        height_parts.append(f"{_bn(soldier.height_inches)} ইঞ্চি")
    height = " ".join(height_parts)
    overweight = _bn(soldier.overweight) if soldier.overweight else ""

    story.extend(
        [
            Spacer(1, 6),
            _item_row("১৮", "বেসামরিক শিক্ষাগত যোগ্যতা", _dari(civil) if civil else "", item_widths),
            _item_row("১৯", "খেলাধুলা", sports_text, item_widths),
            _item_row("২০", "বিশেষ কোন যোগ্যতা", special, item_widths),
            _item_row("২১", "ডাক্তারী শ্রেণীবিন্যাস", medical.type if medical else "", item_widths),
            _item_row("২২", "শারীরিক কোন সমস্যা আছে কিনা\n(সমস্যা থাকলে তার সংক্ষিপ্ত বিবরণ)", "", item_widths),
            _item_row("২৩", "ওজন এবং উচ্চতা", height, item_widths),
            _item_row("২৪", "অতিরিক্ত ওজন", overweight, item_widths),
            _item_row(
                "২৫",
                "আচরণ বিবরণী (লাল/কালো কালি ধারা সহ উল্লেখ করুন) ঘটনার সংক্ষিপ্ত বিবরণ",
                _recorded(soldier.discipline, soldier.punishment),
                item_widths,
            ),
        ]
    )

    ipft_table = Table(
        [
            [
                _p(f"আইপিএফটি {_bn(year)}", 9, 12, TA_CENTER),
                _p("", 9),
                _p("আরইটি", 9, 12, TA_CENTER),
                _p("স্পীড মার্চ", 9, 12, TA_CENTER),
                _p("মন্তব্য", 9, 12, TA_CENTER),
            ],
            [
                _p("১ম অর্ধ বাৎসরিক", 9, 12, TA_CENTER),
                _p("২য় অর্ধ বাৎসরিক", 9, 12, TA_CENTER),
                _p("", 9),
                _p("", 9),
                _p("", 9),
            ],
            [
                _p(_result_bn(first_ipft), 9, 12, TA_CENTER),
                _p(_result_bn(second_ipft), 9, 12, TA_CENTER),
                _p(_result_bn(ret.result if ret else ""), 9, 12, TA_CENTER),
                _p(_result_bn(march.result if march else ""), 9, 12, TA_CENTER),
                _p("", 9),
            ],
        ],
        colWidths=[inner_w * 0.20, inner_w * 0.20, inner_w * 0.18, inner_w * 0.22, inner_w * 0.20],
    )
    ipft_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("GRID", (0, 0), (-1, -1), 0.5, BLACK),
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (2, 0), (2, 1)),
                ("SPAN", (3, 0), (3, 1)),
                ("SPAN", (4, 0), (4, 1)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(
        KeepTogether(
            [
                _item_row("২৬", "শারীরিক যোগ্যতা", "যোগ্য।", item_widths),
                Spacer(1, 4),
                _inset(ipft_table, serial_w, usable),
                Spacer(1, 8),
                _item_row(
                    "২৭",
                    "পারিবারিক কোন কলহ আছে কিনা এবং ফৌজদারী ও অন্য কোন মামলায় জড়িত আছে কিনা",
                    NA,
                    item_widths,
                ),
                Spacer(1, 18),
                Table(
                    [[_p("ব্যক্তিগত স্বাক্ষর", 10, 14, TA_CENTER)]],
                    colWidths=[usable * 0.45],
                    hAlign="RIGHT",
                ),
                Spacer(1, 16),
                _p("সদর কোম্পানী সিনিয়র জেসিওর মতামত/ সুপারিশ ________________________________", 10, 14),
                Spacer(1, 10),
                _p("সদর কোম্পানী অধিনায়কের মতামত/সুপারিশ ________________________________", 10, 14),
            ]
        )
    )

    document.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buffer.seek(0)
    return buffer


def _section_table(title, headers, rows, styles):
    """Kept for duty roster PDFs that import this helper."""
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph as RLParagraph

    styles = styles or getSampleStyleSheet()
    flowables = [RLParagraph(title, styles["Heading2"])]
    if not rows:
        flowables.append(RLParagraph("None recorded.", styles["Normal"]))
        flowables.append(Spacer(1, 6))
        return flowables
    data = [headers, *rows]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.90, 0.90, 0.88)),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.7, 0.7, 0.7)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    flowables.append(table)
    flowables.append(Spacer(1, 8))
    return flowables
<<<<<<< HEAD


def build_soldier_pdf(soldier):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"1 BIR — {soldier.army_number} {soldier.name}",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("1 BIR — Soldier Record", styles["Title"]),
        Paragraph(
            f"{_text(soldier.army_number)} · {_text(soldier.rank)} · {_text(soldier.name)}",
            styles["Heading3"],
        ),
        Spacer(1, 6),
    ]

    particulars = [
        ["Organization", _text(soldier.organization)],
        ["Date of birth", _text(soldier.dob)],
        ["Enrollment", _text(soldier.doe)],
        ["Age", _text(soldier.age)],
        ["Service years", _text(soldier.service_years)],
        ["Batch", _text(soldier.batch)],
        ["NID", _text(soldier.nid_number)],
        ["Passport", _text(soldier.passport_number)],
        ["Service ID", _text(soldier.service_id_card_number)],
        ["Present district", _text(soldier.present_district)],
        ["Present upazila", _text(soldier.present_upazila)],
        ["Present thana", _text(soldier.present_thana)],
        ["Present area/road/house", _text(soldier.present_area_road_house)],
        ["Permanent district", _text(soldier.permanent_district)],
        ["Permanent upazila", _text(soldier.permanent_upazila)],
        ["Permanent thana", _text(soldier.permanent_thana)],
        ["Permanent area/road/house", _text(soldier.permanent_area_road_house)],
        ["Discipline", _text(soldier.discipline)],
        ["Punishment", _text(soldier.punishment)],
    ]
    story.extend(_section_table("Particulars", ["Field", "Value"], particulars, styles))

    story.extend(
        _section_table(
            "Service history",
            ["Organization", "Rank", "Start", "End"],
            [
                [
                    _text(item.organization),
                    _text(item.rank),
                    _text(item.start_date),
                    _text(item.end_date),
                ]
                for item in soldier.service_histories.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Civil education",
            ["Level", "Institution", "From", "To", "Grade"],
            [
                [
                    _text(item.level),
                    _text(item.institution_name),
                    _text(item.from_date),
                    _text(item.to_date),
                    _text(item.grade),
                ]
                for item in soldier.civil_educations.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Medical category",
            ["Type", "From", "To"],
            [
                [_text(item.type), _text(item.from_date), _text(item.to_date)]
                for item in soldier.medical_categories.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Annual performance",
            ["Year", "Score", "Report"],
            [
                [_text(item.year), _text(item.score), _text(item.report)]
                for item in soldier.annual_performance_reports.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Appointments",
            ["Appointment", "Organization", "Start", "End"],
            [
                [
                    _text(item.appointment_name),
                    _text(item.organization),
                    _text(item.start_date),
                    _text(item.end_date),
                ]
                for item in soldier.appointment_histories.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Family",
            ["Relation", "Name", "Mobile", "Occupation", "Remarks"],
            [
                [
                    _text(item.get_relation_display()),
                    _text(item.name),
                    _text(item.mobile_number),
                    _text(item.occupation),
                    _text(item.remarks),
                ]
                for item in soldier.family_members.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Contact",
            ["Type", "Number"],
            [
                [_text(item.get_type_of_number_display()), _text(item.mobile_number)]
                for item in soldier.mobile_numbers.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Leave",
            ["Slot", "Type", "From", "To", "Status"],
            [
                [
                    _text(item.get_slot_display()),
                    _text(item.leave_type),
                    _text(item.from_date),
                    _text(item.to_date),
                    _text(item.get_status_display()),
                ]
                for item in soldier.leave_states.all()
            ],
            styles,
        )
    )
    story.extend(
        _section_table(
            "Qualifications",
            ["Year", "PE", "SPL", "Next promotion"],
            [
                [
                    _text(item.year),
                    _text(item.pe),
                    _text(item.spl),
                    "Yes" if item.qual_for_next_promotion else "No",
                ]
                for item in soldier.qualifications.all()
            ],
            styles,
        )
    )

    document.build(story)
    buffer.seek(0)
    return buffer
=======
>>>>>>> backup/local-full-wip
