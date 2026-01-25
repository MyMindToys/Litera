# -*- coding: utf-8 -*-
from .auth_utils import can_see_templates


def litera_nav(request):
    return {"can_see_templates": can_see_templates(request.user) if request.user.is_authenticated else False}
