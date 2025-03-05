import argparse

from antlr4 import *

from fuzzer.gptfuzzer import GPTFuzzer, MultiLLM
from pyverilog.vparser_anltr4.SystemVerilogLexer import SystemVerilogLexer
from pyverilog.vparser_anltr4.SystemVerilogParser import SystemVerilogParser
from pyverilog.vparser_anltr4.svast2pyverilog import SVastToPyverilogVisitor


class PyverilogSVParser:
    def __init__(self):
        pass

    @classmethod
    def parse(cls, file_path):
        input_stream = FileStream(file_path, encoding='utf-8')

        lexer = SystemVerilogLexer(input_stream)
        stream = CommonTokenStream(lexer)

        parser = SystemVerilogParser(stream)
        context = parser.source_text()

        visitor = SVastToPyverilogVisitor()
        ast = visitor.visit(context)
        return ast


def main(args):
    llm = MultiLLM(
        model=args.model,
        use_local=args.local,
    )
    fuzzer = GPTFuzzer(
        model=llm,
        lang="SystemVerilog",
        wk_dir=args.wk_dir,
        iter_num=args.iter_num,
        prompt=args.prompt,
    )

    parser = PyverilogSVParser()

    fuzzer.boot_fuzzing(parser)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--wk-dir", default="wk_dir", required=True)
    arg_parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    arg_parser.add_argument("--local", action="store_true")
    arg_parser.add_argument("--prompt", required=True)
    arg_parser.add_argument("--iter-num", default=5)

    args = arg_parser.parse_args()
    main(args)
