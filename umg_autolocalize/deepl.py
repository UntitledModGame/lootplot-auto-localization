import collections.abc
import enum

import httpx
import pydantic


class SourceLanguage(enum.Enum):
    BG = "BG"
    CS = "CS"
    DA = "DA"
    DE = "DE"
    EL = "EL"
    EN = "EN"
    ES = "ES"
    ET = "ET"
    FI = "FI"
    FR = "FR"
    HU = "HU"
    ID = "ID"
    IT = "IT"
    JA = "JA"
    KO = "KO"
    LT = "LT"
    LV = "LV"
    NB = "NB"
    NL = "NL"
    PL = "PL"
    PT = "PT"
    RO = "RO"
    RU = "RU"
    SK = "SK"
    SL = "SL"
    SV = "SV"
    TR = "TR"
    UK = "UK"
    ZH = "ZH"


class TargetLanguage(enum.Enum):
    AR = "AR"
    BG = "BG"
    CS = "CS"
    DA = "DA"
    DE = "DE"
    EL = "EL"
    EN_GB = "EN-GB"
    EN_US = "EN-US"
    ES = "ES"
    ET = "ET"
    FI = "FI"
    FR = "FR"
    HU = "HU"
    ID = "ID"
    IT = "IT"
    JA = "JA"
    KO = "KO"
    LT = "LT"
    LV = "LV"
    NB = "NB"
    NL = "NL"
    PL = "PL"
    PT_BR = "PT-BR"
    PT_PT = "PT-PT"
    RO = "RO"
    RU = "RU"
    SK = "SK"
    SL = "SL"
    SV = "SV"
    TR = "TR"
    UK = "UK"
    ZH = "ZH"
    ZH_HANS = "ZH-HANS"
    ZH_HANT = "ZH-HANT"


class SplitSentences(enum.Enum):
    NO_SPLITTING = "0"
    SPLIT_ON_PUNCTUATION = "1"
    NONEWLINES = "nonewlines"


class Formality(enum.Enum):
    DEFAULT = "default"
    MORE = "more"
    LESS = "less"
    PREFER_MORE = "prefer_more"
    PREFER_LESS = "prefer_less"


class ModelType(enum.Enum):
    LATENCY_OPTIMIZED = "latency_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    PREFER_QUALITY_OPTIMIZED = "prefer_quality_optimized"


class TagHandling(enum.Enum):
    HTML = "html"
    XML = "xml"


class DeepLRequest(pydantic.BaseModel):
    text: list[str]
    source_lang: SourceLanguage | None = None
    target_lang: TargetLanguage
    context: str | None = None
    show_billed_characters: bool = True
    split_sentences: SplitSentences | None = None
    formality: Formality | None = None
    model_type: ModelType | None = None
    tag_handling: TagHandling | None = None
    outline_detection: bool | None = None
    non_splitting_tags: list[str] | None = None
    splitting_tags: list[str] | None = None


class DeepLTranslation(pydantic.BaseModel):
    detected_source_language: SourceLanguage
    text: str
    billed_characters: int


class DeepLResponse(pydantic.BaseModel):
    translations: list[DeepLTranslation]


MAX_REQUEST_SIZE = 128000


def _count_billed(t: collections.abc.Sequence[DeepLTranslation]):
    billed = 0
    for tinfo in t:
        billed = billed + tinfo.billed_characters
    return billed


class RequestTooLarge(ValueError):
    pass


class Translator:
    def __init__(self, apikey: str, /, *, free: bool = False):
        self.endpoint = "https://api-free.deepl.com/v2/translate" if free else "https://api.deepl.com/v2/translate"
        self.key = apikey
        self.httpx = httpx.Client(http2=True)

    def __call__(
        self,
        target_lang: TargetLanguage,
        text: collections.abc.Iterable[str],
        /,
        *,
        source_lang: SourceLanguage | None = None,
        context: str | None = None,
        tag_handling: TagHandling | None = None,
        outline_detection: bool | None = None,
        non_splitting_tags: collections.abc.Iterable[str] | None = None,
        splitting_tags: collections.abc.Iterable[str] | None = None,
    ):
        request = DeepLRequest(
            text=list(text),
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            tag_handling=tag_handling,
            outline_detection=outline_detection,
            non_splitting_tags=None if non_splitting_tags is None else list(non_splitting_tags),
            splitting_tags=None if splitting_tags is None else list(splitting_tags),
        )
        request_bytes = request.model_dump_json().encode("utf-8")
        if len(request_bytes) > MAX_REQUEST_SIZE:
            raise RequestTooLarge("request size too large")

        response = self._hit_api(request_bytes)
        return response.translations, _count_billed(response.translations)

    def can_send(
        self,
        target_lang: TargetLanguage,
        text: collections.abc.Iterable[str],
        /,
        *,
        source_lang: SourceLanguage | None = None,
        context: str | None = None,
        tag_handling: TagHandling | None = None,
        outline_detection: bool | None = None,
        non_splitting_tags: collections.abc.Iterable[str] | None = None,
        splitting_tags: collections.abc.Iterable[str] | None = None,
    ):
        request = DeepLRequest(
            text=list(text),
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
            tag_handling=tag_handling,
            outline_detection=outline_detection,
            non_splitting_tags=None if non_splitting_tags is None else list(non_splitting_tags),
            splitting_tags=None if splitting_tags is None else list(splitting_tags),
        )
        request_bytes = request.model_dump_json().encode("utf-8")
        return len(request_bytes) <= MAX_REQUEST_SIZE

    def _hit_api(self, req: bytes):
        response = self.httpx.post(
            self.endpoint,
            content=req,
            headers={"Content-Type": "application/json", "Authorization": f"DeepL-Auth-Key {self.key}"},
        )
        response.raise_for_status()
        responnse_json = response.json()
        return DeepLResponse.model_validate(responnse_json)
