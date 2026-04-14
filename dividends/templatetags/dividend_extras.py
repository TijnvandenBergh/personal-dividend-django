from django import template

register = template.Library()


@register.filter
def cents_as_money(value):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return ""
    negative = v < 0
    v = abs(v)
    whole, frac = divmod(v, 100)
    s = f"{whole:,}.{frac:02d}"
    return f"-{s}" if negative else s
