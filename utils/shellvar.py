import re


def get_var_from_shell(script: str, var: list[str]) -> dict[str, str]:
    return dict(re.findall(r'({})="(.+?)"'.format('|'.join(var)), script))
