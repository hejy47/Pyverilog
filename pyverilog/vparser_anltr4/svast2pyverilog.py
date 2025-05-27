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
                if result is not None:
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
        if not isinstance(children, list):
            children = [children]
        lineno = ctx.start.line
        ast = Description(children, lineno)
        return ast

    def visitModule_declaration(self, ctx):
        lineno = ctx.start.line
        name, paramlist, portlist = self.visitModule_header(ctx.module_header())
        items = self.visitChildren(ctx.module_item())
        if not isinstance(items, list):
            items = [items]
        ast = ModuleDef(name, paramlist, portlist, items, lineno=lineno)
        return ast

    def visitModule_header(self, ctx):
        identifier = ctx.module_identifier().getText()
        parameter_port_list = self.visitChildren(ctx.parameter_port_list())
        if not isinstance(parameter_port_list, list):
            parameter_port_list = [parameter_port_list]
        param_lineno = ctx.parameter_port_list().start.line if ctx.parameter_port_list() else ctx.start.line
        paramlist = Paramlist(parameter_port_list, lineno=param_lineno)
        port_decl_list = self.visitChildren(ctx.list_of_port_declarations())
        if not isinstance(port_decl_list, list):
            port_decl_list = [port_decl_list]
        port_lineno = ctx.list_of_port_declarations().start.line if ctx.list_of_port_declarations() else ctx.start.line
        portlist = Portlist(port_decl_list, lineno=port_lineno)
        return identifier, paramlist, portlist
    
    def visitModule_program_interface_instantiation(self, ctx):
        lineno = ctx.start.line
        module_name = self.visit(ctx.instance_identifier())
        params = self.visit(ctx.parameter_value_assignment()) if ctx.parameter_value_assignment() else []
        if not isinstance(params, list):
            params = [params]
        instances = self.visitChildren(ctx.hierarchical_instance())
        if not isinstance(instances, list):
            instances = [instances]
        for instance in instances:
            instance.module = module_name
            instance.parameterlist = params
        prog_interface = InstanceList(module_name, params, instances, lineno)
        return prog_interface
    
    def visitGate_instantiation(self, ctx):
        lineno = ctx.start.line
        module_name = self.visit(ctx.n_input_gatetype())
        instances = self.visitChildren(ctx.n_input_gate_instance())
        if not isinstance(instances, list):
            instances = [instances]
        for instance in instances:
            instance.module = module_name
        gate_interface = InstanceList(module_name, [], instances, lineno)
        return gate_interface
    
    def visitN_input_gatetype(self, ctx):
        return self.visitIdentifier(ctx)
    
    def visitN_input_gate_instance(self, ctx):
        lineno = ctx.start.line
        instance_info = self.visit(ctx.name_of_instance()) if ctx.name_of_instance() else None
        instance_id, instance_width = None, None
        if isinstance(instance_info, list):
            instance_id = instance_info[0]
            instance_width = instance_info[1]
        output = self.visitChildren(ctx.output_terminal())
        inputs = self.visitChildren(ctx.input_terminal())
        if not isinstance(inputs, list):
            inputs = [inputs]
        ports = [PortArg(None, output, lineno=output.lineno)]
        for _input in inputs:
            ports.append(PortArg(None, _input, lineno=_input.lineno))
        instance = Instance(module=None, name=instance_id, portlist=ports, parameterlist=[], array=instance_width, lineno=lineno)
        return instance

    def visitNamed_parameter_assignment(self, ctx):
        lineno = ctx.start.line
        param_id = self.visit(ctx.parameter_identifier())
        param_value = self.visit(ctx.param_expression())
        param = ParamArg(param_id, param_value, lineno=lineno)
        return param
    
    def visitNamed_port_connection(self, ctx):
        lineno = ctx.start.line
        port_id = self.visit(ctx.port_identifier())
        port_value = self.visit(ctx.port_assign())
        port = PortArg(port_id, port_value, lineno=lineno)
        return port
    
    def visitOrdered_port_connection(self, ctx):
        lineno = ctx.start.line
        port_value = self.visit(ctx.expression())
        port = PortArg(None, port_value, lineno=lineno)
        return port
    
    def visitHierarchical_instance(self, ctx):
        lineno = ctx.start.line
        instance_info = self.visit(ctx.name_of_instance()) if ctx.name_of_instance() else None
        instance_id, instance_width = None, None
        if isinstance(instance_info, list):
            instance_id = instance_info[0]
            instance_width = instance_info[1]
        else:
            instance_id = instance_info
        ports = self.visitChildren(ctx.list_of_port_connections())
        instance = Instance(module=None, name=instance_id, portlist=ports, parameterlist=[], array=instance_width, lineno=lineno)
        return instance

    def visitParameter_declaration(self, ctx):
        lineno = ctx.start.line
        param_width = self.visit(ctx.data_type_or_implicit())[2] if ctx.data_type_or_implicit() else None

        params_list = self.visitChildren(ctx.list_of_param_assignments())
        if not isinstance(params_list, list):
            params_list = [params_list]
        params = []
        for i in range(len(params_list)):
            param_id, param_val, param_lineno = params_list[i]
            param = Parameter(param_id, param_val, width=param_width, lineno=param_lineno)
            params.append(param)
        param_decl = Decl(params, lineno=lineno)
        return param_decl
    
    def visitParam_assignment(self, ctx):
        lineno = ctx.start.line
        identifier = ctx.parameter_identifier().getText()
        value = self.visit(ctx.constant_param_expression()) if ctx.constant_param_expression() else None
        param_value = Rvalue(value, lineno=lineno) if value else None
        return identifier, param_value, lineno
    
    def visitAnsi_port_declaration(self, ctx):
        lineno = ctx.start.line
        direction = ctx.port_direction().getText() if ctx.port_direction() else None
        identifier = ctx.port_identifier().getText()
        data_type_lineno, data_type, port_width = None, None, None
        if ctx.data_type() is not None:
            data_type_lineno, data_type, port_width = self.visit(ctx.data_type())
        elif ctx.implicit_data_type() is not None:
            data_type_lineno, _, port_width = self.visit(ctx.implicit_data_type())
        if data_type_lineno is None:
            data_type_lineno = ctx.start.line
        
        port = None
        if direction:
            port_direction = None
            if direction == "input":
                port_direction = Input(identifier, width=port_width, lineno=data_type_lineno)
            elif direction == "output":
                port_direction = Output(identifier, width=port_width, lineno=data_type_lineno)
            elif direction == "inout":
                port_direction = Inout(identifier, width=port_width, lineno=data_type_lineno)
            port_type = None
            if data_type == "reg":
                port_type = Reg(identifier, width=port_width, lineno=data_type_lineno)
            elif data_type == "wire":
                port_type = Wire(identifier, width=port_width, lineno=data_type_lineno)
            port = Ioport(port_direction, port_type, lineno=lineno)
        else:
            port = Port(identifier, width=port_width, dimensions=None, type=data_type, lineno=data_type_lineno)
        return port
    
    def visitPort_declaration(self, ctx):
        lineno = ctx.start.line
        ports = self.visitChildren(ctx)
        if not isinstance(ports, list):
            ports = [ports]
        port_decl = Decl(ports, lineno=lineno)
        return port_decl
    
    def visitInput_declaration(self, ctx):
        inputs = self.visitChildren(ctx.list_of_port_identifiers())
        if not isinstance(inputs, list):
            inputs = [inputs]
        input_decls = []
        for _input in inputs:
            input_decl = Input(_input, width=None, dimensions=None, lineno=_input.lineno)
            input_decls.append(input_decl)
        return input_decls
    
    def visitOutput_declaration(self, ctx):
        outputs = self.visitChildren(ctx.list_of_port_identifiers())
        if not isinstance(outputs, list):
            outputs = [outputs]
        output_decls = []
        for _output in outputs:
            output_decl = Output(_output, width=None, dimensions=None, lineno=_output.lineno)
            output_decls.append(output_decl)
        return output_decls
    
    def visitInterface_port_declaration(self, ctx):
        lineno = ctx.start.line
        identifier = ctx.interface_identifier().getText()
        interfaces_list = self.visitChildren(ctx.list_of_interface_identifiers())
        if not isinstance(interfaces_list, list):
            interfaces_list = [interfaces_list]
        interfaces = []
        for _interface in interfaces_list:
            interface = NewType(identifier, _interface.name, lineno=_interface.lineno)
            interfaces.append(interface)
        return interfaces
    
    def visitImplicit_data_type(self, ctx):
        lineno = ctx.start.line
        data_width = self.visitChildren(ctx.packed_dimension()) if ctx.packed_dimension() else None
        return lineno, None, data_width
    
    def visitData_type(self, ctx):
        lineno = ctx.start.line
        data_type = None
        if ctx.integer_vector_type():
            data_type = ctx.integer_vector_type().getText()
        elif ctx.integer_atom_type():
            data_type = ctx.integer_atom_type().getText()
        if ctx.enum_base_type():
            enum_base_lineno, enum_base, enum_base_width = self.visit(ctx.enum_base_type())
            enum_identifiers = self.visitChildren(ctx.enum_name_declaration())
            data_type = TypedefEnum(enum_base, enum_identifiers, width=enum_base_width, lineno=enum_base_lineno)
        data_width = self.visitChildren(ctx.packed_dimension()) if ctx.packed_dimension() else None
        return lineno, data_type, data_width
    
    def visitEnum_base_type(self, ctx):
        lineno = ctx.start.line
        data_type = None
        if ctx.integer_vector_type():
            data_type = ctx.integer_vector_type().getText()
        elif ctx.integer_atom_type():
            data_type = ctx.integer_atom_type().getText()
        data_width = self.visitChildren(ctx.packed_dimension()) if ctx.packed_dimension() else None
        return lineno, data_type, data_width
    
    def visitConstant_range(self, ctx):
        lineno = ctx.start.line
        width  = self.visitChildren(ctx.constant_expression())
        if isinstance(ctx.parentCtx, SystemVerilogParser.Unpacked_dimensionContext):
            constant_range = Length(width[0], width[1], lineno=lineno)
        else:
            constant_range = Width(width[0], width[1], lineno=lineno)
        return constant_range
    
    def visitLocal_parameter_declaration(self, ctx):
        lineno = ctx.start.line
        local_param_width = self.visit(ctx.data_type_or_implicit())[2] if ctx.data_type_or_implicit() else None
        params_list = self.visitChildren(ctx.list_of_param_assignments())
        if not isinstance(params_list, list):
            params_list = [params_list]
        params = []
        for i in range(len(params_list)):
            param_id, param_val, param_lineno = params_list[i]
            param = Localparam(param_id, param_val, width=local_param_width, lineno=param_lineno)
            params.append(param)
        param_decl = Decl(params, lineno=lineno)
        return param_decl
    
    def visitData_declaration(self, ctx):
        if ctx.type_declaration():
            return self.visit(ctx.type_declaration())
        lineno = ctx.start.line
        data_type_lineno, data_type, data_width = None, None, None
        if ctx.data_type() is not None:
            data_type_lineno, data_type, data_width = self.visitData_type(ctx.data_type())
        vars_list = self.visit(ctx.list_of_variable_decl_assignments())
        if not isinstance(vars_list, list):
            vars_list = [vars_list]
        vars = []
        for i in range(len(vars_list)):
            var_id, var_dimension, var_value, var_lineno = vars_list[i]
            var, var_assign = None, None
            if data_type == "wire":
                var = Wire(var_id.name, width=data_width, dimensions=var_dimension, lineno=var_lineno)
            elif data_type == "reg":
                var = Reg(var_id.name, width=data_width, dimensions=var_dimension, lineno=var_lineno)
            elif data_type == "logic":
                var = Logic(var_id.name, width=data_width, dimensions=var_dimension, lineno=var_lineno)
            vars.append(var)
            if var_value:
                lvalue = Lvalue(var_id, lineno=var_lineno)
                rvalue = Rvalue(var_value, lineno=var_lineno)
                var_assign = Assign(lvalue, rvalue, lineno=var_lineno)
                vars.append(var_assign)
        var_decl = Decl(vars, lineno=lineno)
        return var_decl
    
    def visitVariable_decl_assignment(self, ctx):
        lineno = ctx.start.line
        identifier = self.visit(ctx.variable_identifier())
        dimensions = None
        if ctx.unsized_dimension():
            dimensions = self.visitChildren(ctx.unsized_dimension())
            if not isinstance(dimensions, list):
                dimensions = [dimensions]
            dimensions = Dimensions(dimensions, lineno=dimensions[0].lineno)
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return identifier, dimensions, value, lineno
    
    def visitType_declaration(self, ctx):
        lineno = ctx.start.line
        _, data_type, _ = self.visit(ctx.data_type())
        type_identifier = self.visitChildren(ctx.type_identifier())
        type_def = Typedef(type_identifier, data_type, lineno=lineno)
        return type_def
    
    def visitNet_declaration(self, ctx):
        lineno = ctx.start.line
        net_type = ctx.net_type().getText()
        net_width = self.visit(ctx.data_type_or_implicit())[2] if ctx.data_type_or_implicit() else None
        nets_list = self.visit(ctx.list_of_net_decl_assignments())
        if not isinstance(nets_list, list):
            nets_list = [nets_list]
        nets = []
        for i in range(len(nets_list)):
            net_id, net_dimension, net_value, net_lineno = nets_list[i]
            net, net_assign = None, None
            if net_type == "wire":
                net = Wire(net_id.name, width=net_width, dimensions=net_dimension, lineno=net_lineno)
            elif net_type == "reg":
                net = Reg(net_id.name, width=net_width, dimensions=net_dimension, lineno=net_lineno)
            nets.append(net)
            if net_value:
                lvalue = Lvalue(net_id, lineno=net_lineno)
                rvalue = Rvalue(net_value, lineno=net_lineno)
                net_assign = Assign(lvalue, rvalue, lineno=net_lineno)
                nets.append(net_assign)
        net_decl = Decl(nets, lineno=lineno)
        return net_decl
    
    def visitNet_decl_assignment(self, ctx):
        lineno = ctx.start.line
        identifier = self.visit(ctx.net_identifier())
        dimensions = None
        if ctx.unpacked_dimension():
            dimensions = self.visitChildren(ctx.unpacked_dimension())
            if not isinstance(dimensions, list):
                dimensions = [dimensions]
            dimensions = Dimensions(dimensions, lineno=dimensions[0].lineno)
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return identifier, dimensions, value, lineno
    
    def visitGenvar_declaration(self, ctx):
        lineno = ctx.start.line
        identifier_list = self.visit(ctx.list_of_genvar_identifiers())
        if not isinstance(identifier_list, list):
            identifier_list = [identifier_list]
        genvar_list = []
        for identifier in identifier_list:
            genvar = Genvar(name=identifier,
                      width=Width(msb=IntConst('31', lineno=lineno),
                                  lsb=IntConst('0', lineno=lineno),
                                  lineno=identifier.lineno))
            genvar_list.append(genvar)
        var_decl = Decl(genvar_list, lineno=lineno)
        return var_decl

    def visitAlways_construct(self, ctx):
        lineno = ctx.start.line
        always_type = self.visitAlways_keyword(ctx.always_keyword()) if ctx.always_keyword() else None
        if ctx.statement() is None:
            sens, statements = None, None
        else:
            sub_res = self.visit(ctx.statement())
            if isinstance(sub_res, tuple):
                sens, statements = sub_res
            else:
                sens, statements = None, sub_res
        if always_type == "always":
            always_cls = Always
        elif always_type == "always_ff":
            always_cls = AlwaysFF
        elif always_type == "always_comb":
            always_cls = AlwaysComb
        elif always_type == "always_latch":
            always_cls = AlwaysLatch
        else:
            raise NotImplementedError("Unknown always type")
        if sens is None:
            sens = SensList((Sens(None, 'all', lineno=lineno),), lineno=lineno)
        ast = always_cls(sens, statements, lineno)
        return ast

    def visitAlways_keyword(self, ctx):
        keyword = ctx.getText()
        return keyword
    
    def visitLoop_statement(self, ctx):
        lineno = ctx.start.line
        for_init = self.visit(ctx.for_initialization())
        for_expr = self.visit(ctx.expression())
        for_iter = self.visit(ctx.for_step())
        for_block = self.visit(ctx.statement_or_null())
        for_statement = ForStatement(for_init, for_expr, for_iter, for_block, lineno=lineno)
        return for_statement
    
    def visitFor_variable_declaration(self, ctx):
        lineno = ctx.start.line
        data_type_lineno, data_type, data_width = None, None, None
        if ctx.data_type() is not None:
            data_type_lineno, data_type, data_width = self.visitData_type(ctx.data_type())
        vars_list = self.visitChildren(ctx.for_variable_assign())
        if not isinstance(vars_list, list):
            vars_list = [vars_list]
        vars = []
        for i in range(len(vars_list)):
            var_id, var_value, var_lineno = vars_list[i]
            var, var_assign = None, None
            if data_type == "int" or data_type == "integer":
                var = Integer(var_id.name, width=data_width, dimensions=None, lineno=var_lineno)
            vars.append(var)
            if var_value:
                lvalue = Lvalue(var_id, lineno=var_lineno)
                rvalue = Rvalue(var_value, lineno=var_lineno)
                var_assign = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=var_lineno)
                vars.append(var_assign)
        var_decl = Decl(vars, lineno=lineno)
        return var_decl
    
    def visitFor_variable_assign(self, ctx):
        lineno = ctx.start.line
        identifier = self.visit(ctx.variable_identifier())
        value = self.visit(ctx.expression()) if ctx.expression() else None
        return identifier, value, lineno

    def visitInc_or_dec_expression(self, ctx):
        lineno = ctx.start.line
        lvalue = self.visit(ctx.variable_lvalue())
        inc_or_dec = ctx.inc_or_dec_operator().getText()
        op = None
        if inc_or_dec == '++':
            op = Plus
        elif inc_or_dec == '--':
            op = Minus
        rvalue = op(lvalue, IntConst('1', lineno=lvalue.lineno), lineno=ctx.inc_or_dec_operator().start.line)

        lvalue = Lvalue(lvalue, lineno=lvalue.lineno)
        rvalue = Rvalue(rvalue, lineno=rvalue.lineno)
        ast = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=lineno)
        return ast
        
    def visitGenerate_region(self, ctx):
        lineno = ctx.start.line
        generate_items = self.visitChildren(ctx.generate_item())
        if not isinstance(generate_items, list):
            generate_items = [generate_items]
        generate_region = GenerateStatement(generate_items, lineno=lineno)
        return generate_region

    def visitLoop_generate_construct(self, ctx):
        lineno = ctx.start.line
        generate_init = self.visit(ctx.genvar_initialization())
        generate_expr = self.visit(ctx.genvar_expression())
        generate_iter = self.visit(ctx.genvar_iteration())
        generate_block = self.visit(ctx.generate_block())
        generate_statement = ForStatement(generate_init, generate_expr, generate_iter, generate_block, lineno=lineno)
        return generate_statement
    
    def visitGenvar_initialization(self, ctx):
        lineno = ctx.start.line
        identifier = self.visit(ctx.genvar_identifier())
        var = self.visit(ctx.constant_expression())
        lvalue = Lvalue(identifier, lineno=identifier.lineno)
        rvalue = Rvalue(var, lineno=var.lineno)
        ast = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=lineno)
        return ast
    
    def visitGenvar_iteration(self, ctx):
        lineno = ctx.start.line
        identifier = self.visit(ctx.genvar_identifier())
        var = self.visit(ctx.genvar_expression())
        op = ctx.assignment_operator().getText()
        if op != '=':
            operator = self.get_operator(ctx.assignment_operator())
            var = operator(identifier, var, lineno=ctx.assignment_operator().start.line)
        
        lvalue = Lvalue(identifier, lineno=identifier.lineno)
        rvalue = Rvalue(var, lineno=var.lineno)
        ast = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=lineno)
        return ast
    
    def visitGenerate_block(self, ctx):
        lineno = ctx.start.line
        block_name = self.visitChildren(ctx.generate_block_name()) if ctx.generate_block_name() else None
        block_items = self.visitChildren(ctx.generate_item())
        if not isinstance(block_items, list):
            block_items = [block_items]
        block = Block(block_items, scope=block_name, lineno=lineno)
        return block

    def visitSeq_block(self, ctx):
        lineno = ctx.start.line
        statements = self.visitChildren(ctx)
        if isinstance(statements, tuple):
            statements = list(statements)
        if not isinstance(statements, list):
            statements = [statements]
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
    
    def visitCase_statement(self, ctx):
        keyword = ctx.case_keyword().getText()
        case_cls = CaseStatement
        if keyword == "case":
            case_cls = CaseStatement
        elif keyword == "casex":
            case_cls = CasexStatement
        elif keyword == "casez":
            case_cls = CasezStatement
        expression = self.visit(ctx.case_expression())
        items = self.visitChildren(ctx.case_item())
        ast = case_cls(expression, items, lineno=ctx.start.line)
        return ast
    
    def visitCase_item(self, ctx):
        lineno = ctx.start.line
        conds = self.visitChildren(ctx.case_item_expression())
        if not isinstance(conds, list):
            conds = [conds]
        if conds == []:
            conds = None
        statement = self.visit(ctx.statement_or_null())
        case_item = Case(conds, statement, lineno=lineno)
        return case_item
    
    def visitFunction_declaration(self, ctx):
        return self.visitFunction_body_declaration(ctx.function_body_declaration())
    
    def visitFunction_body_declaration(self, ctx):
        lineno = ctx.start.line
        func_width = self.visit(ctx.function_data_type_or_implicit())[2] if ctx.function_data_type_or_implicit() else None
        func_id = self.visit(ctx.function_identifier())
        func_input = self.visitChildren(ctx.tf_item_declaration())
        if not isinstance(func_input, list):
            func_input = [func_input]
        func_statement = self.visitChildren(ctx.function_statement_or_null())
        if not isinstance(func_statement, list):
            func_statement = [func_statement]
        func = Function(func_id, func_width, func_input+func_statement, lineno=lineno)
        return func
    
    def visitTf_item_declaration(self, ctx):
        lineno = ctx.start.line
        ports = self.visitChildren(ctx)
        if not isinstance(ports, list):
            ports = [ports]
        port_decl = Decl(ports, lineno=lineno)
        return port_decl
    
    def visitTf_port_declaration(self, ctx):
        direction = ctx.tf_port_direction().getText() if ctx.tf_port_direction() else None
        identifiers = self.visitChildren(ctx.list_of_tf_variable_identifiers())
        if not isinstance(identifiers, list):
            identifiers = [identifiers]
        data_type_lineno, data_type, port_width = None, None, None
        if ctx.data_type_or_implicit() is not None:
            data_type_lineno, data_type, port_width = self.visit(ctx.data_type_or_implicit())
        
        direction_cls = Input
        if direction == "input":
            direction_cls = Input
        elif direction == "output":
            direction_cls = Output
        elif direction == "inout":
            direction_cls = Inout
        decls = []
        for identifier in identifiers:
            input_decl = direction_cls(identifier, width=port_width, dimensions=None, lineno=identifier.lineno)
            decls.append(input_decl)
        return decls

    def visitProcedural_timing_control_statement(self, ctx):
        sens = self.visit(ctx.getChild(0)) if ctx.getChild(0) else None
        statements = self.visit(ctx.getChild(1)) if ctx.getChild(1) else None
        return sens, statements

    def visitEvent_control(self, ctx):
        lineno = ctx.start.line
        sens_list = self.visit(ctx.getChild(2))
        if sens_list is None:
            sens_list = Sens(None, 'all', lineno=lineno)
        if not isinstance(sens_list, list):
            sens_list = [sens_list]
        ast = SensList(sens_list, lineno=lineno)
        return ast

    def visitUnsigned_number(self, ctx):
        lineno = ctx.start.line
        ast = IntConst(ctx.getText(), lineno=lineno)
        return ast
    
    def visitUnbased_unsized_literal(self, ctx):
        lineno = ctx.start.line
        ast = IntConst(ctx.getText(), lineno=lineno)
        return ast

    def visitDelay_control(self, ctx):
        lineno = ctx.start.line
        delay = self.visit(ctx.getChild(1))
        ast = DelayStatement(delay, lineno=lineno)
        return ast

    def visitEvent_expression(self, ctx):
        lineno = ctx.start.line
        if ctx.expression():
            sigs = self.visitChildren(ctx.expression())
            if not isinstance(sigs, list):
                sigs = [sigs]
            type = ctx.edge_identifier().getText() if ctx.edge_identifier() else "level"
            sens = []
            for sig in sigs:
                sen = Sens(type=type, sig=sig, lineno=sig.lineno)
                sens.append(sen)
            return sens
        all_event_expression = []
        for event_expr in ctx.event_expression():
            event_expr = self.visit(event_expr)
            if not isinstance(event_expr, list):
                event_expr = [event_expr]
            all_event_expression += event_expr
        return all_event_expression
    
    def visitConcatenation(self, ctx):
        lineno = ctx.start.line
        children = self.visitChildren(ctx)
        if not isinstance(children, list):
            children = [children]
        ast = Concat(children, lineno=lineno)
        return ast
    
    def visitMultiple_concatenation(self, ctx):
        lineno = ctx.start.line
        repeat_count = self.visit(ctx.expression())
        concat_value = self.visit(ctx.concatenation())
        ast = Repeat(concat_value, repeat_count, lineno=lineno)
        return ast

    def visitExpression(self, ctx):
        lineno = ctx.start.line
        if ctx.getChildCount() == 1:
            return self.visitChildren(ctx)
        elif ctx.getChildCount() == 2:
            # unary operator
            op_cls = self.get_operator(ctx.getChild(0), unary=True)
            right = self.visit(ctx.getChild(1))
            return op_cls(right, lineno=lineno)
        elif ctx.getChildCount() == 3:
            # binary operator
            left = self.visit(ctx.getChild(0))
            op_cls = self.get_operator(ctx.getChild(1))
            right = self.visit(ctx.getChild(2))
            return op_cls(left, right, lineno=lineno)
        elif ctx.getChildCount() == 5:
            # trinary operator
            cond = self.visit(ctx.getChild(0))
            true_statement = self.visit(ctx.getChild(2))
            false_statement = self.visit(ctx.getChild(4))
            return Cond(cond, true_statement, false_statement, lineno=lineno)
        else:
            raise NotImplementedError(f"Unknown expression type with childCount: {ctx.getChildCount()}")
    
    def visitConstant_expression(self, ctx):
        return self.visitExpression(ctx)

    def get_operator(self, ctx, unary=False):
        text = ctx.getText()
        if isinstance(ctx, SystemVerilogParser.Assignment_operatorContext):
            text = text.replace('=', '')
        if text == "^~": text = "~^"
        op_cls = None
        for k, v in operator_mark.items():
            if text == v:
                if unary and 'U' in k:
                    op_cls = eval(k)
                if not unary and 'U' not in k:
                    op_cls = eval(k)
        if op_cls is None:
            raise NotImplementedError(f"Unknown operator {text}")
        return op_cls

    def visitUnary_operator(self, ctx):
        op_cls = self.get_operator(ctx)
        return op_cls

    def visitIdentifier(self, ctx):
        lineno = ctx.start.line
        identifier = Identifier(ctx.getText(), scope=None, lineno=lineno)
        return identifier

    def visitIntegral_number(self, ctx):
        lineno = ctx.start.line
        text = ctx.getText()
        ast = IntConst(text, lineno=lineno)
        return ast
    
    def getVariable_slice(self, identifier, slice, lineno):
        if isinstance(slice, Width):
            return Partselect(identifier, slice.msb, slice.lsb, lineno=lineno)
        else:
            return Pointer(identifier, slice, lineno=lineno)
    
    def visitVariable_lvalue(self, ctx):
        lineno = ctx.start.line
        primary = None
        identifier = None
        if ctx.hierarchical_identifier():
            identifier = self.visit(ctx.hierarchical_identifier())
        elif ctx.variable_lvalue():
            identifiers = self.visitChildren(ctx.variable_lvalue())
            if not isinstance(identifiers, list):
                identifiers = [identifiers]
            identifier = LConcat(identifiers, lineno=lineno)

        if ctx.select_():
            select = self.visit(ctx.select_())
            if not isinstance(select, list):
                primary = self.getVariable_slice(identifier, select, lineno)
            else:
                if isinstance(select[0], list):
                    select = select[0] + select[1:]
                primary = self.getVariable_slice(identifier, select[0], lineno)
                for s in select[1:]:
                    primary = self.getVariable_slice(primary, s, lineno)
        else:
            primary = identifier
        return primary
    
    def visitHierarchical_identifier(self, ctx):
        hier_refs = self.visitChildren(ctx.hier_ref()) if ctx.hier_ref() else None
        identifier = self.visit(ctx.identifier())
        if hier_refs:
            if not isinstance(hier_refs, list):
                hier_refs = [hier_refs]
            identifier_scope = IdentifierScope(hier_refs, lineno=hier_refs[0].lineno)
            identifier.scope = identifier_scope
        return identifier
    
    def visitHier_ref(self, ctx):
        lineno = ctx.start.line
        identifier = self.visit(ctx.identifier())
        select = self.visit(ctx.constant_bit_select()) if ctx.constant_bit_select() else None
        hier_ref = IdentifierScopeLabel(identifier, select, lineno=lineno)
        return hier_ref
    
    def visitPrimary(self, ctx):
        lineno = ctx.start.line
        primary = None
        if ctx.select_():
            identifier = self.visit(ctx.hierarchical_identifier())
            select = self.visit(ctx.select_())
            if not isinstance(select, list):
                primary = self.getVariable_slice(identifier, select, lineno)
            else:
                primary = self.getVariable_slice(identifier, select[0], lineno)
                for s in select[1:]:
                    primary = self.getVariable_slice(primary, s, lineno)
        elif hasattr(ctx, 'primary_literal') and ctx.primary_literal():
            primary = self.visit(ctx.primary_literal())
        elif hasattr(ctx, 'hierarchical_identifier') and ctx.hierarchical_identifier():
            primary = self.visit(ctx.hierarchical_identifier())
        elif hasattr(ctx, 'arg_list') and ctx.arg_list():
            func_call_id = self.visit(ctx.identifier())
            func_call_args = self.visit(ctx.arg_list())
            if not isinstance(func_call_args, list):
                func_call_args = [func_call_args]
            primary = FunctionCall(func_call_id, func_call_args, lineno=lineno)
        elif hasattr(ctx, 'primary') and ctx.primary() and hasattr(ctx, 'expression') and ctx.expression():
            # Cast
            cast_type = self.visit(ctx.primary())
            cast_expr = self.visit(ctx.expression())
            cast = Cast(cast_type, cast_expr, lineno=lineno)
            primary = cast
        else:
            primary = self.visitChildren(ctx)
            assert not isinstance(primary, list)
        return primary
    
    def visitSystem_tf_call(self, ctx):
        lineno = ctx.start.line
        sys_call_id = ctx.system_tf_identifier().getText()[1:] # remove $
        sys_call_args = self.visit(ctx.arg_list())
        if not isinstance(sys_call_args, list):
            sys_call_args = [sys_call_args]
        ast = SystemCall(sys_call_id, sys_call_args, lineno=lineno)
        return ast

    def visitNonblocking_assignment(self, ctx):
        lineno = ctx.start.line
        lvalue = self.visit(ctx.variable_lvalue())
        lvalue = Lvalue(lvalue, lineno=lvalue.lineno)
        rvalue = self.visit(ctx.expression())
        rvalue = Rvalue(rvalue, lineno=rvalue.lineno)
        rdelay = self.visit(ctx.delay_or_event_control()) if ctx.delay_or_event_control() else None
        ast = NonblockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=rdelay, lineno=lineno)
        return ast

    def visitBlocking_assignment(self, ctx):
        if ctx.operator_assignment():
            return self.visit(ctx.operator_assignment())
        lineno = ctx.start.line
        lvalue = self.visit(ctx.variable_lvalue())
        lvalue = Lvalue(lvalue, lineno=lvalue.lineno)
        rvalue = self.visit(ctx.expression())
        rvalue = Rvalue(rvalue, lineno=rvalue.lineno)
        rdelay = self.visit(ctx.delay_or_event_control()) if ctx.delay_or_event_control() else None
        ast = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=rdelay, lineno=lineno)
        return ast

    def visitOperator_assignment(self, ctx):
        lineno = ctx.start.line
        lvalue = self.visit(ctx.variable_lvalue())
        rvalue = self.visit(ctx.expression())
        if ctx.assignment_operator().getText() != '=':
            assign_op = self.get_operator(ctx.assignment_operator())
            assign_op_line = ctx.assignment_operator().start.line
            rvalue = assign_op(lvalue, rvalue, lineno=assign_op_line)

        lvalue = Lvalue(lvalue, lineno=lvalue.lineno)
        rvalue = Rvalue(rvalue, lineno=rvalue.lineno)
        ast = BlockingSubstitution(lvalue, rvalue, ldelay=None, rdelay=None, lineno=lineno)
        return ast
    
    def visitContinuous_assign(self, ctx):
        lineno = ctx.start.line
        ldelay = self.visit(ctx.delay_control()) if ctx.delay_control() else None
        lvalue, rvalue = self.visit(ctx.list_of_variable_assignments())
        ast = Assign(lvalue, rvalue, ldelay=ldelay, rdelay=None, lineno=lineno)
        return ast

    def visitVariable_assignment(self, ctx):
        lineno = ctx.start.line
        lvalue = self.visit(ctx.variable_lvalue())
        lvalue = Lvalue(lvalue, lineno=lvalue.lineno)
        rvalue = self.visit(ctx.expression())
        rvalue = Rvalue(rvalue, lineno=rvalue.lineno)
        return lvalue, rvalue