"""Country and region codes the product accepts.

Countries are ISO 3166-1 alpha-2 codes (the 249 officially assigned). Names, aliases and
search live in the frontend (``frontend/src/lib/countries.ts``); the backend only checks
that a stored code is real. Region groups are Verity's own reserved codes for answers such
as "my customers are across the European Union", expanded where a rule needs countries.
"""

from __future__ import annotations

from typing import Final

_ISO_CODES: Final = """
    AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR
    BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ
    EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW
    GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY
    KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV
    MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY
    QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG
    TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM
    ZW
"""
_EU_CODES: Final = (
    "AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK"
)

ISO_3166_ALPHA2: Final[frozenset[str]] = frozenset(_ISO_CODES.split())
EU_MEMBERS: Final[frozenset[str]] = frozenset(_EU_CODES.split())
EEA_MEMBERS: Final[frozenset[str]] = EU_MEMBERS | {"IS", "LI", "NO"}
GCC_MEMBERS: Final[frozenset[str]] = frozenset({"AE", "BH", "KW", "OM", "QA", "SA"})

REGIONS: Final[dict[str, frozenset[str]]] = {
    "EU": EU_MEMBERS,
    "EEA": EEA_MEMBERS,
    "GCC": GCC_MEMBERS,
    "WORLD": ISO_3166_ALPHA2,
}
"""Reserved region codes and the countries each stands for."""


def is_country(code: str) -> bool:
    return code in ISO_3166_ALPHA2


def is_country_or_region(code: str) -> bool:
    return code in ISO_3166_ALPHA2 or code in REGIONS


def expand(codes: list[str]) -> set[str]:
    """Countries named directly or through a region group."""
    out: set[str] = set()
    for code in codes:
        out |= REGIONS.get(code, frozenset({code}))
    return out
