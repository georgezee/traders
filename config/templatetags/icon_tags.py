from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def icon(name, alt='', extra_classes=''):
    """
    Renders an icon font class from traders-icons font.
    Icon selection can be updated through Fontello.
    If no extra_classes are provided, defaults to 'w-7 h-6'.
    Examples:
    {% icon "camera" "Camera icon" %}
    {% icon "camera" "Camera icon" "text-xl text-primary" %}
    """
    class_name = f"icon-{name}"
    default_classes = "w-7 h-6"
    final_classes = f"{class_name} inline-block {extra_classes or default_classes}".strip()
    aria = f'aria-label="{alt}"' if alt else 'aria-hidden="true"'
    html = f'<i class="{final_classes}" {aria}></i>'
    return mark_safe(html)
