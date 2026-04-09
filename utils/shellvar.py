import re


def get_var_from_shell(script: str | bytes, var: list[str]) -> dict[str, str]:
    return dict(re.findall(rf'(?<! )({"|".join(var)})="(.+?)"', str(script)))
