import argparse
import enum
import json
import os.path

from . import deepl
from . import umgtext2xml


REMAP_TARGET_LANG = {deepl.TargetLanguage.ZH_HANS: "zh_CN", deepl.TargetLanguage.ZH_HANT: "zh_TW"}


def get_lang_lower(tgt: deepl.SourceLanguage | deepl.TargetLanguage) -> str:
    result = REMAP_TARGET_LANG.get(tgt)  # type: ignore

    if result is None:
        enumval = tgt.value
        if len(enumval) > 2:
            result = enumval[:2].lower() + enumval[2:].upper()
        else:
            result = enumval.lower()

    return result


def parse_exclusion(string: str):
    splitted = string.split(":", 1)
    if len(splitted) != 2:
        raise ValueError("invalid exclusion specifier")
    return (splitted[0], splitted[1])


def enumval(e: type[enum.Enum]):
    return list(map(lambda k: k.value, e))


class Args:
    source_lang: deepl.SourceLanguage | None
    target_lang: deepl.TargetLanguage
    free: bool
    apikey: str
    output: str
    exclude_dir: list[tuple[str, str]] | None
    localization: list[str]


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--exclude-dir",
        help="Additional translation string to exclude in format modname:path/to/localization/folder.",
        type=parse_exclusion,
        action="append",
    )
    parser.add_argument(
        "--source-lang",
        help="Source language of input string (if absent, let DeepL auto-guess).",
        type=deepl.SourceLanguage,
    )
    parser.add_argument(
        "--target-lang",
        help="Target language of output string.",
        type=deepl.TargetLanguage,
        required=True,
    )
    parser.add_argument("--free", help="APIKey is free API key (use different endpoint)", action="store_true")
    parser.add_argument("--apikey", help="DeepL API key", required=True)
    parser.add_argument("--output", help="Output directory, each directory contains modname", required=True)
    parser.add_argument("localization", help="localization.json file", nargs="+")
    args = parser.parse_args(namespace=Args())

    translator = deepl.Translator(args.apikey, free=args.free)

    # Phase 1: Collect all strings that have been translated
    lang_filename = get_lang_lower(args.target_lang) + ".json"
    exclude_translation: dict[str, set[str]] = {}
    translated_localization_by_mod: dict[str, set[str]] = {}

    if args.exclude_dir:
        for modname, locpath in args.exclude_dir:
            exclude_translation.setdefault(modname, set())

            locfile = os.path.join(locpath, lang_filename)
            if os.path.isfile(locfile):
                with open(locfile, "r", encoding="utf-8", newline="") as f:
                    modjsondata: dict[str, str] = json.load(f)

                exclude_translation[modname].update(modjsondata.keys())

    # Phase 2: Get localization.json file
    for locfile in args.localization:
        with open(locfile, "r", encoding="utf-8", newline="") as f:
            locjsondata: dict[str, dict[str, str]] = json.load(f)

        for modname, tdata in locjsondata.items():
            if modname not in translated_localization_by_mod:
                translated_localization_by_mod[modname] = set()

            if modname not in exclude_translation:
                exclude_translation[modname] = set()

            translated_localization_by_mod[modname].update(
                k for k in tdata.keys() if k not in exclude_translation[modname]
            )

    # Phase 3: hit the DeepL API
    billed = 0

    for modname, keys_to_translate in translated_localization_by_mod.items():
        if len(keys_to_translate) > 0:
            listkeys = list(keys_to_translate)  # Ensure consistent ordering
            destdir = os.path.join(args.output, modname)
            os.makedirs(destdir, exist_ok=True)
            result, billed_count = translator(
                args.target_lang,
                [umgtext2xml.umgtext2xml(t) for t in listkeys],
                source_lang=args.source_lang,
                tag_handling=deepl.TagHandling.XML,
                outline_detection=False,
            )
            billed = billed + billed_count

            with open(os.path.join(destdir, lang_filename), "w", encoding="utf-8", newline="") as f:
                result = dict((k, umgtext2xml.xml2umgtext(v.text)) for k, v in zip(listkeys, result))
                json.dump(result, f, indent="\t", ensure_ascii=False)

            print(f"Strings for mod '{modname}' has been translated")

    print("Billed characters:", billed)


if __name__ == "__main__":
    main()
