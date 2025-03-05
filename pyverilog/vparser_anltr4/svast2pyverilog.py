from antlr4 import *
from SystemVerilogLexer import SystemVerilogLexer
from SystemVerilogParser import SystemVerilogParser
from SystemVerilogParserVisitor import SystemVerilogParserVisitor
from pyverilog.vparser.ast import *

class SVastToPyverilogVisitor(SystemVerilogParserVisitor):
    def visitChildren(self, node):
        results = []
        if node == None: return results
        if isinstance(node, list):
            for child in node:
                result = child.accept(self)
                results.append(result)
        else:
            for i in range(node.getChildCount()):
                child = node.getChild(i)
                result = child.accept(self)
                results.append(result)
        # avoid meaningless wrap.
        if len(results) == 1:
            return results[0]
        return results

    def visitSource_text(self, ctx):
        children = self.visitChildren(ctx)
        lineno = ctx.start.line
        ast = Source("", children, lineno)
        return ast
    
    def visitDescription(self, ctx):
        children = self.visitChildren(ctx)
        lineno = ctx.start.line
        ast = Description(children, lineno)
        return ast
    
    def visitModule_declaration(self, ctx):
        lineno = ctx.start.line
        name, paramlist, portlist = self.visitModule_header(ctx.module_header())
        # bug:  ctx.module_item() returns a list
        items = self.visitChildren(ctx.module_item())
        ast = ModuleDef(name, paramlist, portlist, items, lineno)
        return ast
    
    def visitModule_header(self, ctx):
        identifier = ctx.module_identifier().getText()
        paramlist = Paramlist(self.visitChildren(ctx.parameter_port_list()))
        portlist = Portlist(self.visitChildren(ctx.list_of_port_declarations()))

        return identifier, paramlist, portlist
    
    def visitParameter_port_declaration(self, ctx):
        pass
    
    def visitPort_decl(self, ctx):
        lineno = ctx.start.line
        # TODO: ctx.getText() is not port name
        port = Port(ctx.getText(), width=None, dimensions=None, type=None, lineno=lineno)
        return port
    
    def visitModule_item(self, ctx):
        return None
