"""D&D coin arithmetic for the money modal.

Pure utility module — no model imports, so the calculator also works in
demo mode. Expressions mix coin amounts (`2gp`, `5 sp`, `1pp`) with
arithmetic (`+ - * /` and parentheses); juxtaposed amounts add up
("2gp 5sp"). Everything is computed in copper pieces.

Rates (D&D 5e): 1 pp = 10 gp, 1 gp = 10 sp, 1 ep = 5 sp, 1 sp = 10 cp.
"""

from __future__ import annotations

import ast
import re

RATES = {"pp": 1000, "gp": 100, "ep": 50, "sp": 10, "cp": 1}

_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(pp|gp|ep|sp|cp)(?![a-z])")
_ALLOWED_CHARS = re.compile(r"^[\d.()+\-*/\s]*$")
_IMPLICIT_ADD = re.compile(r"\)\s*(?=[\d(])")   # "(200)(50)" -> "(200)+(50)"

_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UAdd, ast.USub)


def money_to_cp(expr: str) -> float:
    """Evaluate a coin expression to copper pieces.

    Raises ValueError on anything unparsable (including unknown units).
    Bare numbers count as copper, so "+5" adds 5 cp.
    """
    s = expr.strip().lower()
    if not s:
        raise ValueError("empty expression")
    s = _AMOUNT.sub(lambda m: f"({float(m.group(1)) * RATES[m.group(2)]})", s)
    if not _ALLOWED_CHARS.match(s):
        raise ValueError("unknown unit or symbol")
    s = _IMPLICIT_ADD.sub(")+", s)
    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError as exc:
        raise ValueError("bad expression") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError("bad expression")
        if isinstance(node, ast.Constant) and not isinstance(node.value,
                                                             (int, float)):
            raise ValueError("bad expression")
    try:
        return float(_eval(tree.body))
    except ZeroDivisionError as exc:
        raise ValueError("division by zero") from exc


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    left, right = _eval(node.left), _eval(node.right)
    if isinstance(node.op, ast.Add):
        return left + right
    if isinstance(node.op, ast.Sub):
        return left - right
    if isinstance(node.op, ast.Mult):
        return left * right
    return left / right


def split_cp(total_cp: int) -> tuple[int, int, int]:
    """abs(total_cp) -> (gp, sp, cp), mirroring inventory_service.cp_to_coins."""
    gp, rem = divmod(abs(int(total_cp)), 100)
    sp, cp = divmod(rem, 10)
    return gp, sp, cp


def fmt_cp(total_cp: float) -> str:
    """105 -> '1 GP 5 CP'; negative and fractional values stay visible."""
    sign = "-" if total_cp < 0 else ""
    whole = int(abs(total_cp))
    frac = abs(total_cp) - whole
    gp, sp, cp = split_cp(whole)
    parts = [f"{n} {d}" for n, d in ((gp, "GP"), (sp, "SP"), (cp, "CP")) if n]
    text = sign + " ".join(parts or ["0 CP"])
    if frac > 1e-9:
        text += f" (+{frac:.2f} cp)"
    return text


def fmt_equivalents(total_cp: float) -> str:
    """One line of denominational equivalents for the calculator."""
    return "  ·  ".join(f"{total_cp / rate:g} {unit.upper()}"
                        for unit, rate in RATES.items())


def is_transaction(expr: str) -> bool:
    """Leading +/- marks an expression as a pouch transaction."""
    return expr.strip().startswith(("+", "-"))


def transaction_cp(expr: str) -> float:
    """Evaluate a pouch transaction: the leading sign applies to the
    WHOLE amount, so "-2gp 5sp" means spend 2gp5sp (-250), not -200+50.
    """
    s = expr.strip()
    if not is_transaction(s):
        raise ValueError("transaction must start with + or -")
    sign = -1 if s[0] == "-" else 1
    return sign * money_to_cp(s[1:])
