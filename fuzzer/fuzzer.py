import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


@dataclass
class FuzzingReport:
    src_code: str
    error_report: str

    def to_json(self) -> dict:
        return {"src_code": self.src_code, "error_report": self.error_report}


class AstFuzzer(ABC):
    def __init__(self, wk_dir, iter_num=-1):
        self.wk_dir = Path(wk_dir)
        # iter_num = -1 -> infinite
        assert iter_num > 0 or iter_num == -1
        self.iter_num = iter_num

    @abstractmethod
    def gen_code(self) -> Path:
        pass

    def boot_fuzzing(self, parser) -> List[FuzzingReport]:
        reports = []

        while True:
            print(f"Fuzzing @ {self.iter_num}")
            code = self.gen_code()
            try:
                ast = parser.parse(code)
                if ast is None:
                    raise RuntimeError(f"Failed to parse {code}: AST is None")
            except Exception as e:
                error_report = f"{e}"
                reports.append(FuzzingReport(src_code=str(code), error_report=error_report))
                rep_str = json.dumps([i.to_json() for i in reports], indent=4)
                (self.wk_dir / 'reports.json').write_text(rep_str)
            if self.iter_num == -1:
                continue
            self.iter_num -= 1
            if self.iter_num == 0:
                break

        return reports
