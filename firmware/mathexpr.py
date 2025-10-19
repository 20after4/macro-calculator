from decimal import DecimalNumber
import re
import builtins

try:
    from sys import print_exception
except Exception as e:
    def print_exception(e):
        print(e)

class Token(object):
    type: str
    value: str
    result: int

    def __init__(self, type, value, result=None):
        self.type = type
        self.value = value
        self.result = result

    def final_value(self):
        if self.result is not None:
            return self.result
        return self.value

    def __repr__(self):
        return str(self.final_value())


class Tokenizer:
    code = ""
    WHITESPACE = re.compile(r"^\s+")
    NUMBER = re.compile(r'^(\d+(\.\d*)?)')
    GRPSTART = re.compile(r'^\(')
    GRPEND = re.compile(r'^\)')
    IDENTIFIER = re.compile(r'^([A-Za-z]+[A-Za-z0-9]*)')
    OPERATOR = re.compile(r'^[+\-*/]')

    def __init__(self):
        pass

    def match(self):
        if self.code == "":
            return None
        for kind in ('WHITESPACE', 'GRPSTART', 'GRPEND', 'NUMBER', 'OPERATOR', 'IDENTIFIER'):
            regex = getattr(self, kind)
            match = regex.match(self.code)
            if match:
                self.code = self.code[match.end():]
                return (kind, match.group(0))
        return None

    def tokenize(self, code):
        #tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        self.code = code

        stack = []
        group = []

        while True:
            mo = self.match()
            if mo is None:
                break

            kind = mo[0]
            value = mo[1]

            if kind == 'NUMBER':
                value = DecimalNumber(value)
            elif kind == 'GRPSTART':
                stack.append(group)
                group = []
                continue
            elif kind == 'GRPEND':
                group_token = Token('list',group)
                group = stack.pop()
                group.append(group_token)
                continue
            elif kind == 'WHITESPACE':
                continue

            tok = Token(kind, value)
            group.append(tok)

        if len(stack) > 0:
            raise RuntimeError('Unclosed parenthesis')

        return group

tokenizer = Tokenizer()


def evaluate(expr):
    stack = []
    out = []
    g = globals()
    tokens = tokenizer.tokenize(expr)
    print('tokens', tokens)
    while len(tokens) > 0:
        t = tokens.pop(0)
        identifier = t.value
        if t.type == "IDENTIFIER":
            global_value = g[identifier]
            if callable(global_value):
                fn = global_value
                arg = tokens.pop(0)
                args = [to.value for to in arg.value]
                res = fn(*args)
                t.result = res
                print('args', args, 'result', res)
                out.append(t.final_value())
            elif str(global_value).isdigit():
                out.append( DecimalNumber(str(global_value)) )
            else:
                raise RuntimeError('Unknown identifier')
        else:
            out.append(t.value)


    eval_str = ""
    for i in out:
        if type(i) == str:
            eval_str = eval_str + i
        else:
            eval_str = eval_str + repr(i)
    print('eval:', eval_str)
    return eval(eval_str)

class Interpreter:
    lines = []
    stack = []

    def show_err(self, msg):
        print("show_err",msg)

    def func(self, name):
        builtin = getattr(builtins, name, None)
        if builtin:
            return builtin
        return getattr(self, "_"+name, None)


    def numformat(self, num):
        if type(num) is DecimalNumber:
            return num.to_string_max_length(16)
        else:
            return "{: 16.10g}".format(num)

    def tokenize(self, text):
        return tok.match(text)


    def exec(self, input):

        global M1, M2, M3, M4
        lines = len(self.lines)
        stack = self.stack
        try:
            orig_expr = input
            expr = self.tokenize(orig_expr)
            out = []
            groups = None
            if expr:
                groups = expr.groups()
            if not groups:
                groups = [orig_expr]
            i=0
            tokens = len(groups)
            print(groups)
            for group in groups:
                if group is None or group == " ":
                    continue
                print("group:" + str(group))
                f = self.func(group)
                if f is not None:
                    #stack.append(f)
                    stack.append(out)
                    out = []
                    stack.append((f, out))
                elif group == ")":
                    f, arg = stack.pop()
                    arg = str("".join(arg))
                    try:
                        res = f(eval(arg))
                        print('sub_expr:',res)
                        out.append(res)
                    except Exception as e:
                        show_err(e)
                elif group == "=":
                    out.append("=")
                elif group.isdigit():
                    out.append('DecimalNumber("'+group+'")')
                elif group in ("==", "//", "**", "<", ">", "<=", ">=", "!="):
                    if i > 0 and tokens > 2:
                        out.append(group)
                    else:
                        raise Exception("Invalid boolean Expression.")
                elif group[0] == "M" and group[1].isdigit():
                    out.append(group)
                elif group[0] in ("+","/","*","-"):
                    out.append(group)
                else:
                    raise Exception("["+str(i)+"] syntax err: \""+group+"\" " + "".join(groups))
                i = i + 1


            "".join(out)
            if (expr == "" or expr[0] in ("+","/","*","-")):
                expr = "M1" + expr
            expr = "("+expr+")"
            res = None
            try:
                res = eval(str(expr))
            except Exception as e:
                print("Err in expression:",str(expr),e)
            if type(res) is float:
                res = DecimalNumber(str(res))
            elif type(res) is not DecimalNumber:
                if type(res) == str and res.isdigit():
                    res = DecimalNumber(res)

            M2 = M1
            M1 = res
            self.hide_err()
            self.lines[lines-4].set_text(numformat(M3))
            self.lines[lines-3].set_text(numformat(M2))
            self.lines[lines-2].set_text(numformat(res))
            self.clear(self.index)
        except Exception as e:
            self.show_err(e)

    def hide_err(self):
        pass

M1 = 0
M2 = 0
M3 = 0
M4 = 0

num_expr = "([0-9]*\.?[0-9]+|M[1-4])?"
oper_expr = ".?([\+\-\*\/\=]).?"
func_expr = "(.?([0-9a-z]+)\(([^\(]+)\).?)*"
tok = re.compile(num_expr+func_expr+oper_expr+num_expr+func_expr)

def test(arg1, arg2):
    print('test', arg1, arg2)
    return arg1 + arg2
