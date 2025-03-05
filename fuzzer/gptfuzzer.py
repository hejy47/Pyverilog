import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI
import ollama

from fuzzer.fuzzer import AstFuzzer
from dotenv import load_dotenv

load_dotenv()


def extract_verilog_code(text) -> Optional[str]:
    pattern = r'```verilog(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0].strip() if matches else None


class MultiLLM:
    def __init__(
            self,
            model,
            use_local=False
    ):
        self.use_local = use_local
        self.model = model

    def query(self, prompt):
        if self.use_local:
            return self.ollama_local_query(prompt)
        else:
            return self.openai_api_query(prompt)

    def openai_api_query(self, prompt):
        client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("BASE_URL")
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def ollama_local_query(self, prompt):
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.message.content.strip()

    def generate_verilog_code(self, prompt) -> Optional[str]:
        response = self.query(prompt)

        verilog_code = extract_verilog_code(response)

        if verilog_code:
            return verilog_code
        else:
            return None


def timestamp() -> str:
    today = datetime.now()
    timestamp = f'{today.month}-{today.day}-{today.hour}-{today.minute}-{today.second}'
    return timestamp


class GPTFuzzer(AstFuzzer):
    def __init__(self, model: MultiLLM, prompt: str, lang: str, wk_dir: str, iter_num: int = -1):
        AstFuzzer.__init__(self, wk_dir, iter_num)
        self.model = model
        self.lang = lang
        self.prompt = Path(prompt).read_text().format(lang=self.lang)

    def gen_code(self) -> Path:
        retry = 0
        while True:
            if retry > 5:
                raise RuntimeError(f"Too many retries for code generation, try again later")
            res = self.model.generate_verilog_code(self.prompt)
            if res is None:
                retry += 1
                continue
            break

        target_file = self.wk_dir / f"{timestamp()}.sv"
        target_file.write_text(res)
        return target_file
