import os
import sys

from ast import parse
from inspect import trace
from locale import getlocale
from os import environ
from time import sleep
from textwrap import dedent
from termcolor import cprint, colored
from pycodestyle import Checker


debug = environ.get("CL_DEBUG", "0") == "1"


class Printer:
    def __init__(self, margin=None, **kwargs):
        self.kwargs = kwargs
        self.margin = margin

    def __call__(self, *args, sep=" ", end="\n"):
        if self.margin in ("mt", "m"):
            print()
        print(self.get(*args, sep=sep), end=end, flush=True)
        if self.margin in ("mb", "m"):
            print()

    def get(self, *args, sep=" "):
        return colored(sep.join(map(str, args)), **self.kwargs)

    def __getattr__(self, name):
        if name in (
            "m",
            "mb",
            "mt",
        ):
            return Printer(**self.kwargs, margin=name)

        if name == "b":
            return Printer(attrs=["bold"], margin=self.margin, **self.kwargs)

        if name.startswith("on_"):
            return Printer(on_color=name, margin=self.margin, **self.kwargs)

        return Printer(color=name, margin=self.margin, **self.kwargs)


_locale = getlocale()[0]

lang = _locale[:2] if _locale else "en"

def _(en, pl):
    if lang == 'pl':
        return pl
    return en


p = Printer()


class CodersLabException(Exception):
    def __init__(self, text):
        super().__init__(dedent(str(text)))


class CodersLabTestSuite:
    _ast_cached = None
    _code_cached = None

    def __init__(self, title, path=None):
        self._title = title
        self._path = path or os.path.join(
            os.path.dirname(sys.argv[0]),
            "task.py",
        )
        self._tests = []

    def test(self, title, *, aborts=False, mandatory=True, points=1, params=None):
        """Parameterized decorator to collect test cases.

        :param str title: Test case name. Can contain {param_name}
        :param bool aborts: Do not run further tests if this test fails
        :param bool mandatory: This is required to pass the task
        :param int points: How many points for this case
        :param list params: List of dicts: params to be passed to the test case
        """

        def decorator(func):
            self._tests.append(
                {
                    "func": func,
                    "title": title,
                    "aborts": aborts,
                    "mandatory": mandatory,
                    "points": points,
                    "params": params or ({},),
                }
            )
            return func

        return decorator

    @property
    def _ast(self):
        if not self._ast_cached:
            with open(self._path, "r") as task:
                self._ast_cached = parse(task.read())
        return self._ast_cached

    @property
    def _code(self):
        if not self._code_cached:
            self._code_cached = compile(self._ast, self._path, "exec")
        return self._code_cached

    def _get_invoker(self):
        stdin = []
        stdout = []
        history = []

        def capturing_print(*args, sep=" ", end="\n"):
            text = sep.join(str(arg) for arg in args) + end
            history.append({"text": text, "stream": "stdout"})
            stdout.append(text)

        def predefined_input(prompt=""):
            history.append({"text": prompt, "stream": "stdout"})
            stdout.append(prompt)
            try:
                history.append({"text": stdin[0] + "\n", "stream": "stdin"})
                return stdin.pop(0)
            except IndexError:
                raise CodersLabException(INPUT_CALLED_TOO_MANY_TIMES)

        def invoke():
            namespace = {
                "print": capturing_print,
                "input": predefined_input,
            }
            exec(self._code, namespace)
            return namespace

        return invoke, stdin, stdout, history

    def _run_tests(self):
        for test in self._tests:
            for params in test["params"]:
                invoke, stdin, stdout, history = self._get_invoker()
                try:
                    test["func"](
                        ast=self._ast,
                        invoke=invoke,
                        stdin=stdin,
                        stdout=stdout,
                        history=history,
                        **params
                    )

                except CodersLabException as exc:
                    if debug:
                        raise
                    yield {
                        "outcome": "fail",
                        "title": test["title"].format(**params),
                        "reason": str(exc),
                        "mandatory": test["mandatory"],
                    }
                    if test["aborts"]:
                        return

                except Exception as exc:
                    if debug:
                        raise
                    yield {
                        "outcome": "error",
                        "title": test["title"].format(**params),
                        "reason": self._get_reason(exc, trace()[-1][2]),
                        "mandatory": test["mandatory"],
                    }
                    if test["aborts"]:
                        return

                else:
                    yield {
                        "outcome": "pass",
                        "title": test["title"].format(**params),
                        "points": test["points"],
                        "mandatory": test["mandatory"],
                    }

    def _get_reason(self, exc, lineno):
        if type(exc) == IndexError:
            return dedent(str(EXPLANATIONS[IndexError]).format(
                lineno=p.b.get(lineno),
            ))
        if type(exc) == TypeError:
            return dedent(str(EXPLANATIONS[TypeError]).format(
                lineno=p.b.get(lineno),
            ))
        if type(exc) == NameError:
            return dedent(str(EXPLANATIONS[NameError]).format(
                lineno=p.b.get(lineno),
                name=p.b.get(str(exc).split()[1].strip("'")),
            ))
        if type(exc) == AttributeError:
            return dedent(str(EXPLANATIONS[AttributeError]).format(
                lineno=p.b.get(lineno),
                name=p.b.get(str(exc).split()[-1].strip("'")),
            ))
        return _(
            pl="B????d {} w linii {}",
            en="Error {} on line {}",
        ).format(repr(exc), lineno)

    def run(self):
        p.m.b.blue(CHECKING_TASK, self._title)

        try:
            self._ast
        except SyntaxError as exc:
            p.yellow(SYNTAX_ERROR.format(exc.lineno))

            p.mt.b.blue("{} | ".format(exc.lineno).rjust(8), end="")
            p.red(exc.text.rstrip())
            p.mb.red("        {}^".format(" " * exc.offset))
            if debug:
                raise
            return

        passed = True
        for test in self._run_tests():
            if test["outcome"] == "pass":
                p.mb.green(
                    "[{}: {}]".format(
                        MANDATORY if test["mandatory"] else OPTIONAL, OK
                    ).ljust(20),
                    test["title"],
                )

            elif test["outcome"] in (
                "fail",
                "error",
            ):
                if test["mandatory"]:
                    p.b.red(
                        "[{}: {}]".format(MANDATORY, FAILED).ljust(20), test["title"]
                    )
                else:
                    p.b.yellow(
                        "[{}: {}]".format(OPTIONAL, FAILED).ljust(20), test["title"]
                    )
                p.mb(test["reason"].strip())

                if test["mandatory"]:
                    passed = False

        p.mb.b.blue(SUMMARY)

        if passed:
            p.m.b.blue(CHECKING_STYLE)
            if Checker(filename=self._path).check_all():
                p.m.b.yellow(STYLE_ERRORS)
            else:
                p(STYLE_OK)
                p.m.b.green(TASK_PASSED)
        else:
            p.m.b.yellow(TASK_FAILED)

    def assert_print_called(self, stdout):
        if not stdout:
            raise CodersLabException(PRINT_NOT_USED)


