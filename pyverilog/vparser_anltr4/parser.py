import sys
from antlr4 import *
from .SystemVerilogLexer import SystemVerilogLexer
from .SystemVerilogParser import SystemVerilogParser
from .svast2pyverilog import SVastToPyverilogVisitor

def parse_verilog(file_path):
    input_stream = FileStream(file_path, encoding='utf-8')
    
    lexer = SystemVerilogLexer(input_stream)
    stream = CommonTokenStream(lexer)
    
    parser = SystemVerilogParser(stream)
    context = parser.source_text()
    
    visitor = SVastToPyverilogVisitor()
    ast = visitor.visit(context)

def parse_verilog_text(text):
    input_stream = InputStream(text)
    
    lexer = SystemVerilogLexer(input_stream)
    stream = CommonTokenStream(lexer)
    
    parser = SystemVerilogParser(stream)
    context = parser.source_text()
    
    visitor = SVastToPyverilogVisitor()
    ast = visitor.visit(context)

    return ast

if __name__ == "__main__":
    arg = sys.argv[1]
    parse_verilog(arg)