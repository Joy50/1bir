CADRE_NAMES = [
    "All cdr",
    "BTT (Inf)",
    "Arms Cdo",
    "SvcsCdo",
    "BMR",
    "PC (Inf)",
    "ATT (Inf)",
    "MG",
    "MOR",
    "ATGW (Metis M-1)",
    "AGL",
    "SAGL",
    "Cbt life Saver Offr",
    "Cbt life Saver OR",
    "MT Dvr&Maint (RamuCantt)",
    "AC Bus Dvr&Maint",
    "Kote and Mag NCO",
    "Marksmanship",
    "Dtmn",
    "Sig",
    "AsltPnr",
    "Com",
    "APC Dvr&Maint",
    "ORBIC",
    "Arty Observer",
    "CIED",
    "ATW PF-98",
    "RGW-19",
    "ORs Sy Awareness and sit response",
]

COURSE_NAMES = [
    "UNMOC",
    "Core PDTC",
    "NCOC (Arty)",
    "VVOC",
    "PC",
    "ALC",
    "JNGSC (Fd)",
    "NCOC (ASC)",
    "EJBC",
    "EMC",
    "TA&SC",
    "HVDC",
    "OSC",
    "EP T3",
    "CIMIC",
    "ARIC Gnr (Fd)",
    "OAMTC",
    "BTT",
    "FLC",
    "PCAT",
    "OGSC (Fd)",
    "JOAC",
    "UNMPKI (NL)",
    "PPCC",
    "ARIC Gnr (AD)",
    "MWDC",
    "OBC (Fd)",
    "OBC (AMC/ADC)",
    "WGSOC",
    "ITLS (Ph-2)",
    "OBC (AD)",
    "NCOC (Inf)",
    "UNSOC",
    "JCSC",
    "ARIC (DMT)",
    "43 st/nd DSSC (AFNS)",
    "JCOC",
    "PDTC (ToT)",
    "MIC",
    "NAC",
    "OBC (Inf)",
    "Spl BTT (Clk)",
    "NCOC (AMC)",
    "UNMOC-27",
    "UCSC",
    "ARIC (TA&S)",
    "OWC",
    "OBIDC",
    "DPC",
    "IAC",
    "AGLC",
    "BIDC",
    "IEDDC",
    "ORBIC",
    "BCC",
    "OBC (Engrs)",
    "CC&SBC",
    "BIC",
    "SNIC",
    "PMC",
    "OPC",
    "NCOC (Engr)",
    "ATOC",
    "MBBC",
    "ACC",
    "GMT (Edn JCO)",
    "CL&MTUC",
    "OMC",
    "CIEDC",
    "OBC (Ord)",
    "MBAC",
    "OAFC",
    "BMC",
    "MGC",
    "NCOC (Ord)",
    "FIC",
    "DIC (Female)",
    "ABC",
    "UNLOC",
    "CEIC",
    "HIC",
    "ITLS (Ph-3)",
    "JNFWC",
    "GOEC",
    "AMBC",
    "ATC",
    "NCOC (Sigs)",
    "AAC",
    "TMCC",
    "SLC",
    "NCOC",
    "CPOC (ToT)",
    "CSC",
    "FSC",
    "ALSC",
    "EPM",
    "FFC",
    "MSC",
    "UNCCC",
    "CTC",
    "BWDHC",
    "JMC",
    "CP&SEC",
    "NCOC (RVFC)",
    "UAVMCC",
    "NCOC (AC)",
    "DFIC",
    "AESDTC",
    "UAVMBC",
    "DMIC",
    "EC",
    "UAVPBC",
    "WPSC",
    "WIC",
    "JNIIC",
    "UAVPOOC",
    "OAIC",
    "OBC (AC)",
    "DIC",
    "OMPC",
    "CMC",
    "IHL Trg",
    "ARC",
    "LMC",
    "OBC (AEC)",
    "ATT",
    "EJRC",
    "C-UAS Trg",
    "GIC",
    "OBC (ASC)",
]

COMPETITION_NAMES = [
    "Kabadi",
    "Azan Cricket",
    "Hockey",
    "Aquatic",
    "Volleyball",
    "Boxing",
    "Football",
    "Basketball",
    "Trg Aid Display",
    "Bayonet Ftg",
    "Firing",
    "Quiz",
    "Drill",
    "CAS Trophy Firing",
    "Aslt Course",
]

TRAINING_COMPETITIONS = {
    "Trg Aid Display",
    "Bayonet Ftg",
    "Firing",
    "Quiz",
    "Drill",
    "CAS Trophy Firing",
    "Aslt Course",
}

COMPETITION_CHOICES = [(name, name) for name in COMPETITION_NAMES]

ACHIEVEMENT_GOLD = "GOLD MEDAL"
ACHIEVEMENT_SILVER = "SILVER MEDAL"
ACHIEVEMENT_BRONZE = "BRONZE MEDAL"
ACHIEVEMENT_CHOICES = [
    (ACHIEVEMENT_GOLD, "GOLD MEDAL"),
    (ACHIEVEMENT_SILVER, "SILVER MEDAL"),
    (ACHIEVEMENT_BRONZE, "BRONZE MEDAL"),
]

RESULT_A = "A"
RESULT_B_PLUS = "B+"
RESULT_B = "B"
RESULT_PASS = "Pass"
COURSE_RESULT_CHOICES = [
    (RESULT_A, "A"),
    (RESULT_B_PLUS, "B+"),
    (RESULT_B, "B"),
]
CADRE_RESULT_CHOICES = COURSE_RESULT_CHOICES + [(RESULT_PASS, "Pass")]

CADRE_LEVELS = ("Bde Lvl Cadre", "Div Lvl Cadre")
COURSE_LEVELS = ("Army Lvl Course", "Misc Trg")


def competition_kind(name):
    if name in TRAINING_COMPETITIONS:
        return "training"
    return "sports"


def is_cadre_level(level_name):
    return "cadre" in (level_name or "").lower()


def result_choices_for_level(level_name):
    if is_cadre_level(level_name):
        return CADRE_RESULT_CHOICES
    return COURSE_RESULT_CHOICES
