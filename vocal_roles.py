"""Explicit style guidance for duet section labels, without rewriting lyrics."""
import re


def sections(lyrics):
    result = {'male': [], 'female': []}
    for label in re.findall(r'^\s*\[([^\]\r\n]{1,160})\]\s*$', lyrics, re.M):
        male = bool(re.search(r'\b(male|maschile|uomo)\b', label, re.I))
        female = bool(re.search(r'\b(female|femminile|donna)\b', label, re.I))
        if male == female:
            continue
        role = 'male' if male else 'female'
        if label not in result[role]:
            result[role].append(label)
    return result


def guidance(style, lyrics):
    roles = sections(lyrics)
    if not all(roles.values()):
        return style, None
    # Hints, not a verified singer assignment or a native control parameter.
    instructions = ['Duet with two distinct lead singers.']
    for role in ('male', 'female'):
        labels = ', '.join('['+label+']' for label in roles[role][:8])
        instructions.append(role.capitalize()+' voice sings the sections labelled '+labels+'.')
    instructions.append('Keep each singer in their labelled sections without swapping the voices. '
                        'For unlabelled sections follow the requested style and harmonies.')
    return style+'\n'+' '.join(instructions), {'roles': roles, 'mode': 'style-guidance', 'enforced': False}
