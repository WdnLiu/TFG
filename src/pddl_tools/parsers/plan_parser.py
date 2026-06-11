from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanStep:
    action: str
    args: tuple[str, ...]

    def __str__(self) -> str:
        return f"({self.action} {' '.join(self.args)})" if self.args else f"({self.action})"


@dataclass
class Plan:
    steps: list[PlanStep]
    cost: int | None = None

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)


class PlanParser:
    def parse(self, content: str) -> Plan:
        steps: list[PlanStep] = []
        cost: int | None = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(';'):
                parsed_cost = self._extract_cost(line)
                if parsed_cost is not None:
                    cost = parsed_cost
                continue

            step = self._parse_step(line)
            if step is not None:
                steps.append(step)

        return Plan(steps=steps, cost=cost)

    def parse_file(self, path: str) -> Plan:
        with open(path) as f:
            return self.parse(f.read())

    def _parse_step(self, line: str) -> PlanStep | None:
        if not (line.startswith('(') and line.endswith(')')):
            return None
        body = line[1:-1].strip()
        if not body:
            return None
        tokens = body.split()
        action = tokens[0].lower()
        args = tuple(tok.lower() for tok in tokens[1:])
        return PlanStep(action=action, args=args)

    @staticmethod
    def _extract_cost(line: str) -> int | None:
        stripped = line.lstrip(';').strip().lower()
        if not stripped.startswith('cost'):
            return None
        for token in stripped.split():
            if token.isdigit():
                return int(token)
        return None