EXPLANATIONS = {
    NameError: _(
        pl=dedent(
            """
        W linii {lineno} Python pr??bowa?? odczyta?? zmienn?? {name} kt??ra
        prawdopodobnie jeszcze nie istnia??a. Sprawd??, czy na pewno jest
        utworzona wcze??niej i czy w jej nazwie nie ma liter??wek.
        """
        ),
        en=dedent(
            """
        Python tried to read the variable {name} on line {lineno}, that
        probably has not been created yet. Check if it has been created before
        and if there are no typos.
        """
        ),
    ),
    AttributeError: _(
        pl=dedent(
            """
        W linii {lineno} Python pr??bowa?? odczyta?? atrybut {name} z warto??ci,
        kt??ra takiego atrybutu nie posiada.
        """
        ),
        en=dedent(
            """
        Python tried to read the attribute {name} on line {lineno} from an
        object that does not possess such attribute.
        """
        ),
    ),
    TypeError: _(
        pl=dedent(
            """
        W linii {lineno} Python pr??bowa?? wykona?? operacj??, kt??ra dla tych typ??w
        danych jest niedozwolona.
        """
        ),
        en=dedent(
            """
        On line {lineno} Python tried to execute an operation that is not
        allowed for those types of data.
        """
        ),
    ),
    IndexError: _(
        pl=dedent(
            """
        W linii {lineno} Python pr??bowa?? odczyta?? dane z listy spod indeksu,
        kt??ry w tej li??cie nie istnieje - lista jest za kr??tka.
        """
        ),
        en=dedent(
            """
        On line {lineno} Python tried to read some data from a list under
        an index that does not exist in that list - the list is too short.
        """
        ),
    ),
}

INPUT_CALLED_TOO_MANY_TIMES = _(
    pl="Tw??j skrypt u??y?? funkcji " + p.b.get("input()") + " za du??o razy!",
    en="Your script has used the " + p.b.get("input()") + " too many times!",
)

