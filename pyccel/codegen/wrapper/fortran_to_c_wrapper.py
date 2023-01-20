# coding: utf-8
#------------------------------------------------------------------------------------------#
# This file is part of Pyccel which is released under MIT License. See the LICENSE file or #
# go to https://github.com/pyccel/pyccel/blob/master/LICENSE for full license details.     #
#------------------------------------------------------------------------------------------#
from pyccel.ast.bind_c import BindCFunctionDefArgument, BindCFunctionDefResult
from pyccel.ast.bind_c import BindCPointer, BindCFunctionDef, C_F_Pointer
from pyccel.ast.core import Module, Assign, FunctionCall, FunctionDefArgument
from pyccel.ast.internals import Slice
from pyccel.ast.literals import LiteralInteger, Nil
from pyccel.ast.variable import Variable, IndexedElement
from pyccel.parser.scope import Scope
from .wrapper import Wrapper

class FortranToCWrapper(Wrapper):

    def _get_function_def_body(self, func, func_def_args, func_arg_to_call_arg, results):
        """ Get the body of the function definition by inserting if blocks
        to check the presence of optional variables

        Arguments
        ---------
        func_def_args : list of FunctionDefArguments
                The arguments received by the function
        func_arg_to_call_arg : dict
                A dictionary mapping the arguments received by the function to the arguments
                to be passed to the function call
        results : list of Variables
                The Variables where the result of the function call will be saved
        """
        optional = next((a for a in func_def_args if a.var.is_optional), None)
        if optional:
            args = func_def_args.copy()
            true_section = IfSection(PyccelIsNot(optional, Nil()),
                                    self._get_function_def_body(func, args, func_arg_to_call_arg, results))
            args.remove(optional)
            false_section = IfSection(LiteralTrue(),
                                    self._get_function_def_body(func, args, func_arg_to_call_arg, results))
            return If(true_section, false_section)
        else:
            args = [func_arg_to_call_arg[fa] for fa in func_def_args]
            body = [C_F_Pointer(fa.var, func_arg_to_call_arg[fa], fa.sizes)
                    for fa in func_def_args if isinstance(func_arg_to_call_arg[fa], IndexedElement)]
            return body + [Assign(results, FunctionCall(func, args))]

    def _get_call_argument(self, original_arg, bind_c_arg):
        if original_arg.is_ndarray:
            new_var = original_arg.clone(self.scope.get_new_name(original_arg.name), is_argument = False, is_optional = False)
            self.scope.insert_variable(new_var)
            start = LiteralInteger(0)
            stop = None
            indexes = [Slice(start, stop, step) for step in bind_c_arg.strides]
            return IndexedElement(new_var, *indexes)
        else:
            return bind_c_arg.var

    def _wrap_Module(self, expr):
        # Define scope
        scope = expr.scope
        mod_scope = Scope(used_symbols = scope.local_used_symbols.copy())
        self.set_scope(mod_scope)

        # Wrap contents
        funcs = [self._wrap(f) for f in expr.funcs if not f.is_private]
        interfaces = [self._wrap(f) for f in expr.interfaces]
        classes = [self._wrap(f) for f in expr.classes]
        variable_getters = [self._wrap(f) for v in expr.variables if not v.is_private]
        init_func = self._wrap(expr.init_func) if expr.init_func else None
        free_func = self._wrap(expr.free_func) if expr.free_func else None

        name = mod_scope.get_new_name(f'bind_c_{expr.name}')

        return Module(name, (), funcs + variable_getters,
                init_func = init_func, free_func = free_func, 
                interfaces = interfaces, classes = classes,
                scope = mod_scope)

    def _wrap_FunctionDef(self, expr):
        name = self.scope.get_new_name(f'bind_c_{expr.name}')
        func_scope = self.scope.new_child_scope(name)
        self.set_scope(func_scope)

        func_arguments = [self._wrap_FunctionDefArgument(a) for a in expr.arguments]
        original_arguments = [a.var for a in expr.arguments]
        call_arguments = [self._get_call_argument(oa, fa) for oa, fa in zip(original_arguments, func_arguments)]
        func_to_call = {fa : ca for ca, fa in zip(call_arguments, func_arguments)}

        results = [r.clone(self.scope.get_new_name(r.name)) for r in expr.results]
        func_results = [BindCFunctionDefResult(r, func_scope) for r in expr.results]

        body = self._get_function_def_body(expr, func_arguments, func_to_call, results)

        return BindCFunctionDef(name, func_arguments, func_results, body, scope=func_scope, original_function = expr)

    def _wrap_FunctionDefArgument(self, expr):
        var = expr.var
        if var.is_ndarray:
            new_var = Variable(BindCPointer(), self.scope.get_new_name(var.name),
                                memory_handling='alias', is_argument = True, is_optional = var.is_optional)
            return BindCFunctionDefArgument(new_var, value = expr.value, rank = var.rank,
                    kwonly = expr.is_kwonly, annotation = expr.annotation, scope = self.scope)
        else:
            new_var = var.clone(self.scope.get_new_name(expr.name))
            return FunctionDefArgument(new_var, value = expr.value,
                    kwonly = expr.is_kwonly, annotation = expr.annotation)
