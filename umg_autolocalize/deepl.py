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


class DeepLResponse(pydantic.BaseModel):
    pass


MAX_REQUEST_SIZE = 128000


class Translator:
    def __init__(self, apikey: str, /, *, free: bool = False):
        self.endpoint = "https://api-free.deepl.com/v2/translate" if free else "https://api.deepl.com/v2/translate"
        self.key = apikey
        self.httpx = httpx.Client(http2=True)

    def __call__(
        self,
        target_lang: TargetLanguage,
        text: list[str],
        /,
        *,
        source_lang: SourceLanguage | None = None,
        context: str | None = None,
        tag_handling: TagHandling | None = None,
    ):
        request = DeepLRequest(
            text=[""], source_lang=source_lang, target_lang=target_lang, context=context, tag_handling=tag_handling
        )
        overhead = len(request.model_dump_json().encode("utf-8"))

        for i, txt in enumerate(text):
            if len(txt.encode("utf-8")) + overhead >= MAX_REQUEST_SIZE:
                raise ValueError("string at index {i} is too large")

        result: list[str] = []
        start = 0
        stop = len(text)
        billed = 0

        while start < stop:
            # The reason we need to split this because DeepL has limit of 128K request body.
            request.text = text[start:stop]
            request_bytes = request.model_dump_json().encode("utf-8")
            if len(request_bytes) >= MAX_REQUEST_SIZE:
                stop = stop - 1

            if stop < start:
                raise ValueError(f"translation text at index {start} is too long")

    def _hit_api(self, req: bytes):
        response = self.httpx.post(
            self.endpoint,
            content=req,
            headers={"Content-Type": "application/json", "Authorization": f"DeepL-Auth-Key {self.key}"},
        )
        response.raise_for_status()
        return DeepLResponse.model_validate(response.json())