CHECKING_TASK = _(pl="Sprawdzanie zadania:", en="Checking task:")

SYNTAX_ERROR = _(
    pl=dedent(
        """
    Wygl??da na to, ??e masz w kodzie b????d sk??adni, kt??ry
    kompletnie powstrzymuje Pythona przed uruchomieniem
    Twojego kodu. Python zg??asza b????d w linii {}:
    """
    ),
    en=dedent(
        """
    Looks like your code has a syntax error, that prevents Python
    from running your code. Python reports errors on line: {}:
    """
    ),
)

MANDATORY = _(pl="WYMAGANE", en="MANDATORY")

OPTIONAL = _(pl="DODATKOWE", en="OPTIONAL")

OK = _(pl="OK", en="OK")

FAILED = _(pl="B????D", en="FAILED")

SUMMARY = _(pl="===== PODSUMOWANIE =====", en="===== SUMMARY =====")

SCORE = _(pl="Masz {} punkt??w na {} mo??liwych", en="You scored {} out of {}")

TASK_PASSED = _(pl="Gratulacje! Zadanie zaliczone!", en="Congratulations! Task passed!")

TASK_FAILED = _(
    pl=dedent(
        """
    Niestety, zadanie nie jest jeszcze zaliczone.
    Przeczytaj podpowiedzi powy??ej i popraw swoje rozwi??zanie,
    a w razie potrzeby, popro?? mentora o pomoc.
    """
    ),
    en=dedent(
        """
    Unfortunately, this task is not passed yet.
    Read the hints above and improve your solution,
    and don't hesistate to ask your mentor for help!
    """
    ),
)

CHECKING_STYLE = _(
    pl="===== SPRAWDZANE ZGODNO??CI Z PEP8 (STYL KODU) =====",
    en="===== CHECKING CONFORMANCE WITH PEP8 (CODE STYLE) =====",
)

STYLE_OK = _(pl="Brak b????d??w zwi??zanych ze stylem.", en="No code style errors.")

STYLE_ERRORS = _(
    pl=dedent(
        """
    Wygl??da na to, ??e Tw??j kod nie przestrzega zalece?? co do stylistyki.
    Lista powy??ej wskazuje co nale??y poprawi?? oraz w kt??rej linii.

    Popraw wskazane b????dy i uruchom testy ponownie.
    """
    ),
    en=dedent(
        """
    It looks like your code has some style error.
    The list above shows them together with the number of line they appeared.

    Correct those mistakes and run those tests again.
    """
    ),
)

USE_CHECK_PY = _(
    pl=dedent(
        """
    Tego pliku nie nale??y uruchamia?? bezpo??rednio - on istnieje tylko po to,
    aby zadania mog??y by?? testowane automatycznie.

    Przy ka??dym zadaniu (czyli pliku "task.py") znajdziesz plik "check.py".
    Uruchom "check.py":
        korzystaj??c z Pythona w konsoli:
            - u??ywaj??c komendy "cd nazwa-folderu" przejd?? do folderu z zadaniem
            - u??yj komendy "python3 check.py" aby sprawdzi?? zadanie
            zawsze mo??esz sprawdzi?? gdzie jeste?? u??ywaj??c komendy "pwd",
            oraz jakie pliki i foldery s?? w tym miejscu dost??pne, u??ywaj??c "ls"

        korzystaj??c z PyCharm:
            - znajd?? zadanie ("task.py") w drzewie plik??w i folder??w
            - obok znajdziesz "check.py" - kliknij go prawym i wybierz "Run"
    """
    ),
    en=dedent(
        """
    You are not supposed to run this file on it's own - it exists only so you
    can run automated tests of exercises.

    Next to each task ("task.py") you will find a "check.py" file.
    To run "check.py":
        using Python in a console:
            - go to the directory using "cd name-of-the-directory"
            - use "python3 check.py" to test your solution
            you can always check where you are by using "pwd" command
            and see what files and directories are there using "ls" command

        using PyCharm:
            - find the task ("task.py") in the directory tree on the left side
            - find "check.py" next to it - right-click it and choose "Run"
    """
    ),
)

PRINT_NOT_USED = _(
    pl=dedent(
        """
        Skrypt nie wypisa?? ??adnego tekstu na ekranie.
        Czy funkcja {} zosta??a u??yta?
    """
    ).format(p.b.get("print")),
    en=dedent(
        """
        The script did not write anything on the screen.
        Has function {} been used?
    """
    ).format(p.b.get("print")),
)

if __name__ == "__main__":
    p(USE_CHECK_PY)
