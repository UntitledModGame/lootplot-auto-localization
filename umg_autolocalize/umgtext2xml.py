import html
import io

NPOS = 2**64 - 1


def umgtext2xml(umgtext: str):
    f = io.StringIO()
    active_tags: list[str] = []

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
                        raise ValueError("unclosed opening tag")
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
                            raise ValueError(f"unknown tag {tag[1:]}")
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
                            raise ValueError("invalid effect parameter specifier")
                        xmlparams.append(f'{param[:equal_sign]}="{param[equal_sign+1:]}"')

                    f.write(" ".join(xmlparams))
                    f.write(">")
                if not closing:
                    active_tags.append(tags_and_params[0])

        elif curly_bracket > percent:
            f.write(html.escape(umgtext[:pos]))

            # Handle percent sign
            if umgtext[pos + 1] == "{":
                # Handle variable
                endtagpos = umgtext.find("}", pos)
                if endtagpos == -1:
                    raise ValueError("unclosed variable tag")
                f.write(f'<umg:variable name="{umgtext[pos+2:endtagpos]}"/>')
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
