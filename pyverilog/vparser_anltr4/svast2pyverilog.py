from antlr4 import *
from .SystemVerilogLexer import SystemVerilogLexer
from .SystemVerilogParser import SystemVerilogParser
from .SystemVerilogParserVisitor import SystemVerilogParserVisitor
from pyverilog.utils.op2mark import operator_mark
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

    def visitAlways_construct(self, ctx):
        lineno = ctx.start.line
        always_type = self.visitAlways_keyword(ctx.getChild(0)) if ctx.getChild(0) else None
        if ctx.getChild(1) is None:
            sens, statements = None, None
        else:
            sub_res = self.visit(ctx.getChild(1))
            if isinstance(sub_res, tuple):
                sens, statements = sub_res
            else:
                sens, statements = None, sub_res

        if always_type == "always_ff":
            always_cls = AlwaysFF
        elif always_type == "always_comb":
            always_cls = AlwaysComb
        elif always_type == "always_latch":
            always_cls = AlwaysLatch
        else:
            raise NotImplementedError("Unknown always type")
        ast = always_cls(sens, statements, lineno)
        return ast

    def visitAlways_keyword(self, ctx):
        keyword = ctx.getText()
        return keyword

    def visitSeq_block(self, ctx):
        lineno = ctx.start.line
        statements = self.visitChildren(ctx)
        ast = Block(statements, scope=None, lineno=lineno)
        return ast

    def visitConditional_statement(self, ctx):
        lineno = ctx.start.line
        # TODO: better?
        cond = self.visit(ctx.children[2]) if ctx.getChild(2) else None
        true_statement = self.visit(ctx.children[4]) if ctx.getChild(4) else None
        false_statement = self.visit(ctx.children[6]) if ctx.getChild(6) else None
        ast = IfStatement(cond, true_statement, false_statement, lineno=lineno)
        return ast

    def visitProcedural_timing_control_statement(self, ctx):
        sens = self.visit(ctx.getChild(0)) if ctx.getChild(0) else None
        statements = self.visit(ctx.getChild(1)) if ctx.getChild(1) else None
        return sens, statements

    def visitProcedural_timing_control(self, ctx):
        lineno = ctx.start.line
        sens_list = self.visit(ctx.getChild(0).getChild(2))
        ast = SensList(sens_list, lineno=lineno)
        return ast

    def visitEvent_expression(self, ctx):
        lineno = ctx.start.line
        if ctx.getChildCount() == 2:
            sens = Sens(type=ctx.getChild(0).getText(), sig=self.visit(ctx.getChild(1)), lineno=lineno)
            return [sens]
        left = self.visit(ctx.getChild(0))
        right = self.visit(ctx.getChild(2))
        assert isinstance(left, list)
        assert isinstance(right, list)
        return left + right

    def visitExpression(self, ctx):
        lineno = ctx.start.line
        if ctx.getChildCount() == 1:
            return self.visitChildren(ctx)
        elif ctx.getChildCount() == 2:
            # unary operator
            op_cls = self.get_operator(ctx.getChild(0))
            right = self.visit(ctx.getChild(1))
            return op_cls(right, lineno=lineno)
        elif ctx.getChildCount() == 3:
            # binary operator
            left = self.visit(ctx.getChild(0))
            op_cls = self.get_operator(ctx.getChild(1))
            right = self.visit(ctx.getChild(2))
            return op_cls(left, right, lineno=lineno)
        else:
            raise NotImplementedError(f"Unknown expression type with {ctx.getChildCount()}")

    def get_operator(self, ctx):
        text = ctx.getText()
        op_cls = None
        for k, v in operator_mark.items():
            if text == v:
                op_cls = eval(k)
        if op_cls is None:
            raise NotImplementedError(f"Unknown operator {text}")
        return op_cls

    def visitUnary_operator(self, ctx):
        op_cls = self.get_operator(ctx)
        return op_cls

    def visitSimple_identifier(self, ctx):
        lineno = ctx.start.line
        identifier = Identifier(ctx.getText(), scope=None, lineno=lineno)
        return identifier

    def visitIntegral_number(self, ctx):
        lineno = ctx.start.line
        text = ctx.getText()
        ast = IntConst(text, lineno=lineno)
        return ast

    def visitNonblocking_assignment(self, ctx):
        lineno = ctx.start.line
        lvalue = self.visit(ctx.getChild(0))
        rvalue = self.visit(ctx.getChild(2))
        ast = NonblockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=lineno)
        return ast

    def visitBlocking_statement(self, ctx):
        return self.visitOperator_assignment(ctx)

    def visitOperator_assignment(self, ctx):
        lineno = ctx.start.line
        lvalue = self.visit(ctx.getChild(0))
        rvalue = self.visit(ctx.getChild(2))
        ast = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=lineno)
        return ast
