import html
import io

NPOS = 2**64 - 1


def umgtext2xml(umgtext: str):
    wholetext = umgtext
    active_tags: list[str] = []

    with io.StringIO() as f:
        while umgtext:
            percent = umgtext.find("%")
            curly_bracket = umgtext.find("{")
            if percent == -1:
                percent = NPOS
            if curly_bracket == -1:
                curly_bracket = NPOS

            pos = min(percent, curly_bracket)

            if percent > curly_bracket:
                f.write(html.escape(umgtext[:pos]))
                # Handle curly brackets

                if umgtext[pos + 1] == "{":
                    # Escaping.
                    f.write("{")
                    umgtext = umgtext[pos + 2 :]
                else:
                    # Parse text effect
                    endtagpos = pos

                    while True:
                        endtagpos = umgtext.find("}", endtagpos)
                        if endtagpos == -1:
                            raise ValueError("unclosed opening tag: " + wholetext)
                        try:
                            if umgtext[endtagpos + 1] == "}":
                                endtagpos = endtagpos + 2
                            else:
                                break
                        except IndexError:
                            # I'm lazy
                            break

                    tags_and_params = list(filter(None, umgtext[pos + 1 : endtagpos].split()))
                    # Advance
                    umgtext = umgtext[endtagpos + 1 :]

                    closing = False
                    if len(tags_and_params) == 1:
                        tag = tags_and_params[0]

                        if tag[0] == "/":
                            # Closing tag
                            closing = True
                            found = False

                            for i in range(len(active_tags) - 1, -1, -1):
                                if active_tags[i] == tag[1:]:
                                    found = True
                                    assert active_tags.pop(i) == tag[1:]
                                    f.write(f"<{tag}>")
                                    break

                            if not found:
                                print(f"warn: unknown tag {tag[1:]}: {wholetext}")
                        else:
                            # Shortcut, write tag only
                            f.write(f"<{tag}>")
                    else:
                        # Write tag and attributes
                        xmlparams: list[str] = []
                        f.write(f"<{tags_and_params[0]} ")

                        for param in tags_and_params[1:]:
                            equal_sign = param.find("=")
                            if equal_sign == -1:
                                raise ValueError("invalid effect parameter specifier: " + wholetext)
                            xmlparams.append(f'{param[:equal_sign]}="{param[equal_sign+1:]}"')

                        f.write(" ".join(xmlparams))
                        f.write(">")
                    if not closing:
                        active_tags.append(tags_and_params[0])

            elif curly_bracket > percent:
                f.write(html.escape(umgtext[:pos]))

                # Handle percent sign
                if pos < (len(umgtext) - 1) and umgtext[pos + 1] == "{":
                    # Handle variable
                    endtagpos = umgtext.find("}", pos)
                    if endtagpos == -1:
                        raise ValueError("unclosed variable tag")
                    f.write(f"<umgvar:{umgtext[pos+2:endtagpos]}/>")
                    umgtext = umgtext[endtagpos + 1 :]
                else:
                    # False alarm
                    f.write("%")
                    umgtext = umgtext[pos + 1 :]
            else:
                # Note: percent == curly_bracket means both is NPOS.
                assert percent == NPOS and curly_bracket == NPOS
                f.write(html.escape(umgtext))
                break

        # Ensure rest of the tags is closed properly.
        for i in range(len(active_tags) - 1, -1, -1):
            f.write(f"</{active_tags[i]}>")

        return f.getvalue()


def xml2umgtext(xml: str):
    """Note: It actually only supports input from umgtext2xml function!"""

    f = io.StringIO()
    active_tags: list[str] = []
    wholetext = xml

    with io.StringIO() as f:
        while xml:
            starttagpos = xml.find("<")

            if starttagpos >= 0:
                f.write(html.unescape(xml[:starttagpos]))
                endtagpos = xml.find(">", starttagpos)
                if endtagpos == -1:
                    raise ValueError("unclosed tag: " + wholetext)

                tags_and_attrs = list(filter(None, xml[starttagpos + 1 : endtagpos].strip().split()))
                closing = False
                tag = tags_and_attrs[0]
                if tag[0] == "/":
                    # Closing tag
                    closing = True
                    found = False

                    for i in range(len(active_tags) - 1, -1, -1):
                        if active_tags[i] == tag[1:]:
                            found = True
                            assert active_tags.pop(i) == tag[1:]
                            f.write(f"{{{tag}}}")  # includes closing tag
                            break

                    if not found:
                        raise ValueError(f"unknown tag {tag[1:]}: {wholetext}")
                elif tag[-1] == "/" or (len(tags_and_attrs) > 1 and tags_and_attrs[1] == "/"):
                    # Opening and closing tag, likely be variable
                    if tag[:6] != "umgvar":
                        raise ValueError("<.../> tag only supported for umgvar: " + wholetext)

                    varname = tag[7:].replace("/", "")
                    f.write(f"%{{{varname}}}")
                else:
                    # Opening tag
                    active_tags.append(tag)

                    if len(tags_and_attrs) == 1:
                        # Shortcut
                        f.write(f"{{{tag}}}")
                    else:
                        # With params
                        param_list: list[str] = []
                        f.write(f"{{{tag} ")

                        for param in tags_and_attrs[1:]:
                            key, val = param.split("=", 1)
                            param_list.append(f"{key}={val[1:-1]}")

                        f.write(" ".join(param_list))
                        f.write("}")

                xml = xml[endtagpos + 1 :]
            else:
                f.write(html.unescape(xml))
                break

        # Don't care for closing tags. UMG handles it automatically.
        return f.getvalue()


# test
_TEST_STRING = "{foo bar=1}Hello {baz}wor%{var}ld{/foo}{/baz}"
assert xml2umgtext(umgtext2xml(_TEST_STRING)) == _TEST_STRING
